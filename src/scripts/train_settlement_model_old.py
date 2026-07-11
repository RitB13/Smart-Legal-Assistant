"""
Settlement Range Model Training
================================
Trains a LightGBM classifier on Indian court cases to predict
P(petition accepted) for a given (case_type, year) profile.

At inference time, this probability is used to compute a data-driven
settlement range rather than relying on an LLM estimate.

Data source:
  src/data/processed/outcome_train.csv  )
  src/data/processed/outcome_dev.csv    ) — all three splits combined
  src/data/processed/outcome_test.csv   )

Only the 'id' and 'label' columns are read (text is never loaded).
Year is extracted from the case ID via regex.
Case type is inferred from the case ID prefix (court/body abbreviation).

Run from project root:
    python src/scripts/train_settlement_model_old.py
"""

import os
import csv
import sys
import json
import pickle
import numpy as np
import pandas as pd

# Some court judgment cells exceed Python csv's default 128 KB field limit.
# Find the largest value the platform accepts (sys.maxsize overflows on Windows).
_limit = sys.maxsize
while True:
    try:
        csv.field_size_limit(_limit)
        break
    except OverflowError:
        _limit = _limit // 10
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
import lightgbm as lgb

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PROC_DIR   = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "processed"))
OUTPUT_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "models", "mediation"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTCOME_SPLITS = [
    os.path.join(PROC_DIR, "outcome_train.csv"),
    os.path.join(PROC_DIR, "outcome_dev.csv"),
    os.path.join(PROC_DIR, "outcome_test.csv"),
]

MEDIATION_TO_MODEL_TYPE = {
    "property":   "property",
    "money":      "appeal",
    "family":     "family",
    "employment": "appeal",
    "consumer":   "petition",
    "contract":   "contract",
    "general":    "other",
    "other":      "other",
}


def normalize_verdict(val) -> int | None:
    if pd.isna(val):
        return None
    s = str(val).strip().lower()
    if s in ("1", "1.0", "accepted", "accept", "allowed", "granted"):
        return 1
    if s in ("0", "0.0", "rejected", "reject", "dismissed", "denied"):
        return 0
    return None


def infer_case_type_from_source(source: str) -> str:
    """
    Map preprocessed dataset source tag to a case_type_group.
    The 'source' column was added by preprocess_datasets.py to track origin.
    """
    s = str(source).lower().strip()
    if "jud" in s or "ipl" in s:
        return "contract"      # Jud-IPL: IP / commercial litigation
    if "ildc" in s or "cjpe" in s or "il_tur" in s:
        return "other"         # IL-TUR / ILDC: Supreme Court misc
    if "nya" in s or "nyaya" in s or "sci" in s:
        return "other"         # NyayaAnumana SCI: Supreme Court
    if "hc" in s:
        return "appeal"        # High Court splits
    return "other"


