"""
Fairness / Linguistic Privilege Classifier Training
=====================================================
Trains a Logistic Regression classifier on sentence-level rhetorical role
annotations from Indian court judgments (OpenNyAI dataset).

Label scheme:
  Privilege = 1 : ARG_PETITIONER + ARG_RESPONDENT  (formal legal argumentation)
  Privilege = 0 : FAC + NONE                        (plain narrative / factual writing)

The resulting model scores any free-text statement on a [0, 1] privilege scale.
Statements with high scores use formal legal language; low scores indicate plain
language. A large gap between the two parties triggers compensation in Layer 3.

Run from project root:
    python src/data/mediation_training/train_fairness_model.py
"""

import os
import re
import json
import pickle
import numpy as np
from collections import Counter
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "rhetorical-role-baseline-main", "train.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Legal vocabulary ─────────────────────────────────────────────────────────

LEGAL_TERMS = {
    "hereinafter", "pursuant", "aforementioned", "notwithstanding", "indemnify",
    "liability", "plaintiff", "defendant", "jurisdiction", "statute", "provision",
    "clause", "remedy", "damages", "injunction", "breach", "consideration",
    "estoppel", "negligence", "tort", "affidavit", "deposition", "subpoena",
    "arbitration", "mediation", "petitioner", "respondent", "appellant",
    "decree", "cognizance", "adjudication", "promissory", "undertaking",
    "covenant", "subrogation", "lien", "encumbrance", "caveat", "ultra",
    "vires", "prima", "facie", "locus", "standi", "bona", "fide", "inter",
    "alia", "ibid", "habeas", "corpus", "mandamus", "certiorari", "prohibition",
    "quorum", "affirmative", "averment", "contravention", "deponent",
    "enactment", "impugned", "incumbent", "indispensable", "inter", "alia",
    "ipso", "facto", "maintainable", "malfeasance", "memorandum", "novation",
    "ordinance", "pecuniary", "perusal", "privity", "promulgation", "quantum",
    "repudiation", "rescission", "restitution", "sanction", "sequestration",
    "tortfeasor", "traverse", "tribunal", "unilateral", "vicarious",
    "volenti", "whereof", "whereas", "therefor", "thereof", "therein",
    "hereof", "herein", "hereby", "heretofore",
}

SECTION_PATTERN = re.compile(
    r'[Ss]ection\s+\d+|[Aa]rticle\s+\d+|[Rr]ule\s+\d+|'
    r'\bAct\b|\bCode\b|\bSchedule\b|\bAmendment\b|'
    r'[Cc]lause\s+\(?\w+\)?|[Oo]rder\s+\w+|\bNotification\b'
)
PASSIVE_PATTERN = re.compile(
    r'\b(?:was|were|is|are|has been|have been|had been|being)\s+\w+(?:ed|en)\b'
)
HEDGE_PATTERN = re.compile(
    r'\b(?:allegedly|purportedly|ostensibly|seemingly|apparently|'
    r'contended|submitted|averred|contends|submits|avers|pleads|asserts)\b',
    re.IGNORECASE
)


# ─── Feature extraction ───────────────────────────────────────────────────────

FEATURE_NAMES = [
    "legal_term_density",
    "avg_word_length",
    "avg_sentence_length",
    "lexical_diversity",
    "citation_density",
    "passive_ratio",
    "hedge_ratio",
    "log_length_norm",
]


