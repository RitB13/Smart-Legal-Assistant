"""
Unified preprocessing pipeline for all Indian legal datasets.

Sources:
  NyayaAnumana   → src/data/nyayaanumana/          (filename, text, label)
  Jud-IPL        → src/data/jud_ipl/               (name, judgement, label, case_category, proof_sentence)
  IL-TUR CJPE    → src/data/il_tur/cjpe/           (id, text, label)  ← ILDC_multi
  IL-TUR RR      → src/data/il_tur/rr/             (id, text, labels) ← fairness classifier
  IL-TUR SUMM    → src/data/il_tur/summ/           (id, document, summary)
  IL-TUR BAIL    → src/data/il_tur/bail/           (id, district, text, label)

Outputs → src/data/processed/:
  outcome_train/val/test.csv   → case outcome predictor + settlement model
  fairness_train/val/test.csv  → fairness classifier
  rag_corpus.csv               → chatbot RAG + precedent index
  bail_train/val/test.csv      → bail prediction (bonus feature)
"""

import os
import hashlib
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "src" / "data"
OUT  = BASE / "processed"
OUT.mkdir(exist_ok=True)

NYA_TRAIN = BASE / "nyayaanumana/train/binary/binary_multi_train/CJPE_ext_SCI_HCs_Tribunals_multi.csv"
NYA_DEV   = BASE / "nyayaanumana/dev/binary/extracted/binary_dev/CJPE_ext_SCI_HCs_Tribunals_dev.csv"
NYA_TEST  = BASE / "nyayaanumana/test/binary/extracted/binary_test/CJPE_ext_SCI_HCs_Tribunals_test.csv"
JUD_CSV   = BASE / "jud_ipl/case_files_total.csv"
CJPE_DIR  = BASE / "il_tur/cjpe"
RR_DIR    = BASE / "il_tur/rr"
SUMM_DIR  = BASE / "il_tur/summ"
BAIL_DIR  = BASE / "il_tur/bail"

CHUNK_SIZE = 50_000  # rows per chunk for large CSVs


# ── helpers ───────────────────────────────────────────────────────────────────

def fp(text: str) -> str:
    """Short fingerprint on first 300 chars for deduplication."""
    return hashlib.md5(str(text)[:300].encode("utf-8", errors="ignore")).hexdigest()

def normalize_binary_label(val) -> int | None:
    """Map any label variant → 1 (Accept) or 0 (Reject). Returns None to drop."""
    if pd.isna(val):
        return None
    s = str(val).strip().lower()
    if s in ("1", "1.0", "accepted", "accept", "allowed"):
        return 1
    if s in ("0", "0.0", "rejected", "reject", "dismissed"):
        return 0
    return None  # Undetermined / Other → drop


# ── 1. OUTCOME DATASET ────────────────────────────────────────────────────────

