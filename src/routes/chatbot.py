import json as _json
import concurrent.futures as _cf
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
    classify_query_intent,
    CASUAL_SYSTEM_PROMPT,
    _is_raw_filename,
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

_STREAM_TIMEOUT_SECONDS = 90  # SSE stream killed after this many seconds of no completion


_BAIL_KEYWORDS = frozenset({
    "bail", "bailable", "non-bailable", "anticipatory", "regular bail",
    "bail application", "section 437", "section 438", "section 439",
    "crpc 437", "crpc 438", "crpc 439", "bnss 479", "bnss 480", "bnss 483",
    "custody", "arrested", "arrest", "detained", "detention", "remand",
    "bail granted", "bail denied", "bail rejected", "bail hearing",
    "interim bail", "surety", "undertrial",
})


def _is_bail_query(query: str) -> bool:
    """Return True when the user's query is likely bail-related."""
    q_lower = query.lower()
    return any(kw in q_lower for kw in _BAIL_KEYWORDS)


def _run_bail_prediction(query: str) -> dict:
    """Run bail specialist model on a chatbot query. Returns {} on any failure."""
    try:
        from src.services.inlegalbert_bail_service import get_inlegalbert_bail_service
        svc = get_inlegalbert_bail_service()
        if not svc.available:
            return {}
        return svc.predict(query)
    except Exception as exc:
        logger.warning(f"[Bail] Chatbot bail prediction failed: {exc}")
        return {}


def _run_rag(query: str) -> list:
    """
    Run dual-index RAG retrieval (dense InLegalBERT → TF-IDF fallback).
    Returns an empty list on any failure so callers never need to guard.
    """
    try:
        from src.services.dense_retrieval_service import get_dense_retrieval_service
        dense_svc = get_dense_retrieval_service()
        if dense_svc.available:
            results = dense_svc.search(query, top_k=4)
            if results:
                return results
        precedent_svc = get_precedent_service()
        if precedent_svc.available:
            return precedent_svc.search(query, top_k=4)
        return []
    except Exception as exc:
        logger.warning(f"[RAG] Retrieval failed: {exc}")
        return []


