"""
Chat Intelligence Router
Handles intelligent routing between chat and prediction modes
Uses LLM to extract case context from conversations
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.services.llm_service import LLMService
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat-intelligence", tags=["Chat Intelligence"])

# ============================================================================
# MODELS
# ============================================================================

class ChatMessage(BaseModel):
    """Single chat message"""
    text: str
    sender: str  # "user" or "bot"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ContextExtractionRequest(BaseModel):
    """Request to extract case context from chat messages"""
    messages: List[ChatMessage]
    language: str = "en"

class ExtractedCaseContext(BaseModel):
    """Extracted case information from conversation"""
    case_name: Optional[str] = None
    case_type: Optional[str] = None  # criminal, civil, family, property, etc.
    jurisdiction_state: Optional[str] = None
    year: Optional[int] = None
    damages_awarded: Optional[float] = None
    parties_count: Optional[int] = None
    is_appeal: Optional[bool] = None
    case_summary: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)  # How confident are we in extraction
    extraction_warnings: List[str] = []
    missing_fields: List[str] = []  # Which prediction fields are still needed

class ModeDecisionRequest(BaseModel):
    """Request to decide if user wants chat or prediction"""
    user_message: str
    conversation_history: List[ChatMessage] = []
    language: str = "en"

class ModeDecisionResponse(BaseModel):
    """Decision response"""
    suggested_mode: str  # "chat" or "predict"
    confidence: float
    reasoning: str
    follow_up_message: str  # What the bot should say next

class PredictionQuestionRequest(BaseModel):
    """Request to get next prediction question"""
    extracted_context: ExtractedCaseContext
    asked_questions: List[str] = []
    language: str = "en"

class PredictionQuestion(BaseModel):
    """A question for case outcome prediction"""
    question_id: str
    question_text: str
    field_name: str  # Which case field this maps to
    question_type: str  # "multiple_choice", "number", "yes_no", "text"
    options: Optional[List[str]] = None  # For multiple choice
    placeholder: Optional[str] = None
    hints: Optional[str] = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/extract-context",
    response_model=ExtractedCaseContext,
    status_code=200,
    summary="Extract Case Context from Chat",
    description="Uses LLM to intelligently extract case information from conversation"
)
async def extract_case_context(
    request_body: ContextExtractionRequest,
    request: Request
) -> ExtractedCaseContext:
    """
    Analyzes chat history to extract structured case information.
    
    This intelligently identifies:
    - Case type (Criminal, Civil, Family, Property, etc.)
    - Jurisdiction
    - Whether it's an appeal
    - Damages/amounts involved
    - Number of parties
    - Confidence level of extraction
    
    Args:
        request_body: Contains messages and language
    
    Returns:
        ExtractedCaseContext with extracted fields and confidence
    """
    try:
        llm_service = LLMService()
        
        # Build conversation text
        conversation = "\n".join([
            f"{msg.sender.upper()}: {msg.text}"
            for msg in request_body.messages
        ])
        
        extraction_prompt = f"""Analyze this legal conversation and extract structured case information.

CONVERSATION:
{conversation}

Extract the following information if mentioned:
1. case_type: Type of case (criminal, civil, family, property_dispute, appeal, contract_dispute, employment, etc.)
2. jurisdiction_state: Which state/jurisdiction (India: Delhi, Mumbai, Bangalore, etc.; USA: California, Texas, etc.)
3. year: What year is the case from?
4. damages_awarded: Any money/damages mentioned?
5. parties_count: How many parties involved? (default 2)
6. is_appeal: Is this an appeal case? (true/false)
7. case_summary: Brief 1-2 sentence summary
8. confidence: How confident are you (0.0-1.0)?
9. missing_fields: List which prediction fields still need to be clarified
10. warnings: Any ambiguities or unclear information?

Return ONLY valid JSON:
{{
    "case_name": "...",
    "case_type": "...",
    "jurisdiction_state": "...",
    "year": null,
    "damages_awarded": null,
    "parties_count": 2,
    "is_appeal": false,
    "case_summary": "...",
    "confidence": 0.8,
    "missing_fields": ["case_type", "jurisdiction"],
    "extraction_warnings": ["Year not mentioned", "Damages unclear"]
}}"""
        
        response_text = llm_service.get_response(extraction_prompt)
        
        # Parse JSON response
        response_data = json.loads(response_text)
        
        return ExtractedCaseContext(**response_data)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract context from conversation"
        )
    except Exception as e:
        logger.error(f"Context extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Context extraction failed: {str(e)}"
        )

@router.post(
    "/decide-mode",
    response_model=ModeDecisionResponse,
    status_code=200,
    summary="Decide Chat vs Prediction Mode",
    description="Uses LLM to intelligently determine if user wants to chat or predict"
)
async def decide_mode(
    request_body: ModeDecisionRequest,
    request: Request
) -> ModeDecisionResponse:
    """
    Decides whether user wants to chat for legal guidance or predict case outcome.
    
    Args:
        request_body: User message and conversation history
    
    Returns:
        ModeDecisionResponse with suggested mode and follow-up
    """
    try:
        llm_service = LLMService()
        
        conversation = ""
        if request_body.conversation_history:
            conversation = "\n".join([
                f"{msg.sender.upper()}: {msg.text}"
                for msg in request_body.conversation_history[-5:]  # Last 5 messages only
            ])
        
        mode_prompt = f"""Based on this user message, determine if they want:
