"""
Settlement Range Model Training
================================
Trains a LightGBM classifier on 71k Indian court cases to predict
P(petition accepted) for a given (case_type, state, year) profile.

At inference time, this probability is used to compute a data-driven
settlement range rather than relying on an LLM estimate.

Run from project root:
    python src/data/mediation_training/train_settlement_model.py
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
import lightgbm as lgb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "case_outcomes", "cleaned_dataset.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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


def map_case_type(ct: str) -> str:
    ct = str(ct).lower().strip()
    if ct in ("property_dispute", "harassment_civil"):
        return "property"
    if ct in ("divorce_contested", "dowry_harassment"):
        return "family"
    if ct in ("arbitration_appeal", "arbitration appeal"):
        return "contract"
    if "appeal" in ct:
        return "appeal"
    if "writ" in ct:
        return "writ"
    if "petition" in ct:
        return "petition"
    if ct == "unknown":
        return "other"
    return "other"


def main():
    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"  Rows: {len(df)}")

    # Feature engineering
    df["case_type_group"] = df["case_type"].apply(map_case_type)
    df["verdict_binary"] = (df["verdict"].str.lower() == "accepted").astype(int)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(2010).astype(int).clip(1950, 2024)
    df["year_norm"] = (df["year"] - 1950) / (2024 - 1950)
    df["jurisdiction_state"] = df["jurisdiction_state"].fillna("Unknown").astype(str)

    print(f"  Verdict distribution:\n{df['verdict'].value_counts()}")
    print(f"  Case type groups:\n{df['case_type_group'].value_counts()}")
    print(f"  Acceptance rate: {df['verdict_binary'].mean():.3f}")

    # Encode
    type_enc = LabelEncoder()
    state_enc = LabelEncoder()
    df["type_enc"] = type_enc.fit_transform(df["case_type_group"])
    df["state_enc"] = state_enc.fit_transform(df["jurisdiction_state"])

    features = ["type_enc", "state_enc", "year_norm"]
    X = df[features].values
    y = df["verdict_binary"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")

    # Train LightGBM
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

    # Evaluate
    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    y_pred = (y_prob >= 0.5).astype(int)
    print(f"\nAUC: {auc:.4f}")
    print(classification_report(y_test, y_pred, target_names=["Rejected", "Accepted"]))

    # P(Accepted) by case type group — useful sanity check
    print("P(Accepted) by case type group:")
    for g in sorted(df["case_type_group"].unique()):
        mask = df["case_type_group"] == g
        rate = df.loc[mask, "verdict_binary"].mean()
        print(f"  {g}: {rate:.3f} (n={mask.sum()})")

    # Save artifacts
    settlement_lgbm_path = os.path.join(OUTPUT_DIR, "settlement_lgbm.pkl")
    settlement_enc_path  = os.path.join(OUTPUT_DIR, "settlement_encoders.pkl")
    settlement_meta_path = os.path.join(OUTPUT_DIR, "settlement_meta.json")

    with open(settlement_lgbm_path, "wb") as f:
        pickle.dump(model, f)

    with open(settlement_enc_path, "wb") as f:
        pickle.dump({"type_encoder": type_enc, "state_encoder": state_enc}, f)

    # Compute per-(type, state) base rates for confidence calibration
    base_rates = {}
    for g in df["case_type_group"].unique():
        base_rates[g] = float(df.loc[df["case_type_group"] == g, "verdict_binary"].mean())

    meta = {
        "features": features,
        "type_classes": type_enc.classes_.tolist(),
        "state_classes": state_enc.classes_.tolist(),
        "auc": round(auc, 4),
        "overall_acceptance_rate": float(y.mean()),
        "base_rates_by_type": base_rates,
        "mediation_to_model_type": MEDIATION_TO_MODEL_TYPE,
        "year_min": 1950,
        "year_max": 2024,
    }

    with open(settlement_meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved:")
    print(f"  {settlement_lgbm_path}")
    print(f"  {settlement_enc_path}")
    print(f"  {settlement_meta_path}")
    print(f"\nDone. AUC={auc:.4f}")


if __name__ == "__main__":
    main()
