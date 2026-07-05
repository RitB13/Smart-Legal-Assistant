"""
Fairness / Rhetorical Role Prediction Service
==============================================
Loads the fine-tuned InLegalBERT model for 13-class rhetorical role
classification of Indian court judgment sentences.

Model: src/data/inlegalbert_fairness_final/
Task:  Sentence-level rhetorical role tagging (IL-TUR RR dataset)
"""

import logging
import pickle
import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_DIR = Path("src/data/models/inlegalbert/fairness")

# Rhetorical role names — integer labels from IL-TUR RR dataset (CL + IT variants)
# The label encoder classes are alphabetically sorted strings of the integer labels:
# ['0','1','10','11','12','2','3','4','5','6','7','8','9']
ROLE_NAMES: Dict[str, str] = {
    "0":  "Facts",
    "1":  "Ruling by Lower Court",
    "2":  "Argument",
    "3":  "Statute",
    "4":  "Precedent Relied",
    "5":  "Precedent Not Relied",
    "6":  "Ratio of the Decision",
    "7":  "Analysis",
    "8":  "Other",
    "9":  "Issue",
    "10": "Preamble",
    "11": "None",
    "12": "Ruling by Present Court",
}

_instance: Optional["FairnessPredictorService"] = None


def get_fairness_service() -> "FairnessPredictorService":
    global _instance
    if _instance is None:
        _instance = FairnessPredictorService()
    return _instance


class FairnessPredictorService:
    """
    Predicts the rhetorical role of a sentence from an Indian court judgment.

    Usage:
        service = get_fairness_service()
        result  = service.predict("The appellant filed an appeal against the order.")
        # result = {
        #     "label":       "1",
        #     "role":        "Ruling by Lower Court",
        #     "confidence":  72.4,
        #     "probabilities": {"0": 3.1, "1": 72.4, ...}
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
                "[Fairness] Model directory not found: %s — "
                "extract inlegalbert_fairness_final.zip first.",
                MODEL_DIR,
            )
            return
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            logger.info("[Fairness] Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(MODEL_DIR), local_files_only=True
            )

            logger.info("[Fairness] Loading model...")
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(MODEL_DIR), local_files_only=True
            )
            self.model.eval()
            self.model.cpu()   # CPU inference for production

            le_path = MODEL_DIR / "label_encoder.pkl"
            with open(le_path, "rb") as f:
                self.le = pickle.load(f)

            n_classes = len(self.le.classes_)
            logger.info(
                "[Fairness] Model loaded — %d classes: %s",
                n_classes, self.le.classes_.tolist()
            )
            self._available = True

        except ImportError:
            logger.error("[Fairness] torch/transformers not installed — model unavailable")
        except Exception as e:
            logger.error("[Fairness] Failed to load model: %s", e, exc_info=True)

    @property
    def available(self) -> bool:
        return self._available

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predict the rhetorical role of a single sentence.

        Args:
            text: A sentence or short paragraph from a court judgment.

        Returns:
            Dict with keys:
              - label:         raw label string ("0"–"12")
              - role:          human-readable role name
              - confidence:    probability of predicted class (0–100)
              - probabilities: {label_str: probability_pct} for all classes
        """
        if not self._available:
            raise RuntimeError(
                "Fairness model is not loaded. "
                "Check logs for the reason and ensure the model directory exists."
            )
        try:
            import torch

            inputs = self.tokenizer(
                text[:2000],
                return_tensors = "pt",
                truncation     = True,
                max_length     = 512,
                padding        = True,
            )
            with torch.no_grad():
                logits = self.model(**inputs).logits   # (1, n_classes)

            probs    = torch.softmax(logits, dim=-1)[0].cpu().numpy()  # (n_classes,)
            pred_idx = int(np.argmax(probs))

            # le.inverse_transform returns the original string label e.g. "10"
            pred_str   = str(self.le.inverse_transform([pred_idx])[0])
            confidence = float(probs[pred_idx]) * 100.0

            all_probs = {
                str(self.le.inverse_transform([i])[0]): round(float(p) * 100.0, 2)
                for i, p in enumerate(probs)
            }

            return {
                "label":         pred_str,
                "role":          ROLE_NAMES.get(pred_str, f"Role {pred_str}"),
                "confidence":    round(confidence, 1),
                "probabilities": all_probs,
            }

        except Exception as e:
            logger.error("[Fairness] predict() failed: %s", e, exc_info=True)
            raise

    def predict_batch(self, texts: List[str], batch_size: int = 8) -> List[Dict[str, Any]]:
        """
        Predict rhetorical roles for a list of sentences.

        Args:
            texts:      List of sentence strings.
            batch_size: Number of sentences to process at once.

        Returns:
            List of result dicts (same structure as predict()).
        """
        if not self._available:
            raise RuntimeError("Fairness model is not loaded.")

        try:
            import torch

            results = []
            for start in range(0, len(texts), batch_size):
                batch = [t[:2000] for t in texts[start:start + batch_size]]

                inputs = self.tokenizer(
                    batch,
                    return_tensors = "pt",
                    truncation     = True,
                    max_length     = 512,
                    padding        = True,
                )
                with torch.no_grad():
                    logits = self.model(**inputs).logits   # (B, n_classes)

                probs_batch = torch.softmax(logits, dim=-1).cpu().numpy()  # (B, n_classes)

                for probs in probs_batch:
                    pred_idx   = int(np.argmax(probs))
                    pred_str   = str(self.le.inverse_transform([pred_idx])[0])
                    confidence = float(probs[pred_idx]) * 100.0
                    all_probs  = {
                        str(self.le.inverse_transform([i])[0]): round(float(p) * 100.0, 2)
                        for i, p in enumerate(probs)
                    }
                    results.append({
                        "label":         pred_str,
                        "role":          ROLE_NAMES.get(pred_str, f"Role {pred_str}"),
                        "confidence":    round(confidence, 1),
                        "probabilities": all_probs,
                    })

            return results

        except Exception as e:
            logger.error("[Fairness] predict_batch() failed: %s", e, exc_info=True)
            raise

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type":   "InLegalBERT",
            "task":         "rhetorical_role_classification",
            "n_classes":    len(self.le.classes_) if self.le else 0,
            "classes":      self.le.classes_.tolist() if self.le else [],
            "role_names":   ROLE_NAMES,
            "model_loaded": self._available,
            "model_dir":    str(MODEL_DIR),
        }
