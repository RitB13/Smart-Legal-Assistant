"""
Mediation Service — Core logic for AI-Mediated Dispute Resolution.

Architecture (three layers):
  Layer 1 — Extraction: structured facts pulled from each party's statement (LLM tonight, spaCy/ML later)
  Layer 2 — Analysis:   fairness audit (heuristic tonight, ML classifier later) + settlement range (LLM tonight, LightGBM later)
  Layer 3 — Reasoning:  LLM sees only structured facts (not raw text), constrained by Layer 2 outputs
"""

import json
import json as _json
import logging
import re
from datetime import datetime
from typing import Optional

from src.models.mediation_model import (
    MediationReport, AgreementPoint, ConflictPoint,
    SettlementRange, FairnessAudit, PartyExtraction
)
from src.services.llm_service import get_legal_response
from src.services.database_service import get_database_service
from src.services.mediation_ml_service import get_mediation_ml_service
from src.services.precedent_service import get_precedent_service
from src.services.dense_retrieval_service import get_dense_retrieval_service

logger = logging.getLogger(__name__)

COLLECTION = "mediations"
FEEDBACK_COLLECTION = "mediation_feedback"

# Roles from InLegalBERT IL-TUR that indicate formal legal argumentation.
# Used to derive a privilege score from rhetorical-role predictions instead of
# running a separate LR classifier.
_LEGAL_ARG_ROLES = frozenset({
    "Argument", "Analysis", "Statute",
    "Precedent Relied", "Precedent Not Relied", "Ratio of the Decision",
})


def _privilege_from_rr(predictions: list) -> float:
    """Fraction of sentences classified as formal legal argumentation [0, 1]."""
    if not predictions:
        return 0.5
    legal = sum(1 for p in predictions if p.get("role") in _LEGAL_ARG_ROLES)
    return round(legal / len(predictions), 3)


def _enrich_similar_precedents(raw_results: list) -> list:
    """
    Call Groq once with all precedent summaries to generate a meaningful title,
    2-3 sentence description, cited laws, and court decision for each case.

    Mirrors _enrich_similar_cases in case_outcome.py exactly:
    only the summary text is sent to the LLM — case_name is never exposed,
    so the LLM cannot hallucinate from a bad identifier.
    Returns [] on any failure so the caller falls back gracefully.
    """
    if not raw_results:
        return []
    try:
        case_blocks = ""
        for i, r in enumerate(raw_results):
            summary = (r.get("summary") or "").strip()
            if summary:
                case_blocks += f"\nCase {i + 1}:\n{summary[:800]}\n"

        if not case_blocks.strip():
            return []

        prompt = (
            "You are a legal analyst reviewing Indian court case excerpts.\n"
            "For each excerpt below, provide four fields:\n"
            "1. TITLE: A concise headline (5–10 words) naming the legal dispute "
            "(e.g. 'SARFAESI Bank Recovery — NPA Challenge', "
            "'Tenant Eviction — Arrears and Unauthorised Subletting').\n"
            "2. DESCRIPTION: Exactly 2–3 complete sentences in plain English "
            "explaining what the case is about. Every sentence must end with a full stop. "
            "Do NOT use '...' or leave sentences incomplete. "
            "If the excerpt ends mid-sentence, infer a logical conclusion from context.\n"
            "3. LAWS_CITED: A JSON array of strings listing every Act, Code, Section, or Rule "
            "explicitly mentioned or clearly applicable to this case "
            "(e.g. [\"SARFAESI Act 2002\", \"Companies Act 1956\", \"Code of Civil Procedure\"]). "
            "Return an empty array [] if none are identifiable.\n"
            "4. DECISION: One complete sentence stating what the court decided or ordered, "
            "or what relief was granted/refused. "
            "If the excerpt does not reveal the final outcome, write what stage the case was at.\n\n"
            "Rules:\n"
            "- Title must be specific to this case, not a generic label.\n"
            "- Do not put judge names or citation numbers in the title.\n"
            "- Respond with ONLY valid JSON — no markdown fences, no extra text.\n\n"
            f"{case_blocks}\n"
            "Return a JSON array with one object per case in the same order:\n"
            '[\n'
            '  {"title": "...", "description": "...", "laws_cited": [...], "decision": "..."},\n'
            '  {"title": "...", "description": "...", "laws_cited": [...], "decision": "..."}\n'
            ']'
        )

        raw_response = get_legal_response(
            prompt,
            language="en",
            max_tokens=1200,
            temperature=0.15,
            timeout=60,
            system_prompt=(
                "You are a legal analyst. Respond ONLY with a valid JSON array exactly "
                "matching the structure the user specifies. "
                "No extra text, no markdown fences, no prose outside the JSON array."
            ),
        )
        cleaned = raw_response.strip()

        if "```" in cleaned:
            for block in cleaned.split("```"):
                b = block.strip()
                if b.startswith("json"):
                    b = b[4:].strip()
                if b.startswith("["):
                    cleaned = b
                    break

        try:
            result = _json.loads(cleaned)
            if isinstance(result, list):
                return result
        except _json.JSONDecodeError:
            pass

        try:
            s = cleaned.index("[")
            e = cleaned.rindex("]") + 1
            result = _json.loads(cleaned[s:e])
            if isinstance(result, list):
                return result
        except Exception:
            pass

        logger.warning("[MediationService] LLM precedent enrichment: could not parse JSON")
        return []

    except Exception as e:
        logger.warning("[MediationService] LLM precedent enrichment failed: %s", e)
        return []


