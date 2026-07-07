"""
Build Dense Retrieval Index
===========================
One-time script: encodes all 82k Indian court cases in rag_corpus.csv using
paraphrase-multilingual-MiniLM-L12-v2 (via sentence-transformers) and saves
L2-normalised embeddings + corpus metadata.

Why this model:
  - Supports 50+ languages including Hindi, Bengali, Tamil, Telugu, Marathi,
    Gujarati, Kannada, Malayalam, Punjabi — enabling cross-lingual retrieval
    so users asking in Indian languages still find relevant English court cases.
  - 12-layer MiniLM: 4-6x faster on CPU than full BERT, produces 384-dim vectors.

Usage (from project root, after Ctrl+C on any previous run):
    python -m src.scripts.build_dense_index

Output (saved to src/data/models/dense/):
    embeddings.npy    -- float32 (N, 384), L2-normalised
    corpus_meta.json  -- [{case_name, case_type, summary, source}, ...]
    index_meta.json   -- build metadata (n_docs, model, embedding_dim, etc.)
"""

import ast
import json
import logging
import sys
import numpy as np
import pandas as pd
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "src" / "data" / "processed" / "rag_corpus.csv"
OUT_DIR     = ROOT / "src" / "data" / "models" / "dense"

# ── Model config ───────────────────────────────────────────────────────────────
MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE  = 256   # sentence-transformers handles batching + threading internally
MAX_CHARS   = 1500  # truncate each text before encoding

SOURCE_TO_CASE_TYPE = {
    "il_tur_summ": "Turnaround Case",
    "jud_ipl":     "IPL Case",
    "ildc":        "Supreme Court Case",
}


def _parse_list_field(val) -> str:
    """Convert Python list-repr strings (il_tur_summ source) to plain text."""
    if isinstance(val, str) and val.strip().startswith("["):
        try:
            parts = ast.literal_eval(val)
            return " ".join(str(p) for p in parts).strip()
        except Exception:
            pass
    return str(val) if val is not None else ""


def build_index():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error(
            "sentence-transformers is not installed. "
            "Run:  pip install sentence-transformers>=2.7.0"
        )
        sys.exit(1)

    # ── Load model ─────────────────────────────────────────────────────────────
    logger.info("Loading model: %s  (downloads ~280 MB on first run)", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Model loaded — embedding dim: %d", model.get_sentence_embedding_dimension())

    # ── Load corpus ─────────────────────────────────────────────────────────────
    logger.info("Loading corpus from %s", CORPUS_PATH)
    df = pd.read_csv(CORPUS_PATH, low_memory=False)
    logger.info("Corpus: %d rows, columns=%s", len(df), list(df.columns))

    embed_texts = []
    meta        = []

    for _, row in df.iterrows():
        raw_id      = str(row.get("id",      "")).strip()
        raw_text    = _parse_list_field(row.get("text",    ""))
        raw_summary = _parse_list_field(row.get("summary", ""))
        source      = str(row.get("source", "")).strip()

        # Prefer summary (shorter, more semantic), fall back to full text
        index_text = raw_summary if len(raw_summary) > 20 else raw_text
        index_text = index_text[:MAX_CHARS].strip() or raw_id

        embed_texts.append(index_text)
        meta.append({
            "case_name": raw_id[:200],
            "case_type": SOURCE_TO_CASE_TYPE.get(source, "Court Case"),
            "summary":   (raw_summary or raw_text)[:600],
            "source":    source,
        })

    n = len(embed_texts)
    logger.info(
        "Encoding %d documents with %s (batch_size=%d) …",
        n, MODEL_NAME, BATCH_SIZE,
    )
    logger.info("Estimated time: 1-2 hours on CPU. Progress bar below:")

    # ── Encode — sentence-transformers handles batching, threading, normalisation
    embeddings = model.encode(
        embed_texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,   # L2-normalise so dot product == cosine
        convert_to_numpy=True,
    ).astype(np.float32)             # ensure float32 for compact storage

    logger.info("Embeddings shape: %s  dtype: %s", embeddings.shape, embeddings.dtype)

    # ── Save ───────────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    emb_path  = OUT_DIR / "embeddings.npy"
    meta_path = OUT_DIR / "corpus_meta.json"
    idx_path  = OUT_DIR / "index_meta.json"

    np.save(str(emb_path), embeddings)
    logger.info("Saved embeddings  → %s  (%.1f MB)", emb_path,
                emb_path.stat().st_size / 1e6)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info("Saved corpus meta → %s", meta_path)

    index_meta = {
        "n_docs":        n,
        "model":         MODEL_NAME,
        "embedding_dim": int(embeddings.shape[1]),
        "max_chars":     MAX_CHARS,
        "batch_size":    BATCH_SIZE,
        "normalised":    True,
        "library":       "sentence-transformers",
    }
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index_meta, f, indent=2)
    logger.info("Saved index meta  → %s", idx_path)
    logger.info("Dense index build complete.")


if __name__ == "__main__":
    build_index()
