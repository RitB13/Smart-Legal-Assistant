"""
Explainability Service: Generates detailed explanations for all calculations and decisions
Made during legal query processing.

Provides:
1. Score calculation explanations with breakdown
2. Law matching reasoning
3. Jurisdiction decision reasoning
4. Checklist priority justification
5. Step-by-step calculation traces
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScoreComponentExplanation:
    """Detailed explanation for a single score component"""
    component_name: str
    score: float
    weight: float
    weighted_contribution: float
    explanation: str
    factors_considered: List[str]
    law_references: List[str]


@dataclass
class CalculationTrace:
    """Complete trace of a calculation with all inputs and steps"""
    calculation_type: str  # "overall_score", "financial_risk", etc.
    inputs: Dict[str, Any]
    intermediate_steps: List[str]
    formula: str
    result: float
    timestamp: str


@dataclass
class LawMatchingExplanation:
    """Explanation for why a law was matched"""
    law_id: str
    law_name: str
    relevance_score: float
    matching_factors: List[str]
    keyword_matches: List[str]
    category_alignment: str
    severity_match: str
    total_reasoning: str


@dataclass
class JurisdictionExplanation:
    """Explanation for jurisdiction detection decision"""
    detected_country: str
    detected_state: str
    detection_method: str
    confidence_score: float
    signals_considered: Dict[str, Any]
    reasoning: str


@dataclass
class ChecklistPriorityExplanation:
    """Explanation for why a checklist item has specific priority"""
    step_number: int
    action: str
    priority_level: str
    reasoning: str
    legal_basis: str
    statute_references: List[str]


class ExplainabilityService:
    """Centralized service for generating explanations of legal analysis"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExplainabilityService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def explain_score_calculation(
        self,
        financial_score: float,
        legal_exposure_score: float,
        long_term_impact_score: float,
        rights_lost_score: float,
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate detailed explanation of score calculation with component breakdown.
        
        Args:
            financial_score: Financial risk score (0-100)
            legal_exposure_score: Legal exposure score (0-100)
            long_term_impact_score: Long-term impact score (0-100)
            rights_lost_score: Rights lost score (0-100)
            features: Extracted legal features
            
        Returns:
            Full explanation with components and reasoning
        """
        explanation = {
            "overview": self._generate_score_overview(financial_score, legal_exposure_score, 
                                                      long_term_impact_score, rights_lost_score),
            "components": [],
            "total_calculation": self._explain_overall_formula(
                financial_score, legal_exposure_score, long_term_impact_score, rights_lost_score
            ),
            "feature_impact": self._explain_feature_impact(features),
            "key_factors": self._identify_score_drivers(
                financial_score, legal_exposure_score, long_term_impact_score, rights_lost_score
            )
        }
        
        # Add component explanations
        explanation["components"].append(
            self._explain_component(
                "Financial Risk Score",
                financial_score,
                0.40,
                features,
                ["financial_loss", "dowry_amount", "property_damage", "business_impact"]
            )
        )
        
        explanation["components"].append(
            self._explain_component(
                "Legal Exposure Score",
                legal_exposure_score,
                0.30,
                features,
                ["has_criminal_case", "has_civil_case", "arrest_warrant", "imprisonment_risk"]
            )
        )
        
        explanation["components"].append(
            self._explain_component(
                "Long-term Impact Score",
                long_term_impact_score,
                0.20,
                features,
                ["custody_impact", "career_impact", "reputation_damage", "long_term_consequence"]
            )
        )
        
        explanation["components"].append(
            self._explain_component(
                "Rights Lost Score",
                rights_lost_score,
                0.10,
                features,
                ["inheritance_loss", "guardianship_loss", "property_loss", "personal_freedom"]
            )
        )
        
        self.logger.debug(f"Generated score calculation explanation with {len(explanation['components'])} components")
        return explanation
    
    def _explain_component(
        self,
        component_name: str,
        score: float,
        weight: float,
        features: Dict[str, Any],
        relevant_features: List[str]
    ) -> Dict[str, Any]:
        """Generate explanation for a single score component"""
        weighted_contribution = (score / 100) * weight
        
        # Determine factors that affected this score
        active_factors = [
            f for f in relevant_features 
            if features.get(f) is not None and features.get(f) is not False
        ]
        
        return {
            "name": component_name,
            "score": score,
            "weight": f"{int(weight * 100)}%",
            "weighted_contribution": round(weighted_contribution, 2),
            "explanation": self._get_component_explanation(component_name, score, active_factors),
            "factors_considered": active_factors,
            "score_interpretation": self._interpret_score_level(score)
        }
    
    def _generate_score_overview(self, f: float, l: float, lt: float, r: float) -> str:
        """Generate overview of what the score means"""
        overall = (f * 0.40 + l * 0.30 + lt * 0.20 + r * 0.10)
        
        if overall >= 80:
            return ("🔴 CRITICAL RISK: Your legal situation is very serious and requires immediate professional intervention. "
                   "You face substantial financial, legal, or personal consequences.")
        elif overall >= 60:
            return ("🟠 HIGH RISK: Your situation is significant and requires prompt legal attention. "
                   "You may face serious consequences if not addressed properly.")
        elif overall >= 40:
            return ("🟡 MODERATE RISK: Your situation needs proper legal handling to avoid complications. "
                   "Professional advice is recommended.")
        else:
            return ("🟢 LOW RISK: While your situation requires attention, the immediate legal risks are manageable. "
                   "Professional guidance will help protect your interests.")
    
    def _explain_overall_formula(self, f: float, l: float, lt: float, r: float) -> Dict[str, Any]:
        """Explain the overall score formula with numbers"""
        overall = (f * 0.40 + l * 0.30 + lt * 0.20 + r * 0.10)
        
        return {
            "formula": "Overall Score = (F × 0.40) + (L × 0.30) + (LT × 0.20) + (R × 0.10)",
            "component_abbreviations": {
                "F": f"Financial Risk Score ({f})",
                "L": f"Legal Exposure Score ({l})",
                "LT": f"Long-term Impact Score ({lt})",
                "R": f"Rights Lost Score ({r})"
            },
            "calculation": f"({f} × 0.40) + ({l} × 0.30) + ({lt} × 0.20) + ({r} × 0.10)",
            "step_by_step": [
                f"Financial contribution: {f} × 0.40 = {f * 0.40:.1f}",
                f"Legal contribution: {l} × 0.30 = {l * 0.30:.1f}",
                f"Long-term contribution: {lt} × 0.20 = {lt * 0.20:.1f}",
                f"Rights lost contribution: {r} × 0.10 = {r * 0.10:.1f}",
                f"Total: {overall:.1f} / 100"
            ],
            "final_score": round(overall, 1)
        }
    
    def _explain_feature_impact(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Explain which features most impacted the score"""
        impact = {
            "detected_features": [],
            "risk_multipliers": []
        }
        
        # List detected features
        for feature_name, feature_value in features.items():
            if feature_value is True or (isinstance(feature_value, (int, float)) and feature_value > 0):
                impact["detected_features"].append(feature_name)
        
        # Identify risk multipliers
        if features.get("has_criminal_case"):
            impact["risk_multipliers"].append("Criminal case involvement (increases legal exposure significantly)")
        if features.get("has_arrest_warrant"):
            impact["risk_multipliers"].append("Active arrest warrant (immediate legal danger)")
        if features.get("high_severity"):
            impact["risk_multipliers"].append("High severity offense (severe penalties possible)")
        if features.get("child_custody_involved"):
            impact["risk_multipliers"].append("Child custody stake (long-term impact on family)")
        
        return impact
    
    def _identify_score_drivers(self, f: float, l: float, lt: float, r: float) -> List[str]:
        """Identify which score components are driving the overall score"""
        drivers = []
        
        if f >= 70:
            drivers.append(f"Financial impact is HIGH ({f}/100) - significant financial loss at stake")
        if l >= 70:
            drivers.append(f"Legal exposure is HIGH ({l}/100) - serious criminal/legal consequences possible")
        if lt >= 70:
            drivers.append(f"Long-term impact is HIGH ({lt}/100) - long-lasting consequences likely")
        if r >= 70:
            drivers.append(f"Rights loss is HIGH ({r}/100) - significant loss of personal/property rights")
        
        if not drivers:
            drivers.append("Balanced risk across multiple dimensions")
        
        return drivers
    
    def _get_component_explanation(self, component: str, score: float, factors: List[str]) -> str:
        """Get explanation for a specific component score"""
        explanations = {
            "financial_risk": {
                "high": "You face substantial financial loss or liability in this matter.",
                "medium": "There is notable financial exposure, but manageable with proper action.",
                "low": "Financial impact is limited compared to other factors."
            },
            "legal_exposure": {
                "high": "You face serious criminal charges, imprisonment, or legal penalties.",
                "medium": "There are legal consequences that need careful management.",
                "low": "Current legal risk is relatively contained."
            },
            "long_term_impact": {
                "high": "This will have lasting effects on your life, relationships, or career.",
                "medium": "Consequences will extend beyond immediate resolution.",
                "low": "Impact will likely be resolved without long-term effects."
            },
            "rights_lost": {
                "high": "You risk losing significant personal, property, or inheritance rights.",
                "medium": "Some rights may be affected depending on case outcome.",
                "low": "Your fundamental rights are not at major risk."
            }
        }
        
        level = "high" if score >= 70 else "medium" if score >= 40 else "low"
        component_key = component.lower().replace(" score", "").replace("-", "_")
        
        base = explanations.get(component_key, {}).get(level, "Impact assessment in progress.")
        
        if factors:
            base += f" Factors: {', '.join(factors[:3])}."
        
        return base
    
    def _interpret_score_level(self, score: float) -> str:
        """Interpret what a score level means"""
        if score >= 80:
            return "🔴 CRITICAL - Immediate action needed"
        elif score >= 60:
            return "🟠 HIGH - Urgent attention required"
        elif score >= 40:
            return "🟡 MODERATE - Professional guidance needed"
        else:
            return "🟢 LOW - Monitor and protect yourself"
    
    def explain_law_matching(
        self,
        matched_laws: List[Dict[str, Any]],
        features: Dict[str, Any],
        country: str
    ) -> List[Dict[str, Any]]:
        """
        Explain why each law was matched to the user's case.
        
        Args:
            matched_laws: List of matched laws with relevance scores
            features: Extracted features from query
            country: User's jurisdiction
            
        Returns:
            List of law matching explanations
        """
        explanations = []
        
        for law in matched_laws[:5]:  # Top 5 laws
            explanation = {
                "law_id": law.get("law_id"),
                "law_name": law.get("name"),
                "relevance_score": law.get("relevance_score", 0),
                "relevance_percentage": f"{law.get('relevance_score', 0) * 100:.0f}%",
                "why_matched": self._explain_why_matched(law, features),
                "keywords_found": self._find_matching_keywords(law, features),
                "applicable_section": law.get("law_id", ""),
                "statute_url": law.get("url", ""),
                "severity": law.get("severity", "medium"),
                "key_penalties": self._extract_penalties(law)
            }
            explanations.append(explanation)
        
        self.logger.debug(f"Generated explanations for {len(explanations)} matched laws")
        return explanations
    
    def _explain_why_matched(self, law: Dict[str, Any], features: Dict[str, Any]) -> str:
        """Explain why a specific law is relevant"""
        reason = f"This law applies because "
        
        keywords = law.get("relevant_keywords", [])
        matching_keywords = [k for k in keywords if k.lower() in str(features).lower()]
        
        if matching_keywords:
            reason += f"your case involves {', '.join(matching_keywords[:2])}. "
        
        reason += f"It's a {law.get('severity', 'medium')}-severity offense "
        reason += f"with jurisdiction in {law.get('jurisdiction', 'general')}. "
        
        if law.get("penalty"):
            reason += f"Potential penalties include {law.get('penalty')}."
        
        return reason
    
    def _find_matching_keywords(self, law: Dict[str, Any], features: Dict[str, Any]) -> List[str]:
        """Find keywords from the law that match features"""
        law_keywords = law.get("relevant_keywords", [])
        feature_str = str(features).lower()
        
        matches = [k for k in law_keywords if k.lower() in feature_str]
        return matches[:5]  # Top 5 matches
    
    def _extract_penalties(self, law: Dict[str, Any]) -> str:
        """Extract penalty information from law"""
        return law.get("penalties", law.get("penalty", "Refer to statute for details"))
    
    def explain_jurisdiction_detection(
        self,
        detected_country: str,
        detected_state: str,
        detected_method: str,
        confidence: float,
        signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Explain how jurisdiction was detected and why.
        
        Args:
            detected_country: Detected country
            detected_state: Detected state/region
            detected_method: Method used for detection
            confidence: Confidence score (0.0-1.0)
            signals: All signals considered
            
        Returns:
            Detailed explanation of jurisdiction detection
        """
        explanation = {
            "detected_location": f"{detected_country}/{detected_state}",
            "confidence_level": f"{confidence * 100:.0f}%",
            "detection_method": detected_method,
            "confidence_interpretation": self._interpret_confidence(confidence),
            "reasoning": self._explain_jurisdiction_reasoning(detected_method, signals),
            "signals_evaluated": signals,
            "legal_significance": f"All legal guidance and laws applied are specific to {detected_country}/{detected_state}"
        }
        
        return explanation
    
    def _interpret_confidence(self, confidence: float) -> str:
        """Interpret confidence score"""
        if confidence >= 0.9:
            return "Very High - We are very confident about this location"
        elif confidence >= 0.7:
            return "High - We are reasonably confident about this location"
        elif confidence >= 0.5:
            return "Medium - Location detected but please verify"
        else:
            return "Low - Uncertain; please specify your location"
    
    def _explain_jurisdiction_reasoning(self, method: str, signals: Dict[str, Any]) -> str:
        """Explain the reasoning behind jurisdiction detection"""
        if method == "explicit":
            return "You explicitly provided your jurisdiction."
        elif method == "ip":
            return f"Detected from your IP address location."
        elif method == "browser_language":
            return f"Detected from your browser settings (language: {signals.get('browser_language')})."
        else:
            return "Defaulted to India (National). Please specify your location for precise guidance."
    
    def explain_checklist_priorities(
        self,
        checklist_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Explain why each checklist item has its priority level.
        
        Args:
            checklist_items: List of checklist items
            
        Returns:
            Checklist items with priority explanations
        """
        explanations = []
        
        for item in checklist_items:
            explanation = {
                "step": item.get("step_number"),
                "action": item.get("action"),
                "priority": item.get("priority"),
                "priority_reasoning": self._explain_priority(
                    item.get("priority"),
                    item.get("action"),
                    item.get("reference_law")
                ),
                "urgency_level": self._urgency_from_priority(item.get("priority")),
                "timeline": item.get("timeline"),
                "legal_basis": item.get("reference_law"),
                "consequence_if_delayed": self._explain_delay_consequence(
                    item.get("priority"),
                    item.get("action")
                )
            }
            explanations.append(explanation)
        
        return explanations
    
    def _explain_priority(self, priority: str, action: str, law: str) -> str:
        """Explain why an action has this priority"""
        if priority == "critical":
            return (f"CRITICAL: {action} is essential to protect your immediate legal and personal safety. "
                   f"Delays can result in loss of rights or worse legal consequences.")
        elif priority == "high":
            return (f"HIGH: {action} should be completed soon to establish your legal position and protect your interests. "
                   f"Timely action prevents complications.")
        elif priority == "medium":
            return (f"MEDIUM: {action} is important for building your case, but can be done within weeks. "
                   f"Focus on critical items first.")
        else:  # low
            return (f"LOW: {action} is part of thorough preparation but can be completed as opportunities arise. "
                   f"Ensure critical items are done first.")
    
    def _urgency_from_priority(self, priority: str) -> str:
        """Convert priority to urgency description"""
        urgency_map = {
            "critical": "🔴 Do immediately (today/tomorrow)",
            "high": "🟠 Do this week",
            "medium": "🟡 Do within 1-3 weeks",
            "low": "🟢 Do as part of ongoing process"
        }
        return urgency_map.get(priority, "Check timeline")
    
    def _explain_delay_consequence(self, priority: str, action: str) -> str:
        """Explain what happens if this action is delayed"""
        if priority == "critical":
            return "Delay may result in loss of critical evidence, increased harm, or loss of legal remedies."
        elif priority == "high":
            return "Delay weakens your legal position and may limit your options."
        elif priority == "medium":
            return "Delay is acceptable but may complicate matters later."
        else:
            return "Can be delayed without major consequence."


def get_explainability_service() -> ExplainabilityService:
    """Get singleton instance of ExplainabilityService"""
    return ExplainabilityService()
