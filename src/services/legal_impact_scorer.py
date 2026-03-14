import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Weighting for subscores
SCORE_WEIGHTS = {
    "financial_risk": 0.40,      # 40% - Financial impact is biggest factor
    "legal_exposure": 0.30,       # 30% - Legal liability/consequences
    "long_term_impact": 0.20,     # 20% - Duration and permanence
    "rights_lost": 0.10           # 10% - Fundamental rights affected
}

# Base scoring ranges for severity levels
SEVERITY_SCORE_MAP = {
    "high": 75,
    "medium": 50,
    "low": 25
}

FINANCIAL_RISK_SCORE_MAP = {
    "high": 85,
    "medium": 55,
    "low": 25
}


@dataclass
class ImpactScore:
    """
    Detailed impact score with subscores and explanation.
    """
    overall_score: int                    # 0-100
    financial_risk_score: int            # 0-100
    legal_exposure_score: int            # 0-100
    long_term_impact_score: int          # 0-100
    rights_lost_score: int               # 0-100
    
    risk_level: str                      # "Critical", "High", "Medium", "Low"
    breakdown: Dict[str, str]            # Detailed explanation of each subscore
    key_factors: List[str]               # Main factors contributing to score
    mitigating_factors: List[str]        # Factors reducing risk
    recommendation: str                  # What user should do
    calculation_details: Dict = None     # NEW: Detailed calculation breakdown


