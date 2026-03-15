"""
Phase 3: Smart Mode Router Service
Intelligently detects user intent and routes to appropriate mode (chat/predict/simulate)
"""

import logging
from typing import Optional, Dict, List, Any
from enum import Enum
from dataclasses import dataclass, asdict

from src.services.enhanced_simulator_detection import (
    EnhancedSimulatorDetectionService,
    get_enhanced_simulator_detection
)
from src.services.language_service import detect_language

logger = logging.getLogger(__name__)


class UserMode(str, Enum):
    """Available user modes for legal assistance"""
    CHAT = "chat"              # Traditional chatbot for legal advice about existing situations
    PREDICT = "predict"        # ML-based case outcome prediction
    SIMULATE = "simulate"      # Consequence simulator for planned actions


class ModeConfidence(str, Enum):
    """Confidence levels for mode recommendations"""
    VERY_HIGH = "very_high"    # >85% confident
    HIGH = "high"              # 70-85% confident
    MEDIUM = "medium"          # 55-70% confident
    LOW = "low"                # 40-55% confident
    VERY_LOW = "very_low"      # <40% confident


@dataclass
class ModeRecommendation:
    """Recommendation for which mode to use"""
    primary_mode: str           # "chat", "predict", or "simulate"
    confidence: float           # 0.0-1.0 confidence in primary recommendation
    confidence_tier: str        # "very_high", "high", "medium", "low", "very_low"
    alternative_modes: List[str] # List of alternative modes if primary not suitable
    reasoning: str              # Human-readable explanation
    extracted_action: Optional[str] = None  # For simulate mode: what action is user asking about
    conversation_context: Optional[Dict] = None  # Context analysis from conversation


@dataclass
class SmartRouteResult:
    """Complete result from smart mode routing"""
    mode_recommendation: ModeRecommendation
    conversation_summary: Optional[str] = None
    needs_context: bool = False  # Whether more context is needed for confident recommendation
    user_intent_analysis: Optional[Dict] = None  # Detailed intent breakdown


