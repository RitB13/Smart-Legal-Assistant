import logging
import re
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

# Legal severity keywords - map to risk categories
SEVERITY_KEYWORDS = {
    "high": ["eviction", "termination", "penalty", "conviction", "jail", "imprisonment", 
             "fine", "cancellation", "suspension", "ban", "seizure", "confiscation", "fraud"],
    "medium": ["dispute", "violation", "breach", "default", "notice", "claim", "lawsuit",
               "appeal", "complaint", "damages", "liability", "obligation"],
    "low": ["inquiry", "question", "clarification", "right", "entitlement", "provision"]
}

# Financial risk indicators
FINANCIAL_KEYWORDS = {
    "high": ["crore", "lakh", "million", "thousand", "rupees", "rs", "₹", "fine", 
             "penalty", "compensation", "loss", "debt", "bankruptcy"],
    "medium": ["payment", "cost", "fee", "charge", "expense", "deposit", "bail"]
}

# Duration/Timeframe indicators
DURATION_KEYWORDS = {
    "permanent": ["forever", "permanent", "life", "lifelong", "indefinite", "continued"],
    "long_term": ["years", "year", "decades", "long", "extended"],
    "short_term": ["months", "month", "weeks", "temporary", "interim"],
    "immediate": ["immediately", "at once", "now", "urgent"]
}

# Rights affected
RIGHTS_KEYWORDS = {
    "property": ["property", "assets", "ownership", "land", "house", "home", "real estate"],
    "liberty": ["liberty", "freedom", "imprisonment", "jail", "arrest"],
    "employment": ["job", "employment", "termination", "terminating", "work"],
    "education": ["education", "school", "university", "college", "admission"],
    "family": ["custody", "guardianship", "divorce", "marriage", "child", "parent"],
    "contract": ["contract", "agreement", "terms", "conditions", "obligation", "liability"]
}

# Mitigating factors (reduce risk)
MITIGATING_KEYWORDS = {
    "appeal": ["appeal", "appealed", "appellate", "appeal court", "review", "reconsideration"],
    "settlement": ["settlement", "compromise", "negotiation", "out of court", "agreed"],
    "time_limit": ["within", "period", "deadline", "days", "grace"],
    "exception": ["exception", "exemption", "waiver", "excluded"]
}


class LegalFeatureExtractor:
    """
    Extracts legal features from user query and LLM response for impact scoring.
    """

    def __init__(self):
        self.severity_keywords = SEVERITY_KEYWORDS
        self.financial_keywords = FINANCIAL_KEYWORDS
        self.duration_keywords = DURATION_KEYWORDS
        self.rights_keywords = RIGHTS_KEYWORDS
        self.mitigating_keywords = MITIGATING_KEYWORDS

    def extract_features(self, query: str, summary: str, laws: List[str]) -> Dict:
        """
        Extract all relevant features from query, summary, and laws.
        
        Args:
            query: User's legal question
            summary: LLM-generated summary
            laws: List of relevant laws cited
            
        Returns:
            Dictionary with all extracted features
        """
        combined_text = f"{query} {summary}".lower()
        
        features = {
            "severity_level": self._extract_severity(combined_text),
            "financial_figures": self._extract_financial_figures(combined_text),
            "financial_risk_level": self._extract_financial_risk(combined_text),
            "duration": self._extract_duration(combined_text),
            "rights_affected": self._extract_rights(combined_text),
            "mitigating_factors": self._extract_mitigating_factors(combined_text),
            "laws_count": len(laws),
            "laws_mentioned": laws,
            "has_criminal_aspect": self._detect_criminal_aspect(combined_text),
            "has_property_aspect": self._detect_property_aspect(combined_text),
        }
        
        logger.info(f"Extracted features: {features}")
        return features

    def _extract_severity(self, text: str) -> str:
        """Determine overall severity level from keywords."""
        high_count = sum(1 for keyword in self.severity_keywords["high"] if keyword in text)
        medium_count = sum(1 for keyword in self.severity_keywords["medium"] if keyword in text)
        low_count = sum(1 for keyword in self.severity_keywords["low"] if keyword in text)
        
        if high_count >= 2:
            return "high"
        elif high_count >= 1 or medium_count >= 3:
            return "medium"
        else:
            return "low"

    def _extract_financial_figures(self, text: str) -> List[Dict]:
        """Extract monetary amounts from text."""
        # Pattern: number (crore/lakh/thousand/rupees/rs/₹)
        patterns = [
            (r'(\d+(?:,\d{2})?)\s*(crore|lakh|thousand|rupees?|rs|₹)', 100),  # crore multiplier
            (r'₹\s*(\d+(?:,\d{2})?)', 1),  # Direct currency
            (r'rs\s*(\d+(?:,\d{2})?)', 1),
        ]
        
        figures = []
        for pattern, multiplier in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount = match.group(1).replace(",", "")
                figures.append({
                    "amount": amount,
                    "unit": match.group(2) if len(match.groups()) > 1 else "rupees",
                    "estimated_value": int(amount) * multiplier
                })
        
        return figures

    def _extract_financial_risk(self, text: str) -> str:
        """Determine financial risk level."""
        high_count = sum(1 for keyword in self.financial_keywords["high"] if keyword in text)
        medium_count = sum(1 for keyword in self.financial_keywords["medium"] if keyword in text)
        
        # Check for large amounts
        figures = self._extract_financial_figures(text)
        has_large_amount = any(fig["estimated_value"] > 100000 for fig in figures)
        
        if high_count >= 2 or has_large_amount:
            return "high"
        elif high_count >= 1 or medium_count >= 2:
            return "medium"
        else:
            return "low"

    def _extract_duration(self, text: str) -> str:
        """Determine impact duration."""
        for duration_type, keywords in self.duration_keywords.items():
            if any(keyword in text for keyword in keywords):
                return duration_type
        
        return "unknown"

    def _extract_rights(self, text: str) -> List[str]:
        """Identify which rights are affected."""
        affected_rights = []
        for right_type, keywords in self.rights_keywords.items():
            if any(keyword in text for keyword in keywords):
                affected_rights.append(right_type)
        
        return affected_rights

    def _extract_mitigating_factors(self, text: str) -> List[str]:
        """Identify factors that reduce risk."""
        factors = []
        for factor_type, keywords in self.mitigating_keywords.items():
            if any(keyword in text for keyword in keywords):
                factors.append(factor_type)
        
        return factors

    def _detect_criminal_aspect(self, text: str) -> bool:
        """Check if case has criminal law aspect."""
        criminal_keywords = ["criminal", "crime", "prosecution", "accused", "conviction",
                            "jail", "imprisonment", "fir", "ipc"]
        return any(keyword in text for keyword in criminal_keywords)

    def _detect_property_aspect(self, text: str) -> bool:
        """Check if case involves property."""
        property_keywords = ["property", "land", "real estate", "house", "flat", "owner",
                            "ownership", "possession"]
        return any(keyword in text for keyword in property_keywords)
