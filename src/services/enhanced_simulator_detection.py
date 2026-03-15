"""
Phase 2: Enhanced Simulator Detection Service
Multilingual keyword detection with improved confidence scoring
"""

import logging
from typing import Tuple, Optional, Dict, Any, List
from enum import Enum

from src.services.language_service import detect_language
from src.models.simulator_model import SimulatorDetectionResult

logger = logging.getLogger(__name__)


class LanguageCode(str, Enum):
    """Supported language codes"""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    BENGALI = "bn"
    MARATHI = "mr"
    TELUGU = "te"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    GUJARATI = "gu"


class ConfidenceTier(str, Enum):
    """Confidence tiers for detection"""
    VERY_HIGH = "very_high"      # 0.85-1.0
    HIGH = "high"                 # 0.70-0.84
    MEDIUM = "medium"             # 0.55-0.69
    LOW = "low"                   # 0.40-0.54
    VERY_LOW = "very_low"         # 0.0-0.39


class EnhancedSimulatorDetectionService:
    """
    Enhanced simulator detection with:
    - Multilingual support (10 Indian languages)
    - Improved confidence scoring
    - Context-aware detection
    - Better action extraction
    - Conversation history analysis
    """

    def __init__(self):
        """Initialize with comprehensive keyword patterns"""
        self._init_multilingual_patterns()
        self._init_context_weights()

    def _init_multilingual_patterns(self):
        """Initialize keyword patterns for all supported languages"""
        
        self.detection_patterns = {
            "en": {  # English
                "future_intent": [
                    "i want to", "i'm planning to", "i plan to", "can i",
                    "could i", "will i", "should i", "would i", "is it okay to",
                    "would it be legal", "what if i", "suppose i", "imagine i",
                    "if i", "thinking about", "considering", "about to", "i'm going to",
                    "i intend to", "my plan is to", "i'm thinking of", "i'd like to",
                    "is it possible to", "can you help me", "how to", "in order to"
                ],
                "action_keywords": [
                    "record", "hack", "fraud", "threat", "erase", "delete",
                    "terminate", "post", "share", "leak", "bypass", "forge",
                    "access", "send", "transfer", "change", "modify", "edit",
                    "download", "upload", "steal", "copy", "paste", "create fake",
                    "impersonate", "deceive", "blackmail", "extort"
                ],
                "consequence_queries": [
                    "what happens if", "what are the consequences", "will i be punished",
                    "penalty", "punishment", "jail", "fine", "legal problem",
                    "consequence", "liability", "lawsuit", "case", "charge",
                    "before i take action", "before proceeding", "is it safe to",
                    "what's the risk", "could i be sued", "will i face consequences",
                    "is this illegal", "am i breaking law", "could i go to jail"
                ],
                "existing_situation": [
                    "i have", "i was", "someone did", "what is", "what are",
                    "i received", "my employer", "the other party", "already happened",
                    "in the past", "is this legal", "what should i do about",
                    "what are my rights", "can i sue", "what happened", "i faced",
                    "i experienced", "i'm currently", "right now", "my situation"
                ],
                "prevention_keywords": [
                    "how to avoid", "how to prevent", "safer way", "alternative",
                    "safer option", "safer approach", "to minimize risk", "best practice",
                    "precautions", "steps to", "how to do this safely", "safe way to",
                    "without getting caught", "without consequences", "legally safe"
                ]
            },
            "hi": {  # Hindi
                "future_intent": [
                    "मैं चाहता हूँ", "मैं करना चाहता हूँ", "बैं करना पड़ेगा",
                    "क्या मैं", "क्या मैं कर सकता हूँ", "मैं योजना बना रहा हूँ",
                    "मैंने सोच रहा हूँ", "अगर मैं", "मैं करने चला हूँ",
                    "मेरा इरादा है", "मैं सोच रहा हूँ कि", "क्या यह ठीक है",
                    "क्या यह कानूनी है"
                ],
                "action_keywords": [
                    "रिकॉर्ड करना", "हैक करना", "धोखाधड़ी", "धमकी", "मिटाना",
                    "हटाना", "नौकरी से निकालना", "पोस्ट करना", "साझा करना",
                    "लीक करना", "फर्जी", "नकल करना", "चोरी करना", "जालसाजी"
                ],
                "consequence_queries": [
                    "क्या होगा अगर", "क्या परिणाम होंगे", "क्या मुझे सजा मिलेगी",
                    "जेल", "जुर्माना", "कानूनी समस्या", "परिणाम", "मुकदमा",
                    "कानून तोड़ना", "क्या यह अवैध है", "क्या यह गलत है"
                ],
                "existing_situation": [
                    "मेरे साथ हुआ", "मुझे मिला", "पहले से", "पहले हुआ",
                    "अभी मेरी स्थिति है", "मेरे अधिकार क्या हैं", "क्या मैं मुकदमा दायर कर सकता हूँ"
                ]
            },
            "ta": {  # Tamil
                "future_intent": [
                    "நான் செய்ய விரும்புகிறேன்", "நான் திட்டமிட்டுக்கொண்டிருக்கிறேன்",
                    "என்னால் முடியுமா", "நான் செய்யலாமா", "நான் செய்ய போகிறேன்"
                ],
                "action_keywords": [
                    "பதிவு செய்தல்", "ஹ్యాக్", "欺చतা", "சுരक్షితం", "తొలగించుക"
                ],
                "consequence_queries": [
                    "என்ன நடக்கிறது", "ఫలితం", "జైలు", "జరిమానా", "చట్ట సమస్య"
                ]
            },
            "bn": {  # Bengali
                "future_intent": [
                    "আমি করতে চাই", "আমি পরিকল্পনা করছি", "আমি কি করতে পারি",
                    "যদি আমি", "আমি যেতে চাই"
                ],
                "action_keywords": [
                    "রেকর্ড করা", "হ্যাক করা", "জালিয়াতি", "হুমকি", "মোছা"
                ],
                "consequence_queries": [
                    "কী হবে", "ফলাফল", "জেল", "জরিমানা", "আইনি সমস্যা"
                ]
            },
            "mr": {  # Marathi
                "future_intent": [
                    "मी करू इच्छितो", "मी योजना आखत आहे", "मी करू शकतो का",
                    "जर मी", "मी करायला जाणार आहे"
                ],
                "action_keywords": [
                    "रेकॉर्ड करणे", "हॅक करणे", "फसवणूक", "धमकी", "हटवणे"
                ],
                "consequence_queries": [
                    "काय होईल", "परिणाम", "तुरुंग", "दंड", "कायदेशीर समस्या"
                ]
            },
            "te": {  # Telugu
                "future_intent": [
                    "నేను చేయాలనుకుంటున్నాను", "నేను ప్లాన్ చేస్తున్నాను",
                    "నేను చేయవచ్చుా", "నేను చేయబోతున్నాను"
                ],
                "action_keywords": [
                    "రికార్డ్ చేయడం", "హ్యాక్ చేయడం", "మోసం", "బెదరింపు", "తొలగించడం"
                ],
                "consequence_queries": [
                    "ఏమి జరుగుతుంది", "ఫలితం", "జైలు", "జరిమానా", "చట్ట సమస్య"
                ]
            },
            "kn": {  # Kannada
                "future_intent": [
                    "ನಾನು ಮಾಡಲು ಬಯಸುತ್ತೇನೆ", "ನಾನು ಯೋಜನೆ ಮಾಡುತ್ತಿದ್ದೇನೆ",
                    "ನಾನು ಮಾಡಬಹುದೆ"
                ],
                "action_keywords": [
                    "ರೆಕಾರ್ಡ್ ಮಾಡುವುದು", "ಹ್ಯಾಕ್ ಮಾಡುವುದು", "ದುರ್ಬಳಕೆ", "ಬೆದರಿಕೆ"
                ],
                "consequence_queries": [
                    "ಏನು ಸಂಭವಿಸುತ್ತದೆ", "ಫಲಾಫಲ", "ಜೈಲು", "ದಂಡ", "ಕಾನೂನು ಸಮಸ್ಯೆ"
                ]
            },
            "ml": {  # Malayalam
                "future_intent": [
                    "ഞാൻ ചെയ്യാൻ ആഗ്രഹിക്കുന്നു", "ഞാൻ ആസൂത്രണം ചെയ്യുന്നു",
                    "എനിക്കാവോ"
                ],
                "action_keywords": [
                    "റെക്കോർഡ് ചെയ്യുന്നു", "ഹ്യാക്ക് ചെയ്യുന്നു", "വഞ്ചന", "ഭീഷണി"
                ],
                "consequence_queries": [
                    "എന്ത് സംഭവിക്കുന്നു", "ഫലം", "ജയിൽ", "പിഴ", "നിയമ പ്രശ്നം"
                ]
            },
            "pa": {  # Punjabi
                "future_intent": [
                    "ਮੈਂ ਕਰਨਾ ਚਾਹਦਾ ਹਾਂ", "ਮੈਂ ਯੋਜਨਾ ਬਣਾ ਰਿਹਾ ਹਾਂ",
                    "ਕੀ ਮੈਂ ਕਰ ਸਕਦਾ ਹਾਂ"
                ],
                "action_keywords": [
                    "ਰਿਕਾਰਡ ਕਰਨਾ", "ਹ੍ਯਾਕ ਕਰਨਾ", "ਧੋਖਾਧੜੀ", "ਧਮਕੀ"
                ],
                "consequence_queries": [
                    "ਕੀ ਹੋਵੇਗਾ", "ਨਤੀਜਾ", "ਜੇਲ", "ਜੁਰਮਾਨਾ", "ਕਾਨੂੰਨੀ ਮਸੀਲਾ"
                ]
            },
            "gu": {  # Gujarati
                "future_intent": [
                    "હું કરવા માંગું છું", "હું આયોજન કરી રહ્યો છું",
                    "શું હું કરી શકું"
                ],
                "action_keywords": [
                    "રેકર્ડ કરવું", "હ્যાક કરવું", "છેતરપીંડી", "ધમકી"
                ],
                "consequence_queries": [
                    "શું થશે", "પરિણામ", "જેલ", "દંડ", "કાનૂની સમસ્યા"
                ]
            }
        }

    def _init_context_weights(self):
        """Initialize weights for different detection factors"""
        self.weights = {
            "future_intent": 0.35,           # Strong indicator
            "action_keyword": 0.25,          # Moderate indicator
            "consequence_query": 0.20,       # Supporting indicator
            "prevention_keyword": 0.15,      # Supporting indicator
            "existing_situation": -0.30,     # Negative indicator (chatbot territory)
        }

    def is_simulator_query(
        self,
        query: str,
        language: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> SimulatorDetectionResult:
        """
        Enhanced detection with:
        - Multilingual support (10 languages)
        - Context-aware scoring
        - Conversation history analysis
        - Confidence tiers
        
        Args:
            query: User's query text
            language: Language code (auto-detected if not provided)
            conversation_history: Previous messages for context
            
        Returns:
            SimulatorDetectionResult with decision and detailed confidence
        """
        
        try:
            # Detect language if not provided
            if not language:
                language = detect_language(query)
                if not language:
                    language = "en"
            
            # Normalize language code
            language = language.lower()
            if language not in self.detection_patterns:
                language = "en"  # Default to English
            
            # Get patterns for language
            patterns = self.detection_patterns.get(language, self.detection_patterns["en"])
            
            # Normalize query
            query_lower = query.lower()
            
            # Calculate detection scores with weights
            future_intent_score = self._calculate_score(
                query_lower,
                patterns.get("future_intent", [])
            )
            
            action_keyword_score = self._calculate_score(
                query_lower,
                patterns.get("action_keywords", [])
            )
            
            consequence_score = self._calculate_score(
                query_lower,
                patterns.get("consequence_queries", [])
            )
            
            prevention_score = self._calculate_score(
                query_lower,
                patterns.get("prevention_keywords", [])
            )
            
            existing_situation_score = self._calculate_score(
                query_lower,
                patterns.get("existing_situation", [])
            )
            
            # Weighted composite score
            weighted_score = (
                future_intent_score * self.weights["future_intent"] +
                action_keyword_score * self.weights["action_keyword"] +
                consequence_score * self.weights["consequence_query"] +
                prevention_score * self.weights["prevention_keyword"] +
                existing_situation_score * self.weights["existing_situation"]
            )
            
            # Conversation context adjustment
            if conversation_history:
                context_boost = self._analyze_conversation_context(
                    conversation_history,
                    language
                )
                weighted_score += context_boost
            
            # Determine if this is simulator query
            # Lower threshold (0.15) to catch realistic single-keyword matches
            # especially important for Hindi and other languages with longer phrases
            is_simulator = weighted_score > 0.15
            
            # Calculate confidence based on indicator strength
            confidence = self._calculate_confidence(
                weighted_score,
                future_intent_score,
                action_keyword_score,
                consequence_score,
                is_simulator
            )
            
            # Ensure confidence in valid range
            confidence = max(0.0, min(1.0, confidence))
            
            # Extract action if confident
            extracted_action = None
            if is_simulator and confidence > 0.45:
                extracted_action = self._extract_action(query, language)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                query,
                is_simulator,
                confidence,
                future_intent_score,
                action_keyword_score,
                consequence_score,
                language
            )
            
            # Determine suggested mode
            if is_simulator and confidence > 0.60:
                suggested_mode = "simulate"
            elif consequence_score > 0.5:
                suggested_mode = "chat"  # Chatbot can help with consequences
            elif any(word in query_lower for word in ["predict", "outcome", "verdict", "case"]):
                suggested_mode = "predict"
            else:
                suggested_mode = "chat"
            
            return SimulatorDetectionResult(
                is_simulator_query=is_simulator,
                confidence=confidence,
                extracted_action=extracted_action,
                reasoning=reasoning,
                suggested_mode=suggested_mode
            )
        
        except Exception as e:
            logger.error(f"Error in enhanced simulator detection: {str(e)}")
            return SimulatorDetectionResult(
                is_simulator_query=False,
                confidence=0.5,
                extracted_action=None,
                reasoning="Detection failed, defaulting to chat mode",
                suggested_mode="chat"
            )

    def _calculate_score(self, text: str, keywords: list) -> float:
        """
        Calculate keyword match score (0.0-1.0)
        Uses exponential scaling: even single keyword match is significant
        Now supports both exact phrase matching and component word matching
        """
        if not keywords:
            return 0.0
        
        matches = 0
        for keyword in keywords:
            # Try exact phrase match first (for English)
            if keyword in text:
                matches += 1
            else:
                # For languages with multi-word phrases, check if key words match
                # E.g., "मैं चाहता हूँ करना" might match even if exact phrase isn't found
                key_components = keyword.split()
                if len(key_components) > 1:
                    # If multiple words in keyword, check if main words are present
                    matching_components = sum(1 for comp in key_components if comp in text)
                    if matching_components >= max(1, len(key_components) - 1):
                        matches += 1
        
        if matches == 0:
            return 0.0
        
        # Score based on number of matches with exponential weight
        # 1 match = 0.4, 2 matches = 0.7, 3+ matches = 1.0
        if matches == 1:
            return 0.40
        elif matches == 2:
            return 0.70
        else:
            return 1.0

    def _analyze_conversation_context(
        self,
        conversation_history: List[Dict],
        language: str
    ) -> float:
        """
        Analyze conversation history for context clues.
        Returns context boost/penalty (-0.3 to 0.3)
        """
        
        if not conversation_history or len(conversation_history) < 2:
            return 0.0
        
        # Look at recent history
        recent_msgs = conversation_history[-3:]
        
        context_boost = 0.0
        
        patterns = self.detection_patterns.get(language, self.detection_patterns["en"])
        
        for msg in recent_msgs:
            if msg.get("role") == "user":
                msg_text = msg.get("content", "").lower()
                
                # Check for planning context
                if any(word in msg_text for word in ["planning", "thinking", "want", "should i"]):
                    context_boost += 0.1
                
                # Check for consequence focus
                if any(word in msg_text for word in patterns.get("consequence_queries", [])):
                    context_boost += 0.1
        
        return min(0.3, context_boost)

    def _calculate_confidence(
        self,
        weighted_score: float,
        future_intent_score: float,
        action_keyword_score: float,
        consequence_score: float,
        is_simulator: bool
    ) -> float:
        """
        Calculate confidence score based on multiple factors
        Returns 0.0-1.0 representing how confident we are in the classification
        """
        
        if not is_simulator:
            # For non-simulator cases, confidence based on existence of non-simulator indicators
            # and absence of simulator indicators
            existing_situation_indicator = min(1.0, weighted_score < 0.15)  # Likely chat if weak simulator signals
            consequence_indicator = consequence_score > 0.3  # Consequence questions -> chat
            
            base_confidence = 0.55  # Base confidence for non-simulator
            
            # Boost confidence if we have clear non-simulator signals
            if weighted_score < 0.1:  # Very weak simulator signals
                base_confidence = 0.85
            elif weighted_score < 0.2:  # Weak simulator signals
                base_confidence = 0.70
            elif weighted_score < 0.3:  # Moderate simulator signals but below threshold
                base_confidence = 0.60
            
            return min(1.0, base_confidence)
        
        # For simulator cases, confidence based on indicator strength
        if future_intent_score > 0.3 and action_keyword_score > 0.3:
            # Strong: both future intent AND action found
            base_confidence = 0.80
        elif future_intent_score > 0.3:
            # Clear future intent
            base_confidence = 0.70
        elif action_keyword_score > 0.3 and consequence_score > 0.3:
            # Action + consequences
            base_confidence = 0.65
        else:
            # Weaker signals
            base_confidence = 0.55
        
        # Small adjustment based on weighted score
        adjustment = min(0.05, weighted_score / 4)
        final_confidence = base_confidence + adjustment
        
        return min(1.0, final_confidence)

    def _extract_action(self, query: str, language: str) -> Optional[str]:
        """
        Extract the planned action from query
        Works for multiple languages
        """
        
        # Language-specific extraction patterns
        extraction_patterns = {
            "en": [
                "want to", "planning to", "plan to", "thinking about",
                "considering", "going to", "about to", "would like to",
                "intend to", "my plan is"
            ],
            "hi": [
                "चाहता हूँ", "योजना बना रहा", "सोच रहा हूँ",
                "करना पड़ेगा"
            ],
            "ta": ["செய்ய விரும்புகிறேன்"],
            "bn": ["করতে চাই", "পরিকল্পনা করছি"],
            "mr": ["करू इच्छितो", "योजना आखत"],
            "te": ["చేయాలనుకుంటున్నాను", "ప్లాన్ చేస్తున్నాను"],
            "kn": ["ಮಾಡಲು ಬಯಸುತ್ತೇನೆ"],
            "ml": ["ചെയ്യാൻ ആഗ്രഹിക്കുന്നു"],
            "pa": ["ਕਰਨਾ ਚਾਹਦਾ ਹਾਂ"],
            "gu": ["કરવા માંગું છું"]
        }
        
        query_lower = query.lower()
        patterns = extraction_patterns.get(language, extraction_patterns["en"])
        
        for start_phrase in patterns:
            idx = query_lower.find(start_phrase)
            if idx != -1:
                # Extract from start phrase to end or period
                end_idx = query.find(".", idx)
                if end_idx == -1:
                    end_idx = len(query)
                
                action = query[idx:end_idx].strip()
                return action if len(action) > 10 else None
        
        # Fallback: return query if substantive
        if len(query) > 20:
            return query[:100] + ("..." if len(query) > 100 else "")
        
        return None

    def _generate_reasoning(
        self,
        query: str,
        is_simulator: bool,
        confidence: float,
        future_score: float,
        action_score: float,
        consequence_score: float,
        language: str
    ) -> str:
        """Generate detailed reasoning for the detection decision"""
        
        if is_simulator:
            reasons = []
            
            if future_score > 0.3:
                reasons.append("Future intent detected")
            
            if action_score > 0.3:
                reasons.append("Action-oriented keywords found")
            
            if consequence_score > 0.3:
                reasons.append("Legal consequence inquiry")
            
            reason_text = ", ".join(reasons) if reasons else "Multiple indicators"
            confidence_tier = self._get_confidence_tier(confidence)
            
            return f"Consequence Simulator ({confidence_tier}): {reason_text}. " \
                   f"Confidence: {confidence:.0%}. Language: {language.upper()}"
        else:
            return "Chat mode recommended. This appears to be a question about an existing " \
                   "situation or general legal guidance. Consider the Consequence Simulator " \
                   "if you want to analyze a planned action before taking it."

    def _get_confidence_tier(self, confidence: float) -> str:
        """Convert confidence score to tier"""
        if confidence >= 0.85:
            return "Very High"
        elif confidence >= 0.70:
            return "High"
        elif confidence >= 0.55:
            return "Medium"
        elif confidence >= 0.40:
            return "Low"
        else:
            return "Very Low"


def get_enhanced_simulator_detection() -> EnhancedSimulatorDetectionService:
    """Get singleton instance of enhanced detection service"""
    if not hasattr(get_enhanced_simulator_detection, '_instance'):
        get_enhanced_simulator_detection._instance = EnhancedSimulatorDetectionService()
    return get_enhanced_simulator_detection._instance
