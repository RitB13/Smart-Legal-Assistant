"""
Case Outcome Prediction Service — InLegalBERT Backend

Loads the fine-tuned InLegalBERT model for binary outcome classification
(Accepted / Rejected) trained on NyayaAnumana + IL-TUR CJPE + Jud-IPL.

Model artifacts: src/data/models/inlegalbert/outcome/
  - model.safetensors   — fine-tuned InLegalBERT weights
  - config.json         — model architecture config
  - tokenizer.json      — tokenizer vocab
  - label_encoder.pkl   — LabelEncoder: ['0' → Rejected, '1' → Accepted]
"""

import json
import logging
import pickle
import numpy as np
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_DIR = Path("src/data/models/inlegalbert/outcome")

_instance: Optional["CaseOutcomePredictorService"] = None


def get_predictor_service() -> "CaseOutcomePredictorService":
    global _instance
    if _instance is None:
        _instance = CaseOutcomePredictorService()
    return _instance


class CaseOutcomePredictorService:

    def __init__(self):
        self.tokenizer  = None
        self.model      = None
        self.le         = None
        self._available = False
        self._load()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load(self):
        if not MODEL_DIR.exists():
            logger.warning("[Outcome] Model directory not found: %s", MODEL_DIR)
            return
        try:
            import torch  # noqa: F401
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            logger.info("[Outcome] Loading InLegalBERT tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(MODEL_DIR), local_files_only=True
            )

            logger.info("[Outcome] Loading InLegalBERT model...")
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(MODEL_DIR), local_files_only=True,
                attn_implementation="eager",  # sdpa does not support output_attentions=True
            )
            self.model.eval()
            self.model.cpu()

            with open(MODEL_DIR / "label_encoder.pkl", "rb") as f:
                self.le = pickle.load(f)

            logger.info(
                "[Outcome] InLegalBERT loaded — classes: %s",
                self.le.classes_.tolist(),
            )
            self._available = True

        except ImportError:
            logger.error("[Outcome] torch / transformers not installed — model unavailable")
        except Exception as e:
            logger.error("[Outcome] Failed to load model: %s", e, exc_info=True)

    # ── Text builder ──────────────────────────────────────────────────────────

    def _build_text(self, case_data: Dict[str, Any]) -> str:
        desc = str(case_data.get("description", "")).strip()
        if desc and len(desc) > 50:
            return desc[:2000]

        parts = [
            str(case_data.get("case_name", "")),
            str(case_data.get("case_type", "")),
            f"filed in {case_data.get('jurisdiction_state', '')}",
            f"year {case_data.get('year', '')}",
        ]
        if case_data.get("is_appeal"):
            parts.append("appeal case")
        legal = str(case_data.get("legal_representation", ""))
        if legal and legal not in ("unknown", "None", ""):
            parts.append(f"legal representation {legal}")
        return " ".join(p for p in parts if p.strip() and p.strip() != "None")

    def _label_to_verdict(self, label_str: str) -> str:
        return "Accepted" if str(label_str) == "1" else "Rejected"

    # ── Core inference ────────────────────────────────────────────────────────

    def _infer(self, text: str):
        """Run one forward pass; returns (probs_np, pred_idx, inputs, outputs)."""
        import torch  # noqa: F811
        inputs = self.tokenizer(
            text[:2000],
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        with torch.no_grad():
            outputs = self.model(**inputs, output_attentions=True)
        probs = torch.softmax(outputs.logits, dim=-1)[0].cpu().numpy()
        pred_idx = int(np.argmax(probs))
        return probs, pred_idx, inputs, outputs

    # ── Public API ────────────────────────────────────────────────────────────

    def predict_outcome(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            raise RuntimeError("Outcome model is not loaded. Check logs for details.")
        try:
            text = self._build_text(case_data)
            probs, pred_idx, _inputs, _outputs = self._infer(text)

            pred_label = str(self.le.inverse_transform([pred_idx])[0])
            verdict    = self._label_to_verdict(pred_label)
            confidence = round(float(probs[pred_idx]) * 100.0, 1)

            prob_accepted, prob_rejected = 0.0, 0.0
            for i, cls in enumerate(self.le.classes_):
                p = round(float(probs[i]) * 100.0, 1)
                if str(cls) == "1":
                    prob_accepted = p
                else:
                    prob_rejected = p

            return {
                "predicted_verdict": verdict,
                "verdict_id":        0 if verdict == "Accepted" else 4,
                "confidence":        confidence,
                "risk_level":        self._risk(verdict, confidence),
                "warnings":          [],
                "probabilities": {
                    "Accepted":   prob_accepted,
                    "Acquitted":  0.0,
                    "Convicted":  0.0,
                    "Other":      0.0,
                    "Rejected":   prob_rejected,
                    "Settlement": 0.0,
                    "Unknown":    0.0,
                },
            }
        except Exception as e:
            logger.error("[Outcome] predict_outcome failed: %s", e, exc_info=True)
            raise

    def batch_predict(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self._available:
            raise RuntimeError("Outcome model is not loaded.")
        predictions: List[Dict[str, Any]] = []
        failures:    List[Dict[str, Any]] = []

        for i, case_data in enumerate(cases):
            try:
                r = self.predict_outcome(case_data)
                predictions.append({
                    "case_index":    i,
                    "verdict":       r["predicted_verdict"],
                    "verdict_id":    r["verdict_id"],
                    "probability":   round(r["confidence"] / 100.0, 4),
                    "confidence":    r["confidence"],
                    "risk_level":    r["risk_level"],
                    "probabilities": r["probabilities"],
                })
            except Exception as e:
                failures.append({"case_index": i, "error": str(e)})

        return {
            "summary": {
                "total":      len(cases),
                "successful": len(predictions),
                "failed":     len(failures),
            },
            "predictions": predictions,
            "failures":    failures,
        }

    def explain_prediction(
        self, case_data: Dict[str, Any], num_top_features: int = 5
    ) -> Dict[str, Any]:
        """
        Attention-saliency explanation: identifies which tokens the model
        focused on most when making its prediction (CLS→token attention,
        averaged over all heads in the last layer).
        """
        if not self._available:
            return {
                "method":                "unavailable",
                "top_positive_features": [],
                "top_negative_features": [],
                "summary":               "Model not loaded.",
                "model_certainty":       0.0,
            }
        try:
            text = self._build_text(case_data)
            probs, pred_idx, inputs, outputs = self._infer(text)

            # Last-layer attention, averaged over all heads, CLS token → each token
            last_attn  = outputs.attentions[-1]               # (1, heads, seq, seq)
            cls_attn   = last_attn[0, :, 0, :].mean(dim=0)   # (seq,)
            cls_attn   = cls_attn.cpu().numpy()

            tokens = self.tokenizer.convert_ids_to_tokens(
                inputs["input_ids"][0].tolist()
            )

            SPECIAL = {"[CLS]", "[SEP]", "[PAD]", "<s>", "</s>", "<pad>"}

            # Merge consecutive BERT subword tokens into whole words before scoring.
            # e.g. ["securit", "##isation"] → ("securitisation", avg_score)
            # This prevents partial tokens like "securit" appearing as features.
            merged: list = []
            for tok, score in zip(tokens, cls_attn):
                if tok in SPECIAL:
                    continue
                if tok.startswith("##") and merged:
                    word, sc_sum, count = merged[-1]
                    merged[-1] = (word + tok[2:], sc_sum + float(score), count + 1)
                else:
                    merged.append((tok, float(score), 1))

            token_scores = [
                (word, sc_sum / count)
                for word, sc_sum, count in merged
                if len(word) >= 3
            ]
            token_scores.sort(key=lambda x: x[1], reverse=True)

            top_pos = [
                {"feature": tok, "impact": round(sc, 4)}
                for tok, sc in token_scores[:num_top_features]
            ]
            top_neg = [
                {"feature": tok, "impact": round(sc, 4)}
                for tok, sc in reversed(token_scores[-num_top_features:])
            ]

            verdict    = self._label_to_verdict(str(self.le.inverse_transform([pred_idx])[0]))
            confidence = float(probs[pred_idx])
            key_terms  = ", ".join(t["feature"] for t in top_pos[:3]) or "N/A"

            return {
                "method":                "attention_saliency",
                "top_positive_features": top_pos,
                "top_negative_features": top_neg,
                "summary": (
                    f"Prediction: '{verdict}' with {confidence * 100:.1f}% confidence. "
                    f"Key legal terms the model focused on: {key_terms}."
                ),
                "model_certainty": round(confidence, 4),
            }

        except Exception as e:
            logger.warning("[Outcome] explain_prediction failed: %s", e)
            return {
                "method":                "unavailable",
                "top_positive_features": [],
                "top_negative_features": [],
                "summary":               "Explanation unavailable.",
                "model_certainty":       0.5,
            }

    def compose_petition_text(
        self,
        statement: str,
        relief_sought: str,
        role: str,
        jurisdiction: str,
        case_type: str,
    ) -> str:
        """
        Converts the user's plain-language answers into a formal Indian legal
        petition summary that InLegalBERT understands.

        InLegalBERT was trained on NyayaAnumana / ILDC / Jud-IPL — all formal
        High Court / Supreme Court petition text.  Bridging the gap between a
        user's informal language and that register dramatically improves
        prediction quality.

        Falls back to a structured template if the LLM call fails so prediction
        always continues.
        """
        from src.services.llm_service import get_legal_response

        role_label = "petitioner / complainant" if role == "petitioner" else "respondent / accused"

        prompt = (
            "You are a legal analyst writing a neutral case synopsis for a court record.\n"
            "Write a concise factual summary (4–6 sentences) in formal Indian judicial language "
            "— the register used in High Court and Supreme Court case synopses.\n"
            "Describe the facts as they occurred: what happened, what documents or agreements "
            "exist, what the other party's position is, and what the filing party seeks.\n"
            "IMPORTANT: Do NOT argue for either side. Include any facts that weaken the filing "
            "party's claim — an accurate summary must reflect the full picture, not just the "
            "petitioner's version. Do NOT invent facts. Write only the summary — "
            "no headings, no bullet points, no explanation.\n\n"
            f"Filing party's role: {role_label}\n"
            f"What happened (in their words): {statement[:800]}\n"
            f"Relief / outcome they are seeking: {relief_sought}\n"
            f"Case category: {case_type}\n"
            f"Jurisdiction: {jurisdiction}\n"
        )

        try:
            raw = get_legal_response(prompt, language="en", max_tokens=400, temperature=0.15)
            composed = raw.strip()
            if len(composed) >= 80:
                logger.info("[Outcome] Petition text composed (%d chars)", len(composed))
                return composed[:2000]
        except Exception as e:
            logger.warning("[Outcome] LLM petition composition failed: %s", e)

        # Structured fallback — still much better than raw user text for the model
        return (
            f"The {role_label} approaches this court in a matter of {case_type.replace('_', ' ')} "
            f"arising in the jurisdiction of {jurisdiction}. "
            f"{statement.strip()} "
            f"The {role_label} seeks the following relief from this court: {relief_sought}."
        )

    def enrich_with_llm(
        self,
        prediction: Dict[str, Any],
        case_data:  Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Passes the ML model's raw prediction to the LLM to produce a
        professional, presentation-quality legal analysis.

        The ML model makes the verdict decision.
        The LLM only formats and explains that decision — it cannot override it.
        """
        from src.services.llm_service import get_legal_response

        verdict    = prediction.get("predicted_verdict", prediction.get("verdict", "Unknown"))
        confidence = float(prediction.get("confidence", 50.0))
        risk_level = prediction.get("risk_level", "medium")
        case_name  = str(case_data.get("case_name", ""))
        case_type  = str(case_data.get("case_type", ""))
        jurisdiction = str(case_data.get("jurisdiction_state", "India"))
        description  = str(case_data.get("description", "")).strip()

        conf_label = (
            "very high" if confidence >= 85 else
            "high"      if confidence >= 70 else
            "moderate"  if confidence >= 55 else
            "low"
        )

        prompt = (
            "You are a senior Indian legal analyst. A machine learning model trained on Indian "
            "court judgments has predicted the outcome of a case. Present this professionally.\n\n"
            "CASE DETAILS:\n"
            f"- Case: {case_name}\n"
            f"- Type: {case_type}\n"
            f"- Jurisdiction: {jurisdiction}\n"
            f"- Description: {description[:500] if description else 'Not provided'}\n\n"
            "ML MODEL PREDICTION (THE VERDICT IS FINAL — DO NOT CHANGE IT):\n"
            f"- Verdict: {verdict}\n"
            f"- Confidence: {confidence:.1f}% ({conf_label})\n"
            f"- Risk Level: {risk_level}\n\n"
            "Return ONLY valid JSON with no extra text:\n"
            "{\n"
            '  "verdict_summary": "<2-3 sentences: plain-English summary of what this prediction means>",\n'
            '  "legal_reasoning": "<3-4 sentences: likely legal basis under Indian law for this outcome>",\n'
            '  "applicable_laws": ["<Indian statute/section 1>", "<statute 2>", "<statute 3>"],\n'
            '  "key_factors": ["<factor influencing prediction 1>", "<factor 2>", "<factor 3>"],\n'
            '  "risk_assessment": "<1-2 sentences: practical implications of the risk level>",\n'
            '  "recommendations": ["<concrete next step 1>", "<next step 2>", "<next step 3>"],\n'
            f'  "confidence_note": "<1 sentence on what {confidence:.0f}% confidence means practically>",\n'
            '  "counter_arguments": ["<respondent\'s strongest legal argument 1>", "<argument 2>", "<argument 3>"]\n'
            "}"
        )

        try:
            raw     = get_legal_response(prompt, language="en", max_tokens=1200, temperature=0.2)
            cleaned = raw.strip()
            # Strip markdown fences if the LLM wraps JSON in ```
            if "```" in cleaned:
                for block in cleaned.split("```"):
                    if "{" in block:
                        cleaned = block.strip()
                        if cleaned.startswith("json"):
                            cleaned = cleaned[4:].strip()
                        break
            return json.loads(cleaned)

        except json.JSONDecodeError:
            # Try to extract the JSON object if surrounded by prose
            try:
                start = raw.index("{")
                end   = raw.rindex("}") + 1
                return json.loads(raw[start:end])
            except Exception:
                pass
        except Exception as e:
            logger.warning("[Outcome] LLM enrichment failed: %s", e)

        # Safe fallback — app still works even if LLM is down
        return {
            "verdict_summary":  f"The model predicts this case will be {verdict} with {confidence:.1f}% confidence.",
            "legal_reasoning":  "Based on patterns learned from thousands of Indian court judgments.",
            "applicable_laws":  [],
            "key_factors":      [],
            "risk_assessment":  f"Risk level is {risk_level}.",
            "recommendations":  ["Consult a qualified legal professional for detailed advice."],
            "confidence_note":  f"The model is {conf_label} confident in this prediction.",
        }

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type":      "InLegalBERT",
            "model_loaded":    self._available,
            "feature_count":   512,
            "feature_names":   ["Transformer attention over full case text (512 tokens)"],
            "verdict_classes": ["Accepted", "Rejected"],
            "shap_available":  False,
            "metadata": {
                "base_model":    "law-ai/InLegalBERT",
                "task":          "binary_outcome_classification",
                "dataset":       "NyayaAnumana + IL-TUR CJPE (ILDC) + Jud-IPL",
                "test_accuracy": "68.0%",
                "f1_weighted":   "67.6%",
                "f1_macro":      "67.7%",
                "model_dir":     str(MODEL_DIR),
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _risk(verdict: str, confidence_pct: float) -> str:
        """
        Risk from the PETITIONER's perspective.
        Accepted at low confidence is still very risky — near coin-flip territory.
        Any Rejected verdict carries high or very-high risk.
        """
        if verdict == "Rejected":
            return "very_high" if confidence_pct >= 65 else "high"
        # Accepted:
        if confidence_pct >= 80:
            return "low"
        if confidence_pct >= 70:
            return "medium"
        if confidence_pct >= 60:
            return "high"
        return "very_high"   # < 60% Accepted ≈ coin flip — very risky
