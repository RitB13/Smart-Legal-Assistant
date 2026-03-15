"""
Jurisdiction Detection Service
Detects user's legal jurisdiction based on multiple signals
"""

import requests
import json
from typing import Optional, Dict, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Mapping of browser language codes to jurisdictions
LANGUAGE_TO_JURISDICTION = {
    "en-IN": ("India", "National"),
    "hi": ("India", "National"),
    "en": ("USA", "National"),
    "en-GB": ("UK", "National"),
    "en-AU": ("Australia", "National"),
    "en-CA": ("Canada", "National"),
}

# Known state codes for different countries
INDIA_STATES = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "CT": "Chhattisgarh",
    "DA": "Dadra and Nagar Haveli",
    "DD": "Daman and Diu",
    "DL": "Delhi",
    "DN": "Dadra and Nagar Haveli and Daman and Diu",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HR": "Haryana",
    "HP": "Himachal Pradesh",
    "JK": "Jammu and Kashmir",
    "JH": "Jharkhand",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OR": "Odisha",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TG": "Telangana",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "TS": "Tripura",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "UT": "Uttarakhand",
    "WB": "West Bengal",
}

USA_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


class JurisdictionDetector:
    """
    Detects user's legal jurisdiction using multiple methods:
    1. User explicit input (highest priority)
    2. Browser/IP information
    3. Language detection
    """
    
    def __init__(self):
        self.geoip_provider = "https://ip-api.com/json"
        self.cache = {}
    
    def detect_jurisdiction(
        self,
        ip_address: Optional[str] = None,
        browser_language: Optional[str] = None,
        explicit_jurisdiction: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> Dict:
        """
        Detect jurisdiction using multiple signals with priority:
        1. Explicit jurisdiction (if provided)
        2. Browser language
        3. IP-based geolocation
        
        Args:
            ip_address: Client IP address
            browser_language: Browser language code (e.g., "en-IN", "hi")
            explicit_jurisdiction: User explicitly selected jurisdiction (e.g., "India/Maharashtra")
            timezone: Browser timezone
            
        Returns:
            Dict with keys:
                - country: Country code or name
                - state_or_region: State/region name
                - detected_method: How jurisdiction was detected
                - confidence: Confidence level (0.0-1.0)
                - timestamp: Detection timestamp
        """
        
        # Priority 1: Explicit jurisdiction
        if explicit_jurisdiction:
            return self._parse_explicit_jurisdiction(explicit_jurisdiction)
        
        # Priority 2: Browser language
        if browser_language:
            result = self._detect_from_language(browser_language)
            if result:
                return result
        
        # Priority 3: IP-based geolocation
        if ip_address and ip_address != "127.0.0.1":
            result = self._detect_from_ip(ip_address)
            if result:
                return result
        
        # Fallback: Default to India (primary use case)
        return {
            "country": "India",
            "state_or_region": "National",
            "detected_method": "default",
            "confidence": 0.5,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _parse_explicit_jurisdiction(self, jurisdiction_string: str) -> Dict:
        """Parse explicit jurisdiction string like 'India/Maharashtra'"""
        try:
            parts = jurisdiction_string.split("/")
            country = parts[0].strip()
            state_region = parts[1].strip() if len(parts) > 1 else "National"
            
            return {
                "country": country,
                "state_or_region": state_region,
                "detected_method": "user_input",
                "confidence": 1.0,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error parsing jurisdiction: {e}")
            return None
    
    def _detect_from_language(self, browser_language: str) -> Optional[Dict]:
        """Detect jurisdiction from browser language code"""
        if browser_language in LANGUAGE_TO_JURISDICTION:
            country, region = LANGUAGE_TO_JURISDICTION[browser_language]
            return {
                "country": country,
                "state_or_region": region,
                "detected_method": "browser_language",
                "confidence": 0.7,
                "timestamp": datetime.utcnow().isoformat(),
            }
        return None
    
    def _detect_from_ip(self, ip_address: str) -> Optional[Dict]:
        """Detect jurisdiction using IP geolocation"""
        try:
            # Check cache first
            if ip_address in self.cache:
                cached = self.cache[ip_address]
                if (datetime.utcnow() - cached["cached_at"]).seconds < 86400:
                    return cached["data"]
            
            # Query IP geolocation API
            response = requests.get(
                f"{self.geoip_provider}/?query={ip_address}",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                country = data.get("country")
                region = data.get("regionName", "National")
                
                result = {
                    "country": country,
                    "state_or_region": region,
                    "detected_method": "ip_geolocation",
                    "confidence": 0.8,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                # Cache result
                self.cache[ip_address] = {
                    "data": result,
                    "cached_at": datetime.utcnow()
                }
                
                return result
        except Exception as e:
            logger.warning(f"IP geolocation failed: {e}")
        
        return None
    
    def normalize_jurisdiction(self, country: str, state: str) -> Tuple[str, str]:
        """
        Normalize jurisdiction strings to standard format
        E.g., "India", "Maharashtra" → "India", "Maharashtra"
        """
        # Normalize country
        country_map = {
            "india": "India",
            "usa": "USA",
            "us": "USA",
            "united states": "USA",
            "uk": "UK",
            "united kingdom": "UK",
            "australia": "Australia",
            "canada": "Canada",
        }
        
        country_normalized = country_map.get(country.lower(), country)
        
        # Normalize state
        if country_normalized == "India":
            state_normalized = INDIA_STATES.get(state.upper(), state)
        elif country_normalized == "USA":
            state_normalized = USA_STATES.get(state.upper(), state)
        else:
            state_normalized = state
        
        return country_normalized, state_normalized
    
    def get_jurisdiction_string(self, jurisdiction_dict: Dict) -> str:
        """Convert jurisdiction dict to readable string"""
        country = jurisdiction_dict.get("country", "Unknown")
        state = jurisdiction_dict.get("state_or_region", "National")
        
        if state == "National" or state == country:
            return country
        return f"{country}/{state}"


# Singleton instance
_detector = None


def get_jurisdiction_detector() -> JurisdictionDetector:
    """Get or create singleton detector instance"""
    global _detector
    if _detector is None:
        _detector = JurisdictionDetector()
    return _detector