def _build_rag_system_prompt(language: str, precedents: list, state: str = "") -> str:
    """
    Build the legal system prompt augmented with RAG precedents.
    Applies state-level jurisdiction addendum when `state` is provided.
    """
    system_prompt = create_streaming_prompt(language, state=state)

    relevant = [p for p in precedents if float(p.get("similarity", 0.0)) >= 0.08]
    if relevant:
        rag_ctx = "\n\nRELEVANT INDIAN COURT PRECEDENTS (background context only):\n"
        rag_ctx += (
            "Use these only as factual background. "
            "DO NOT cite them by number, filename, or ID. "
            "Only mention a case by name if it has a proper descriptive name.\n"
        )
        for i, p in enumerate(relevant, 1):
            raw_name = p.get("case_name", "")
            summary  = (p.get("summary", "") or "")[:350]
            has_real_name = raw_name and not _is_raw_filename(raw_name)
            label = f"[Context {i}]" + (f" {raw_name}" if has_real_name else "")
            rag_ctx += f"\n{label}: {summary}\n"
        system_prompt += rag_ctx

    if state and state not in ("National", "All India"):
        addendum = (
            f"\n\nJURISDICTION: The user is asking about laws in {state}, India. "
            f"Prioritise {state}-specific legislation, High Court judgments, and state regulations. "
            f"Explicitly note when advice is specific to {state}."
        )
        system_prompt += addendum

    return system_prompt


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

        # Parallel: classify query intent + run RAG retrieval (+ bail model when relevant)
        is_bail = _is_bail_query(req.query)
        n_workers = 3 if is_bail else 2
        bail_likelihood = None
        with _cf.ThreadPoolExecutor(max_workers=n_workers) as _pool:
            _clf_fut  = _pool.submit(classify_query_intent, req.query)
            _rag_fut  = _pool.submit(_run_rag, req.query)
            _bail_fut = _pool.submit(_run_bail_prediction, req.query) if is_bail else None
            try:
                query_intent = _clf_fut.result(timeout=8)
            except Exception:
                query_intent = "legal"
            try:
                precedents: list = _rag_fut.result(timeout=8)
            except Exception:
                precedents = []
            bail_likelihood = None
            if _bail_fut is not None:
                try:
                    bail_result = _bail_fut.result(timeout=10)
                    if bail_result:
                        bail_likelihood = bail_result
                        logger.info(
                            f"[{request_id}] Bail prediction: {bail_result.get('prediction')} "
                            f"({bail_result.get('confidence', 0):.1f}% conf)"
                        )
                except Exception:
                    bail_likelihood = None
        # Discard RAG results for casual queries — they are irrelevant
        if query_intent != "legal":
            precedents = []

        logger.info(f"[{request_id}] Intent: {query_intent}, RAG hits: {len(precedents)}")

        # Handle casual queries: warm conversational reply, no legal analysis
        if query_intent == "casual":
            try:
                casual_text = get_legal_response(
                    req.query,
                    language=language,
                    system_prompt=CASUAL_SYSTEM_PROMPT,
                    conversation_history=None,
                )
            except Exception:
                casual_text = (
                    "Hello! I'm Nyaya, your AI legal assistant. "
                    "Feel free to ask me any legal questions!"
                )
            elapsed = time.time() - start_time
            logger.info(f"[{request_id}] Casual response in {elapsed:.2f}s")
            return QueryResponse(
                request_id=request_id,
                summary=casual_text,
                laws=[],
                suggestions=[],
                impact_score=ImpactScoreModel(
                    overall_score=0,
                    financial_risk_score=0,
                    legal_exposure_score=0,
                    long_term_impact_score=0,
                    rights_lost_score=0,
                    risk_level="",
                    breakdown={},
                    key_factors=[],
                    mitigating_factors=[],
                    recommendation="",
                ),
                language=language,
                suggested_mode="chat",
                mode_confidence=1.0,
                mode_reasoning="Casual query — no legal analysis needed.",
                extracted_action=None,
                response_type="casual",
                conversation_id=None,
            )

        # Legal query: build RAG-augmented system prompt
        rag_system_prompt = None
        if precedents:
            rag_system_prompt = create_rag_enhanced_prompt(language, precedents)
            logger.info(f"[{request_id}] RAG: {len(precedents)} precedents injected")

        # Apply state-level jurisdiction context when caller specifies a state
        req_state = (req.state or "").strip()
        if req_state and req_state not in ("National", "All India"):
            jurisdiction_addendum = (
                f"\n\nJURISDICTION: The user is asking about laws in {req_state}, India. "
                f"Prioritise {req_state}-specific legislation, High Court judgments, and state regulations. "
                f"Explicitly note when advice is specific to {req_state}."
            )
            if rag_system_prompt:
                rag_system_prompt += jurisdiction_addendum
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
            # Return a graceful fallback instead of a hard 503 so the frontend
            # can display something helpful rather than a blank error page.
            fallback_summary = (
                "I'm currently unable to reach the legal AI service. "
                "Please try again in a moment, or consult a qualified legal professional "
                "for urgent matters."
            )
            return QueryResponse(
                request_id=request_id,
                summary=fallback_summary,
                laws=[],
                suggestions=["Please try your question again shortly."],
                impact_score=ImpactScoreModel(
                    overall_score=0,
                    financial_risk_score=0,
                    legal_exposure_score=0,
                    long_term_impact_score=0,
                    rights_lost_score=0,
                    risk_level="Unavailable",
                    breakdown={},
                    key_factors=[],
                    mitigating_factors=[],
                    recommendation="Consult a qualified legal professional for urgent matters.",
                ),
                language=language,
                suggested_mode=mode_rec.primary_mode if mode_rec else "chat",
                mode_confidence=mode_rec.confidence if mode_rec else 0.0,
                mode_reasoning="",
                extracted_action=None,
                response_type="error_fallback",
                conversation_id=None,
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

        # Mark prediction-type queries so the frontend shows the Run Prediction bridge
        if mode_rec.primary_mode == "predict" and mode_rec.confidence >= 0.80:
            parsed["response_type"] = "prediction_prompt"

        # Conversation persistence is handled by the frontend via POST /conversations
        # and POST /conversations/{id}/messages. The /query endpoint does not create
        # conversations itself to avoid duplicates.
        parsed["conversation_id"] = None

        # Attach bail likelihood when a bail prediction was run
        if bail_likelihood:
            parsed["bail_likelihood"] = bail_likelihood

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

    # ── Smart mode detection ─────────────────────────────────────────────────
    mode_rec = None
    try:
        mode_result = smart_router.route_query(req.query, language=language, session_id=None)
        mode_rec = mode_result.mode_recommendation
        logger.info(
            f"[{request_id}] Stream mode: {mode_rec.primary_mode} "
            f"({mode_rec.confidence:.0%} confidence)"
        )
    except Exception as mode_err:
        logger.warning(f"[{request_id}] Stream mode detection failed: {mode_err}")

    # ── Parallel: classify intent + RAG retrieval (+ bail model when relevant) ──
    _stream_is_bail = _is_bail_query(req.query)
    _stream_bail_likelihood = None
    with _cf.ThreadPoolExecutor(max_workers=3 if _stream_is_bail else 2) as _pool:
        _clf_fut  = _pool.submit(classify_query_intent, req.query)
        _rag_fut  = _pool.submit(_run_rag, req.query)
        _bail_fut = _pool.submit(_run_bail_prediction, req.query) if _stream_is_bail else None
        try:
            query_intent = _clf_fut.result(timeout=8)
        except Exception:
            query_intent = "legal"
        try:
            precedents: list = _rag_fut.result(timeout=8)
        except Exception:
            precedents = []
        if _bail_fut is not None:
            try:
                _br = _bail_fut.result(timeout=10)
                if _br:
                    _stream_bail_likelihood = _br
            except Exception:
                pass
    if query_intent != "legal":
        precedents = []

    logger.info(
        f"[{request_id}] Stream intent: {query_intent}, RAG hits: {len(precedents)}, "
        f"lang={language}"
    )

    # ── Build legal system prompt (RAG-augmented) ────────────────────────────
    req_state = (req.state or "").strip()
    legal_system_prompt = _build_rag_system_prompt(language, precedents, state=req_state)

    # Court precedents attached in the done event (legal queries only)
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

    # ── Conversation history ─────────────────────────────────────────────────
    history = (
        [{"role": m.role, "content": m.content} for m in req.conversation_history]
        if req.conversation_history else None
    )

    def event_stream():
        full_text = ""
        stream_start = time.time()
        timed_out = False

        # Route to appropriate system prompt
        active_prompt = CASUAL_SYSTEM_PROMPT if query_intent == "casual" else legal_system_prompt
        active_history = None if query_intent == "casual" else history

        try:
            for chunk in get_legal_response_stream(
                req.query,
                language=language,
                system_prompt=active_prompt,
                conversation_history=active_history,
            ):
                if time.time() - stream_start > _STREAM_TIMEOUT_SECONDS:
                    logger.error(
                        f"[{request_id}] Stream timeout after {_STREAM_TIMEOUT_SECONDS}s — aborting"
                    )
                    timed_out = True
                    break
                full_text += chunk
                yield f"data: {_json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        except Exception as stream_err:
            logger.error(f"[{request_id}] Streaming generation error: {stream_err}")
            fallback = (
                "I'm having trouble generating a response right now. "
                "Please try again, or rephrase your question."
            )
            yield f"data: {_json.dumps({'type': 'chunk', 'content': fallback})}\n\n"
            yield f"data: {_json.dumps({'type': 'done', 'summary': fallback, 'laws': [], 'suggestions': ['Please try again shortly.'], 'follow_up_questions': [], 'risk_level': '', 'similar_cases': [], 'request_id': request_id, 'language': language})}\n\n"
            return

        if timed_out:
            timeout_msg = (
                "The response is taking longer than expected. "
                "Please try again with a shorter or more specific question."
            )
            yield f"data: {_json.dumps({'type': 'chunk', 'content': timeout_msg})}\n\n"
            yield f"data: {_json.dumps({'type': 'done', 'summary': timeout_msg, 'laws': [], 'suggestions': ['Try rephrasing with more specific details.'], 'follow_up_questions': [], 'risk_level': '', 'similar_cases': [], 'request_id': request_id, 'language': language})}\n\n"
            return

        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] Stream completed in {elapsed:.2f}s ({len(full_text)} chars)")

        if query_intent == "casual":
            # Casual responses are plain text — skip JSON parsing
            done_payload = {
                "type":                "done",
                "summary":             full_text.strip(),
                "laws":                [],
                "suggestions":         [],
                "follow_up_questions": [],
                "risk_level":          "",
                "similar_cases":       [],
                "request_id":          request_id,
                "language":            language,
                "response_type":       "casual",
            }
        else:
            # Legal response: parse structured fields from accumulated text
            try:
                parsed = parse_streaming_output(full_text)
            except Exception:
                parsed = {"summary": full_text.strip(), "laws": [], "suggestions": []}

            is_predict = (
                mode_rec is not None
                and mode_rec.primary_mode == "predict"
                and mode_rec.confidence >= 0.80
            )
            done_payload = {
                "type":                "done",
                "summary":             parsed.get("summary", ""),
                "laws":                parsed.get("laws", []),
                "suggestions":         parsed.get("suggestions", []),
                "follow_up_questions": parsed.get("follow_up_questions", []),
                "risk_level":          parsed.get("risk_level", ""),
                "similar_cases":       similar_cases,
                "request_id":          request_id,
                "language":            language,
                "response_type":       "prediction_prompt" if is_predict else None,
                "bail_likelihood":     _stream_bail_likelihood,
            }

        yield f"data: {_json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
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
