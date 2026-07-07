import json as _json
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from src.models.query_model import QueryRequest, QueryResponse, ImpactScoreModel
from src.models.db_models import ConversationCreate
from src.services.llm_service import (
    get_legal_response,
    create_rag_enhanced_prompt,
    create_streaming_prompt,
    parse_streaming_output,
    get_legal_response_stream,
)
from src.services.precedent_service import get_precedent_service
from src.services.parser import parse_llm_output
from src.services.language_service import detect_language, get_language_name
from src.services.feedback_processor import FeedbackProcessor, ScoreFeedback, ScoreFeedbackResponse
from src.services.smart_mode_router import get_smart_mode_router, ModeRecommendation
from src.services.conversation_service import ConversationService
import logging
import uuid
import time

logger = logging.getLogger(__name__)
router = APIRouter()
smart_router = get_smart_mode_router()


@router.post("/detect-mode")
def detect_query_mode(req: QueryRequest, request: Request):
    """
    Phase 3: Smart mode detection endpoint.
    Analyzes a query and recommends the most appropriate mode.
    
    Modes:
    - 'chat': Traditional chatbot for legal advice about existing situations
    - 'predict': ML-based case outcome prediction
    - 'simulate': Consequence simulator for planned actions
    
    Args:
        req: QueryRequest with query text and optional language
        request: HTTP request object
        
    Returns:
        Mode recommendation with confidence and reasoning
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"[{request_id}] Mode detection requested: {req.query[:80]}...")
        
        # Detect language if not provided
        language = req.language or detect_language(req.query)
        if not language:
            language = "en"
        
        # Get mode recommendation from smart router
        result = smart_router.route_query(
            req.query,
            language=language,
            session_id=None  # Optional: client can provide session_id
        )
        
        recommendation = result.mode_recommendation
        
        response = {
            "request_id": request_id,
            "suggested_mode": recommendation.primary_mode,
            "confidence": recommendation.confidence,
            "confidence_tier": recommendation.confidence_tier,
            "alternative_modes": recommendation.alternative_modes,
            "reasoning": recommendation.reasoning,
            "extracted_action": recommendation.extracted_action,
            "needs_context": result.needs_context,
            "language": language,
            "processing_time_ms": (time.time() - start_time) * 1000
        }
        
        logger.info(
            f"[{request_id}] Mode detected: {recommendation.primary_mode} "
            f"({recommendation.confidence:.0%} confidence)"
        )
        
        return response
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"[{request_id}] Error in mode detection after {elapsed:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect mode. Please try again."
        )


@router.post("/query", response_model=QueryResponse, status_code=200)
def handle_query(req: QueryRequest, request: Request) -> QueryResponse:
    """
    Process a legal chatbot query and return structured response.
    
    Simple pipeline:
    1. Detect language from query
    2. Call LLM for legal analysis
    3. Parse response
    4. Return summary, laws, and suggestions
    
    Args:
        req: QueryRequest containing the user's legal question and optional language code
        request: HTTP request object
        
    Returns:
        QueryResponse with summary, laws, and suggestions
        
    Raises:
        HTTPException: For various error conditions during processing
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"[{request_id}] New chatbot query received: {req.query[:80]}...")
        
        # Detect language
        if req.language:
            language = req.language.lower()
            logger.info(f"[{request_id}] Language: {language} (provided)")
        else:
            logger.debug(f"[{request_id}] Detecting language from query...")
            language = detect_language(req.query)
            logger.info(f"[{request_id}] Language auto-detected: {language}")
        
        # Phase 3: Smart mode detection
        logger.debug(f"[{request_id}] Detecting query mode...")
        mode_start = time.time()
        mode_result = smart_router.route_query(
            req.query,
            language=language,
            session_id=None
        )
        mode_time = time.time() - mode_start
        logger.debug(f"[{request_id}] Mode detection took {mode_time:.2f}s")
        
        mode_rec = mode_result.mode_recommendation

        logger.info(
            f"[{request_id}] Query mode: {mode_rec.primary_mode} "
            f"({mode_rec.confidence:.0%} confidence)"
        )

        # Auto-route to consequence simulator when intent is clear
        if mode_rec.primary_mode == "simulate" and mode_rec.confidence >= 0.70:
            logger.info(f"[{request_id}] Auto-routing to consequence simulator")
            try:
                from src.services.consequence_simulator import get_consequence_simulator
                import json as _json

                simulator = get_consequence_simulator()
                action = mode_rec.extracted_action or req.query
                sim_result = simulator.simulate_planned_action(
                    action_description=action,
                    jurisdiction="India",
                    language=language
                )

                risk_score_map = {"Low": 20, "Medium": 50, "High": 70, "Critical": 90}
                risk_label_map = {
                    "Low": "🟢 Low", "Medium": "🟡 Medium",
                    "High": "🟠 High", "Critical": "🔴 Critical"
                }
                risk_str = sim_result.risk_level.value if hasattr(sim_result.risk_level, "value") else str(sim_result.risk_level)
                score_val = risk_score_map.get(risk_str, 50)
                risk_label = risk_label_map.get(risk_str, "🟡 Medium")

                sim_impact = ImpactScoreModel(
                    overall_score=score_val,
                    financial_risk_score=score_val,
                    legal_exposure_score=score_val,
                    long_term_impact_score=score_val,
                    rights_lost_score=score_val,
                    risk_level=risk_label,
                    breakdown={"consequence_analysis": f"Risk level: {risk_str}"},
                    key_factors=[r.factor for r in sim_result.key_risks[:3]] if sim_result.key_risks else [],
                    mitigating_factors=[a.alternative for a in sim_result.safer_alternatives[:2]] if sim_result.safer_alternatives else [],
                    recommendation=sim_result.explanation[:300] if sim_result.explanation else "Consult a legal professional."
                )

                try:
                    sim_dict = _json.loads(sim_result.json())
                except Exception:
                    sim_dict = {}

                conv_id = None
                try:
                    conv_data = ConversationCreate(user_id="anonymous", title=req.query[:100], language=language)
                    conv = ConversationService.create_conversation(conv_data)
                    if conv:
                        ConversationService.add_message(str(conv.id), role="user", content=req.query, language=language)
                        ConversationService.add_message(str(conv.id), role="assistant", content=sim_result.explanation or "", language=language)
                        conv_id = str(conv.id)
                except Exception as conv_err:
                    logger.warning(f"[{request_id}] Could not persist simulation conversation: {conv_err}")

                elapsed = time.time() - start_time
                logger.info(f"[{request_id}] Simulation response ready in {elapsed:.2f}s")

                return QueryResponse(
                    request_id=request_id,
                    summary=sim_result.explanation or "Simulation complete.",
                    laws=[law.name for law in sim_result.applicable_laws] if sim_result.applicable_laws else [],
                    suggestions=[alt.alternative for alt in sim_result.safer_alternatives] if sim_result.safer_alternatives else [],
                    impact_score=sim_impact,
                    language=language,
                    suggested_mode="simulate",
                    mode_confidence=mode_rec.confidence,
                    mode_reasoning=mode_rec.reasoning,
                    extracted_action=mode_rec.extracted_action,
                    response_type="simulation",
                    simulation_data=sim_dict,
                    conversation_id=conv_id
                )

            except Exception as sim_err:
                logger.warning(f"[{request_id}] Simulator failed, falling back to chat: {sim_err}")
                # Fall through to normal LLM chat flow below

        # Return a lightweight prediction prompt — no LLM call needed
        if mode_rec.primary_mode == "predict" and mode_rec.confidence >= 0.80:
            logger.info(f"[{request_id}] Returning prediction_prompt response")
            return QueryResponse(
                request_id=request_id,
                summary="It sounds like you want to know how your case might turn out in court. I can guide you through a quick assessment — just switch to Predict mode and I'll ask you a few structured questions.",
                laws=[],
                suggestions=["Switch to Predict mode to get an ML-based case outcome prediction.", "Have your case details ready: case type, jurisdiction, year, and any damages claimed."],
                impact_score=ImpactScoreModel(
                    overall_score=0,
                    financial_risk_score=0,
                    legal_exposure_score=0,
                    long_term_impact_score=0,
                    rights_lost_score=0,
                    risk_level="Assessment not performed",
                    breakdown={"note": "Use Predict mode for case outcome analysis"},
                    key_factors=[],
                    mitigating_factors=[],
                    recommendation="Switch to Predict mode for a structured case outcome assessment."
                ),
                language=language,
                suggested_mode="predict",
                mode_confidence=mode_rec.confidence,
                mode_reasoning=mode_rec.reasoning,
                extracted_action=mode_rec.extracted_action,
                response_type="prediction_prompt",
                conversation_id=None
            )

        # RAG: retrieve precedents — dense (InLegalBERT) if available, TF-IDF fallback
        rag_system_prompt = None
        precedents: list = []   # populated inside try; used below to build similar_cases
        try:
            from src.services.dense_retrieval_service import get_dense_retrieval_service
            precedents = []

            dense_svc = get_dense_retrieval_service()
            if dense_svc.available:
                rag_start  = time.time()
                precedents = dense_svc.search(req.query, top_k=4)
                rag_time   = time.time() - rag_start
                if precedents:
                    logger.info(
                        f"[{request_id}] Dense RAG: {len(precedents)} results "
                        f"in {rag_time:.2f}s (top_sim={precedents[0].get('similarity',0):.3f})"
                    )
                else:
                    logger.debug(f"[{request_id}] Dense RAG: no results above threshold")

            # Fall back to TF-IDF precedent index when dense index is not ready
            if not precedents:
                precedent_svc = get_precedent_service()
                if precedent_svc.available:
                    rag_start  = time.time()
                    precedents = precedent_svc.search(req.query, top_k=4)
                    rag_time   = time.time() - rag_start
                    if precedents:
                        logger.info(
                            f"[{request_id}] TF-IDF RAG: {len(precedents)} results "
                            f"in {rag_time:.2f}s (top_sim={precedents[0].get('similarity',0):.3f})"
                        )
                    else:
                        logger.debug(f"[{request_id}] TF-IDF RAG: no results above threshold")
                else:
                    logger.debug(f"[{request_id}] Precedent index not available — skipping RAG")

            if precedents:
                rag_system_prompt = create_rag_enhanced_prompt(language, precedents)

        except Exception as rag_err:
            logger.warning(f"[{request_id}] RAG retrieval failed, proceeding without context: {rag_err}")

        # Apply state-level jurisdiction context when caller specifies a state
        req_state = (req.state or "").strip()
        if req_state and req_state not in ("National", "All India"):
            base = rag_system_prompt if rag_system_prompt else None
            # Build or augment the system prompt with a jurisdiction note
            jurisdiction_addendum = (
                f"\n\nJURISDICTION: The user is asking about laws in {req_state}, India. "
                f"Prioritise {req_state}-specific legislation, High Court judgments, and state regulations. "
                f"Explicitly note when advice is specific to {req_state}."
            )
            if base:
                rag_system_prompt = base + jurisdiction_addendum
            else:
                from src.services.llm_service import create_language_aware_prompt
                rag_system_prompt = create_language_aware_prompt(language) + jurisdiction_addendum
            logger.info(f"[{request_id}] Jurisdiction override → {req_state}")

        # Build conversation history list for multi-turn memory
        history = (
            [{"role": m.role, "content": m.content} for m in req.conversation_history]
            if req.conversation_history else None
        )

        # Call LLM for legal analysis (RAG-augmented prompt + conversation history)
        logger.debug(f"[{request_id}] Calling LLM service for legal analysis...")
        llm_start = time.time()
        try:
            raw_output = get_legal_response(
                req.query,
                language=language,
                system_prompt=rag_system_prompt,       # None → default prompt (no RAG)
                conversation_history=history,           # None → stateless (no history)
            )
            llm_time = time.time() - llm_start
            logger.debug(f"[{request_id}] LLM response received in {llm_time:.2f}s ({len(raw_output)} chars)")
        except Exception as e:
            llm_time = time.time() - llm_start
            logger.error(f"[{request_id}] LLM service failed after {llm_time:.2f}s: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Legal AI service unavailable: {str(e)}"
            )
        
        # Parse LLM response
        logger.debug(f"[{request_id}] Parsing LLM response...")
        try:
            parsed = parse_llm_output(raw_output)
        except Exception as e:
            logger.error(f"[{request_id}] Failed to parse LLM output: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse AI response"
            )
        
        # Add required metadata
        parsed["request_id"] = request_id
        parsed["language"]    = language

        # Attach retrieved court precedents so the frontend can display them
        parsed["similar_cases"] = [
            {
                "case_name":  p.get("case_name",  ""),
                "case_type":  p.get("case_type",  ""),
                "summary":    (p.get("summary") or "")[:350],
                "similarity": round(float(p.get("similarity", 0.0)), 4),
            }
            for p in precedents
            if float(p.get("similarity", 0.0)) >= 0.08
        ]
        logger.debug(
            f"[{request_id}] Attaching {len(parsed['similar_cases'])} similar cases to response"
        )

        # Add mode information
        parsed["suggested_mode"] = mode_rec.primary_mode
        parsed["mode_confidence"] = mode_rec.confidence
        parsed["mode_reasoning"] = mode_rec.reasoning
        parsed["extracted_action"] = mode_rec.extracted_action
        
        # Provide default impact score (required by QueryResponse model)
        if "impact_score" not in parsed or parsed["impact_score"] is None:
            parsed["impact_score"] = ImpactScoreModel(
                overall_score=0,
                financial_risk_score=0,
                legal_exposure_score=0,
                long_term_impact_score=0,
                rights_lost_score=0,
                risk_level="Assessment not performed",
                breakdown={"note": "This is a chatbot response without detailed impact analysis"},
                key_factors=[],
                mitigating_factors=[],
                recommendation="Please consult with a legal professional for detailed analysis"
            )
        
        # Log completion
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] Query processed successfully in {elapsed:.2f}s")

        # Conversation persistence is handled by the frontend via POST /conversations
        # and POST /conversations/{id}/messages. The /query endpoint does not create
        # conversations itself to avoid duplicates.
        parsed["conversation_id"] = None

        # Return response
        response = QueryResponse(**parsed)
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"[{request_id}] Unexpected error after {elapsed:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query. Please try again."
        )


