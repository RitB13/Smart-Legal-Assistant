"""
Classical ML Training Pipeline
Trains LR, LinearSVC, LightGBM on all three tasks:
  - Case outcome prediction  (outcome_train/dev/test.csv)
  - Fairness classification  (fairness_train/dev/test.csv)
  - Bail prediction          (bail_train/dev/test.csv)

Run: python src/scripts/train_classical_models.py
Results saved to: src/data/models/classical/
"""

import pandas as pd
import numpy as np
import pickle
import json
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report
)
import lightgbm as lgb

# ── Paths ────────────────────────────────────────────────────────────────────
DATA  = Path("src/data/processed")
OUT   = Path("src/data/models/classical")
OUT.mkdir(parents=True, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────
def load_csv(path, sample=None, seed=42):
    # Use nrows to avoid loading the full file when sampling
    df = pd.read_csv(path, usecols=["text", "label"], nrows=sample).dropna()
    df["text"] = df["text"].str[:2000].fillna("")
    return df

def train_task(task_name, train_df, dev_df, test_df, n_tfidf=20_000):
    print(f"\n{'='*65}")
    print(f"  TASK: {task_name.upper()}")
    print(f"  Train: {len(train_df):,}  Dev: {len(dev_df):,}  Test: {len(test_df):,}")
    print(f"{'='*65}")

    # Label encode
    le = LabelEncoder()
    y_train = le.fit_transform(train_df["label"].astype(str))
    y_dev   = le.transform(dev_df["label"].astype(str))
    y_test  = le.transform(test_df["label"].astype(str))
    print(f"  Classes ({len(le.classes_)}): {le.classes_.tolist()}")

    # TF-IDF
    print(f"\n  Fitting TF-IDF (max_features={n_tfidf:,})...")
    tfidf = TfidfVectorizer(
        max_features   = n_tfidf,
        sublinear_tf   = True,
        ngram_range    = (1, 2),
        min_df         = 3,
        strip_accents  = "unicode",
    )
    X_train = tfidf.fit_transform(train_df["text"])
    X_dev   = tfidf.transform(dev_df["text"])
    X_test  = tfidf.transform(test_df["text"])
    print(f"  TF-IDF matrix: {X_train.shape}")

    # Models
    n_classes = len(le.classes_)
    models = {
        "LogisticRegression": LogisticRegression(
            max_iter=1000, C=1.0, class_weight="balanced",
            solver="saga", n_jobs=-1, random_state=42
        ),
        "LinearSVC": LinearSVC(
            max_iter=2000, C=1.0, class_weight="balanced", random_state=42
        ),
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=300, learning_rate=0.05, num_leaves=63,
            max_depth=8, subsample=0.8, colsample_bytree=0.8,
            class_weight="balanced", random_state=42,
            n_jobs=-1, verbose=-1,
            objective="multiclass" if n_classes > 2 else "binary",
            num_class=n_classes if n_classes > 2 else None,
        ),
    }

    # Only add RF for small tasks (fairness/bail) — too slow on 200k+
    if len(train_df) <= 150_000:
        models["RandomForest"] = RandomForestClassifier(
            n_estimators=200, max_depth=20, class_weight="balanced",
            n_jobs=-1, random_state=42
        )

    results = {}
    best_name, best_f1 = None, -1

    for name, model in models.items():
        print(f"\n  Training {name}...")
        t0 = datetime.now()
        model.fit(X_train, y_train)
        elapsed = (datetime.now() - t0).seconds

        # Predict
        if hasattr(model, "predict_proba"):
            y_dev_pred  = model.predict(X_dev)
            y_test_pred = model.predict(X_test)
        else:
            y_dev_pred  = model.predict(X_dev)
            y_test_pred = model.predict(X_test)

        dev_acc  = accuracy_score(y_dev,  y_dev_pred)
        dev_f1   = f1_score(y_dev,  y_dev_pred, average="weighted", zero_division=0)
        test_acc = accuracy_score(y_test, y_test_pred)
        test_f1  = f1_score(y_test, y_test_pred, average="weighted", zero_division=0)
        test_f1m = f1_score(y_test, y_test_pred, average="macro",    zero_division=0)

        print(f"    Dev  — Acc: {dev_acc:.4f}  F1-w: {dev_f1:.4f}")
        print(f"    Test — Acc: {test_acc:.4f}  F1-w: {test_f1:.4f}  F1-m: {test_f1m:.4f}  ({elapsed}s)")

        results[name] = {
            "dev_accuracy":  dev_acc,
            "dev_f1":        dev_f1,
            "test_accuracy": test_acc,
            "test_f1_weighted": test_f1,
            "test_f1_macro":    test_f1m,
            "classification_report": classification_report(
                y_test, y_test_pred,
                target_names=le.classes_.tolist(),
                zero_division=0
            ),
            "training_seconds": elapsed,
        }

        if dev_f1 > best_f1:
            best_f1, best_name = dev_f1, name

    # Summary
    print(f"\n  {'Model':<22} {'Dev F1':>8} {'Test F1':>8} {'Test Acc':>9}")
    print(f"  {'-'*50}")
    for name, r in results.items():
        marker = " ← BEST" if name == best_name else ""
        print(f"  {name:<22} {r['dev_f1']:>8.4f} {r['test_f1_weighted']:>8.4f} {r['test_accuracy']:>9.4f}{marker}")

    # Save best model
    task_dir = OUT / task_name
    task_dir.mkdir(exist_ok=True)

    best_model = models[best_name]
    with open(task_dir / "best_model.pkl",  "wb") as f: pickle.dump(best_model, f)
    with open(task_dir / "tfidf.pkl",       "wb") as f: pickle.dump(tfidf, f)
    with open(task_dir / "label_encoder.pkl","wb") as f: pickle.dump(le, f)

    summary = {
        "task":       task_name,
        "best_model": best_name,
        "train_rows": len(train_df),
        "results":    {k: {m: float(v) for m, v in r.items() if isinstance(v, float)}
                       for k, r in results.items()},
        "classification_report": results[best_name]["classification_report"],
    }
    with open(task_dir / "results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  BEST: {best_name} — Test F1: {results[best_name]['test_f1_weighted']:.4f}")
    print(f"  Saved to: {task_dir}/")
    return summary


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    start = datetime.now()
    all_results = {}

    # ── 1. Case Outcome ──────────────────────────────────────────────────────
    print("\nLoading outcome data (sampling 200k from 692k)...")
    train = load_csv(DATA / "outcome_train.csv", sample=200_000)
    dev   = load_csv(DATA / "outcome_dev.csv")
    test  = load_csv(DATA / "outcome_test.csv")
    all_results["outcome"] = train_task("outcome", train, dev, test, n_tfidf=20_000)
    del train, dev, test

    # ── 2. Fairness ──────────────────────────────────────────────────────────
    print("\nLoading fairness data...")
    train = load_csv(DATA / "fairness_train.csv")
    dev   = load_csv(DATA / "fairness_dev.csv")
    test  = load_csv(DATA / "fairness_test.csv")
    all_results["fairness"] = train_task("fairness", train, dev, test, n_tfidf=10_000)
    del train, dev, test

    # ── 3. Bail ──────────────────────────────────────────────────────────────
    print("\nLoading bail data...")
    train = load_csv(DATA / "bail_train.csv")
    dev   = load_csv(DATA / "bail_dev.csv")
    test  = load_csv(DATA / "bail_test.csv")
    all_results["bail"] = train_task("bail", train, dev, test, n_tfidf=15_000)
    del train, dev, test

    # ── Final summary ────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).seconds // 60
    print(f"\n{'='*65}")
    print(f"  ALL TASKS COMPLETE  ({elapsed} min)")
    print(f"{'='*65}")
    print(f"\n  {'Task':<12} {'Best Model':<22} {'Test F1':>8} {'Test Acc':>9}")
    print(f"  {'-'*55}")
    for task, r in all_results.items():
        bm   = r["best_model"]
        f1   = r["results"][bm]["test_f1_weighted"]
        acc  = r["results"][bm]["test_accuracy"]
        print(f"  {task:<12} {bm:<22} {f1:>8.4f} {acc:>9.4f}")

    print(f"\n  Models saved to: {OUT}/")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
