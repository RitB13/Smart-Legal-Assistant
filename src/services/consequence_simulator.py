"""
Legal Consequence Simulator Service
Analyzes planned legal actions and simulates consequences
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from src.models.simulator_model import (
    PlannedActionInput,
    ConsequenceSimulationResult,
    ApplicableLaw,
    Penalty,
    PenaltyType,
    RiskLevelEnum,
    SaferAlternative,
    PrecautionStep,
    RiskFactor,
)
from src.services.llm_service import get_legal_response
from src.services.feature_extractor import LegalFeatureExtractor
from src.services.legal_impact_scorer import LegalImpactScorer
from src.services.checklist_generator import ChecklistGenerator
from src.services.explainability_service import ExplainabilityService
from src.services.jurisdiction_detector import JurisdictionDetector
from src.services.law_matcher import LawMatcher
from src.services.language_service import detect_language
from src.services.parser import parse_llm_output

logger = logging.getLogger(__name__)


class ConsequenceSimulatorService:
    """Service for simulating legal consequences of planned actions"""

    def __init__(self):
        """Initialize simulator with required services"""
        self.llm_service = None  # Used indirectly through get_legal_response
        self.feature_extractor = LegalFeatureExtractor()
        self.impact_scorer = LegalImpactScorer()
        self.checklist_generator = ChecklistGenerator()
        self.explainability_service = ExplainabilityService()
        self.jurisdiction_detector = JurisdictionDetector()
        self.law_matcher = LawMatcher()
        
        # Load action patterns and consequences
        self._load_action_patterns()

    def _load_action_patterns(self):
        """Load common action patterns and their consequences"""
        self.action_patterns = {
            "record call": {
                "laws": ["IT_Act_2000_66C", "Privacy_Law", "Indian_Telegraph_Act"],
                "risk": "Medium",
                "key_risks": [
                    "Recording without consent",
                    "Privacy violation",
                    "Legal liability"
                ]
            },
            "hack": {
                "laws": ["IT_Act_2000_66", "IPC_420", "IPC_419"],
                "risk": "Critical",
                "key_risks": [
                    "Unauthorized access",
                    "Criminal liability",
                    "Imprisonment up to 3 years"
                ]
            },
            "terminate employee": {
                "laws": ["Labour_Law_1946", "Industrial_Disputes_Act", "Payment_of_Gratuity_Act"],
                "risk": "High",
                "key_risks": [
                    "Wrongful termination claim",
                    "Compensation liability",
                    "Court case"
                ]
            },
            "erase evidence": {
                "laws": ["IPC_201", "IPC_202", "Evidence_Act"],
                "risk": "Critical",
                "key_risks": [
                    "Obstruction of justice",
                    "7 years imprisonment",
                    "Criminal prosecution"
                ]
            },
            "fraud": {
                "laws": ["IPC_420", "IPC_415", "IT_Act_2000"],
                "risk": "Critical",
                "key_risks": [
                    "Criminal fraud charges",
                    "Imprisonment",
                    "Fine and compensation"
                ]
            },
            "post threat": {
                "laws": ["IPC_505", "IPC_506", "IT_Act_2000_66D"],
                "risk": "High",
                "key_risks": [
                    "Criminal intimidation",
                    "Defamation claim",
                    "Civil and criminal liability"
                ]
            }
        }

    def simulate_planned_action(
        self,
        action_description: str,
        jurisdiction: str = "India",
        state: Optional[str] = None,
        context: Optional[str] = None,
        language: str = "en"
    ) -> ConsequenceSimulationResult:
        """
        Simulate legal consequences of a planned action.
        
        Args:
            action_description: User's description of planned action
            jurisdiction: Legal jurisdiction
            state: State/region within jurisdiction
            context: Additional context
            language: Language of analysis
            
        Returns:
            ConsequenceSimulationResult with detailed analysis
        """
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        logger.info(f"[{simulation_id}] Starting consequence simulation")
        logger.info(f"[{simulation_id}] Action: {action_description[:100]}...")

        try:
            # Step 1: Detect language if needed
            if not language or language == "en":
                detected_lang = detect_language(action_description)
                language = detected_lang if detected_lang else "en"

            # Step 2: Use LLM to analyze the action
            logger.debug(f"[{simulation_id}] Calling LLM for legal analysis")
            llm_analysis = self._analyze_action_with_llm(
                action_description, 
                jurisdiction, 
                language
            )

            # Step 3: Extract legal features from action
            logger.debug(f"[{simulation_id}] Extracting legal features")
            extracted_features = self._extract_action_features(
                action_description,
                llm_analysis
            )

            # Step 4: Detect jurisdiction if not provided
            logger.debug(f"[{simulation_id}] Detecting jurisdiction")
            if not jurisdiction or jurisdiction.lower() == "unknown":
                jurisdiction = "India"  # Default
            detected_country = jurisdiction
            detected_state = state or "National"

            # Step 5: Match applicable laws
            logger.debug(f"[{simulation_id}] Matching applicable laws")
            applicable_laws = self._match_applicable_laws(
                extracted_features,
                detected_country,
                detected_state,
                llm_analysis
            )

            # Step 6: Extract penalties
            logger.debug(f"[{simulation_id}] Extracting penalties")
            penalties = self._extract_penalties(applicable_laws, llm_analysis)

            # Step 7: Calculate risk score
            logger.debug(f"[{simulation_id}] Calculating risk score")
            risk_level, confidence, key_risks = self._calculate_risk(
                extracted_features,
                applicable_laws,
                penalties
            )

            # Step 8: Generate safer alternatives
            logger.debug(f"[{simulation_id}] Generating safer alternatives")
            safer_alternatives = self._generate_safer_alternatives(
                action_description,
                llm_analysis
            )

            # Step 9: Generate precaution checklist
            logger.debug(f"[{simulation_id}] Generating precaution checklist")
            precautions = self._generate_precaution_checklist(
                action_description,
                extracted_features,
                applicable_laws,
                safer_alternatives
            )

            # Step 10: Generate explanation
            logger.debug(f"[{simulation_id}] Generating explanation")
            explanation = self._generate_explanation(
                action_description,
                risk_level,
                key_risks,
                applicable_laws
            )

            # Step 11: Jurisdiction-specific notes
            jurisdiction_notes = self._get_jurisdiction_specific_notes(
                detected_country,
                detected_state,
                extracted_features
            )

            # Step 12: Build result
            result = ConsequenceSimulationResult(
                simulation_id=simulation_id,
                timestamp=datetime.utcnow(),
                risk_level=risk_level,
                confidence_score=confidence,
                action_analyzed=action_description,
                jurisdiction=detected_country,
                applicable_laws=applicable_laws,
                penalties=penalties,
                civil_exposure=llm_analysis.get("civil_exposure", "Unknown"),
                criminal_exposure=llm_analysis.get("criminal_exposure", "Unknown"),
                key_risks=key_risks,
                safer_alternatives=safer_alternatives,
                precautions_checklist=precautions,
                explanation=explanation,
                jurisdiction_specific_notes=jurisdiction_notes,
                language=language
            )

            logger.info(f"[{simulation_id}] Simulation completed successfully")
            return result

        except Exception as e:
            logger.error(f"[{simulation_id}] Error during simulation: {str(e)}", exc_info=True)
            raise

    def _analyze_action_with_llm(
        self,
        action_description: str,
        jurisdiction: str,
        language: str
    ) -> Dict[str, Any]:
        """Use LLM to analyze the planned action"""
        
        prompt = f"""You are a legal consequence analyzer. A person is considering the following action:

