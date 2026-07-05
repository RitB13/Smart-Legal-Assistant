"""
Mediation ML Service
====================
Loads and serves the two trained models for AI-Mediated Dispute Resolution:

  1. Settlement Range Model (LightGBM)
     - Trained on 71k Indian court cases (AUC 0.77)
     - Predicts P(petition accepted) given case_type + state + year
     - Converts probability into a monetary settlement range

  2. Fairness / Privilege Classifier (Logistic Regression)
     - Trained on 9,180 sentences from OpenNyAI InRhetoricalRoles dataset (AUC 0.72)
     - Outputs P(formal legal argumentation style) as a privilege score
     - Used by compute_fairness_audit() in mediation_service.py

Both models gracefully fall back to heuristics if artifacts are missing.
"""

import os
import re
import json
import pickle
import logging
import numpy as np
from typing import List, Optional

from src.models.mediation_model import SettlementRange

logger = logging.getLogger(__name__)

_MODEL_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "models", "mediation")
)

# ─── Legal vocabulary (matches training script exactly) ───────────────────────

_LEGAL_TERMS = {
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
    "enactment", "impugned", "incumbent", "indispensable", "ipso", "facto",
    "maintainable", "malfeasance", "memorandum", "novation", "ordinance",
    "pecuniary", "perusal", "privity", "promulgation", "quantum", "repudiation",
    "rescission", "restitution", "sanction", "sequestration", "tortfeasor",
    "traverse", "tribunal", "unilateral", "vicarious", "volenti", "whereof",
    "whereas", "therefor", "thereof", "therein", "hereof", "herein",
    "hereby", "heretofore",
}

_SECTION_PAT = re.compile(
    r"[Ss]ection\s+\d+|[Aa]rticle\s+\d+|[Rr]ule\s+\d+|"
    r"\bAct\b|\bCode\b|\bSchedule\b|\bAmendment\b|"
    r"[Cc]lause\s+\(?\w+\)?|[Oo]rder\s+\w+|\bNotification\b"
)
_PASSIVE_PAT = re.compile(
    r"\b(?:was|were|is|are|has been|have been|had been|being)\s+\w+(?:ed|en)\b"
)
_HEDGE_PAT = re.compile(
    r"\b(?:allegedly|purportedly|ostensibly|seemingly|apparently|"
    r"contended|submitted|averred|contends|submits|avers|pleads|asserts)\b",
    re.IGNORECASE,
)

_MEDIATION_TO_MODEL_TYPE = {
    "property":   "property",
    "money":      "appeal",
    "family":     "family",
    "employment": "appeal",
    "consumer":   "petition",
    "contract":   "contract",
    "general":    "other",
    "other":      "other",
}


# ─── Feature computation (identical to training) ──────────────────────────────

def _compute_features(text: str) -> List[float]:
    text = str(text).strip()
    if not text:
        return [0.0] * 8

    words = text.split()
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    n_words = max(len(words), 1)
    n_sents = max(len(sentences), 1)

    clean = [re.sub(r"[^a-zA-Z]", "", w).lower() for w in words]
    clean = [w for w in clean if w]

    legal_density  = sum(1 for w in clean if w in _LEGAL_TERMS) / max(len(clean), 1)
    avg_word_len   = float(np.mean([len(w) for w in clean])) if clean else 0.0
    avg_sent_len   = n_words / n_sents
    lex_diversity  = len(set(clean)) / max(len(clean), 1)
    citation_den   = len(_SECTION_PAT.findall(text)) / (n_words / 100.0)
    passive_ratio  = len(_PASSIVE_PAT.findall(text)) / n_sents
    hedge_ratio    = len(_HEDGE_PAT.findall(text)) / n_sents
    log_len_norm   = float(np.log1p(n_words) / np.log1p(600))

    return [
        legal_density, avg_word_len, avg_sent_len, lex_diversity,
        citation_den, passive_ratio, hedge_ratio, log_len_norm,
    ]


_LAKH_PAT  = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs)", re.IGNORECASE)
_CRORE_PAT = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:crore|crores|cr\.?)", re.IGNORECASE)