class SmartModeRouter:
    """
    Intelligently routes user queries to appropriate mode based on:
    1. Detected intent (planned action vs existing situation vs prediction)
    2. Confidence in detection
    3. Conversation history/context
    4. User's language
    """

    def __init__(self):
        """Initialize smart router with detection service"""
        self.detector = get_enhanced_simulator_detection()
        self.conversation_history: Dict[str, List[Dict]] = {}  # session_id -> message list

    def route_query(
        self,
        query: str,
        language: Optional[str] = None,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> SmartRouteResult:
        """
        Route user query to appropriate mode with intelligent detection.
        
        Args:
            query: User's query text
            language: Language code (auto-detected if not provided)
            session_id: Session/conversation ID for tracking context
            conversation_history: Previous messages in conversation
            
        Returns:
            SmartRouteResult with mode recommendation and reasoning
        """
        
        try:
            # Auto-detect language if not provided
            if not language:
                language = detect_language(query)
                if not language:
                    language = "en"
            
            logger.info(f"[SmartRouter] Routing query in {language}: {query[:60]}...")
            
            # Run enhanced detection for simulator mode
            detection_result = self.detector.is_simulator_query(
                query,
                language=language,
                conversation_history=conversation_history
            )
            
            # Analyze intent based on detection
            mode_recommendation = self._analyze_intent(
                query,
                language,
                detection_result,
                conversation_history
            )
            
            # Store conversation if session ID provided
            if session_id:
                self._add_to_history(session_id, query, mode_recommendation.primary_mode)
            
            result = SmartRouteResult(
                mode_recommendation=mode_recommendation,
                needs_context=self._assess_context_need(
                    mode_recommendation,
                    conversation_history
                ),
                user_intent_analysis=self._analyze_intent_breakdown(
                    query,
                    detection_result,
                    language
                )
            )
            
            logger.info(
                f"[SmartRouter] Recommended mode: {mode_recommendation.primary_mode} "
                f"({mode_recommendation.confidence:.0%} confidence)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[SmartRouter] Error routing query: {str(e)}")
            # Fallback to chat mode on error
            return SmartRouteResult(
                mode_recommendation=ModeRecommendation(
                    primary_mode="chat",
                    confidence=0.5,
                    confidence_tier="low",
                    alternative_modes=["chat"],
                    reasoning="Error in mode detection, defaulting to chat mode"
                ),
                needs_context=True
            )

    def _analyze_intent(
        self,
        query: str,
        language: str,
        detection_result: Any,
        conversation_history: Optional[List[Dict]]
    ) -> ModeRecommendation:
        """
        Analyze user intent and recommend appropriate mode.
        
        Logic:
        - If planned action detected → SIMULATE mode
        - If prediction/outcome query → PREDICT mode
        - Default → CHAT mode
        """
        
        query_lower = query.lower()
        
        # Check for simulate mode indicators
        if detection_result.is_simulator_query:
            return ModeRecommendation(
                primary_mode="simulate",
                confidence=detection_result.confidence,
                confidence_tier=detection_result.confidence_tier,
                alternative_modes=["chat"],  # Can also ask chat about legal questions
                reasoning=detection_result.reasoning,
                extracted_action=detection_result.extracted_action,
                conversation_context=self._extract_context(conversation_history)
            )
        
        # Check for predict mode indicators
        predict_indicators = [
            "predict", "outcome", "verdict", "will i win", "case prediction",
            "chances", "likely result", "probable outcome", "probable verdict",
            "what will happen", "how will court", "will i succeed"
        ]
        
        if any(indicator in query_lower for indicator in predict_indicators):
            confidence = 0.75
            return ModeRecommendation(
                primary_mode="predict",
                confidence=confidence,
                confidence_tier=self._confidence_to_tier(confidence),
                alternative_modes=["chat", "simulate"],
                reasoning=f"User is asking about case prediction/outcome. "
                         f"Recommend case outcome predictor for ML-based analysis."
            )
        
        # Default to chat mode
        return ModeRecommendation(
            primary_mode="chat",
            confidence=0.85,
            confidence_tier="high",
            alternative_modes=["chat"],
            reasoning="User is asking about existing situation or legal advice. "
                     "Recommend chatbot for comprehensive legal guidance."
        )

    def suggest_mode_transition(
        self,
        current_mode: str,
        new_query: str,
        language: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Optional[ModeRecommendation]:
        """
        Suggest transitioning to a different mode if user's intent changes.
        
        Returns:
            ModeRecommendation if transition suggested, None if stay in current mode
        """
        
        try:
            if not language:
                language = detect_language(new_query)
            
            result = self.route_query(
                new_query,
                language=language,
                conversation_history=conversation_history
            )
            
            recommended_mode = result.mode_recommendation.primary_mode
            
            # Suggest transition only if confident and different from current
            if (recommended_mode != current_mode and 
                result.mode_recommendation.confidence > 0.70):
                return result.mode_recommendation
            
            return None
            
        except Exception as e:
            logger.error(f"[SmartRouter] Error suggesting transition: {str(e)}")
            return None

    def _analyze_intent_breakdown(
        self,
        query: str,
        detection_result: Any,
        language: str
    ) -> Dict[str, Any]:
        """
        Break down intent analysis with detailed metrics.
        """
        
        query_lower = query.lower()
        
        analysis = {
            "language": language,
            "query_length": len(query),
            "detected_intent": {
                "is_planning": detection_result.is_simulator_query,
                "planning_confidence": detection_result.confidence,
                "extracted_action": detection_result.extracted_action
            },
            "intent_indicators": {
                "future_tense": self._has_future_tense(query_lower),
                "conditional": self._has_conditional(query_lower),
                "hypothetical": self._has_hypothetical(query_lower),
                "existing_situation": self._has_existing_situation(query_lower),
                "needs_prediction": self._has_prediction_query(query_lower)
            }
        }
        
        return analysis

    def _extract_context(self, conversation_history: Optional[List[Dict]]) -> Dict:
        """Extract useful context from conversation history"""
        if not conversation_history:
            return {}
        
        context = {
            "conversation_length": len(conversation_history),
            "has_planning_context": False,
            "has_legal_terms": False,
            "primary_topics": []
        }
        
        # Analyze conversation for planning/legal language
        if len(conversation_history) > 0:
            planning_words = ["plan", "think", "consider", "want", "intend"]
            legal_words = ["law", "legal", "rights", "court", "attorney"]
            
            conversation_text = " ".join([
                msg.get("content", "") for msg in conversation_history
                if isinstance(msg, dict)
            ]).lower()
            
            context["has_planning_context"] = any(
                word in conversation_text for word in planning_words
            )
            context["has_legal_terms"] = any(
                word in conversation_text for word in legal_words
            )
        
        return context

    def _assess_context_need(
        self,
        recommendation: ModeRecommendation,
        conversation_history: Optional[List[Dict]]
    ) -> bool:
        """
        Assess whether we need more context for a confident recommendation.
        
        Returns:
            True if more context is needed, False if confident enough
        """
        
        # If low confidence, need more context
        if recommendation.confidence < 0.60:
            return True
        
        # If no conversation history and complex mode, might need more context
        if not conversation_history and recommendation.primary_mode in ["predict", "simulate"]:
            return True
        
        return False

    def _confidence_to_tier(self, confidence: float) -> str:
        """Convert numeric confidence (0-1) to tier name"""
        if confidence >= 0.85:
            return "very_high"
        elif confidence >= 0.70:
            return "high"
        elif confidence >= 0.55:
            return "medium"
        elif confidence >= 0.40:
            return "low"
        else:
            return "very_low"

    def _has_future_tense(self, text: str) -> bool:
        """Check if text contains future tense indicators"""
        future_indicators = [
            "will", "going to", "going to", "plan to", "intend to",
            "want to", "would", "could", "should", "i'm planning"
        ]
        return any(indicator in text for indicator in future_indicators)

    def _has_conditional(self, text: str) -> bool:
        """Check if text has conditional language"""
        conditionals = ["if", "suppose", "imagine", "what if"]
        return any(cond in text for cond in conditionals)

    def _has_hypothetical(self, text: str) -> bool:
        """Check if text has hypothetical language"""
        hypotheticals = ["hypothetically", "theoretically", "assume", "assuming"]
        return any(hyp in text for hyp in hypotheticals)

    def _has_existing_situation(self, text: str) -> bool:
        """Check if text describes existing situation"""
        situation_indicators = [
            "i have", "i was", "i received", "already", "happened",
            "situation", "current", "right now", "my employer"
        ]
        return any(indicator in text for indicator in situation_indicators)

    def _has_prediction_query(self, text: str) -> bool:
        """Check if text asks for prediction"""
        prediction_words = ["predict", "outcome", "verdict", "win", "case"]
        return any(word in text for word in prediction_words)

    def _add_to_history(self, session_id: str, query: str, mode: str):
        """Add query to conversation history"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "query": query,
            "mode": mode,
            "timestamp": __import__("time").time()
        })

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Retrieve conversation history for a session"""
        return self.conversation_history.get(session_id, [])

    def clear_conversation_history(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]


# Singleton instance
_smart_router_instance: Optional[SmartModeRouter] = None


def get_smart_mode_router() -> SmartModeRouter:
    """Get or create singleton instance of smart mode router"""
    global _smart_router_instance
    if _smart_router_instance is None:
        _smart_router_instance = SmartModeRouter()
    return _smart_router_instance
