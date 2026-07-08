"""
Bail Prediction Service
=======================
Loads the classical LinearSVC + TF-IDF model for binary bail prediction.

Model: src/data/models/classical/bail/
Task:  Binary classification — Bail Granted (1) vs Bail Denied (0)
Accuracy: 85.8% on held-out test set (LinearSVC, 123 k samples)
"""

import logging
import pickle
import warnings
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_DIR = Path("src/data/models/classical/bail")

LABEL_NAMES: Dict[str, str] = {
    "0": "Bail Denied",
    "1": "Bail Granted",
}

_instance: Optional["BailPredictorService"] = None


def get_bail_service() -> "BailPredictorService":
    global _instance
    if _instance is None:
        _instance = BailPredictorService()
    return _instance


class BailPredictorService:
    """
    Predicts whether bail will be granted or denied for a given petition text.

    Uses LinearSVC + TF-IDF (15 k features) trained on 123,742 samples from the
    IL-TUR bail dataset.  Confidence scores are derived from the SVM decision
    function via sigmoid normalisation (not calibrated probabilities, but
    reliable for ranking and risk classification).

    Usage:
        service = get_bail_service()
        result  = service.predict("The accused is charged with IPC 302...")
        # result = {
        #     "prediction":    "Bail Denied",
        #     "label":         "0",
        #     "confidence":    84.2,
        #     "risk_level":    "high",
        #     "probabilities": {"bail_granted": 15.8, "bail_denied": 84.2}
        # }
    """

    def __init__(self):
        self.model  = None   # LinearSVC
        self.tfidf  = None   # TfidfVectorizer
        self.le     = None   # LabelEncoder
        self._available = False
        self._load()

    def _load(self):
        if not MODEL_DIR.exists():
            logger.warning(
                "[Bail] Model directory not found: %s — "
                "train the classical model first (train_classical_models.py).",
                MODEL_DIR,
            )
            return
        try:
            # Suppress sklearn version mismatch warning: models were pickled with
            # an older sklearn build but are structurally identical at this version.
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=".*Trying to unpickle estimator.*",
                    category=UserWarning,
                )
                with open(MODEL_DIR / "tfidf.pkl", "rb") as f:
                    self.tfidf = pickle.load(f)
                with open(MODEL_DIR / "best_model.pkl", "rb") as f:
                    self.model = pickle.load(f)
                with open(MODEL_DIR / "label_encoder.pkl", "rb") as f:
                    self.le = pickle.load(f)

            self._available = True
            logger.info(
                "[Bail] Classical model loaded — %s, vocab=%d, classes: %s",
                type(self.model).__name__,
                len(self.tfidf.vocabulary_),
                self.le.classes_.tolist(),
            )

        except Exception as e:
            logger.error("[Bail] Failed to load classical model: %s", e, exc_info=True)

    @property
    def available(self) -> bool:
        return self._available

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predict bail outcome for a petition or case description.

        Args:
            text: Bail petition text or case description (up to 2000 chars used).

        Returns:
            Dict with keys:
              - prediction:    "Bail Granted" or "Bail Denied"
              - label:         "0" or "1"
              - confidence:    probability of predicted class (0–100)
              - risk_level:    "low" | "medium" | "high" | "uncertain"
              - probabilities: {"bail_granted": float, "bail_denied": float}
        """
        if not self._available:
            raise RuntimeError(
                "Bail model is not loaded. "
                "Check logs for the reason and ensure the model directory exists."
            )
        try:
            # Vectorise (TF-IDF expects an iterable)
            X = self.tfidf.transform([text[:2000]])

            # LinearSVC decision_function returns the signed distance from the
            # hyperplane: positive → classes_[1] (1 = Bail Granted),
            # negative → classes_[0] (0 = Bail Denied).
            score    = float(self.model.decision_function(X)[0])
            pred_raw = int(self.model.predict(X)[0])           # 0 or 1 (int)
            pred_str = str(self.le.inverse_transform([pred_raw])[0])  # "0" or "1"

            # Sigmoid maps the unbounded SVM score to a [0,1] interval.
            prob_granted = float(1.0 / (1.0 + np.exp(-score)))
            prob_denied  = 1.0 - prob_granted

            confidence = (prob_granted if pred_str == "1" else prob_denied) * 100.0

            return {
                "prediction":  LABEL_NAMES.get(pred_str, f"Class {pred_str}"),
                "label":       pred_str,
                "confidence":  round(confidence, 1),
                "risk_level":  self._risk(pred_str, confidence),
                "probabilities": {
                    "bail_granted": round(prob_granted * 100.0, 1),
                    "bail_denied":  round(prob_denied  * 100.0, 1),
                },
            }

        except Exception as e:
            logger.error("[Bail] predict() failed: %s", e, exc_info=True)
            raise

    @staticmethod
    def _risk(label: str, confidence: float) -> str:
        """
        Compute semantic risk level based on prediction and confidence.

        - uncertain:  confidence < 55% (model unsure)
        - low:        bail granted, high confidence
        - medium:     bail granted, low confidence OR bail denied, low confidence
        - high:       bail denied, high confidence
        """
        if confidence < 55.0:
            return "uncertain"
        if label == "1":   # Bail Granted
            return "low" if confidence >= 70.0 else "medium"
        # Bail Denied
        return "high" if confidence >= 70.0 else "medium"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type":       "LinearSVC + TF-IDF",
            "task":             "bail_prediction",
            "n_classes":        2,
            "classes":          self.le.classes_.tolist() if self.le else [],
            "label_names":      LABEL_NAMES,
            "model_loaded":     self._available,
            "model_dir":        str(MODEL_DIR),
            "test_accuracy":    0.858,
            "test_f1_weighted": 0.859,
            "training_samples": 123742,
        }
