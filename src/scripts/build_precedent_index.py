"""
Precedent Index Builder
=======================
Builds a TF-IDF + TruncatedSVD semantic search index over rag_corpus.csv
(82k Indian court cases from IL-TUR SUMM, Jud-IPL, and ILDC).

Uses TF-IDF with Latent Semantic Analysis (SVD) for fast local indexing —
no GPU required, runs in ~5 minutes.

Index is saved to: src/data/mediation_training/models/precedent_index.pkl

Run from project root:
    python src/scripts/build_precedent_index.py
"""

import ast
import re
import pickle
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

CORPUS_CSV   = Path("src/data/processed/rag_corpus.csv")
OUTPUT_DIR   = Path("src/data/models/precedent")
INDEX_PATH   = OUTPUT_DIR / "precedent_index.pkl"

SVD_DIMS     = 256
MAX_FEATURES = 20_000
TEXT_TRUNC   = 3000   # chars used for TF-IDF embedding per doc

SOURCE_TYPE = {
    "jud_ipl":     "IPL Case",
    "il_tur_summ": "Supreme Court Case",
    "ildc":        "ILDC Case",
}


# ─── Text helpers ──────────────────────────────────────────────────────────────

def parse_text(raw: str) -> str:
    """
    Convert raw text field to a clean string.
    Handles two formats:
      - Plain string (jud_ipl, ildc)
      - Python list repr stored as string: "['sent1', 'sent2', ...]"  (il_tur_summ)
    """
    if not raw or not isinstance(raw, str):
        return ""
    raw = raw.strip()
    if raw.startswith("["):
        try:
            sentences = ast.literal_eval(raw)
            if isinstance(sentences, list):
                return " ".join(str(s).strip() for s in sentences if s)
        except Exception:
            pass
    # Already a plain string — strip any escaped quotes
    return raw


def derive_case_name(row_id: str, text: str, source: str) -> str:
    """
    Derive a display case name.
    - jud_ipl: id IS the case name (original 'name' column)
    - others:  search text for 'X vs Y' pattern, fallback to first line
    """
    if source == "jud_ipl" and row_id and str(row_id).strip():
        name = str(row_id).strip()
        return name[:150]

    # Search first 600 chars for versus pattern
    snippet = text[:600].replace("\n", " ")
    m = re.search(
        r"([A-Z][^.]{4,60})\s+[vV](?:ersus|s\.?)\s+([A-Z][^.]{4,60})",
        snippet
    )
    if m:
        full = m.group(0).strip()
        return full[:150]

    # Fallback: first non-trivial line
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 15:
            return line[:120]

    return "Unknown Case"


def build_corpus_entry(row: pd.Series, text: str, summary_text: str) -> dict:
    source = str(row.get("source", "unknown"))
    row_id = str(row.get("id", ""))

    case_name = derive_case_name(row_id, text, source)
    case_type = SOURCE_TYPE.get(source, source)

    # Summary: use summary field if available, else first 300 chars of text
    if summary_text and len(summary_text) > 20:
        display_summary = summary_text[:300]
        outcome         = summary_text[-200:] if len(summary_text) > 400 else ""
    else:
        display_summary = text[:300]
        outcome         = ""

    return {
        "case_id":   row_id,
        "case_name": case_name,
        "case_type": case_type,
        "summary":   display_summary,
        "outcome":   outcome,
        "source":    source,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading corpus: {CORPUS_CSV}")
    df = pd.read_csv(CORPUS_CSV, dtype=str).fillna("")
    logger.info(f"  {len(df):,} documents — sources: {df['source'].value_counts().to_dict()}")

    # Parse text fields
    logger.info("Parsing and cleaning text fields...")
    texts    = [parse_text(t) for t in df["text"].tolist()]
    summaries = [parse_text(s) for s in df["summary"].tolist()]

    # Build corpus metadata
    logger.info("Building corpus entries...")
    corpus = []
    embed_texts = []
    for i, (_, row) in enumerate(df.iterrows()):
        text    = texts[i]
        summary = summaries[i]
        corpus.append(build_corpus_entry(row, text, summary))
        # Use summary if available (more informative), else full text
        embed_text = (summary if len(summary) > 100 else text)[:TEXT_TRUNC]
        embed_texts.append(embed_text)

    logger.info(f"  {len(corpus):,} corpus entries built")

    # TF-IDF
    logger.info(f"Fitting TF-IDF (max_features={MAX_FEATURES:,}, bigrams)...")
    vectorizer = TfidfVectorizer(
        max_features = MAX_FEATURES,
        sublinear_tf = True,
        ngram_range  = (1, 2),
        min_df       = 3,
        strip_accents = "unicode",
        dtype         = np.float32,
    )
    tfidf_matrix = vectorizer.fit_transform(embed_texts)
    logger.info(f"  Matrix shape: {tfidf_matrix.shape}  nnz: {tfidf_matrix.nnz:,}")

    # TruncatedSVD — converts sparse TF-IDF to dense semantic vectors
    logger.info(f"Running TruncatedSVD → {SVD_DIMS} dims...")
    svd = TruncatedSVD(n_components=SVD_DIMS, n_iter=7, random_state=42)
    dense = svd.fit_transform(tfidf_matrix).astype(np.float32)
    explained = svd.explained_variance_ratio_.sum()
    logger.info(f"  SVD done. Explained variance: {explained:.3f}")

    # L2-normalize so dot product == cosine similarity
    embeddings = normalize(dense, norm="l2").astype(np.float32)
    logger.info(f"  Embeddings shape: {embeddings.shape}  dtype: {embeddings.dtype}")

    # Save index
    index = {
        "model":       "tfidf-svd",
        "n_cases":     len(corpus),
        "svd_dims":    SVD_DIMS,
        "max_features": MAX_FEATURES,
        "vectorizer":  vectorizer,
        "svd":         svd,
        "embeddings":  embeddings,
        "corpus":      corpus,
    }

    logger.info(f"Saving index → {INDEX_PATH}")
    with open(INDEX_PATH, "wb") as f:
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_mb = INDEX_PATH.stat().st_size / 1024 / 1024
    logger.info(f"Done. {len(corpus):,} cases indexed. File size: {size_mb:.1f} MB")

    # Quick sanity check
    logger.info("Sanity check — querying 'property dispute lease agreement'...")
    q_tfidf = vectorizer.transform(["property dispute lease agreement"])
    q_svd   = svd.transform(q_tfidf).astype(np.float32)
    q_vec   = normalize(q_svd, norm="l2")[0]
    scores  = embeddings @ q_vec
    top3    = np.argsort(scores)[::-1][:3]
    for rank, idx in enumerate(top3):
        c = corpus[idx]
        logger.info(f"  [{rank+1}] {c['case_name'][:60]} ({c['case_type']}) sim={scores[idx]:.3f}")


if __name__ == "__main__":
    main()