def compute_features(text: str) -> list:
    text = str(text).strip()
    if not text:
        return [0.0] * len(FEATURE_NAMES)

    words = text.split()
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    n_words = max(len(words), 1)
    n_sents = max(len(sentences), 1)

    clean_words = [re.sub(r"[^a-zA-Z]", "", w).lower() for w in words]
    clean_words = [w for w in clean_words if w]

    legal_density   = sum(1 for w in clean_words if w in LEGAL_TERMS) / max(len(clean_words), 1)
    avg_word_len    = float(np.mean([len(w) for w in clean_words])) if clean_words else 0.0
    avg_sent_len    = n_words / n_sents
    lex_diversity   = len(set(clean_words)) / max(len(clean_words), 1)
    citation_den    = len(SECTION_PATTERN.findall(text)) / (n_words / 100.0)
    passive_ratio   = len(PASSIVE_PATTERN.findall(text)) / n_sents
    hedge_ratio     = len(HEDGE_PATTERN.findall(text)) / n_sents
    log_len_norm    = float(np.log1p(n_words) / np.log1p(600))

    return [
        legal_density, avg_word_len, avg_sent_len, lex_diversity,
        citation_den, passive_ratio, hedge_ratio, log_len_norm,
    ]


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading {DATA_PATH} ...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Cases: {len(data)}")

    # Extract sentences by label
    by_label = Counter()
    X_data, y_data = [], []

    for case in data:
        for ann in case.get("annotations", []):
            for item in ann.get("result", []):
                text   = item.get("value", {}).get("text", "").strip()
                labels = item.get("value", {}).get("labels", [])
                if not labels or not text:
                    continue
                label = labels[0]
                by_label[label] += 1

                if label in ("ARG_PETITIONER", "ARG_RESPONDENT"):
                    y = 1
                elif label in ("FAC", "NONE"):
                    y = 0
                else:
                    continue  # skip PREAMBLE, ANALYSIS etc. (ambiguous privilege)

                X_data.append(compute_features(text))
                y_data.append(y)

    print("\nSentences per label:")
    for label, count in by_label.most_common():
        print(f"  {label}: {count}")

    X = np.array(X_data, dtype=np.float32)
    y = np.array(y_data, dtype=np.int32)
    print(f"\nTraining samples: {len(X)}")
    print(f"  Privilege=1 (ARG): {(y==1).sum()}")
    print(f"  Privilege=0 (FAC/NONE): {(y==0).sum()}")

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Cross-validation
    clf_cv = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42, C=1.0)
    cv_scores = cross_val_score(clf_cv, X_scaled, y, cv=5, scoring="roc_auc")
    print(f"\nCross-validation AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Final train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    clf = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42, C=1.0)
    clf.fit(X_train, y_train)

    y_prob = clf.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    auc = roc_auc_score(y_test, y_prob)
    print(f"Test AUC: {auc:.4f}")
    print(classification_report(y_test, y_pred, target_names=["Low privilege (FAC/NONE)", "High privilege (ARG)"]))

    # Feature importance (logistic regression coefficients)
    print("\nFeature coefficients:")
    for name, coef in sorted(zip(FEATURE_NAMES, clf.coef_[0]), key=lambda x: -abs(x[1])):
        print(f"  {name}: {coef:+.4f}")

    # Save
    clf_path    = os.path.join(OUTPUT_DIR, "fairness_clf.pkl")
    scaler_path = os.path.join(OUTPUT_DIR, "fairness_scaler.pkl")
    meta_path   = os.path.join(OUTPUT_DIR, "fairness_meta.json")

    with open(clf_path, "wb") as f:
        pickle.dump(clf, f)
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    meta = {
        "features": FEATURE_NAMES,
        "auc": round(auc, 4),
        "cv_auc_mean": round(float(cv_scores.mean()), 4),
        "cv_auc_std": round(float(cv_scores.std()), 4),
        "bias_detection_threshold": 0.12,
        "description": (
            "Logistic regression trained on Indian court judgment sentence-level "
            "rhetorical role annotations (OpenNyAI InRhetoricalRoles dataset). "
            "Outputs P(formal legal argumentation style) as a linguistic privilege score. "
            "High score = formal legal writing (ARG_PETITIONER/RESPONDENT style); "
            "Low score = plain factual/narrative writing (FAC/NONE style)."
        ),
        "training_labels": {
            "high_privilege": ["ARG_PETITIONER", "ARG_RESPONDENT"],
            "low_privilege": ["FAC", "NONE"],
        },
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved:")
    print(f"  {clf_path}")
    print(f"  {scaler_path}")
    print(f"  {meta_path}")
    print(f"\nDone. AUC={auc:.4f}")


if __name__ == "__main__":
    main()
