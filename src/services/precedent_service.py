"""
Precedent Service — Semantic Similar-Case Retrieval
=====================================================
Loads the InLegalBERT embedding index built by build_precedent_index.py and
provides fast cosine-similarity search over indexed Indian court cases.

Architecture:
  - Index: pre-computed L2-normalised embeddings (N, 768) stored in a .pkl file
  - Query : embed dispute description → cosine similarity → top-K results
  - Model : law-ai/InLegalBERT (BERT-base trained on Indian legal text)

When the ILDC full dataset (34k+ cases) is added tomorrow:
  1. Run build_precedent_index.py again — it rebuilds the index automatically.
  2. Restart the server — the service reloads from the new index file.
  No code changes needed.
"""

import os
import pickle
import logging
import numpy as np
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

_MODEL_DIR  = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "mediation_training", "models")
)
_INDEX_PATH = os.path.join(_MODEL_DIR, "precedent_index.pkl")

MAX_TOKENS = 512


class PrecedentService:
    """
    Loads the pre-built InLegalBERT precedent index and answers
    nearest-neighbour queries for dispute case descriptions.
    """

    def __init__(self):
        self._index: Optional[Dict[str, Any]] = None
        self._tokenizer = None
        self._model     = None
        self._available = False
        self._load()

    def _load(self):
        if not os.path.exists(_INDEX_PATH):
            logger.warning("[Precedent] Index file not found — similar_precedents will be empty. "
                           "Run build_precedent_index.py to create it.")
            return

        try:
            with open(_INDEX_PATH, "rb") as f:
                self._index = pickle.load(f)

            model_name = self._index.get("model", "law-ai/InLegalBERT")
            logger.info(f"[Precedent] Loading tokenizer/model: {model_name}")

            from transformers import AutoTokenizer, AutoModel
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model     = AutoModel.from_pretrained(model_name)
            self._model.eval()

            n = self._index.get("n_cases", 0)
            logger.info(f"[Precedent] Index loaded — {n} cases, model ready.")
            self._available = True

        except Exception as e:
            logger.error(f"[Precedent] Failed to load index or model: {e}")

    @property
    def available(self) -> bool:
        return self._available

    def _embed(self, text: str) -> np.ndarray:
        """Embed a single text string → L2-normalised (768,) vector."""
        import torch

        encoded = self._tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=MAX_TOKENS,
            return_tensors="pt",
        )
        with torch.no_grad():
            output = self._model(**encoded)

        hidden   = output.last_hidden_state          # (1, T, 768)
        mask     = encoded["attention_mask"]          # (1, T)
        mask_exp = mask.unsqueeze(-1).float()
        pooled   = (hidden * mask_exp).sum(dim=1) / mask_exp.sum(dim=1).clamp(min=1e-9)
        vec      = pooled.squeeze(0).cpu().numpy()   # (768,)
        norm     = np.linalg.norm(vec)
        return vec / max(norm, 1e-9)

    def search(
        self,
        query: str,
        case_type_filter: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find the top-K most similar precedent cases for a query string.

        Args:
            query            : Dispute description or summary text.
            case_type_filter : Optional case category to bias results
                               ("Criminal", "Civil", etc.). If provided,
                               matching cases get a 10% score boost.
            top_k            : Number of results to return.

        Returns:
            List of dicts: [{ case_name, case_type, summary, outcome, similarity }]
            Empty list if the index is not available.
        """
        if not self._available:
            return []

        try:
            query_vec  = self._embed(query)                        # (768,)
            embeddings = self._index["embeddings"]                 # (N, 768)
            scores     = embeddings @ query_vec                    # (N,) cosine similarity

            # Optional category boost
            if case_type_filter:
                for i, c in enumerate(self._index["corpus"]):
                    if c.get("case_type", "").lower() == case_type_filter.lower():
                        scores[i] = min(scores[i] * 1.10, 1.0)

            top_indices = np.argsort(scores)[::-1][:top_k]
            corpus      = self._index["corpus"]

            results = []
            for idx in top_indices:
                c = corpus[idx]
                results.append({
                    "case_name":  c.get("case_name", "Unknown"),
                    "case_type":  c.get("case_type", "Unknown"),
                    "summary":    c.get("summary", ""),
                    "outcome":    c.get("outcome", ""),
                    "similarity": round(float(scores[idx]), 4),
                })

            logger.debug(f"[Precedent] Query returned {len(results)} results "
                         f"(top sim={results[0]['similarity']:.3f} if any)")
            return results

        except Exception as e:
            logger.error(f"[Precedent] Search failed: {e}", exc_info=True)
            return []

    def format_for_report(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Format search results as human-readable strings for the MediationReport
        similar_precedents field.
        """
        formatted = []
        for r in results:
            name     = r.get("case_name", "Unknown case")
            c_type   = r.get("case_type", "")
            outcome  = r.get("outcome", "").strip()
            sim      = r.get("similarity", 0)
            line = f"{name}"
            if c_type:
                line += f" [{c_type}]"
            if outcome:
                short_outcome = outcome[:120].rstrip()
                if len(outcome) > 120:
                    short_outcome += "..."
                line += f" — {short_outcome}"
            line += f" (similarity: {sim:.2f})"
            formatted.append(line)
        return formatted


# ─── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[PrecedentService] = None


def get_precedent_service() -> PrecedentService:
    global _instance
    if _instance is None:
        _instance = PrecedentService()
    return _instance