def load_split(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        print(f"  [SKIP] Not found: {path}")
        return pd.DataFrame()

    # Probe columns — reads only the header line, no data
    available = pd.read_csv(path, nrows=0).columns.tolist()
    print(f"  Columns in {os.path.basename(path)}: {available}")

    if "label" not in available:
        print(f"  [SKIP] No 'label' column found.")
        return pd.DataFrame()

    load_cols = [c for c in ["label", "source"] if c in available]

    # Use engine='python' to avoid the C tokenizer OOM on large text cells.
    # We never request the 'text' column so it is skipped entirely.
    rows = []
    for chunk in pd.read_csv(
        path,
        usecols=load_cols,
        chunksize=20_000,
        engine="python",
        on_bad_lines="skip",
    ):
        rows.append(chunk)
    df = pd.concat(rows, ignore_index=True)

    df["verdict_binary"] = df["label"].apply(normalize_verdict)
    df = df.dropna(subset=["verdict_binary"])
    df["verdict_binary"] = df["verdict_binary"].astype(int)

    # Derive case type from the source tag; default year since no id column
    if "source" in df.columns:
        df["case_type_group"] = df["source"].apply(infer_case_type_from_source)
    else:
        df["case_type_group"] = "other"

    df["year"]               = 2010   # no year metadata in processed CSVs
    df["jurisdiction_state"] = "Unknown"

    print(f"    Rows kept: {len(df):,} | acceptance rate: {df['verdict_binary'].mean():.3f}")
    if "source" in df.columns:
        print(f"    Case types: {df['case_type_group'].value_counts().to_dict()}")
    return df[["verdict_binary", "year", "case_type_group", "jurisdiction_state"]]


def main():
    frames = []
    for path in OUTCOME_SPLITS:
        chunk = load_split(path)
        if not chunk.empty:
            frames.append(chunk)

    if not frames:
        raise RuntimeError(
            "No data loaded. Ensure outcome_train/dev/test.csv exist in "
            "src/data/processed/ — run preprocess_datasets.py first."
        )

    df = pd.concat(frames, ignore_index=True)
    print(f"\n=== Combined: {len(df):,} rows ===")

    df["year"]      = df["year"].clip(1950, 2024)
    df["year_norm"] = (df["year"] - 1950) / (2024 - 1950)

    print(f"  Overall acceptance rate : {df['verdict_binary'].mean():.3f}")
    print(f"  Case type distribution  :\n{df['case_type_group'].value_counts()}")
    print(f"  Year range              : {df['year'].min()} – {df['year'].max()}")

    type_enc  = LabelEncoder()
    state_enc = LabelEncoder()
    df["type_enc"]  = type_enc.fit_transform(df["case_type_group"])
    df["state_enc"] = state_enc.fit_transform(df["jurisdiction_state"])

    features = ["type_enc", "state_enc", "year_norm"]
    X = df[features].values.astype(np.float32)
    y = df["verdict_binary"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train):,}  Test: {len(X_test):,}")

    model = lgb.LGBMClassifier(
        objective="binary",
        metric="auc",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=50,
        class_weight="balanced",
        random_state=42,
        verbose=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(50)],
    )

    y_prob = model.predict_proba(X_test)[:, 1]
    auc    = roc_auc_score(y_test, y_prob)
    y_pred = (y_prob >= 0.5).astype(int)
    print(f"\nAUC: {auc:.4f}")
    print(classification_report(y_test, y_pred, target_names=["Rejected", "Accepted"]))

    print("P(Accepted) by case_type_group:")
    for g in sorted(df["case_type_group"].unique()):
        mask = df["case_type_group"] == g
        rate = df.loc[mask, "verdict_binary"].mean()
        print(f"  {g}: {rate:.3f}  (n={mask.sum():,})")

    lgbm_path = os.path.join(OUTPUT_DIR, "settlement_lgbm.pkl")
    enc_path  = os.path.join(OUTPUT_DIR, "settlement_encoders.pkl")
    meta_path = os.path.join(OUTPUT_DIR, "settlement_meta.json")

    with open(lgbm_path, "wb") as f:
        pickle.dump(model, f)
    with open(enc_path, "wb") as f:
        pickle.dump({"type_encoder": type_enc, "state_encoder": state_enc}, f)

    base_rates = {
        g: float(df.loc[df["case_type_group"] == g, "verdict_binary"].mean())
        for g in df["case_type_group"].unique()
    }
    meta = {
        "features": features,
        "type_classes":  type_enc.classes_.tolist(),
        "state_classes": state_enc.classes_.tolist(),
        "auc": round(auc, 4),
        "overall_acceptance_rate": float(y.mean()),
        "base_rates_by_type": base_rates,
        "mediation_to_model_type": MEDIATION_TO_MODEL_TYPE,
        "year_min": 1950,
        "year_max": 2024,
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved:")
    print(f"  {lgbm_path}")
    print(f"  {enc_path}")
    print(f"  {meta_path}")
    print(f"\nDone. AUC={auc:.4f}")


if __name__ == "__main__":
    main()
