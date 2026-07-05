"""
Precedent Index Builder
=======================
Downloads InLegalBERT (law-ai/InLegalBERT) from HuggingFace and builds
a semantic search index over Indian court judgment cases.

Current corpus  : 247 cases from OpenNyAI InRhetoricalRoles (train.json)
Tomorrow corpus : Full ILDC dataset (34k+ cases) — re-run this script

For each case the script extracts:
  - case_name    : from PREAMBLE sentences
  - case_type    : from meta.group
  - summary      : from FAC (facts) sentences
  - outcome      : from RPC (ruling) sentences
  - embedding    : InLegalBERT mean-pool over first 512 tokens of case text

Index is saved as a .pkl file and loaded at startup by precedent_service.py.

Run from project root:
    python src/data/mediation_training/build_precedent_index.py
"""

import os
import re
import json
import pickle
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
TRAIN_JSON = os.path.join(BASE_DIR, "..", "rhetorical-role-baseline-main", "train.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "models")
INDEX_PATH = os.path.join(OUTPUT_DIR, "precedent_index.pkl")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL_NAME = "law-ai/InLegalBERT"
MAX_TOKENS = 512
BATCH_SIZE = 8


# ─── Corpus extraction ─────────────────────────────────────────────────────────

def _sentences_by_label(annotations):
    result = {}
    for ann in annotations:
        for item in ann.get("result", []):
            text   = item.get("value", {}).get("text", "").strip()
            labels = item.get("value", {}).get("labels", [])
            if not text or not labels:
                continue
            label = labels[0]
            result.setdefault(label, []).append(text)
    return result


def _extract_case_name(preamble_sentences):
    """Pull case title from PREAMBLE — looks for vs/versus pattern."""
    for sent in preamble_sentences:
        if re.search(r"\bvs?\.?\b|\bversus\b", sent, re.IGNORECASE):
            # Remove newlines, collapse whitespace
            name = re.sub(r"\s+", " ", sent.replace("\n", " ")).strip()
            if 10 < len(name) < 300:
                return name
    # Fallback: join first two PREAMBLE sentences
    text = " ".join(preamble_sentences[:2])
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()[:200]


def build_corpus(train_json_path):
    logger.info(f"Loading {train_json_path}")
    with open(train_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"  {len(data)} cases found")

    corpus = []
    for i, case in enumerate(data):
        by_label = _sentences_by_label(case.get("annotations", []))
        meta      = case.get("meta", {})
        full_text = case.get("data", {}).get("text", "")

        case_name  = _extract_case_name(by_label.get("PREAMBLE", []))
        case_type  = meta.get("group", "Unknown")
        facts      = " ".join(by_label.get("FAC", []))[:500]
        ruling     = " ".join(by_label.get("RPC", []))[:300]
        embed_text = full_text[:3000] if full_text else facts  # truncated for embedding

        corpus.append({
            "case_id":    f"rrb_{i:04d}",
            "case_name":  case_name or f"Case {i}",
            "case_type":  case_type,
            "summary":    facts[:300] if facts else "No summary available.",
            "outcome":    ruling[:200] if ruling else "Outcome not extracted.",
            "embed_text": embed_text,
        })

    logger.info(f"Corpus built: {len(corpus)} cases")
    return corpus


# ─── Embedding generation ──────────────────────────────────────────────────────

def get_embeddings(texts, tokenizer, model, batch_size=BATCH_SIZE):
    import torch

    all_embeddings = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        encoded = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=MAX_TOKENS,
            return_tensors="pt",
        )
        with torch.no_grad():
            output = model(**encoded)

        # Mean-pool over non-padding tokens
        hidden   = output.last_hidden_state          # (B, T, 768)
        mask     = encoded["attention_mask"]          # (B, T)
        mask_exp = mask.unsqueeze(-1).float()
        summed   = (hidden * mask_exp).sum(dim=1)
        lengths  = mask_exp.sum(dim=1).clamp(min=1e-9)
        pooled   = (summed / lengths).cpu().numpy()  # (B, 768)
        all_embeddings.append(pooled)

        if (start // batch_size) % 5 == 0:
            logger.info(f"  Embedded {min(start + batch_size, len(texts))}/{len(texts)}")

    return np.vstack(all_embeddings)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    from transformers import AutoTokenizer, AutoModel

    # 1. Build text corpus
    corpus = build_corpus(TRAIN_JSON)

    # 2. Download / load InLegalBERT
    logger.info(f"Loading model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model     = AutoModel.from_pretrained(MODEL_NAME)
    model.eval()
    logger.info("  Model loaded.")

    # 3. Generate embeddings
    texts = [c["embed_text"] for c in corpus]
    logger.info(f"Generating embeddings for {len(texts)} cases (batch={BATCH_SIZE}) ...")
    embeddings = get_embeddings(texts, tokenizer, model, batch_size=BATCH_SIZE)
    logger.info(f"  Embeddings shape: {embeddings.shape}")

    # 4. L2-normalise for cosine similarity via dot product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings_norm = embeddings / np.maximum(norms, 1e-9)

    # 5. Save index
    index = {
        "model": MODEL_NAME,
        "max_tokens": MAX_TOKENS,
        "corpus": corpus,          # list of dicts (no embed_text to save space)
        "embeddings": embeddings_norm,   # float32 (N, 768)
        "n_cases": len(corpus),
    }
    # Strip embed_text from saved corpus (no longer needed)
    for c in index["corpus"]:
        c.pop("embed_text", None)

    with open(INDEX_PATH, "wb") as f:
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_mb = os.path.getsize(INDEX_PATH) / 1024 / 1024
    logger.info(f"Index saved to {INDEX_PATH} ({size_mb:.1f} MB)")
    logger.info(f"Done. {len(corpus)} cases indexed.")


if __name__ == "__main__":
    main()
