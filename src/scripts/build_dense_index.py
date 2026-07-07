"""
Build Dense Retrieval Index
===========================
One-time script: encodes all 82k Indian court cases in rag_corpus.csv using
InLegalBERT and saves L2-normalised embeddings + corpus metadata.

Usage (from project root):
    python -m src.scripts.build_dense_index

Output (saved to src/data/models/dense/):
    embeddings.npy    -- float32 (N, 768), L2-normalised
    corpus_meta.json  -- [{case_name, case_type, summary, source}, ...]
    index_meta.json   -- build metadata (n_docs, model, embedding_dim)
"""

import os
import sys
import ast
import json
import logging
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
ROOT        = Path(__file__).resolve().parents[2]   # project root
CORPUS_PATH = ROOT / "src" / "data" / "processed" / "rag_corpus.csv"
OUT_DIR     = ROOT / "src" / "data" / "models" / "dense"

MODEL_DIRS = [
    ROOT / "src" / "data" / "models" / "inlegalbert" / "outcome",
    ROOT / "src" / "data" / "models" / "inlegalbert" / "bail",
    ROOT / "src" / "data" / "models" / "inlegalbert" / "fairness",
]
HF_FALLBACK = "law-ai/InLegalBERT"

BATCH_SIZE  = 32
MAX_SEQ_LEN = 256

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


def _mean_pool(last_hidden, attention_mask):
    """Attention-mask-aware mean pooling."""
    mask   = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
    summed = (last_hidden * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


def build_index():
    import torch
    from transformers import BertModel, AutoTokenizer
    from sklearn.preprocessing import normalize

    # ── Load model ─────────────────────────────────────────────────────────────
    model_dir = next((d for d in MODEL_DIRS if d.exists()), None)
    if model_dir:
        logger.info("Loading tokenizer + model from local dir: %s", model_dir)
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        model     = BertModel.from_pretrained(str(model_dir))
    else:
        logger.warning("No local InLegalBERT found — downloading from %s", HF_FALLBACK)
        tokenizer = AutoTokenizer.from_pretrained(HF_FALLBACK)
        model     = BertModel.from_pretrained(HF_FALLBACK)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)
    model.to(device)
    model.eval()

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

        # Prefer summary for embedding (shorter, more semantic), fall back to text
        index_text = raw_summary if len(raw_summary) > 20 else raw_text
        index_text = index_text[:1500].strip() or raw_id

        embed_texts.append(index_text)
        meta.append({
            "case_name": raw_id[:200],
            "case_type": SOURCE_TO_CASE_TYPE.get(source, "Court Case"),
            "summary":   (raw_summary or raw_text)[:600],
            "source":    source,
        })

    n        = len(embed_texts)
    n_batches = (n + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info("Embedding %d documents in %d batches (batch_size=%d)", n, n_batches, BATCH_SIZE)

    # ── Embed ──────────────────────────────────────────────────────────────────
    all_vecs = []

    with torch.no_grad():
        for b in range(n_batches):
            start       = b * BATCH_SIZE
            end         = min(start + BATCH_SIZE, n)
            batch_texts = embed_texts[start:end]

            enc = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=MAX_SEQ_LEN,
                return_tensors="pt",
            )
            input_ids      = enc["input_ids"].to(device)
            attention_mask = enc["attention_mask"].to(device)
            token_type_ids = enc.get("token_type_ids")
            if token_type_ids is not None:
                token_type_ids = token_type_ids.to(device)

            out    = model(input_ids=input_ids, attention_mask=attention_mask,
                           token_type_ids=token_type_ids)
            pooled = _mean_pool(out.last_hidden_state, attention_mask)
            all_vecs.append(pooled.cpu().numpy().astype(np.float32))

            if (b + 1) % 100 == 0 or b == n_batches - 1:
                pct = (b + 1) / n_batches * 100
                logger.info("  %d/%d docs (%.1f%%)", end, n, pct)

    embeddings = np.vstack(all_vecs)                           # (N, 768)
    embeddings = normalize(embeddings, norm="l2").astype(np.float32)
    logger.info("Embeddings shape: %s", embeddings.shape)

    # ── Save ───────────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    emb_path  = OUT_DIR / "embeddings.npy"
    meta_path = OUT_DIR / "corpus_meta.json"
    idx_path  = OUT_DIR / "index_meta.json"

    np.save(str(emb_path), embeddings)
    logger.info("Saved embeddings  → %s", emb_path)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info("Saved corpus meta → %s", meta_path)

    index_meta = {
        "n_docs":        n,
        "embedding_dim": int(embeddings.shape[1]),
        "model":         str(model_dir) if model_dir else HF_FALLBACK,
        "max_seq_len":   MAX_SEQ_LEN,
        "batch_size":    BATCH_SIZE,
        "normalised":    True,
    }
    with open(idx_path, "w") as f:
        json.dump(index_meta, f, indent=2)
    logger.info("Saved index meta  → %s", idx_path)
    logger.info("Dense index build complete.")


if __name__ == "__main__":
    build_index()