class MediationService:

    def __init__(self):
        self.db = get_database_service()
        # Load fairness meta for threshold config (soft dependency)
        try:
            import os, json as _json
            _meta_path = os.path.normpath(os.path.join(
                os.path.dirname(__file__), "..", "data", "models", "mediation", "fairness_meta.json"
            ))
            with open(_meta_path) as f:
                self._fairness_meta = _json.load(f)
        except Exception:
            self._fairness_meta = {"bias_detection_threshold": 0.12}

    # ─── Database helpers ──────────────────────────────────────────────────────

    def get_dispute(self, dispute_id: str) -> Optional[dict]:
        return self.db.find_one_doc(COLLECTION, {"dispute_id": dispute_id})

    def get_dispute_by_invite(self, invite_code: str) -> Optional[dict]:
        return self.db.find_one_doc(COLLECTION, {"invite_code": invite_code.upper()})

    def save_dispute(self, dispute_doc: dict) -> bool:
        return self.db.insert_one_doc(COLLECTION, dispute_doc)

    def update_dispute(self, dispute_id: str, update: dict) -> bool:
        return self.db.update_one_doc(COLLECTION, {"dispute_id": dispute_id}, update)

    def get_user_disputes(self, user_id: str) -> list:
        as_a = self.db.find_many_docs(COLLECTION, {"party_a_user_id": user_id})
        as_b = self.db.find_many_docs(COLLECTION, {"party_b_user_id": user_id})
        return as_a + as_b

    def save_feedback(self, feedback_doc: dict) -> bool:
        return self.db.insert_one_doc(FEEDBACK_COLLECTION, feedback_doc)

    # ─── Layer 1: Extraction (LLM-based; replace with spaCy NER + ML later) ───

    def extract_party_context(self, statement: str, language: str = "en") -> PartyExtraction:
        """
        Extract structured facts from a party's statement.
        The LLM is asked for JSON only — this output feeds Layer 3, not the user.
        """
        prompt = (
            "You are a legal analyst extracting facts from a dispute statement. "
            "Return ONLY valid JSON with exactly these fields:\n"
            "{\n"
            '  "key_claims": ["list the main factual claims"],\n'
            '  "amounts_mentioned": ["any monetary amounts as strings"],\n'
            '  "dates_mentioned": ["any dates or timelines"],\n'
            '  "evidence_mentioned": ["documents, receipts, witnesses, agreements mentioned"],\n'
            '  "tone": "one of: aggressive|assertive|distressed|calm|neutral",\n'
            '  "evidence_strength_score": 0.0,\n'
            '  "primary_legal_issue": "one sentence"\n'
            "}\n\n"
            f"Statement:\n{statement}\n\n"
            "Return only the JSON object. No explanation."
        )

        try:
            raw = get_legal_response(prompt, language="en")
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(raw[start:end])
                return PartyExtraction(
                    key_claims=data.get("key_claims", []),
                    amounts_mentioned=data.get("amounts_mentioned", []),
                    dates_mentioned=data.get("dates_mentioned", []),
                    evidence_mentioned=data.get("evidence_mentioned", []),
                    tone=data.get("tone", "neutral"),
                    evidence_strength_score=float(data.get("evidence_strength_score", 0.5)),
                    primary_legal_issue=data.get("primary_legal_issue", "")
                )
        except Exception as e:
            logger.error(f"[MediationService] Extraction failed: {e}")

        return PartyExtraction(evidence_strength_score=0.5, tone="neutral")

    # ─── Rhetorical role structure analysis (InLegalBERT) ────────────────────────

    def analyze_statement_structure(self, statement: str) -> Optional[dict]:
        """
        Classify the rhetorical roles of sentences in a party's statement using the
        InLegalBERT fairness model (13-class IL-TUR RR dataset).

        Groups sentences into five categories and returns fractions plus a plain-
        English summary.  Returns None silently when the model is unavailable.
        """
        try:
            from src.services.fairness_predictor_service import get_fairness_service
            svc = get_fairness_service()
            if not svc.available:
                return None

            import re
            # Split on sentence-ending punctuation; keep non-trivial sentences
            sentences = [
                s.strip()
                for s in re.split(r'(?<=[.!?])\s+', statement)
                if len(s.strip()) > 10
            ]
            if not sentences:
                return None

            predictions = svc.predict_batch(sentences[:60])  # cap at 60 sentences

            # Group role labels into five semantic categories
            NARRATIVE   = {"Facts", "Other", "None", "Preamble"}
            LEGAL_ARG   = {"Argument", "Analysis"}
            AUTHORITY   = {"Statute", "Precedent Relied", "Precedent Not Relied"}
            ISSUE_CORE  = {"Issue", "Ratio of the Decision"}
            RULINGS     = {"Ruling by Lower Court", "Ruling by Present Court"}

            role_counts: dict = {}
            for pred in predictions:
                role = pred.get("role", "Other")
                role_counts[role] = role_counts.get(role, 0) + 1

            total = len(predictions)

            def pct(roles: set) -> float:
                return round(sum(role_counts.get(r, 0) for r in roles) / total * 100, 1)

            groups = {
                "narrative_pct":       pct(NARRATIVE),
                "legal_argument_pct":  pct(LEGAL_ARG),
                "legal_authority_pct": pct(AUTHORITY),
                "issue_core_pct":      pct(ISSUE_CORE),
                "rulings_pct":         pct(RULINGS),
            }

            dominant_key = max(groups, key=lambda k: groups[k])
            dominant     = dominant_key.replace("_pct", "")
            dominant_val = groups[dominant_key]

            summaries = {
                "narrative":       f"Mostly factual narrative ({dominant_val:.0f}%). Consider adding more legal grounding.",
                "legal_argument":  f"Strong legal argumentation ({dominant_val:.0f}%). Well-structured for mediation analysis.",
                "legal_authority": f"Grounded in legal authority ({dominant_val:.0f}%). Effective use of statutes and precedents.",
                "issue_core":      f"Issue-focused ({dominant_val:.0f}%). Clear presentation of core legal issues.",
                "rulings":         f"Ruling-focused ({dominant_val:.0f}%). Anchored in prior court decisions.",
            }

            return {
                "total_sentences": total,
                "dominant_type":   dominant,
                "groups":          groups,
                "role_counts":     role_counts,
                "summary":         summaries.get(dominant, f"Mixed submission ({dominant_val:.0f}% {dominant})."),
                "predictions":     predictions,
            }

        except Exception as e:
            logger.warning("[MediationService] Statement structure analysis skipped: %s", e)
            return None

    # ─── Layer 2a: Fairness audit (RR-derived privilege; fallback to LR/heuristic) ─

    def compute_fairness_audit(
        self,
        statement_a: str,
        statement_b: str,
        rr_a: Optional[list] = None,
        rr_b: Optional[list] = None,
    ) -> FairnessAudit:
        """
        Detect linguistic privilege gap between the two statements.

        If InLegalBERT rhetorical-role predictions are provided (rr_a / rr_b),
        the privilege score is derived from the fraction of sentences labelled as
        formal legal argumentation — this is more principled than the LR classifier
        and costs nothing because the RR forward pass has already run.

        Falls back to the LR classifier (AUC 0.68), and then to a vocabulary
        heuristic, when predictions are unavailable.
        """
        if rr_a is not None and rr_b is not None:
            score_a = _privilege_from_rr(rr_a)
            score_b = _privilege_from_rr(rr_b)
            method = "inlegalbert_rr"
        else:
            ml = get_mediation_ml_service()
            score_a = ml.compute_privilege_score(statement_a)
            score_b = ml.compute_privilege_score(statement_b)
            method = "ml_classifier" if ml.fairness_available else "vocabulary_heuristic"

        diff = abs(score_a - score_b)
        threshold = self._fairness_meta.get("bias_detection_threshold", 0.12)
        bias_detected = diff > threshold

        if bias_detected:
            bias_direction = "party_a" if score_a > score_b else "party_b"
        else:
            bias_direction = "neutral"

        note = (
            f"[{method}] Party A linguistic privilege score: {score_a:.3f}, "
            f"Party B: {score_b:.3f}. "
            + (
                f"A gap of {diff:.3f} was detected — the mediator was instructed to "
                f"weight Party {'A' if bias_direction == 'party_a' else 'B'}'s claims "
                f"equally despite their linguistic advantage."
                if bias_detected else
                "No significant linguistic imbalance detected between submissions."
            )
        )

        return FairnessAudit(
            party_a_privilege_score=score_a,
            party_b_privilege_score=score_b,
            bias_detected=bias_detected,
            bias_direction=bias_direction,
            normalization_applied=bias_detected,
            note=note
        )

    # ─── Layer 2b: Settlement range (InLegalBERT outcome + amount extraction) ─────

    def estimate_settlement_range(
        self,
        extraction_a: PartyExtraction,
        extraction_b: PartyExtraction,
        case_type: str,
        jurisdiction: str,
        year: int = 2024,
        statement_a: str = "",
    ) -> SettlementRange:
        """
        Estimate a fair monetary settlement range.

        Uses InLegalBERT outcome model (68% accuracy) to predict P(accepted) from
        the actual statement text, which is more reliable than the LightGBM model
        that had AUC ≈ 0.51 (coin flip) on the processed dataset. Falls back to the
        LightGBM base-rate estimate when the outcome model is unavailable.

        The probability is then used to anchor a monetary range between the two
        parties' claimed figures.
        """
        ml  = get_mediation_ml_service()
        state = jurisdiction.split("/")[-1].strip() if "/" in jurisdiction else jurisdiction.strip()

        p_accept_override = None
        if statement_a:
            try:
                from src.services.case_outcome_predictor_service import get_predictor_service
                outcome_svc = get_predictor_service()
                if outcome_svc._available:
                    formal_text = outcome_svc.compose_petition_text(
                        statement=statement_a,
                        relief_sought=", ".join(extraction_a.key_claims[:3]) if extraction_a.key_claims else "",
                        role="petitioner",
                        jurisdiction=jurisdiction,
                        case_type=case_type,
                    )
                    p_accept_override = outcome_svc.predict_acceptance_probability(formal_text)
                    logger.info("[MediationService] InLegalBERT P(accepted) = %.4f", p_accept_override)
            except Exception as e:
                logger.warning("[MediationService] InLegalBERT outcome skipped: %s", e)

        return ml.compute_settlement_range(
            case_type=case_type,
            state=state,
            year=year,
            amounts_a=extraction_a.amounts_mentioned,
            amounts_b=extraction_b.amounts_mentioned,
            p_accept_override=p_accept_override,
        )

    # ─── Layer 3: LLM reasoning (constrained by Layers 1 & 2) ────────────────

    def analyze_dispute(
        self,
        extraction_a: PartyExtraction,
        extraction_b: PartyExtraction,
        settlement_range: SettlementRange,
        fairness_audit: FairnessAudit,
        case_type: str,
        jurisdiction: str,
        prior_context_a: Optional[dict] = None,
        prior_context_b: Optional[dict] = None,
        structure_a: Optional[dict] = None,
        structure_b: Optional[dict] = None,
    ) -> dict:
        """
        LLM sees ONLY structured extractions (not raw statements).
        Settlement must fall within the Layer 2b range.
        Fairness note instructs it to compensate for privilege imbalance.
        """

        prior_a_text = ""
        if prior_context_a:
            prior_a_text = (
                f"\n- Prior case predictor result for Party A: verdict={prior_context_a.get('predicted_verdict')}, "
                f"confidence={prior_context_a.get('confidence')}, risk={prior_context_a.get('risk_level')}"
            )

        prior_b_text = ""
        if prior_context_b:
            prior_b_text = (
                f"\n- Prior case predictor result for Party B: verdict={prior_context_b.get('predicted_verdict')}, "
                f"confidence={prior_context_b.get('confidence')}, risk={prior_context_b.get('risk_level')}"
            )

        structure_context = ""
        if structure_a or structure_b:
            structure_context = "\nSTATEMENT STRUCTURE (rhetorical role analysis):\n"
            if structure_a:
                structure_context += (
                    f"- Party A: {structure_a.get('summary', 'N/A')} "
                    f"(dominant type: {structure_a.get('dominant_type', 'unknown')})\n"
                )
            if structure_b:
                structure_context += (
                    f"- Party B: {structure_b.get('summary', 'N/A')} "
                    f"(dominant type: {structure_b.get('dominant_type', 'unknown')})\n"
                )
            structure_context += (
                "Use this structural context to assess how well each party has "
                "grounded their claims legally, but do NOT penalise narrative submissions — "
                "treat both parties' underlying facts equally.\n"
            )

        fairness_instruction = ""
        if fairness_audit.bias_detected:
            advantaged = "A" if fairness_audit.bias_direction == "party_a" else "B"
            fairness_instruction = (
                f"\nFAIRNESS INSTRUCTION: Party {advantaged}'s submission was linguistically more sophisticated. "
                f"You MUST weight both parties' claims equally. Do not let writing quality influence your analysis."
            )

        range_instruction = ""
        if settlement_range.low is not None and settlement_range.high is not None:
            range_instruction = (
                f"\nSETTLEMENT CONSTRAINT: Your proposed monetary settlement MUST fall between "
                f"{settlement_range.low} and {settlement_range.high} INR "
                f"(median: {settlement_range.median}). Do not propose amounts outside this range."
            )

        prompt = (
            "You are a neutral AI legal mediator. Analyze this dispute using ONLY the structured facts below — "
            "you have NOT seen the raw statements and must not speculate beyond what is listed.\n\n"
            f"CASE TYPE: {case_type}\n"
            f"JURISDICTION: {jurisdiction}\n\n"
            f"PARTY A (extracted facts):\n"
            f"- Claims: {extraction_a.key_claims}\n"
            f"- Evidence mentioned: {extraction_a.evidence_mentioned}\n"
            f"- Key dates: {extraction_a.dates_mentioned}\n"
            f"- Primary legal issue: {extraction_a.primary_legal_issue}\n"
            f"- Evidence strength: {extraction_a.evidence_strength_score}{prior_a_text}\n\n"
            f"PARTY B (extracted facts):\n"
            f"- Claims: {extraction_b.key_claims}\n"
            f"- Evidence mentioned: {extraction_b.evidence_mentioned}\n"
            f"- Key dates: {extraction_b.dates_mentioned}\n"
            f"- Primary legal issue: {extraction_b.primary_legal_issue}\n"
            f"- Evidence strength: {extraction_b.evidence_strength_score}{prior_b_text}\n"
            f"{structure_context}"
            f"{fairness_instruction}"
            f"{range_instruction}\n\n"
            "Return ONLY valid JSON:\n"
            "{\n"
            '  "points_of_agreement": [{"point": "...", "confidence": 0.0}],\n'
            '  "points_of_conflict": [{"point": "...", "party_a_position": "...", "party_b_position": "...", "severity": "critical|major|minor"}],\n'
            '  "proposed_settlement": "clear, specific settlement statement",\n'
            '  "proposed_settlement_rationale": "why this is fair to both parties",\n'
            '  "applicable_laws": ["law 1", "law 2"],\n'
            '  "similar_precedents": ["case description 1"],\n'
            '  "next_steps": ["step 1", "step 2", "step 3"]\n'
            "}"
        )

        try:
            raw = get_legal_response(prompt, language="en")
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(raw[start:end])
        except Exception as e:
            logger.error(f"[MediationService] Dispute analysis LLM call failed: {e}")

        return {
            "points_of_agreement": [],
            "points_of_conflict": [],
            "proposed_settlement": "Analysis could not be completed. Please try again.",
            "proposed_settlement_rationale": "",
            "applicable_laws": [],
            "similar_precedents": [],
            "next_steps": ["Contact a legal professional for assistance."]
        }

    # ─── Full pipeline ─────────────────────────────────────────────────────────

    def run_full_analysis(self, dispute: dict) -> MediationReport:
        """
        Runs all three layers in sequence. Called as a background task
        once both parties have submitted their statements.
        """
        dispute_id = dispute["dispute_id"]
        logger.info(f"[MediationService] Starting full analysis for dispute {dispute_id}")

        statement_a = dispute["party_a_statement"]
        statement_b = dispute["party_b_statement"]
        case_type = dispute.get("case_type", "general")
        jurisdiction = dispute.get("jurisdiction", "India")
        language = dispute.get("language", "en")
        year = datetime.utcnow().year

        # Layer 1
        logger.debug(f"[MediationService] Layer 1: extracting party contexts")
        extraction_a = self.extract_party_context(statement_a, language)
        extraction_b = self.extract_party_context(statement_b, language)

        # Layer 2a-rr: rhetorical role structure — runs FIRST so predictions feed fairness audit
        logger.debug(f"[MediationService] Layer 2a-rr: rhetorical role analysis")
        structure_a = self.analyze_statement_structure(statement_a)
        structure_b = self.analyze_statement_structure(statement_b)
        if structure_a:
            logger.info("[MediationService] Party A dominant type: %s", structure_a.get("dominant_type"))
        if structure_b:
            logger.info("[MediationService] Party B dominant type: %s", structure_b.get("dominant_type"))

        # Layer 2a: fairness audit — uses RR predictions when available (no extra model needed)
        logger.debug(f"[MediationService] Layer 2a: fairness audit")
        rr_a = structure_a.get("predictions") if structure_a else None
        rr_b = structure_b.get("predictions") if structure_b else None
        fairness = self.compute_fairness_audit(statement_a, statement_b, rr_a=rr_a, rr_b=rr_b)

        # Layer 2b
        logger.debug(f"[MediationService] Layer 2b: settlement range estimation")
        settlement_range = self.estimate_settlement_range(
            extraction_a, extraction_b, case_type, jurisdiction, year,
            statement_a=statement_a,
        )

        # Layer 3
        logger.debug(f"[MediationService] Layer 3: LLM mediation analysis")
        analysis = self.analyze_dispute(
            extraction_a, extraction_b,
            settlement_range, fairness,
            case_type, jurisdiction,
            prior_context_a=dispute.get("prior_context_a"),
            prior_context_b=dispute.get("prior_context_b"),
            structure_a=structure_a,
            structure_b=structure_b,
        )

        # Settlement range fallback: if no monetary amounts were in party statements,
        # parse from the LLM's proposed settlement (which always contains a specific figure).
        if settlement_range.low is None:
            from src.services.mediation_ml_service import _parse_amounts
            inferred = _parse_amounts([analysis.get("proposed_settlement", "")])
            if inferred:
                ref = max(inferred)
                settlement_range = SettlementRange(
                    low=round(ref * 0.80, 2),
                    median=round(ref, 2),
                    high=round(ref * 1.20, 2),
                    confidence=0.20,
                    basis="llm_estimate",
                )
                logger.info(f"[MediationService] Settlement range inferred from proposed_settlement: {ref}")

        # Layer 3b: dense-first precedent retrieval, TF-IDF fallback
        logger.debug(f"[MediationService] Layer 3b: precedent retrieval (dense → TF-IDF fallback)")
        query_text = f"{case_type} dispute: {dispute.get('case_description', '')} {extraction_a.primary_legal_issue} {extraction_b.primary_legal_issue}"
        raw_precedents = []
        retrieval_method = "none"

        dense_svc = get_dense_retrieval_service()
        if dense_svc.available:
            raw_precedents = dense_svc.search(query_text, top_k=3)
            if raw_precedents:
                retrieval_method = "dense_minilm"
                logger.info("[MediationService] Dense retrieval: %d results", len(raw_precedents))
            else:
                logger.info("[MediationService] Dense returned 0 results — falling back to TF-IDF")

        if not raw_precedents:
            precedent_svc = get_precedent_service()
            if precedent_svc.available:
                raw_precedents = precedent_svc.search(query_text, case_type_filter=case_type, top_k=3)
                retrieval_method = "tfidf_svd"
                logger.info("[MediationService] TF-IDF retrieval: %d results", len(raw_precedents))
            else:
                logger.warning("[MediationService] Both dense and TF-IDF indexes unavailable")

        if raw_precedents:
            enriched = _enrich_similar_precedents(raw_precedents)
            similar_precedents = []
            for i, r in enumerate(raw_precedents):
                enc = enriched[i] if i < len(enriched) else {}
                similar_precedents.append({
                    "case_name":        r.get("case_name", ""),
                    "case_type":        r.get("case_type", ""),
                    "summary":          r.get("summary", ""),
                    "outcome":          r.get("outcome", ""),
                    "similarity":       r.get("similarity", 0.0),
                    "llm_title":        enc.get("title"),
                    "llm_description":  enc.get("description"),
                    "llm_laws_cited":   enc.get("laws_cited", []),
                    "llm_decision":     enc.get("decision"),
                })
            logger.info("[MediationService] %d enriched precedents via %s", len(similar_precedents), retrieval_method)
        else:
            similar_precedents = []

        model_version = f"inlegalbert_{retrieval_method}_v1" if retrieval_method != "none" else "llm_only_v1"

        report = MediationReport(
            dispute_id=dispute_id,
            points_of_agreement=[
                AgreementPoint(**p) for p in analysis.get("points_of_agreement", [])
                if isinstance(p, dict) and "point" in p and "confidence" in p
            ],
            points_of_conflict=[
                ConflictPoint(**c) for c in analysis.get("points_of_conflict", [])
                if isinstance(c, dict) and all(k in c for k in ["point", "party_a_position", "party_b_position", "severity"])
            ],
            settlement_range=settlement_range,
            proposed_settlement=analysis.get("proposed_settlement", ""),
            proposed_settlement_rationale=analysis.get("proposed_settlement_rationale", ""),
            applicable_laws=analysis.get("applicable_laws", []),
            fairness_audit=fairness,
            similar_precedents=similar_precedents,
            next_steps=analysis.get("next_steps", []),
            generated_at=datetime.utcnow(),
            model_version=model_version,
            statement_structure_a=structure_a,
            statement_structure_b=structure_b,
        )

        logger.info(f"[MediationService] Analysis complete for dispute {dispute_id}")
        return report


# ─── Singleton ─────────────────────────────────────────────────────────────────

_mediation_service_instance: Optional[MediationService] = None


def get_mediation_service() -> MediationService:
    global _mediation_service_instance
    if _mediation_service_instance is None:
        _mediation_service_instance = MediationService()
    return _mediation_service_instance