1. "chat" = Legal guidance/advice about their case
2. "predict" = Predict the outcome of their case

RECENT CONVERSATION:
{conversation}

USER'S LATEST MESSAGE:
{request_body.user_message}

Respond with JSON only:
{{
    "suggested_mode": "chat" or "predict",
    "confidence": 0.0-1.0,
    "reasoning": "Brief reason for this decision",
    "follow_up_message": "What the bot should say next to confirm or clarify"
}}

Examples of "predict" keywords: outcome, chances, will I win, predict, likely result
Examples of "chat" keywords: explain, help, understand, how does, what is, advice"""
        
        response_text = llm_service.get_response(mode_prompt)
        response_data = json.loads(response_text)
        
        return ModeDecisionResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Mode decision error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mode decision failed: {str(e)}"
        )

@router.post(
    "/next-prediction-question",
    response_model=PredictionQuestion,
    status_code=200,
    summary="Get Next Prediction Question",
    description="Returns the next most important question needed for prediction"
)
async def get_next_prediction_question(
    request_body: PredictionQuestionRequest,
    request: Request
) -> PredictionQuestion:
    """
    Generates the next question for case outcome prediction.
    Uses progressive disclosure - asks most important questions first.
    
    Args:
        request_body: Current extracted context and asked questions
    
    Returns:
        PredictionQuestion with the next question to ask
    """
    
    # Define all possible questions for predictions
    all_questions = [
        PredictionQuestion(
            question_id="q_case_type",
            question_text="What type of case is this?",
            field_name="case_type",
            question_type="multiple_choice",
            options=["Criminal", "Civil", "Family", "Property Dispute", "Appeal", "Contract", "Employment", "Other"],
            hints="E.g., criminal case, civil dispute, family matter, property conflict..."
        ),
        PredictionQuestion(
            question_id="q_jurisdiction",
            question_text="What is the jurisdiction?",
            field_name="jurisdiction_state",
            question_type="text",
            placeholder="E.g., Delhi, Mumbai, California, Texas...",
            hints="The state or region where the case is being heard"
        ),
        PredictionQuestion(
            question_id="q_appeal",
            question_text="Is this an appeal case?",
            field_name="is_appeal",
            question_type="yes_no",
            options=["Yes", "No"]
        ),
        PredictionQuestion(
            question_id="q_year",
            question_text="What year is/was the case filed?",
            field_name="year",
            question_type="number",
            placeholder="E.g., 2023, 2024...",
            hints="The year when the original case was filed"
        ),
        PredictionQuestion(
            question_id="q_parties",
            question_text="How many parties are involved?",
            field_name="parties_count",
            question_type="number",
            placeholder="E.g., 2, 3, 4...",
            hints="Number of people/organizations involved"
        ),
        PredictionQuestion(
            question_id="q_damages",
            question_text="What is the monetary value/damages involved?",
            field_name="damages_awarded",
            question_type="number",
            placeholder="E.g., 500000, 1000000...",
            hints="In rupees if India case, dollars if USA case"
        ),
    ]
    
    # Filter out already asked questions
    already_asked_ids = {q.split(":")[0] for q in request_body.asked_questions}
    unanswered = [q for q in all_questions if q.question_id not in already_asked_ids]
    
    # Prioritize based on what's missing in context
    missing_fields = request_body.extracted_context.missing_fields or []
    
    # Sort: prioritize missing fields
    def priority_score(q: PredictionQuestion):
        if q.field_name in missing_fields:
            return 0  # Higher priority
        return 1
    
    unanswered.sort(key=priority_score)
    
    if unanswered:
        return unanswered[0]
    else:
        # All questions asked, return dummy (should trigger prediction)
        return PredictionQuestion(
            question_id="q_done",
            question_text="All information collected!",
            field_name="__done__",
            question_type="none"
        )

# ============================================================================
# HELPER: Merge extracted context with user answers
# ============================================================================

class MergeContextRequest(BaseModel):
    """Request to merge user answers with extracted context"""
    current_context: Dict[str, Any]
    field_name: str
    answer: Any

@router.post(
    "/merge-answer",
    status_code=200,
    summary="Merge User Answer into Context",
    description="Updates extracted context with user's answer to a question"
)
async def merge_answer(request_body: MergeContextRequest) -> Dict[str, Any]:
    """Updates the extracted context with a user's answer"""
    updated = {**request_body.current_context}
    updated[request_body.field_name] = request_body.answer
    
    # Update missing_fields
    if "missing_fields" in updated and request_body.field_name in updated["missing_fields"]:
        updated["missing_fields"].remove(request_body.field_name)
    
    return updated