def build_outcome_dataset():
    print("\n" + "="*60)
    print("BUILDING OUTCOME DATASET")
    print("="*60)

    seen_fps = set()
    split_frames = {"train": [], "dev": [], "test": []}

    # ── NyayaAnumana ──────────────────────────────────────────────
    # NOTE: deduplicate WITHIN each split only — do NOT carry seen_fps
    # across splits, otherwise dev/test rows get dropped as "seen in train".
    print("\n[NyayaAnumana] Loading in chunks (this takes a while)...")
    for split, path in [("train", NYA_TRAIN), ("dev", NYA_DEV), ("test", NYA_TEST)]:
        if not path.exists():
            print(f"  WARNING: {path} not found, skipping.")
            continue
        split_fps = set()  # per-split dedup only
        kept = 0
        for chunk in pd.read_csv(path, usecols=["text", "label"],
                                  chunksize=CHUNK_SIZE, low_memory=False):
            chunk = chunk.dropna(subset=["text", "label"])
            chunk["label"] = chunk["label"].apply(normalize_binary_label)
            chunk = chunk.dropna(subset=["label"])
            chunk["label"] = chunk["label"].astype(int)
            chunk["text"]  = chunk["text"].astype(str).str.strip()
            chunk = chunk[chunk["text"].str.len() > 100]
            chunk["_fp"] = chunk["text"].apply(fp)
            chunk = chunk[~chunk["_fp"].isin(split_fps)]
            split_fps.update(chunk["_fp"].tolist())
            # also track in global seen_fps so other sources don't duplicate
            seen_fps.update(chunk["_fp"].tolist())
            chunk = chunk.drop(columns=["_fp"])
            chunk["source"] = "nyayaanumana"
            kept += len(chunk)
            split_frames[split].append(chunk)
        print(f"  {split}: kept {kept:,} rows")

    # ── IL-TUR CJPE (ILDC_multi) ──────────────────────────────────
    print("\n[IL-TUR CJPE / ILDC] Loading...")
    cjpe_map = {
        "train": [CJPE_DIR / "multi_train-00000-of-00002.parquet",
                  CJPE_DIR / "multi_train-00001-of-00002.parquet"],
        "dev":   [CJPE_DIR / "multi_dev-00000-of-00001.parquet"],
        "test":  [CJPE_DIR / "test-00000-of-00001.parquet"],
    }
    for split, files in cjpe_map.items():
        rows = []
        for f in files:
            if not f.exists():
                continue
            df = pq.read_table(f, columns=["id", "text", "label"]).to_pandas()
            df = df.dropna(subset=["text", "label"])
            df["label"] = df["label"].apply(normalize_binary_label)
            df = df.dropna(subset=["label"])
            df["label"] = df["label"].astype(int)
            df["text"]  = df["text"].astype(str).str.strip()
            df = df[df["text"].str.len() > 100]
            df["_fp"] = df["text"].apply(fp)
            df = df[~df["_fp"].isin(seen_fps)]
            seen_fps.update(df["_fp"].tolist())
            df = df.drop(columns=["_fp", "id"])
            df["source"] = "ildc"
            rows.append(df)
        if rows:
            merged = pd.concat(rows, ignore_index=True)
            split_frames[split].append(merged)
            print(f"  {split}: {len(merged):,} rows")

    # ── Jud-IPL ───────────────────────────────────────────────────
    print("\n[Jud-IPL] Loading...")
    if JUD_CSV.exists():
        jud = pd.read_csv(JUD_CSV,
                          usecols=["name", "judgement", "label", "case_category", "proof_sentence"],
                          low_memory=False)
        jud = jud.dropna(subset=["judgement", "label"])
        jud["label"] = jud["label"].apply(normalize_binary_label)
        jud = jud.dropna(subset=["label"])
        jud["label"] = jud["label"].astype(int)
        jud = jud.rename(columns={"judgement": "text"})
        jud["text"] = jud["text"].astype(str).str.strip()
        jud = jud[jud["text"].str.len() > 100]
        jud["_fp"] = jud["text"].apply(fp)
        jud = jud[~jud["_fp"].isin(seen_fps)]
        seen_fps.update(jud["_fp"].tolist())
        jud = jud.drop(columns=["_fp"])
        jud["source"] = "jud_ipl"

        # 80/10/10 split
        jud = jud.sample(frac=1, random_state=42).reset_index(drop=True)
        n = len(jud)
        n_train = int(n * 0.8)
        n_val   = int(n * 0.1)
        split_frames["train"].append(jud.iloc[:n_train])
        split_frames["dev"].append(jud.iloc[n_train:n_train + n_val])
        split_frames["test"].append(jud.iloc[n_train + n_val:])
        print(f"  total: {n:,} rows → train {n_train:,} / dev {n_val:,} / test {n - n_train - n_val:,}")
    else:
        print("  WARNING: Jud-IPL CSV not found.")

    # ── Write outputs ─────────────────────────────────────────────
    print("\nWriting outcome CSVs...")
    for split, frames in split_frames.items():
        if not frames:
            continue
        out = pd.concat(frames, ignore_index=True)[["text", "label", "source"]]
        out.to_csv(OUT / f"outcome_{split}.csv", index=False)
        dist = out["label"].value_counts().to_dict()
        src  = out["source"].value_counts().to_dict()
        print(f"  outcome_{split}.csv — {len(out):,} rows | labels: {dist} | sources: {src}")