def _parse_amounts(amount_list: List[str]) -> List[float]:
    """Extract numeric values from LLM-extracted amount strings.

    Handles Indian currency units: lakh (1e5) and crore (1e7).
    Also handles comma-formatted numbers and ₹/Rs prefixes.
    """
    results = []
    for item in amount_list:
        text = str(item)

        # Handle "X lakh(s)" and "X crore(s)" first
        for match in _LAKH_PAT.finditer(text):
            try:
                results.append(float(match.group(1).replace(",", "")) * 100_000)
            except ValueError:
                pass

        for match in _CRORE_PAT.finditer(text):
            try:
                results.append(float(match.group(1).replace(",", "")) * 10_000_000)
            except ValueError:
                pass

        # Remove lakh/crore tokens so raw number extraction doesn't double-count
        cleaned = _LAKH_PAT.sub("", _CRORE_PAT.sub("", text))
        cleaned = cleaned.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("INR", "")

        for n in re.findall(r"\d+(?:\.\d+)?", cleaned):
            try:
                v = float(n)
                if v >= 100:  # ignore single/double-digit noise
                    results.append(v)
            except ValueError:
                pass

    return results


# ─── Service class ─────────────────────────────────────────────────────────────

class MediationMLService:

    def __init__(self):
        self._settlement_model   = None
        self._settlement_enc     = None
        self._settlement_meta    = None
        self._fairness_clf       = None
        self._fairness_scaler    = None
        self._fairness_meta      = None
        self._load_models()

    def _load_models(self):
        # Settlement model
        try:
            with open(os.path.join(_MODEL_DIR, "settlement_lgbm.pkl"), "rb") as f:
                self._settlement_model = pickle.load(f)
            with open(os.path.join(_MODEL_DIR, "settlement_encoders.pkl"), "rb") as f:
                self._settlement_enc = pickle.load(f)
            with open(os.path.join(_MODEL_DIR, "settlement_meta.json")) as f:
                self._settlement_meta = json.load(f)
            logger.info(f"[MediationML] Settlement model loaded (AUC={self._settlement_meta.get('auc')})")
        except FileNotFoundError:
            logger.warning("[MediationML] Settlement model artifacts not found — using base-rate fallback")
        except Exception as e:
            logger.error(f"[MediationML] Failed to load settlement model: {e}")

        # Fairness classifier
        try:
            with open(os.path.join(_MODEL_DIR, "fairness_clf.pkl"), "rb") as f:
                self._fairness_clf = pickle.load(f)
            with open(os.path.join(_MODEL_DIR, "fairness_scaler.pkl"), "rb") as f:
                self._fairness_scaler = pickle.load(f)
            with open(os.path.join(_MODEL_DIR, "fairness_meta.json")) as f:
                self._fairness_meta = json.load(f)
            logger.info(f"[MediationML] Fairness classifier loaded (AUC={self._fairness_meta.get('auc')})")
        except FileNotFoundError:
            logger.warning("[MediationML] Fairness model artifacts not found — using vocabulary heuristic")
        except Exception as e:
            logger.error(f"[MediationML] Failed to load fairness classifier: {e}")

    # ── Public API ──────────────────────────────────────────────────────────────

    @property
    def settlement_available(self) -> bool:
        return self._settlement_model is not None

    @property
    def fairness_available(self) -> bool:
        return self._fairness_clf is not None

    def predict_acceptance_probability(self, case_type: str, state: str, year: int) -> float:
        """
        Returns P(petition accepted) for the given case profile.
        Falls back to the historical base rate (0.25) if the model is unavailable.
        """
        if not self.settlement_available:
            return 0.25

        try:
            meta = self._settlement_meta
            enc  = self._settlement_enc

            mapped_type  = meta["mediation_to_model_type"].get(case_type.lower().strip(), "other")
            type_classes = enc["type_encoder"].classes_.tolist()
            state_classes = enc["state_encoder"].classes_.tolist()

            type_idx  = type_classes.index(mapped_type) if mapped_type in type_classes else type_classes.index("other")
            state_idx = state_classes.index(state) if state in state_classes else 0
            year_norm = np.clip((year - meta["year_min"]) / (meta["year_max"] - meta["year_min"]), 0.0, 1.0)

            import pandas as _pd
            X = _pd.DataFrame(
                [[type_idx, state_idx, float(year_norm)]],
                columns=self._settlement_meta["features"]
            )
            prob = float(self._settlement_model.predict_proba(X)[0][1])
            logger.debug(f"[MediationML] P(accepted) for ({case_type},{state},{year}) = {prob:.3f}")
            return prob

        except Exception as e:
            logger.error(f"[MediationML] Acceptance probability prediction failed: {e}")
            return 0.25

    def compute_settlement_range(
        self,
        case_type: str,
        state: str,
        year: int,
        amounts_a: List[str],
        amounts_b: List[str],
    ) -> SettlementRange:
        """
        Compute a data-driven settlement range.

        Uses P(accepted) from the LightGBM model to determine what fraction of
        the claimed amount is a fair settlement. When both parties mention monetary
        amounts the range is anchored between the two sets of claims.
        """
        p_accept = self.predict_acceptance_probability(case_type, state, year)

        parsed_a = _parse_amounts(amounts_a)
        parsed_b = _parse_amounts(amounts_b)
        all_amounts = parsed_a + parsed_b

        confidence = 0.68 if self.settlement_available else 0.35
        basis = "ml_verdict_probability" if self.settlement_available else "llm_estimate"

        if not all_amounts:
            return SettlementRange(
                low=None, median=None, high=None,
                confidence=confidence,
                basis=basis,
            )

        # Settlement range computed from P(accepted):
        #   low    = p - 0.20  (conservative estimate for the claiming party)
        #   median = p          (the model's central prediction)
        #   high   = p + 0.20  (optimistic estimate for the claiming party)
        low_f  = max(p_accept - 0.20, 0.05)
        med_f  = p_accept
        high_f = min(p_accept + 0.20, 0.95)

        if parsed_a and parsed_b:
            # Each party's primary figure is their MAXIMUM mentioned amount:
            #   Party A max = their total claim (e.g. Rs. 75,000 security deposit)
            #   Party B max = their counter-offer / what they're willing to concede
            # Using global min() here is wrong — it picks up small sub-items like
            # a Rs. 5,000 electricity bill and drags the entire range down.
            primary_a = max(parsed_a)   # e.g. 75,000 (tenant's claim)
            primary_b = max(parsed_b)   # e.g. 42,000 (landlord's counter-offer)

            ref_low  = min(primary_a, primary_b)   # floor  = lower of the two positions
            ref_high = max(primary_a, primary_b)   # ceiling = higher of the two positions
            span     = max(ref_high - ref_low, 1.0)

            # P(accepted) determines where in the [ref_low, ref_high] range to land.
            # Low P(accepted) → closer to ref_low (respondent's position).
            # High P(accepted) → closer to ref_high (petitioner's position).
            low_amt  = ref_low + span * low_f
            med_amt  = ref_low + span * med_f
            high_amt = ref_low + span * high_f
        else:
            # Only one party mentioned amounts — use as claimed ceiling
            ref = max(all_amounts)
            low_amt  = ref * low_f
            med_amt  = ref * med_f
            high_amt = ref * high_f

        return SettlementRange(
            low=round(low_amt, 2),
            median=round(med_amt, 2),
            high=round(high_amt, 2),
            confidence=confidence,
            basis=basis,
        )

    def compute_privilege_score(self, text: str) -> float:
        """
        Score a text block on [0, 1] for linguistic privilege.
        1.0 = formal legal argumentation style (like a trained lawyer).
        0.0 = plain narrative / factual writing style.

        Falls back to the vocabulary heuristic if the model is unavailable.
        """
        if not self.fairness_available:
            return self._heuristic_privilege_score(text)

        try:
            features = _compute_features(text)
            X = np.array([features], dtype=np.float32)
            X_scaled = self._fairness_scaler.transform(X)
            score = float(self._fairness_clf.predict_proba(X_scaled)[0][1])
            return round(score, 3)
        except Exception as e:
            logger.error(f"[MediationML] Privilege score computation failed: {e}")
            return self._heuristic_privilege_score(text)

    def _heuristic_privilege_score(self, text: str) -> float:
        """Legacy vocabulary-density heuristic (fallback only)."""
        words = str(text).lower().split()
        if not words:
            return 0.5
        legal_density = sum(1 for w in words if w.rstrip(".,;:") in _LEGAL_TERMS) / len(words)
        length_factor = min(len(words) / 400, 1.0)
        raw = (legal_density * 12 + length_factor) / 2
        return round(min(raw, 1.0), 3)


# ─── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[MediationMLService] = None


def get_mediation_ml_service() -> MediationMLService:
    global _instance
    if _instance is None:
        _instance = MediationMLService()
    return _instance
