"""
Precedent Service — TF-IDF + SVD Semantic Search
=================================================
Loads the pre-built TF-IDF/SVD index over 82k Indian court cases and
provides fast cosine-similarity search.

Index is built by: src/scripts/build_precedent_index.py
Index location:    src/data/mediation_training/models/precedent_index.pkl
"""

import os
import pickle
import logging
import numpy as np
from typing import List, Optional, Dict, Any
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

_INDEX_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "data", "models", "precedent", "precedent_index.pkl"
    )
)


class PrecedentService:
    def __init__(self):
        self._index:      Optional[Dict[str, Any]] = None
        self._vectorizer  = None
        self._svd         = None
        self._embeddings: Optional[np.ndarray] = None
        self._available   = False
        self._load()

    def _load(self):
        if not os.path.exists(_INDEX_PATH):
            logger.warning(
                "[Precedent] Index not found at %s — run "
                "src/scripts/build_precedent_index.py to create it. "
                "similar_precedents will be empty until then.",
                _INDEX_PATH,
            )
            return
        try:
            with open(_INDEX_PATH, "rb") as f:
                self._index = pickle.load(f)

            self._vectorizer  = self._index["vectorizer"]
            self._svd         = self._index["svd"]
            self._embeddings  = self._index["embeddings"]   # (N, SVD_DIMS), float32, L2-normed

            n = self._index.get("n_cases", 0)
            model = self._index.get("model", "unknown")
            logger.info("[Precedent] Index loaded — %s cases, model=%s", f"{n:,}", model)
            self._available = True
        except Exception as e:
            logger.error("[Precedent] Failed to load index: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    def _embed(self, text: str) -> np.ndarray:
        """
        Convert a query string to an L2-normalised (SVD_DIMS,) dense vector
        using the same TF-IDF → SVD pipeline used to build the index.
        """
        tfidf_vec = self._vectorizer.transform([text[:3000]])
        svd_vec   = self._svd.transform(tfidf_vec).astype(np.float32)
        normed    = normalize(svd_vec, norm="l2")
        return normed[0]   # (SVD_DIMS,)

    def search(
        self,
        query: str,
        case_type_filter: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find the top-K most similar precedent cases for a query string.

        Args:
            query:            Dispute description or case summary text.
            case_type_filter: Optional category to boost (e.g. "IPL Case").
                              Matching cases get a 10% score boost.
            top_k:            Number of results to return.

        Returns:
            List of dicts: [{case_name, case_type, summary, outcome, similarity}]
            Empty list if the index is not available.
        """
        if not self._available:
            return []

        try:
            query_vec = self._embed(query)                     # (SVD_DIMS,)
            scores    = self._embeddings @ query_vec           # (N,) cosine similarity

            if case_type_filter:
                for i, c in enumerate(self._index["corpus"]):
                    if c.get("case_type", "").lower() == case_type_filter.lower():
                        scores[i] = min(float(scores[i]) * 1.10, 1.0)

            top_indices = np.argsort(scores)[::-1][:top_k]
            corpus      = self._index["corpus"]

            results = []
            for idx in top_indices:
                c = corpus[idx]
                results.append({
                    "case_name":  c.get("case_name",  "Unknown"),
                    "case_type":  c.get("case_type",  "Unknown"),
                    "summary":    c.get("summary",    ""),
                    "outcome":    c.get("outcome",    ""),
                    "similarity": round(float(scores[idx]), 4),
                })

            if results:
                logger.debug(
                    "[Precedent] Query returned %d results (top_sim=%.3f)",
                    len(results), results[0]["similarity"]
                )
            return results

        except Exception as e:
            logger.error("[Precedent] Search failed: %s", e, exc_info=True)
            return []

    def format_for_report(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Format search results as human-readable strings for mediation reports.
        """
        formatted = []
        for r in results:
            name    = r.get("case_name", "Unknown case")
            c_type  = r.get("case_type", "")
            outcome = r.get("outcome", "").strip()
            sim     = r.get("similarity", 0.0)

            line = name
            if c_type:
                line += f" [{c_type}]"
            if outcome:
                short = outcome[:120].rstrip()
                if len(outcome) > 120:
                    short += "..."
                line += f" — {short}"
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
