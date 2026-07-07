"""
Dense Retrieval Service
=======================
Loads the pre-built InLegalBERT dense index (embeddings.npy + corpus_meta.json)
and performs fast cosine-similarity search via numpy dot product.

All stored embeddings are L2-normalised at build time, so dot product == cosine
similarity without any per-query normalisation of the corpus matrix.

Requires: src/scripts/build_dense_index.py to have been run once.
Index dir: src/data/models/dense/
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parents[2]
DENSE_DIR = ROOT / "src" / "data" / "models" / "dense"

MODEL_DIRS = [
    ROOT / "src" / "data" / "models" / "inlegalbert" / "outcome",
    ROOT / "src" / "data" / "models" / "inlegalbert" / "bail",
    ROOT / "src" / "data" / "models" / "inlegalbert" / "fairness",
]
HF_FALLBACK         = "law-ai/InLegalBERT"
MAX_SEQ_LEN         = 256
SIMILARITY_THRESHOLD = 0.20    # only return results at or above this cosine score


class DenseRetrievalService:
    def __init__(self):
        self._embeddings:   Optional[np.ndarray] = None
        self._corpus_meta:  Optional[List[Dict]] = None
        self._tokenizer     = None
        self._model         = None
        self._device        = None
        self._model_loaded  = False
        self._available     = False
        self._load_index()

    # ── Index loading (called once at startup) ─────────────────────────────────
    def _load_index(self):
        emb_path  = DENSE_DIR / "embeddings.npy"
        meta_path = DENSE_DIR / "corpus_meta.json"

        if not emb_path.exists() or not meta_path.exists():
            logger.info(
                "[Dense] Index not found at %s — run "
                "src/scripts/build_dense_index.py to build it. "
                "Dense retrieval will be skipped until then.",
                DENSE_DIR,
            )
            return

        try:
            self._embeddings = np.load(str(emb_path))   # (N, 768), float32
            with open(meta_path, "r", encoding="utf-8") as f:
                self._corpus_meta = json.load(f)

            n_emb  = len(self._embeddings)
            n_meta = len(self._corpus_meta)
            if n_emb != n_meta:
                raise ValueError(
                    f"Embedding rows ({n_emb}) != metadata rows ({n_meta})"
                )

            logger.info(
                "[Dense] Index loaded — %s docs, dim=%d",
                f"{n_emb:,}", self._embeddings.shape[1],
            )
            self._available = True

        except Exception as exc:
            logger.error("[Dense] Failed to load index: %s", exc)

    # ── Lazy model loading (on first search call) ──────────────────────────────
    def _ensure_model(self):
        if self._model_loaded:
            return

        import torch
        from transformers import AutoTokenizer, BertModel

        model_dir = next((d for d in MODEL_DIRS if d.exists()), None)
        if model_dir:
            logger.info("[Dense] Loading encoder from %s", model_dir)
            self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            self._model     = BertModel.from_pretrained(str(model_dir))
        else:
            logger.warning("[Dense] No local model — downloading %s", HF_FALLBACK)
            self._tokenizer = AutoTokenizer.from_pretrained(HF_FALLBACK)
            self._model     = BertModel.from_pretrained(HF_FALLBACK)

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        self._model.eval()
        self._model_loaded = True
        logger.info("[Dense] Encoder ready on %s", self._device)

    # ── Query embedding ────────────────────────────────────────────────────────
    def _embed_query(self, text: str) -> np.ndarray:
        """Return an L2-normalised (768,) embedding for a single query string."""
        import torch

        self._ensure_model()

        enc = self._tokenizer(
            text[:1500],
            padding=True,
            truncation=True,
            max_length=MAX_SEQ_LEN,
            return_tensors="pt",
        )
        input_ids      = enc["input_ids"].to(self._device)
        attention_mask = enc["attention_mask"].to(self._device)
        token_type_ids = enc.get("token_type_ids")
        if token_type_ids is not None:
            token_type_ids = token_type_ids.to(self._device)

        with torch.no_grad():
            out  = self._model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
            )
            # Attention-mask-aware mean pool
            mask   = attention_mask.unsqueeze(-1).expand(out.last_hidden_state.size()).float()
            summed = (out.last_hidden_state * mask).sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1e-9)
            pooled = (summed / counts).cpu().numpy().astype(np.float32)

        return normalize(pooled, norm="l2")[0]   # (768,)

    # ── Public interface ───────────────────────────────────────────────────────
    @property
    def available(self) -> bool:
        return self._available

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Find top-K most similar cases using dense cosine similarity.

        Args:
            query:  Legal question text.
            top_k:  Maximum number of results to return.

        Returns:
            List of dicts: [{case_name, case_type, summary, outcome, similarity}]
            Empty list if the index is unavailable or query embedding fails.
        """
        if not self._available:
            return []

        try:
            query_vec = self._embed_query(query)     # (768,)
            scores    = self._embeddings @ query_vec  # (N,)

            top_idx = np.argsort(scores)[::-1][:top_k]
            results = []
            for idx in top_idx:
                sim = float(scores[idx])
                if sim < SIMILARITY_THRESHOLD:
                    break
                m = self._corpus_meta[idx]
                results.append({
                    "case_name":  m.get("case_name", "Unknown"),
                    "case_type":  m.get("case_type", "Court Case"),
                    "summary":    m.get("summary",   ""),
                    "outcome":    m.get("outcome",   ""),
                    "similarity": round(sim, 4),
                })

            logger.debug(
                "[Dense] Query → %d results (top_sim=%.3f)",
                len(results), results[0]["similarity"] if results else 0.0,
            )
            return results

        except Exception as exc:
            logger.error("[Dense] Search failed: %s", exc, exc_info=True)
            return []


# ─── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[DenseRetrievalService] = None


def get_dense_retrieval_service() -> DenseRetrievalService:
    global _instance
    if _instance is None:
        _instance = DenseRetrievalService()
    return _instance
