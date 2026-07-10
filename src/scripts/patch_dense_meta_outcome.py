"""
Patch corpus_meta.json — add 'outcome' field to each entry.

Reads rag_corpus.csv in the same row order as build_dense_index.py and
applies the same outcome heuristic used by the precedent service:
  - If the parsed summary is longer than 400 chars → outcome = last 200 chars
  - Otherwise → outcome = ""

This allows DenseRetrievalService.search() to return a non-empty 'outcome'
field, which case_outcome.py can normalise to 'Accepted' / 'Rejected'.

Does NOT re-encode embeddings — only patches corpus_meta.json in place.
Runs in a few seconds (pure JSON + CSV read/write, no ML inference).

Usage (from project root):
    python -m src.scripts.patch_dense_meta_outcome
"""

import ast
import json
import sys
import pandas as pd
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "src" / "data" / "processed" / "rag_corpus.csv"
META_PATH   = ROOT / "src" / "data" / "models" / "dense" / "corpus_meta.json"


def _parse_list_field(val) -> str:
    """Convert Python list-repr strings (il_tur_summ source) to plain text."""
    if isinstance(val, str) and val.strip().startswith("["):
        try:
            parts = ast.literal_eval(val)
            return " ".join(str(p) for p in parts).strip()
        except Exception:
            pass
    return str(val) if val is not None else ""


def main():
    if not META_PATH.exists():
        print(f"ERROR: corpus_meta.json not found at {META_PATH}")
        print("Run src/scripts/build_dense_index.py first.")
        sys.exit(1)

    if not CORPUS_PATH.exists():
        print(f"ERROR: rag_corpus.csv not found at {CORPUS_PATH}")
        sys.exit(1)

    print(f"Loading corpus_meta.json from {META_PATH} ...")
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print(f"  {len(meta):,} metadata entries loaded")

    print(f"Loading rag_corpus.csv from {CORPUS_PATH} ...")
    df = pd.read_csv(CORPUS_PATH, low_memory=False)
    print(f"  {len(df):,} rows loaded — columns: {list(df.columns)}")

    if len(meta) != len(df):
        print(
            f"ERROR: metadata rows ({len(meta):,}) != CSV rows ({len(df):,}). "
            "The dense index may have been built from a different version of the corpus. "
            "Re-run build_dense_index.py before patching."
        )
        sys.exit(1)

    print("Patching 'outcome' field for each entry ...")
    non_empty = 0
    for i, (_, row) in enumerate(df.iterrows()):
        raw_summary = _parse_list_field(row.get("summary", ""))
        # Same heuristic as build_precedent_index.py:
        # last 200 chars of the summary when it is long enough to contain a ruling.
        outcome = raw_summary[-200:].strip() if len(raw_summary) > 400 else ""
        meta[i]["outcome"] = outcome
        if outcome:
            non_empty += 1
        if (i + 1) % 10_000 == 0:
            print(f"  {i + 1:,} / {len(meta):,} processed ...")

    print(
        f"  Done — {non_empty:,} of {len(meta):,} entries have a non-empty outcome "
        f"({non_empty / len(meta) * 100:.1f}%)"
    )

    print(f"Saving patched corpus_meta.json to {META_PATH} ...")
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"  Saved ({META_PATH.stat().st_size / 1e6:.1f} MB)")
    print("Patch complete. Restart the FastAPI server to reload the dense index.")


if __name__ == "__main__":
    main()