class LegalImpactScorer:
    """
    Calculates legal impact score based on extracted features.
    """

    def __init__(self):
        self.weights = SCORE_WEIGHTS

    def calculate_score(self, features: Dict) -> ImpactScore:
        """
        Calculate comprehensive impact score from extracted features.
        
        Args:
            features: Dictionary of extracted legal features
            
        Returns:
            ImpactScore object with detailed breakdown
        """
        logger.info("Calculating legal impact score...")
        
        # Calculate individual subscores
        financial_risk_score = self._calculate_financial_risk_score(features)
        legal_exposure_score = self._calculate_legal_exposure_score(features)
        long_term_impact_score = self._calculate_long_term_impact_score(features)
        rights_lost_score = self._calculate_rights_lost_score(features)
        
        # Calculate weighted overall score
        overall_score = int(
            (financial_risk_score * self.weights["financial_risk"]) +
            (legal_exposure_score * self.weights["legal_exposure"]) +
            (long_term_impact_score * self.weights["long_term_impact"]) +
            (rights_lost_score * self.weights["rights_lost"])
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)
        
        # Generate explanations and factors
        breakdown = self._generate_breakdown(
            features, financial_risk_score, legal_exposure_score,
            long_term_impact_score, rights_lost_score
        )
        
        key_factors = self._extract_key_factors(features, overall_score)
        mitigating_factors = self._extract_mitigating_factors(features)
        recommendation = self._generate_recommendation(overall_score, features)
        
        # Generate detailed calculation breakdown
        calculation_details = self._generate_calculation_details(
            financial_risk_score, legal_exposure_score,
            long_term_impact_score, rights_lost_score, overall_score
        )
        
        impact_score = ImpactScore(
            overall_score=overall_score,
            financial_risk_score=financial_risk_score,
            legal_exposure_score=legal_exposure_score,
            long_term_impact_score=long_term_impact_score,
            rights_lost_score=rights_lost_score,
            risk_level=risk_level,
            breakdown=breakdown,
            key_factors=key_factors,
            mitigating_factors=mitigating_factors,
            recommendation=recommendation,
            calculation_details=calculation_details
        )
        
        logger.info(f"Impact Score Calculated: {overall_score}/100 ({risk_level})")
        return impact_score

    def _calculate_financial_risk_score(self, features: Dict) -> int:
        """
        Calculate financial risk subscore (0-100).
        
        Factors:
        - Amount of money at risk
        - Type of financial penalty/loss
        - Recurring vs one-time
        """
        score = FINANCIAL_RISK_SCORE_MAP.get(features["financial_risk_level"], 50)
        
        # Bonus for large amounts
        figures = features.get("financial_figures", [])
        if figures:
            max_amount = max(fig["estimated_value"] for fig in figures)
            if max_amount > 10000000:  # > 1 crore
                score = min(95, score + 10)
            elif max_amount > 500000:  # > 5 lakh
                score = min(85, score + 5)
        
        return min(100, score)

    def _calculate_legal_exposure_score(self, features: Dict) -> int:
        """
        Calculate legal exposure subscore (0-100).
        
        Factors:
        - Severity of allegations
        - Number of applicable laws
        - Criminal vs civil
        - Precedent/established consequences
        """
        score = SEVERITY_SCORE_MAP.get(features["severity_level"], 50)
        
        # Adjust for number of laws - more laws = more exposure
        laws_count = features.get("laws_count", 0)
        if laws_count > 5:
            score = min(90, score + 10)
        elif laws_count > 2:
            score = min(85, score + 5)
        
        # Criminal aspect increases exposure
        if features.get("has_criminal_aspect", False):
            score = min(95, score + 15)
        
        return min(100, score)

    def _calculate_long_term_impact_score(self, features: Dict) -> int:
        """
        Calculate long-term impact subscore (0-100).
        
        Factors:
        - Duration of impact (permanent > long > short)
        - Multiple rights affected
        - Career/life impact
        """
        score = 30  # Default low
        
        duration = features.get("duration", "unknown")
        if duration == "permanent":
            score = 85
        elif duration == "long_term":
            score = 70
        elif duration == "short_term":
            score = 35
        elif duration == "immediate":
            score = 60
        
        # Multiple rights affected increases impact
        rights_affected = features.get("rights_affected", [])
        if len(rights_affected) > 2:
            score = min(95, score + 10)
        elif len(rights_affected) > 1:
            score = min(90, score + 5)
        
        # Property cases have long-term impact
        if features.get("has_property_aspect", False):
            score = min(90, score + 5)
        
        return min(100, score)

    def _calculate_rights_lost_score(self, features: Dict) -> int:
        """
        Calculate rights lost subscore (0-100).
        
        Factors:
        - Fundamental rights affected (liberty > property > others)
        - Number of rights affected
        """
        rights_affected = features.get("rights_affected", [])
        score = 20  # Default low
        
        # Weighting for different rights
        critical_rights = {"liberty", "family"}  # Most important
        important_rights = {"property", "employment", "education"}
        other_rights = {"contract"}
        
        for right in rights_affected:
            if right in critical_rights:
                score = min(95, score + 30)
            elif right in important_rights:
                score = min(90, score + 20)
            elif right in other_rights:
                score = min(85, score + 10)
        
        return min(100, score)

    def _determine_risk_level(self, score: int) -> str:
        """Convert numerical score to risk level."""
        if score >= 75:
            return "🔴 Critical"
        elif score >= 60:
            return "🟠 High"
        elif score >= 40:
            return "🟡 Medium"
        else:
            return "🟢 Low"

    def _generate_breakdown(self, features: Dict, financial: int, legal: int,
                          long_term: int, rights: int) -> Dict[str, str]:
        """Generate human-readable explanation for each subscore."""
        breakdown = {
            "financial_risk": self._explain_financial_score(features, financial),
            "legal_exposure": self._explain_legal_score(features, legal),
            "long_term_impact": self._explain_long_term_score(features, long_term),
            "rights_lost": self._explain_rights_score(features, rights)
        }
        return breakdown

    def _explain_financial_score(self, features: Dict, score: int) -> str:
        """Explain financial risk score."""
        figures = features.get("financial_figures", [])
        if figures:
            amount_str = f"{figures[0]['amount']} {figures[0]['unit']}"
            return f"Score: {score}/100 - Significant financial exposure ({amount_str} at risk)"
        
        financial_risk = features.get("financial_risk_level", "low")
        explanations = {
            "high": "Score: {score}/100 - Multiple high-value penalties or losses involved",
            "medium": "Score: {score}/100 - Moderate financial consequences possible",
            "low": "Score: {score}/100 - Minimal financial impact identified"
        }
        
        return explanations[financial_risk].format(score=score)

    def _explain_legal_score(self, features: Dict, score: int) -> str:
        """Explain legal exposure score."""
        laws_count = features.get("laws_count", 0)
        severity = features.get("severity_level", "low")
        has_criminal = features.get("has_criminal_aspect", False)
        
        factors = []
        if has_criminal:
            factors.append("criminal liability involved")
        if laws_count > 5:
            factors.append(f"multiple laws applicable ({laws_count} laws)")
        if severity == "high":
            factors.append("serious violations")
        
        factor_str = ", ".join(factors) if factors else "civil matter"
        return f"Score: {score}/100 - Legal exposure: {factor_str}"

    def _explain_long_term_score(self, features: Dict, score: int) -> str:
        """Explain long-term impact score."""
        duration = features.get("duration", "unknown")
        duration_map = {
            "permanent": "Permanent/indefinite impact",
            "long_term": "Multi-year consequences",
            "short_term": "Limited duration impact",
            "immediate": "Urgent immediate concern",
            "unknown": "Duration unclear"
        }
        
        return f"Score: {score}/100 - {duration_map.get(duration, 'Unknown duration')}"

    def _explain_rights_score(self, features: Dict, score: int) -> str:
        """Explain rights lost score."""
        rights_affected = features.get("rights_affected", [])
        
        if not rights_affected:
            return f"Score: {score}/100 - No fundamental rights directly affected"
        
        rights_names = {
            "liberty": "Personal liberty",
            "property": "Property rights",
            "employment": "Employment rights",
            "family": "Family rights",
            "education": "Education rights",
            "contract": "Contractual rights"
        }
        
        affected_names = [rights_names.get(r, r) for r in rights_affected]
        rights_str = ", ".join(affected_names)
        
        return f"Score: {score}/100 - {len(rights_affected)} right(s) affected: {rights_str}"

    def _extract_key_factors(self, features: Dict, score: int) -> List[str]:
        """Extract 3-5 most important factors contributing to score."""
        factors = []
        
        # Financial factors
        if features.get("financial_risk_level") == "high":
            figures = features.get("financial_figures", [])
            if figures:
                factors.append(f"High financial exposure: {figures[0]['amount']} {figures[0]['unit']}")
            else:
                factors.append("Significant financial penalties possible")
        
        # Legal factors
        if features.get("has_criminal_aspect"):
            factors.append("Criminal liability exposure")
        
        if features.get("severity_level") == "high":
            factors.append("Severe legal violations involved")
        
        # Duration factors
        if features.get("duration") in ["permanent", "long_term"]:
            factors.append(f"Long-term impact ({features['duration'].replace('_', ' ')})")
        
        # Rights factors
        rights = features.get("rights_affected", [])
        if "liberty" in rights:
            factors.append("Personal liberty at risk")
        elif "property" in rights:
            factors.append("Property/asset affected")
        
        return factors[:5]  # Limit to 5 factors

    def _extract_mitigating_factors(self, features: Dict) -> List[str]:
        """Extract factors that reduce/mitigate the risk."""
        mitigating = features.get("mitigating_factors", [])
        
        explanations = {
            "appeal": "Right to appeal available - can challenge verdict",
            "settlement": "Settlement/negotiation possible - can resolve early",
            "time_limit": "Time limits apply - can file counter-claims within period",
            "exception": "Legal exceptions or exemptions may apply"
        }
        
        return [explanations.get(factor, factor) for factor in mitigating]

    def _generate_calculation_details(
        self,
        financial_score: int,
        legal_score: int,
        long_term_score: int,
        rights_score: int,
        overall_score: int
    ) -> Dict:
        """
        Generate detailed breakdown of score calculation showing formula and inputs.
        
        Returns dict with detailed calculation trace for transparency.
        """
        return {
            "formula": "Overall = (Financial × 0.40) + (Legal × 0.30) + (LongTerm × 0.20) + (Rights × 0.10)",
            "weights": {
                "financial_risk": f"{self.weights['financial_risk'] * 100:.0f}%",
                "legal_exposure": f"{self.weights['legal_exposure'] * 100:.0f}%",
                "long_term_impact": f"{self.weights['long_term_impact'] * 100:.0f}%",
                "rights_lost": f"{self.weights['rights_lost'] * 100:.0f}%"
            },
            "subscores": {
                "financial_risk": {
                    "score": financial_score,
                    "weighted_contribution": round(financial_score * self.weights['financial_risk'], 2)
                },
                "legal_exposure": {
                    "score": legal_score,
                    "weighted_contribution": round(legal_score * self.weights['legal_exposure'], 2)
                },
                "long_term_impact": {
                    "score": long_term_score,
                    "weighted_contribution": round(long_term_score * self.weights['long_term_impact'], 2)
                },
                "rights_lost": {
                    "score": rights_score,
                    "weighted_contribution": round(rights_score * self.weights['rights_lost'], 2)
                }
            },
            "overall_calculation": f"({financial_score} × 0.40) + ({legal_score} × 0.30) + ({long_term_score} × 0.20) + ({rights_score} × 0.10) = {overall_score}",
            "total_score": overall_score
        }

    def _generate_recommendation(self, score: int, features: Dict) -> str:
        """Generate actionable recommendation based on score and factors."""
        if score >= 75:
            return "⚠️ CRITICAL: Seek immediate legal consultation. Consider filing urgent petition/appeal if applicable."
        elif score >= 60:
            return "⚠️ HIGH RISK: Consult lawyer promptly. Document all evidence and gather supporting documents."
        elif score >= 40:
            return "📋 MEDIUM: Professional legal review recommended. Gather documents and prepare your case."
        else:
            return "✅ Low risk, but verify with legal counsel for your jurisdiction. Keep records for reference."