# ── 2. FAIRNESS DATASET (IL-TUR RR) ──────────────────────────────────────────

def build_fairness_dataset():
    print("\n" + "="*60)
    print("BUILDING FAIRNESS DATASET (IL-TUR Rhetorical Roles)")
    print("="*60)

    # CL = Court Language variant, IT = Indian Text variant
    rr_map = {
        "train": ["CL_train-00000-of-00001.parquet", "IT_train-00000-of-00001.parquet"],
        "dev":   ["CL_dev-00000-of-00001.parquet",   "IT_dev-00000-of-00001.parquet"],
        "test":  ["CL_test-00000-of-00001.parquet",  "IT_test-00000-of-00001.parquet"],
    }

    for split, files in rr_map.items():
        rows = []
        for fname in files:
            path = RR_DIR / fname
            if not path.exists():
                print(f"  WARNING: {fname} not found")
                continue
            variant = "CL" if fname.startswith("CL") else "IT"

            # Use pyarrow directly — .as_py() guarantees Python native list types
            tbl = pq.read_table(path, columns=["id", "text", "labels"])
            sentence_rows = []
            for i in range(tbl.num_rows):
                doc_id = tbl["id"][i].as_py()
                texts  = tbl["text"][i].as_py()    # Python list of sentences
                labels = tbl["labels"][i].as_py()  # Python list of int labels
                if not isinstance(texts, list):
                    texts = [texts]
                if not isinstance(labels, list):
                    labels = [labels]
                for j, (sent, lbl) in enumerate(zip(texts, labels)):
                    sentence_rows.append({
                        "id":      f"{doc_id}_{j}",
                        "text":    str(sent).strip(),
                        "label":   lbl,
                        "variant": variant,
                    })
            rows.append(pd.DataFrame(sentence_rows))

        if rows:
            out = pd.concat(rows, ignore_index=True)
            out = out[out["text"].str.len() > 10]
            out.to_csv(OUT / f"fairness_{split}.csv", index=False)
            print(f"  fairness_{split}.csv — {len(out):,} sentences")


# ── 3. RAG CORPUS ─────────────────────────────────────────────────────────────

def build_rag_corpus():
    print("\n" + "="*60)
    print("BUILDING RAG CORPUS")
    print("="*60)

    parts = []

    # IL-TUR SUMM — has both document and summary
    print("[IL-TUR SUMM] Loading...")
    for fname in ["train-00000-of-00001.parquet", "test-00000-of-00001.parquet"]:
        path = SUMM_DIR / fname
        if not path.exists():
            continue
        df = pq.read_table(path, columns=["id", "document", "summary"]).to_pandas()
        df = df.dropna(subset=["document"])
        df = df.rename(columns={"document": "text"})
        df["text"] = df["text"].astype(str).str.strip()
        df["source"] = "il_tur_summ"
        parts.append(df[["id", "text", "summary", "source"]])
    print(f"  Loaded {sum(len(p) for p in parts):,} rows from SUMM")

    # Jud-IPL — full judgment text
    print("[Jud-IPL] Loading full texts...")
    if JUD_CSV.exists():
        jud = pd.read_csv(JUD_CSV, usecols=["name", "judgement"], low_memory=False)
        jud = jud.dropna(subset=["judgement"])
        jud = jud.rename(columns={"name": "id", "judgement": "text"})
        jud["text"] = jud["text"].astype(str).str.strip()
        jud = jud[jud["text"].str.len() > 200]
        jud["summary"] = None
        jud["source"]  = "jud_ipl"
        parts.append(jud[["id", "text", "summary", "source"]])
        print(f"  Loaded {len(jud):,} rows from Jud-IPL")

    # IL-TUR CJPE — full SC judgment text
    print("[IL-TUR CJPE] Loading full texts...")
    cjpe_rows = []
    for fname in CJPE_DIR.glob("*.parquet"):
        df = pq.read_table(fname, columns=["id", "text"]).to_pandas()
        df = df.dropna(subset=["text"])
        df["text"] = df["text"].astype(str).str.strip()
        df = df[df["text"].str.len() > 200]
        df["summary"] = None
        df["source"]  = "ildc"
        cjpe_rows.append(df[["id", "text", "summary", "source"]])
    if cjpe_rows:
        cjpe_all = pd.concat(cjpe_rows, ignore_index=True)
        parts.append(cjpe_all)
        print(f"  Loaded {len(cjpe_all):,} rows from CJPE")

    if not parts:
        print("  ERROR: No RAG data found.")
        return

    corpus = pd.concat(parts, ignore_index=True)
    corpus = corpus.drop_duplicates(subset=["text"])
    corpus.to_csv(OUT / "rag_corpus.csv", index=False)
    src_dist = corpus["source"].value_counts().to_dict()
    print(f"\n  rag_corpus.csv — {len(corpus):,} documents | {src_dist}")


