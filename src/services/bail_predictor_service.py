"""
Bail Prediction Service
=======================
Loads the fine-tuned InLegalBERT model for binary bail prediction.

Model: src/data/inlegalbert_bail_final/
Task:  Binary classification — Bail Granted (1) vs Bail Denied (0)
"""

import logging
import pickle
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_DIR = Path("src/data/models/inlegalbert/bail")

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
        self.tokenizer  = None
        self.model      = None
        self.le         = None
        self._available = False
        self._load()

    def _load(self):
        if not MODEL_DIR.exists():
            logger.warning(
                "[Bail] Model directory not found: %s — "
                "download and extract inlegalbert_bail_final.zip first.",
                MODEL_DIR,
            )
            return
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            logger.info("[Bail] Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(MODEL_DIR), local_files_only=True
            )

            logger.info("[Bail] Loading model...")
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(MODEL_DIR), local_files_only=True
            )
            self.model.eval()
            self.model.cpu()   # CPU inference for production

            le_path = MODEL_DIR / "label_encoder.pkl"
            with open(le_path, "rb") as f:
                self.le = pickle.load(f)

            logger.info(
                "[Bail] Model loaded — classes: %s",
                self.le.classes_.tolist()
            )
            self._available = True

        except ImportError:
            logger.error("[Bail] torch/transformers not installed — model unavailable")
        except Exception as e:
            logger.error("[Bail] Failed to load model: %s", e, exc_info=True)

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
            import torch

            inputs = self.tokenizer(
                text[:2000],
                return_tensors = "pt",
                truncation     = True,
                max_length     = 256,   # trained at 256 tokens
                padding        = True,
            )
            with torch.no_grad():
                logits = self.model(**inputs).logits   # (1, 2)

            probs    = torch.softmax(logits, dim=-1)[0].cpu().numpy()  # (2,)
            pred_idx = int(np.argmax(probs))
            pred_str = str(self.le.inverse_transform([pred_idx])[0])   # "0" or "1"
            confidence = float(probs[pred_idx]) * 100.0

            # Map class probabilities to named keys
            prob_granted = 0.0
            prob_denied  = 0.0
            for i, p in enumerate(probs):
                label = str(self.le.inverse_transform([i])[0])
                if label == "1":
                    prob_granted = float(p) * 100.0
                else:
                    prob_denied  = float(p) * 100.0

            return {
                "prediction":  LABEL_NAMES.get(pred_str, f"Class {pred_str}"),
                "label":       pred_str,
                "confidence":  round(confidence, 1),
                "risk_level":  self._risk(pred_str, confidence),
                "probabilities": {
                    "bail_granted": round(prob_granted, 1),
                    "bail_denied":  round(prob_denied,  1),
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
            "model_type":   "InLegalBERT",
            "task":         "bail_prediction",
            "n_classes":    2,
            "classes":      self.le.classes_.tolist() if self.le else [],
            "label_names":  LABEL_NAMES,
            "model_loaded": self._available,
            "model_dir":    str(MODEL_DIR),
        }
