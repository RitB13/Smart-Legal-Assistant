"""
Case Outcome Prediction Service

Loads the trained LinearSVC + TF-IDF model and predicts binary case outcomes
(Accepted / Rejected) from case text or structured fields.

Model artifacts: src/data/classical_models/outcome/
  - best_model.pkl   — LinearSVC
  - tfidf.pkl        — TfidfVectorizer (20k features, bigrams)
  - label_encoder.pkl — LabelEncoder: ['0' → Rejected, '1' → Accepted]
"""

import logging
import pickle
import numpy as np
from typing import Dict, List, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_DIR = Path("src/data/models/classical/outcome")

VERDICT_MAP = {"0": "Rejected", "1": "Accepted"}
VERDICT_ID  = {"Rejected": 4, "Accepted": 0}

_instance = None


def get_predictor_service() -> "CaseOutcomePredictorService":
    global _instance
    if _instance is None:
        _instance = CaseOutcomePredictorService()
    return _instance


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


class CaseOutcomePredictorService:
    def __init__(self):
        self.model = None
        self.tfidf = None
        self.le    = None
        self._load()

    def _load(self):
        try:
            with open(MODEL_DIR / "best_model.pkl",    "rb") as f: self.model = pickle.load(f)
            with open(MODEL_DIR / "tfidf.pkl",         "rb") as f: self.tfidf = pickle.load(f)
            with open(MODEL_DIR / "label_encoder.pkl", "rb") as f: self.le    = pickle.load(f)
            logger.info("[OK] Classical outcome model loaded (LinearSVC + TF-IDF)")
        except Exception as e:
            logger.error(f"[ERROR] Failed to load outcome model: {e}")
            raise

    def _build_text(self, case_data: Dict[str, Any]) -> str:
        """Synthesize a text string from structured case fields."""
        description = case_data.get("description", "").strip()
        if description:
            return description[:2000]

        parts = [
            str(case_data.get("case_name", "")),
            str(case_data.get("case_type", "")),
            f"filed in {case_data.get('jurisdiction_state', '')}",
            f"year {case_data.get('year', '')}",
        ]
        if case_data.get("is_appeal"):
            parts.append("appeal case")
        legal = case_data.get("legal_representation", "")
        if legal and legal != "unknown":
            parts.append(f"legal representation {legal}")
        return " ".join(p for p in parts if p.strip())

    def _predict_proba_binary(self, X) -> Tuple[float, float]:
        """Return (prob_class0, prob_class1) using decision_function + sigmoid."""
        score = float(self.model.decision_function(X)[0])
        p1 = _sigmoid(score)
        return 1.0 - p1, p1

    def predict_outcome(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            text = self._build_text(case_data)
            X = self.tfidf.transform([text])

            pred_encoded = self.model.predict(X)[0]
            pred_label   = self.le.inverse_transform([pred_encoded])[0]
            verdict      = VERDICT_MAP.get(str(pred_label), "Unknown")

            prob_0, prob_1 = self._predict_proba_binary(X)
            conf_pct = (prob_1 if verdict == "Accepted" else prob_0) * 100.0

            risk_level = self._risk(verdict, conf_pct)

            return {
                "predicted_verdict": verdict,
                "verdict_id":        VERDICT_ID.get(verdict, 0),
                "confidence":        round(conf_pct, 1),
                "risk_level":        risk_level,
                "probabilities": {
                    "Accepted":   round(prob_1 * 100, 1),
                    "Acquitted":  0.0,
                    "Convicted":  0.0,
                    "Other":      0.0,
                    "Rejected":   round(prob_0 * 100, 1),
                    "Settlement": 0.0,
                    "Unknown":    0.0,
                },
                "warnings": [],
            }
        except Exception as e:
            logger.error(f"[ERROR] predict_outcome failed: {e}")
            raise

    def explain_prediction(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            text = self._build_text(case_data)
            X = self.tfidf.transform([text])

            # Top TF-IDF terms by weight in this document
            feature_names = np.array(self.tfidf.get_feature_names_out())
            tfidf_row     = np.asarray(X.todense()).flatten()
            top_idx       = tfidf_row.argsort()[::-1][:5]
            top_terms     = [
                {"feature": feature_names[i], "impact": round(float(tfidf_row[i]), 4)}
                for i in top_idx if tfidf_row[i] > 0
            ]

            return {
                "top_features": top_terms,
                "explanation": (
                    f"Prediction driven by key legal terms: "
                    f"{', '.join(t['feature'] for t in top_terms[:3])}."
                ),
            }
        except Exception as e:
            logger.error(f"[ERROR] explain_prediction failed: {e}")
            return {"top_features": [], "explanation": "Explanation unavailable."}

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type":    "LinearSVC",
            "model_loaded":  self.model is not None,
            "feature_count": len(self.tfidf.get_feature_names_out()) if self.tfidf else 0,
            "verdict_classes": list(VERDICT_MAP.values()),
        }

    @staticmethod
    def _risk(verdict: str, confidence_pct: float) -> str:
        if confidence_pct < 40:
            return "very_high"
        if verdict == "Accepted":
            return "low" if confidence_pct >= 70 else "medium"
        # Rejected
        return "high" if confidence_pct >= 70 else "very_high"