# ── 4. BAIL DATASET (bonus feature) ──────────────────────────────────────────

def build_bail_dataset():
    print("\n" + "="*60)
    print("BUILDING BAIL DATASET")
    print("="*60)

    bail_map = {
        "train": ["train_all-00000-of-00002.parquet", "train_all-00001-of-00002.parquet"],
        "dev":   ["dev_all-00000-of-00001.parquet"],
        "test":  ["test_all-00000-of-00001.parquet"],
    }

    for split, files in bail_map.items():
        rows = []
        for fname in files:
            path = BAIL_DIR / fname
            if not path.exists():
                continue
            df = pq.read_table(path, columns=["id", "district", "text", "label"]).to_pandas()
            df = df.dropna(subset=["text", "label"])
            df["text"] = df["text"].astype(str).str.strip()
            rows.append(df)
        if rows:
            out = pd.concat(rows, ignore_index=True)
            out.to_csv(OUT / f"bail_{split}.csv", index=False)
            dist = out["label"].value_counts().to_dict()
            print(f"  bail_{split}.csv — {len(out):,} rows | labels: {dist}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def already_done(files: list[str], min_rows: int = 1000) -> bool:
    """Return True if all output files exist and are large enough to skip."""
    for fname in files:
        path = OUT / fname
        if not path.exists():
            return False
        # quick row count check via line count (subtract 1 for header)
        with open(path, "rb") as f:
            count = sum(1 for _ in f) - 1
        if count < min_rows:
            print(f"  {fname} exists but only {count} rows — will regenerate.")
            return False
    return True


if __name__ == "__main__":
    print("="*60)
    print("SMART LEGAL ASSISTANT — DATASET PREPROCESSING PIPELINE")
    print("="*60)

    # ── Outcome dataset ───────────────────────────────────────────
    outcome_files = ["outcome_train.csv", "outcome_dev.csv", "outcome_test.csv"]
    if already_done(outcome_files, min_rows=100_000):
        print("\n[SKIP] Outcome dataset already complete.")
    else:
        build_outcome_dataset()

    # ── Fairness dataset ──────────────────────────────────────────
    fairness_files = ["fairness_train.csv", "fairness_dev.csv", "fairness_test.csv"]
    if already_done(fairness_files, min_rows=500):
        print("\n[SKIP] Fairness dataset already complete.")
    else:
        build_fairness_dataset()

    # ── RAG corpus ────────────────────────────────────────────────
    if already_done(["rag_corpus.csv"], min_rows=50_000):
        print("\n[SKIP] RAG corpus already complete.")
    else:
        build_rag_corpus()

    # ── Bail dataset ──────────────────────────────────────────────
    bail_files = ["bail_train.csv", "bail_dev.csv", "bail_test.csv"]
    if already_done(bail_files, min_rows=10_000):
        print("\n[SKIP] Bail dataset already complete.")
    else:
        build_bail_dataset()

    print("\n" + "="*60)
    print("ALL DONE — Output files:")
    for f in sorted(OUT.glob("*.csv")):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name:40s}  {size_mb:>8.1f} MB")
    print("="*60)