ACTION: {action_description}
JURISDICTION: {jurisdiction}

Analyze this action and provide in JSON format:
{{
    "risk_level": "Low/Medium/High/Critical",
    "is_illegal": true/false,
    "applicable_laws": ["law name", ...],
    "penalties": ["penalty description", ...],
    "civil_exposure": "explanation",
    "criminal_exposure": "explanation",
    "reasons_risky": ["reason 1", "reason 2", ...],
    "safer_alternatives": ["alternative 1", "alternative 2", ...],
    "required_precautions": ["precaution 1", "precaution 2", ...],
    "legal_compliance_notes": "notes"
}}

Be thorough and specific to {jurisdiction} law."""

        try:
            # Call LLM service
            raw_response = get_legal_response(prompt, language=language)
            
            # Parse response
            parsed = parse_llm_output(raw_response)
            
            # Extract summary field
            if isinstance(parsed, dict):
                summary = parsed.get("summary", "{}")
            else:
                summary = "{}"
            
            # Try to parse summary as JSON
            try:
                analysis = json.loads(summary) if isinstance(summary, str) else summary
            except:
                analysis = {
                    "risk_level": "Medium",
                    "is_illegal": False,
                    "applicable_laws": parsed.get("laws", []),
                    "penalties": parsed.get("suggestions", []),
                    "civil_exposure": "Unknown",
                    "criminal_exposure": "Unknown",
                    "reasons_risky": [],
                    "safer_alternatives": [],
                    "required_precautions": []
                }
            
            return analysis

        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            return {
                "risk_level": "Medium",
                "is_illegal": None,
                "applicable_laws": [],
                "penalties": [],
                "civil_exposure": "Unknown",
                "criminal_exposure": "Unknown"
            }

    def _extract_action_features(
        self,
        action_description: str,
        llm_analysis: Dict
    ) -> Dict[str, Any]:
        """Extract legal features from action description"""
        
        # Find matching action patterns
        text_lower = action_description.lower()
        matched_patterns = []
        
        for pattern_key in self.action_patterns.keys():
            if pattern_key in text_lower:
                matched_patterns.append(pattern_key)
        
        # Determine severity
        severity = "low"
        if any(word in text_lower for word in ["hack", "erase", "fraud", "threat"]):
            severity = "high"
        elif any(word in text_lower for word in ["terminate", "record", "post"]):
            severity = "medium"
        
        features = {
            "action_type": matched_patterns[0] if matched_patterns else "unknown",
            "severity_level": severity,
            "has_criminal_aspect": llm_analysis.get("is_illegal", False),
            "has_financial_impact": any(word in text_lower for word in ["money", "damages", "fine", "compensation"]),
            "has_privacy_aspect": any(word in text_lower for word in ["record", "access", "share", "data"]),
            "requires_consent": any(word in text_lower for word in ["record", "share", "access"]),
            "involves_person": any(word in text_lower for word in ["employee", "person", "individual"]),
            "pattern_matched": len(matched_patterns) > 0,
            "matched_patterns": matched_patterns
        }
        
        return features

    def _match_applicable_laws(
        self,
        features: Dict,
        country: str,
        state: str,
        llm_analysis: Dict
    ) -> List[ApplicableLaw]:
        """Match applicable laws to the action"""
        
        applicable_laws = []
        
        # Use LLM-suggested laws
        for law_name in llm_analysis.get("applicable_laws", []):
            applicable_laws.append(
                ApplicableLaw(
                    law_id=law_name.replace(" ", "_").upper(),
                    name=law_name,
                    section=None,
                    jurisdiction=country,
                    description=f"Applicable to this action based on {country} law",
                    relevance="high",
                    url=None,
                    statute_text=None
                )
            )
        
        # Add pattern-based laws
        for pattern in features.get("matched_patterns", []):
            if pattern in self.action_patterns:
                pattern_laws = self.action_patterns[pattern]["laws"]
                for law_id in pattern_laws:
                    if not any(l.law_id == law_id for l in applicable_laws):
                        applicable_laws.append(
                            ApplicableLaw(
                                law_id=law_id,
                                name=law_id.replace("_", " "),
                                section=None,
                                jurisdiction=country,
                                description=f"Applicable law for {pattern}",
                                relevance="high"
                            )
                        )
        
        return applicable_laws

    def _extract_penalties(
        self,
        applicable_laws: List[ApplicableLaw],
        llm_analysis: Dict
    ) -> List[Penalty]:
        """Extract penalty information"""
        
        penalties = []
        
        for penalty_desc in llm_analysis.get("penalties", []):
            # Determine penalty type
            penalty_type = PenaltyType.CIVIL
            if any(word in penalty_desc.lower() for word in ["jail", "prison", "arrest", "criminal"]):
                penalty_type = PenaltyType.CRIMINAL
            elif any(word in penalty_desc.lower() for word in ["fine", "rupee", "amount"]):
                penalty_type = PenaltyType.FINANCIAL
            elif any(word in penalty_desc.lower() for word in ["year", "month", "day"]):
                penalty_type = PenaltyType.IMPRISONMENT
            
            penalties.append(
                Penalty(
                    penalty_type=penalty_type,
                    description=penalty_desc,
                    severity="moderate",
                    maximum=penalty_desc,
                    applicable_law=applicable_laws[0].law_id if applicable_laws else None
                )
            )
        
        return penalties

    def _calculate_risk(
        self,
        features: Dict,
        applicable_laws: List[ApplicableLaw],
        penalties: List[Penalty]
    ) -> Tuple[RiskLevelEnum, float, List[RiskFactor]]:
        """Calculate overall risk level and confidence"""
        
        # Base score
        score = 30
        
        # Severity adjustments
        if features.get("severity_level") == "high":
            score += 40
        elif features.get("severity_level") == "medium":
            score += 20
        
        # Criminal aspect
        if features.get("has_criminal_aspect"):
            score += 30
        
        # Number of applicable laws
        score += min(len(applicable_laws) * 5, 15)
        
        # Penalties
        if any(p.penalty_type == PenaltyType.IMPRISONMENT for p in penalties):
            score += 20
        if any(p.penalty_type in [PenaltyType.CRIMINAL, PenaltyType.CRIMINAL] for p in penalties):
            score += 15
        
        # Normalize
        score = min(100, max(0, score))
        
        # Determine risk level
        if score >= 80:
            risk_level = RiskLevelEnum.CRITICAL
        elif score >= 60:
            risk_level = RiskLevelEnum.HIGH
        elif score >= 40:
            risk_level = RiskLevelEnum.MEDIUM
        else:
            risk_level = RiskLevelEnum.LOW
        
        confidence = 0.75 + (len(applicable_laws) * 0.05)  # More laws = higher confidence
        confidence = min(1.0, confidence)
        
        # Key risks
        key_risks = [
            RiskFactor(
                factor="Multiple applicable laws governing this action",
                severity="high" if len(applicable_laws) > 2 else "medium",
                mitigation="Consult legal professional before proceeding"
            ),
        ]
        
        if features.get("has_criminal_aspect"):
            key_risks.append(
                RiskFactor(
                    factor="Potential criminal liability",
                    severity="critical",
                    mitigation="Avoid this action entirely"
                )
            )
        
        if features.get("requires_consent"):
            key_risks.append(
                RiskFactor(
                    factor="Requires explicit consent",
                    severity="high",
                    mitigation="Obtain written consent from all parties"
                )
            )
        
        return risk_level, confidence, key_risks

    def _generate_safer_alternatives(
        self,
        action_description: str,
        llm_analysis: Dict
    ) -> List[SaferAlternative]:
        """Generate safer alternatives"""
        
        alternatives = []
        
        for alt in llm_analysis.get("safer_alternatives", []):
            alternatives.append(
                SaferAlternative(
                    alternative=alt,
                    explanation="This approach minimizes legal risks",
                    requirement="Follow all steps carefully",
                    legal_basis="Complies with applicable laws"
                )
            )
        
        return alternatives

    def _generate_precaution_checklist(
        self,
        action_description: str,
        features: Dict,
        applicable_laws: List[ApplicableLaw],
        alternatives: List[SaferAlternative]
    ) -> List[PrecautionStep]:
        """Generate precaution checklist"""
        
        checklist = []
        step = 1
        
        # Consent requirement
        if features.get("requires_consent"):
            checklist.append(
                PrecautionStep(
                    step_number=step,
                    action="Obtain explicit written consent",
                    details=[
                        "Communicate intent to all parties",
                        "Get signed acknowledgment from each party",
                        "Keep copies for legal record"
                    ],
                    priority="critical",
                    timeline="before proceeding with action",
                    reason="Required by law for this type of action",
                    reference_law=applicable_laws[0].law_id if applicable_laws else None
                )
            )
            step += 1
        
        # Consult lawyer
        checklist.append(
            PrecautionStep(
                step_number=step,
                action="Consult with a legal professional",
                details=[
                    "Find lawyer experienced in this area",
                    "Discuss specific details of your planned action",
                    "Understand legal implications",
                    "Get written legal advice"
                ],
                priority="critical",
                timeline="before proceeding",
                reason="Professional guidance is essential"
            )
        )
        step += 1
        
        # Documentation
        checklist.append(
            PrecautionStep(
                step_number=step,
                action="Document everything",
                details=[
                    "Keep written records of all communications",
                    "Save copies of all agreements",
                    "Document dates and times",
                    "Keep evidence in safe location"
                ],
                priority="high",
                timeline="ongoing"
            )
        )
        step += 1
        
        # Review laws
        checklist.append(
            PrecautionStep(
                step_number=step,
                action="Review applicable laws",
                details=[
                    f"Study {len(applicable_laws)} applicable law(s)",
                    "Understand specific requirements",
                    "Identify potential violations",
                    "Plan compliance measures"
                ],
                priority="high",
                timeline="before proceeding"
            )
        )
        
        return checklist

    def _generate_explanation(
        self,
        action_description: str,
        risk_level: RiskLevelEnum,
        key_risks: List[RiskFactor],
        applicable_laws: List[ApplicableLaw]
    ) -> str:
        """Generate human-readable explanation"""
        
        risk_descriptions = {
            RiskLevelEnum.LOW: "relatively safe from a legal perspective",
            RiskLevelEnum.MEDIUM: "moderately risky and requires careful handling",
            RiskLevelEnum.HIGH: "quite risky with significant legal consequences",
            RiskLevelEnum.CRITICAL: "extremely risky with severe legal consequences"
        }
        
        explanation = f"""
