"""
Law Matcher Service
Matches extracted legal features to relevant laws and statutes
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LawMatcher:
    """
    Matches extracted legal features to jurisdiction-specific laws
    """
    
    def __init__(self):
        self.laws_cache = {}
        self._load_all_laws()
    
    def _load_all_laws(self):
        """Load all jurisdiction laws into cache"""
        base_path = Path(__file__).parent.parent / "data" / "jurisdictions"
        
        # Load India laws
        india_path = base_path / "india_federal_laws.json"
        if india_path.exists():
            with open(india_path, "r", encoding="utf-8") as f:
                self.laws_cache["India"] = json.load(f)
        
        # Load USA laws
        usa_path = base_path / "usa_federal_laws.json"
        if usa_path.exists():
            with open(usa_path, "r", encoding="utf-8") as f:
                self.laws_cache["USA"] = json.load(f)
        
        logger.info(f"Loaded laws for jurisdictions: {list(self.laws_cache.keys())}")
    
    def match_laws(
        self,
        extracted_features: Dict,
        country: str,
        state: str = "National"
    ) -> List[Dict]:
        """
        Match extracted features to applicable laws
        
        Args:
            extracted_features: Dict from feature_extractor with keys like:
                - severity_level
                - has_financial_impact
                - has_criminal_aspect
                - has_harassment
                - has_dowry
                - financial_impact_level
                - rights_affected
                etc.
            country: Country jurisdiction (e.g., "India", "USA")
            state: State/region jurisdiction (e.g., "Maharashtra")
            
        Returns:
            List of matching law objects sorted by relevance
        """
        
        if country not in self.laws_cache:
            logger.warning(f"No laws loaded for jurisdiction: {country}")
            return []
        
        laws = self.laws_cache[country]
        matched_laws = []
        
        # Extract feature keywords from the features dict
        feature_keywords = self._extract_keywords(extracted_features)
        
        # Match each law against features
        for law in laws:
            relevance_score = self._calculate_relevance(
                law, extracted_features, feature_keywords
            )
            
            if relevance_score > 0:
                law_with_score = law.copy()
                law_with_score["relevance_score"] = relevance_score
                matched_laws.append(law_with_score)
        
        # Sort by relevance score (descending)
        matched_laws.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Return top matches (up to 5)
        return matched_laws[:5]
    
    def _extract_keywords(self, features: Dict) -> List[str]:
        """Extract all relevant keywords from features dict"""
        keywords = []
        
        # Add keywords based on boolean flags
        if features.get("has_criminal_aspect"):
            keywords.append("criminal")
        if features.get("has_harassment"):
            keywords.append("harassment")
        if features.get("has_dowry"):
            keywords.append("dowry")
        if features.get("has_financial_impact"):
            keywords.append("financial")
        if features.get("has_threat"):
            keywords.append("threat")
        if features.get("has_property_damage"):
            keywords.append("property")
        
        # Add severity level
        severity = features.get("severity_level", "").lower()
        if severity:
            keywords.append(severity)
        
        # Add rights affected
        rights = features.get("rights_affected", [])
        keywords.extend([r.lower() for r in rights])
        
        # Add issue type
        issue_type = features.get("issue_type", "").lower()
        if issue_type:
            keywords.append(issue_type)
        
        return keywords
    
    def _calculate_relevance(
        self,
        law: Dict,
        features: Dict,
        feature_keywords: List[str]
    ) -> float:
        """
        Calculate relevance score between law and features
        Score is 0.0 to 1.0
        """
        score = 0.0
        
        # Get law keywords
        law_keywords = [kw.lower() for kw in law.get("relevant_keywords", [])]
        
        # Keyword matching (40% weight)
        keyword_matches = sum(1 for kw in feature_keywords if kw in law_keywords)
        if law_keywords:
            keyword_score = min(keyword_matches / len(law_keywords), 1.0)
            score += keyword_score * 0.4
        
        # Category matching (30% weight)
        law_category = law.get("category", "").lower()
        if law_category:
            if self._category_matches_features(law_category, features):
                score += 0.3
        
        # Severity level alignment (20% weight)
        law_severity = law.get("severity", "low").lower()
        feature_severity = features.get("severity_level", "low").lower()
        
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        if law_severity in severity_order and feature_severity in severity_order:
            law_sev_val = severity_order[law_severity]
            feat_sev_val = severity_order[feature_severity]
            # Align if within 1 level
            if abs(law_sev_val - feat_sev_val) <= 1:
                score += 0.2
        
        # Name/text matching (10% weight)
        law_name = law.get("name", "").lower()
        if any(kw in law_name for kw in feature_keywords):
            score += 0.1
        
        return score
    
    def _category_matches_features(self, law_category: str, features: Dict) -> bool:
        """Check if law category matches feature characteristics"""
        
        category_feature_map = {
            "criminal": [
                "has_criminal_aspect",
                "has_harassment",
                "has_threat",
                "has_violence"
            ],
            "family_law": [
                "is_family_matter",
                "has_marriage_issue",
                "has_custody",
                "has_dowry"
            ],
            "civil_rights": [
                "has_discrimination",
                "has_civil_violation"
            ],
            "employment": [
                "is_employment_matter",
                "has_employment_issue"
            ],
            "intellectual_property": [
                "has_ip_issue",
                "has_copyright"
            ],
            "property": [
                "has_property_issue",
                "has_property_damage"
            ],
            "civil": [
                "is_civil_matter",
                "has_financial_impact"
            ]
        }
        
        relevant_features = category_feature_map.get(law_category, [])
        return any(features.get(feat, False) for feat in relevant_features)
    
    def get_law_details(self, law_id: str, country: str = "India") -> Optional[Dict]:
        """Get detailed information about a specific law"""
        if country not in self.laws_cache:
            return None
        
        for law in self.laws_cache[country]:
            if law.get("law_id") == law_id:
                return law
        
        return None
    
    def get_all_relevant_laws(self, country: str, category: str) -> List[Dict]:
        """Get all laws for a specific country and category"""
        if country not in self.laws_cache:
            return []
        
        laws = self.laws_cache[country]
        return [law for law in laws if law.get("category") == category]


# Singleton instance
_matcher = None


def get_law_matcher() -> LawMatcher:
    """Get or create singleton matcher instance"""
    global _matcher
    if _matcher is None:
        _matcher = LawMatcher()
    return _matcher