@router.post("/stream")
def handle_query_stream(req: QueryRequest, request: Request):
    """
    Streaming chatbot endpoint — server-sent events (SSE).

    Each event is a JSON object on a ``data: ...`` line followed by two newlines.
    Event shapes:
      {"type": "chunk",  "content": "<text fragment>"}
      {"type": "done",   "summary": "...", "laws": [...], "suggestions": [...],
                         "similar_cases": [...], "request_id": "..."}
      {"type": "error",  "message": "..."}
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # ── Language detection ───────────────────────────────────────────────────
    if req.language:
        language = req.language.lower().strip()
    else:
        language = detect_language(req.query) or "en"

    # ── RAG retrieval (same dual-index logic as /query) ──────────────────────
    precedents: list = []
    try:
        from src.services.dense_retrieval_service import get_dense_retrieval_service
        dense_svc = get_dense_retrieval_service()
        if dense_svc.available:
            precedents = dense_svc.search(req.query, top_k=4)
        if not precedents:
            precedent_svc = get_precedent_service()
            if precedent_svc.available:
                precedents = precedent_svc.search(req.query, top_k=4)
    except Exception as rag_err:
        logger.warning(f"[{request_id}] Stream RAG failed: {rag_err}")

    # Court precedents to attach in the done event
    similar_cases = [
        {
            "case_name":  p.get("case_name",  ""),
            "case_type":  p.get("case_type",  ""),
            "summary":    (p.get("summary") or "")[:350],
            "similarity": round(float(p.get("similarity", 0.0)), 4),
        }
        for p in precedents
        if float(p.get("similarity", 0.0)) >= 0.08
    ]

    # ── Build streaming system prompt ────────────────────────────────────────
    req_state = (req.state or "").strip()
    system_prompt = create_streaming_prompt(language, state=req_state)

    # Inject retrieved precedents as grounding context
    relevant_prec = [p for p in precedents if float(p.get("similarity", 0.0)) >= 0.08]
    if relevant_prec:
        rag_ctx = "\n\nRELEVANT INDIAN COURT PRECEDENTS (ground your answer in these):\n"
        for i, p in enumerate(relevant_prec, 1):
            rag_ctx += (
                f"\n[{i}] {p.get('case_name', '')}: "
                f"{(p.get('summary', '') or '')[:350]}\n"
            )
        rag_ctx += "\nCite these cases in your SUMMARY where applicable.\n"
        system_prompt += rag_ctx

    # ── Conversation history ─────────────────────────────────────────────────
    history = (
        [{"role": m.role, "content": m.content} for m in req.conversation_history]
        if req.conversation_history else None
    )

    logger.info(
        f"[{request_id}] Stream query: lang={language}, state={req_state or 'national'}, "
        f"rag_hits={len(similar_cases)}"
    )

    def event_stream():
        full_text = ""
        try:
            for chunk in get_legal_response_stream(
                req.query,
                language=language,
                system_prompt=system_prompt,
                conversation_history=history,
            ):
                full_text += chunk
                yield f"data: {_json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        except Exception as stream_err:
            logger.error(f"[{request_id}] Streaming generation error: {stream_err}")
            yield (
                f"data: {_json.dumps({'type': 'error', 'message': 'AI service error. Please try again.'})}\n\n"
            )
            return

        # Parse the full accumulated response into structured fields
        try:
            parsed = parse_streaming_output(full_text)
        except Exception:
            parsed = {"summary": full_text.strip(), "laws": [], "suggestions": []}

        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] Stream completed in {elapsed:.2f}s ({len(full_text)} chars)")

        done_payload = {
            "type":               "done",
            "summary":            parsed.get("summary", ""),
            "laws":               parsed.get("laws", []),
            "suggestions":        parsed.get("suggestions", []),
            "follow_up_questions": parsed.get("follow_up_questions", []),
            "risk_level":         parsed.get("risk_level", ""),
            "similar_cases":      similar_cases,
            "request_id":         request_id,
            "language":           language,
        }
        yield f"data: {_json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",    # disable nginx buffering in production
        },
    )


# Initialize feedback processor
feedback_processor = FeedbackProcessor()


@router.post("/feedback/score", response_model=ScoreFeedbackResponse, status_code=200)
def submit_score_feedback(feedback: ScoreFeedback) -> ScoreFeedbackResponse:
    """
    Submit user feedback on impact score accuracy.
    Helps improve the scoring algorithm through continuous learning.
    
    Args:
        feedback: ScoreFeedback with rating (1-5) and optional comment
        
    Returns:
        Confirmation of feedback submission
    """
    try:
        logger.info(
            f"Received score feedback for request {feedback.request_id}: "
            f"rating={feedback.user_rating}/5, type={feedback.feedback_type}"
        )
        
        result = feedback_processor.submit_feedback(feedback)
        
        return ScoreFeedbackResponse(
            status=result["status"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error(f"Failed to process feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback. Please try again."
        )


@router.get("/feedback/analysis", status_code=200)
def get_feedback_analysis():
    """
    Get analysis of user feedback patterns.
    Shows how well the scoring algorithm is performing and improvement areas.
    
    Returns:
        Analysis of feedback patterns and insights
    """
    try:
        logger.info("Retrieving feedback analysis...")
        analysis = feedback_processor.get_analysis()
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to retrieve feedback analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback analysis."
        )