Based on our analysis, {action_description.lower()} is {risk_descriptions[risk_level]}.

Key Risks Identified:
"""
        
        for i, risk in enumerate(key_risks[:3], 1):
            explanation += f"\n{i}. {risk.factor}\n"
            if risk.mitigation:
                explanation += f"   Mitigation: {risk.mitigation}\n"
        
        if applicable_laws:
            explanation += f"\nApplicable Laws ({len(applicable_laws)} law(s)):\n"
            for law in applicable_laws[:3]:
                explanation += f"- {law.name}\n"
        
        explanation += "\nRecommendation: Consult a legal professional before proceeding."
        
        return explanation

    def _get_jurisdiction_specific_notes(
        self,
        country: str,
        state: str,
        features: Dict
    ) -> str:
        """Get jurisdiction-specific notes"""
        
        if country.lower() == "india":
            return f"""
This analysis is specific to Indian law:
- Laws applicable: IPC (Indian Penal Code), IT Act 2000, Labour Laws, etc.
- Jurisdiction: {state if state != 'National' else 'All India'}
- Court systems: District Courts, High Courts, Supreme Court
- Legal system: Civil and Criminal law
- Important: Laws vary by state for some matters. Consult local lawyer for specific state requirements.
"""
        else:
            return f"Analysis based on {country} legal system"


def get_consequence_simulator() -> ConsequenceSimulatorService:
    """Get singleton instance of ConsequenceSimulatorService"""
    if not hasattr(get_consequence_simulator, '_instance'):
        get_consequence_simulator._instance = ConsequenceSimulatorService()
    return get_consequence_simulator._instance
