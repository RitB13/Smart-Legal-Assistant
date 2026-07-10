"""
InLegalBERT Bail Service
========================
Bail-specialist prediction service for the Case Outcome Predictor and Chatbot.

Primary:  InLegalBERT fine-tuned on IL-TUR BAIL — loads from
          src/data/models/inlegalbert/bail/ when available.
Fallback: Classical LinearSVC + TF-IDF bail model (85.8 % accuracy) used
          automatically when the InLegalBERT bail checkpoint has not been
          trained/extracted yet.

The interface is identical in either case so callers need no special handling.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

INLEGALBERT_BAIL_DIR = Path("src/data/models/inlegalbert/bail")

_instance: Optional["InLegalBertBailService"] = None


def get_inlegalbert_bail_service() -> "InLegalBertBailService":
    global _instance
    if _instance is None:
        _instance = InLegalBertBailService()
    return _instance


class InLegalBertBailService:
    """
    Unified bail prediction service.

    Tries InLegalBERT bail first; falls back to the classical LinearSVC model
    automatically.  Both return the same dict shape:

        {
            "prediction":    "Bail Granted" | "Bail Denied",
            "label":         "1" | "0",
            "confidence":    float (0–100),
            "risk_level":    "low" | "medium" | "high" | "uncertain",
            "probabilities": {"bail_granted": float, "bail_denied": float},
            "model_source":  "inlegalbert" | "classical_linear_svc",
        }
    """

    def __init__(self):
        self._bert_available = False
        self._classical_available = False
        self._bert_tokenizer = None
        self._bert_model = None
        self._bert_le = None
        self._classical_svc = None
        self._load()

    # ── Loading ────────────────────────────────────────────────────────────────

    def _load(self):
        self._try_load_bert()
        if not self._bert_available:
            self._try_load_classical()

    def _try_load_bert(self):
        if not INLEGALBERT_BAIL_DIR.exists():
            logger.info(
                "[BailSvc] InLegalBERT bail directory not found (%s) — "
                "will use classical model fallback.",
                INLEGALBERT_BAIL_DIR,
            )
            return
        try:
            import pickle
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            self._bert_tokenizer = AutoTokenizer.from_pretrained(
                str(INLEGALBERT_BAIL_DIR), local_files_only=True
            )
            self._bert_model = AutoModelForSequenceClassification.from_pretrained(
                str(INLEGALBERT_BAIL_DIR), local_files_only=True
            )
            self._bert_model.eval()
            self._bert_model.cpu()

            le_path = INLEGALBERT_BAIL_DIR / "label_encoder.pkl"
            with open(le_path, "rb") as f:
                self._bert_le = pickle.load(f)

            self._bert_available = True
            logger.info(
                "[BailSvc] InLegalBERT bail model loaded from %s (%d classes)",
                INLEGALBERT_BAIL_DIR,
                len(self._bert_le.classes_),
            )
        except Exception as e:
            logger.warning("[BailSvc] InLegalBERT bail load failed: %s — falling back.", e)

    def _try_load_classical(self):
        try:
            from src.services.bail_predictor_service import get_bail_service
            svc = get_bail_service()
            if svc.available:
                self._classical_svc = svc
                self._classical_available = True
                logger.info("[BailSvc] Classical LinearSVC bail model ready as fallback.")
            else:
                logger.warning("[BailSvc] Classical bail model also unavailable.")
        except Exception as e:
            logger.warning("[BailSvc] Could not load classical bail model: %s", e)

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._bert_available or self._classical_available

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predict whether bail will be granted for the given petition text.

        Args:
            text: Bail petition, case description, or chatbot query string.

        Returns:
            Dict with prediction, label, confidence, risk_level, probabilities,
            and model_source fields.

        Raises:
            RuntimeError: If neither bail model is available.
        """
        if not self.available:
            raise RuntimeError(
                "No bail model is available. "
                "Train the bail model or ensure classical/bail/ artifacts exist."
            )
        if self._bert_available:
            return self._predict_bert(text)
        return self._predict_classical(text)

    # ── Internal inference ─────────────────────────────────────────────────────

    def _predict_bert(self, text: str) -> Dict[str, Any]:
        import torch
        import numpy as np

        inputs = self._bert_tokenizer(
            text[:2000],
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        with torch.no_grad():
            logits = self._bert_model(**inputs).logits

        probs = torch.softmax(logits, dim=-1)[0].cpu().numpy()
        pred_idx = int(np.argmax(probs))
        pred_str = str(self._bert_le.inverse_transform([pred_idx])[0])
        confidence = float(probs[pred_idx]) * 100.0

        label_map = {"0": "Bail Denied", "1": "Bail Granted"}
        prob_granted = float(probs[1]) * 100.0 if len(probs) > 1 else (100.0 - confidence if pred_str == "0" else confidence)
        prob_denied = 100.0 - prob_granted

        return {
            "prediction":    label_map.get(pred_str, f"Class {pred_str}"),
            "label":         pred_str,
            "confidence":    round(confidence, 1),
            "risk_level":    _risk_level(pred_str, confidence),
            "probabilities": {
                "bail_granted": round(prob_granted, 1),
                "bail_denied":  round(prob_denied, 1),
            },
            "model_source":  "inlegalbert",
        }

    def _predict_classical(self, text: str) -> Dict[str, Any]:
        result = self._classical_svc.predict(text)
        result["model_source"] = "classical_linear_svc"
        return result


def _risk_level(label: str, confidence: float) -> str:
    if confidence < 55.0:
        return "uncertain"
    if label == "1":
        return "low" if confidence >= 70.0 else "medium"
    return "high" if confidence >= 70.0 else "medium"
