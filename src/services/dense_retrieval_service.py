"""
Dense Retrieval Service
=======================
Loads the pre-built dense index (embeddings.npy + corpus_meta.json) produced by
src/scripts/build_dense_index.py and performs fast cosine-similarity search via
numpy dot product.

Model: paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers)
  - 384-dim embeddings, L2-normalised at build time
  - Supports 50+ languages including all 10 Indian languages used by this app
  - Dot product over normalised vectors == cosine similarity

Requires: src/scripts/build_dense_index.py to have been run once.
Index dir: src/data/models/dense/
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parents[2]
DENSE_DIR = ROOT / "src" / "data" / "models" / "dense"

MODEL_NAME           = "paraphrase-multilingual-MiniLM-L12-v2"
MAX_CHARS            = 1500
SIMILARITY_THRESHOLD = 0.20


class DenseRetrievalService:
    def __init__(self):
        self._embeddings:  Optional[np.ndarray] = None
        self._corpus_meta: Optional[List[Dict]] = None
        self._model        = None
        self._model_loaded = False
        self._available    = False
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
            self._embeddings = np.load(str(emb_path))
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

    # ── Lazy model loading (on first search call only) ─────────────────────────
    def _ensure_model(self):
        if self._model_loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[Dense] Loading query encoder: %s", MODEL_NAME)
            self._model = SentenceTransformer(MODEL_NAME)
            self._model_loaded = True
            logger.info("[Dense] Query encoder ready (dim=%d)",
                        self._model.get_sentence_embedding_dimension())
        except ImportError:
            logger.error(
                "[Dense] sentence-transformers not installed. "
                "Run: pip install sentence-transformers>=2.7.0"
            )
            self._available = False
        except Exception as exc:
            logger.error("[Dense] Failed to load query encoder: %s", exc)
            self._available = False

    # ── Query embedding ────────────────────────────────────────────────────────
    def _embed_query(self, text: str) -> np.ndarray:
        """Return an L2-normalised embedding for a single query string."""
        self._ensure_model()
        emb = self._model.encode(
            [text[:MAX_CHARS]],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return emb[0].astype(np.float32)

    # ── Public interface ───────────────────────────────────────────────────────
    @property
    def available(self) -> bool:
        return self._available

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Find top-K most similar cases using dense cosine similarity.

        Supports cross-lingual queries: a query in Hindi/Tamil/etc. will still
        retrieve relevant English court cases because the multilingual model maps
        all languages into the same embedding space.

        Args:
            query:  Legal question text (any supported language).
            top_k:  Maximum number of results to return.

        Returns:
            List of dicts: [{case_name, case_type, summary, similarity}]
            Empty list if the index is unavailable or query embedding fails.

        Note: 91% of corpus records (jud_ipl + ildc sources) have summary='nan'
        because the original CSV had no summary column for those sources.  Only
        il_tur_summ (~7k records) has real summaries.  We scan a wider candidate
        pool (top_k * 50) and return only records with usable summaries so that
        the LLM enrichment step always gets real legal text to work with.
        """
        if not self._available:
            return []

        try:
            query_vec = self._embed_query(query)       # (384,)
            scores    = self._embeddings @ query_vec   # (N,)

            # Scan a wide candidate pool so we can filter out nan-summary records
            # and still return up to top_k results with real content.
            search_k = min(top_k * 50, len(self._corpus_meta))
            top_idx  = np.argsort(scores)[::-1][:search_k]

            results = []
            for idx in top_idx:
                sim = float(scores[idx])
                if sim < SIMILARITY_THRESHOLD:
                    break
                m       = self._corpus_meta[idx]
                summary = str(m.get("summary", "") or "").strip()

                # Skip records whose summary is a placeholder — jud_ipl and ildc
                # sources stored "nan" (pandas NaN → str) because the source CSV
                # had no summary column for those rows.
                if not summary or summary.lower() in ("nan", "none") or len(summary) < 50:
                    continue

                results.append({
                    "case_name":  m.get("case_name", "Unknown"),
                    "case_type":  m.get("case_type", "Court Case"),
                    "summary":    summary,
                    "outcome":    m.get("outcome",   ""),
                    "similarity": round(sim, 4),
                })
                if len(results) >= top_k:
                    break

            logger.debug(
                "[Dense] Query → %d results with usable summaries (top_sim=%.3f)",
                len(results), results[0]["similarity"] if results else 0.0,
            )
            return results

        except Exception as exc:
            logger.error("[Dense] Search failed: %s", exc, exc_info=True)
            return []


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[DenseRetrievalService] = None


def get_dense_retrieval_service() -> DenseRetrievalService:
    global _instance
    if _instance is None:
        _instance = DenseRetrievalService()
    return _instance
