"""
Simulator Detection Service
Intelligently detects if a query is for consequence simulation (planned action)
vs. regular chatbot (existing situation)
"""

import logging
from typing import Tuple, Optional, Dict, Any

from src.services.language_service import detect_language
from src.models.simulator_model import SimulatorDetectionResult

logger = logging.getLogger(__name__)


class SimulatorDetectionService:
    """Service to detect if query should use consequence simulator or chatbot"""

    def __init__(self):
        """Initialize with keyword patterns"""
        self._init_keyword_patterns()

    def _init_keyword_patterns(self):
        """Initialize keyword patterns for different languages"""
        
        self.detection_patterns = {
            "en": {
                "future_intent": [
                    "i want to", "i'm planning to", "i plan to", "can i",
                    "could i", "will i", "should i", "would i", "is it okay to",
                    "would it be legal", "what if i", "suppose i", "imagine i",
                    "if i", "thinking about", "considering", "about to", "i'm going to"
                ],
                "action_keywords": [
                    "record", "hack", "fraud", "threat", "erase", "delete",
                    "terminate", "post", "share", "leak", "bypass", "forge",
                    "access", "send", "transfer", "change", "modify", "edit"
                ],
                "consequence_queries": [
                    "what happens if", "what are the consequences", "will i be punished",
                    "penalty", "punishment", "jail", "fine", "legal problem",
                    "consequence", "liability", "lawsuit", "case", "charge",
                    "before i take action", "before proceeding", "is it safe to"
                ],
                "existing_situation": [
                    "i have", "i was", "someone did", "what is", "what are",
                    "i received", "my employer", "the other party", "already happened",
                    "in the past", "is this legal", "what should i do about",
                    "what are my rights", "can i sue"
                ],
                "prevention_keywords": [
                    "how to avoid", "how to prevent", "safer way", "alternative",
                    "safer option", "safer approach", "to minimize risk", "best practice",
                    "precautions", "steps to", "how to do this safely"
                ]
            },
            "hi": {
                "future_intent": [
                    "मैं चाहता हूं", "मैं करना चाहता हूं", "क्या मैं", "क्या मैं कर सकता हूं",
                    "मैं योजना बना रहा हूं", "मैंने सोच रहा हूं", "अगर मैं"
                ],
                "consequence_queries": [
                    "क्या होगा", "क्या परिणाम होंगे", "क्या मुझे सजा मिलेगी",
                    "जेल", "जुर्माना", "कानूनी समस्या", "परिणाम", "मुकदमा"
                ]
            }
        }

    def is_simulator_query(
        self,
        query: str,
        language: Optional[str] = None,
        conversation_history: Optional[list] = None
    ) -> SimulatorDetectionResult:
        """
        Determine if query is for simulator (planned action) or chatbot (existing situation).
        
        Args:
            query: User's query text
            language: Language code (detected if not provided)
            conversation_history: Previous messages for context
            
        Returns:
            SimulatorDetectionResult with decision and confidence
        """
        
        try:
            # Detect language if not provided
            if not language:
                language = detect_language(query)
                if not language:
                    language = "en"
            
            # Get patterns for language
            patterns = self.detection_patterns.get(language, self.detection_patterns["en"])
            
            # Normalize query
            query_lower = query.lower()
            
            # Calculate detection scores
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
            
            # Determine if this is simulator query
            simulator_indicators = future_intent_score > 0 or (
                action_keyword_score > 0 and consequence_score > 0
            )
            
            chatbot_indicators = existing_situation_score > future_intent_score
            
            is_simulator = (
                simulator_indicators and 
                not chatbot_indicators and
                (future_intent_score > 0 or (action_keyword_score > 0.5 and consequence_score > 0))
            )
            
            # Calculate confidence
            if is_simulator:
                confidence = min(
                    0.95,
                    (future_intent_score * 0.4 + 
                     action_keyword_score * 0.3 + 
                     consequence_score * 0.3) / 3
                )
                confidence = max(0.5, confidence)  # Min confidence for positive detection
            else:
                confidence = max(
                    0.5,
                    1.0 - (future_intent_score * 0.5 + action_keyword_score * 0.3)
                ) if future_intent_score == 0 else 0.6
            
            # Extract action if simulator
            extracted_action = None
            if is_simulator:
                extracted_action = self._extract_action(query)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                query,
                is_simulator,
                future_intent_score,
                action_keyword_score,
                consequence_score
            )
            
            # Determine suggested mode
            if is_simulator:
                suggested_mode = "simulate"
            elif consequence_score > 0.5:
                suggested_mode = "chat"  # Chatbot can also help with consequences
            elif any(word in query_lower for word in ["predict", "case", "outcome"]):
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
            logger.error(f"Error in simulator detection: {str(e)}")
            # Default: treat as chat
            return SimulatorDetectionResult(
                is_simulator_query=False,
                confidence=0.5,
                extracted_action=None,
                reasoning="Detection failed, defaulting to chat mode",
                suggested_mode="chat"
            )

    def _calculate_score(self, text: str, keywords: list) -> float:
        """Calculate keyword match score"""
        if not keywords:
            return 0.0
        
        matches = sum(1 for keyword in keywords if keyword in text)
        return min(1.0, matches / max(len(keywords), 1))

    def _extract_action(self, query: str) -> Optional[str]:
        """Extract the planned action from query"""
        
        # Find key phrases
        action_starts = [
            "want to", "planning to", "plan to", "thinking about",
            "considering", "going to", "about to", "would like to"
        ]
        
        query_lower = query.lower()
        
        for start_phrase in action_starts:
            idx = query_lower.find(start_phrase)
            if idx != -1:
                # Extract from start phrase to end or period
                end_idx = query.find(".", idx)
                if end_idx == -1:
                    end_idx = len(query)
                
                action = query[idx:end_idx].strip()
                return action if len(action) > 10 else None
        
        # If no action phrase found, return first part of query
        sentences = query.split(".")
        if sentences and len(sentences[0]) > 20:
            return sentences[0].strip()
        
        return None

    def _generate_reasoning(
        self,
        query: str,
        is_simulator: bool,
        future_score: float,
        action_score: float,
        consequence_score: float
    ) -> str:
        """Generate reasoning for the detection decision"""
        
        if is_simulator:
            reasons = []
            if future_score > 0:
                reasons.append("Future intent detected (want to, planning to, etc.)")
            if action_score > 0:
                reasons.append("Action-oriented keywords detected")
            if consequence_score > 0:
                reasons.append("Consequence inquiry detected")
            
            return f"Simulator mode recommended. Reasons: {', '.join(reasons)}"
        else:
            return "Chat mode recommended. This appears to be a question about an existing situation or general legal guidance."


def get_simulator_detection() -> SimulatorDetectionService:
    """Get singleton instance"""
    if not hasattr(get_simulator_detection, '_instance'):
        get_simulator_detection._instance = SimulatorDetectionService()
    return get_simulator_detection._instance
