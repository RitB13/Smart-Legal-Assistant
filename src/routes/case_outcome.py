from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks
from src.models.case_model import (
    CaseInputModel,
    CaseOutcomePredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionConfidence,
    SHAPExplanation,
    SimilarCase,
    VerdictProbabilities,
    HealthCheckResponse
)
from src.services.case_outcome_predictor_service import get_predictor_service
from src.services.precedent_service import get_precedent_service
from src.services.model_manager import get_model_manager
from src.services.monitoring_service import get_prediction_monitor
from src.services.audit_trail_service import AuditTrailService
import json as _json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/case-outcome", tags=["Case Outcome Prediction"])


# ============================================================================
# SIMILAR CASES LLM ENRICHMENT
# ============================================================================

def _enrich_similar_cases(raw_results: list) -> list:
    """
    Call Groq once with all similar case summaries to generate a meaningful title
    and a complete 2-3 sentence description for each case.

    Returns a list of {"title": str, "description": str} dicts aligned to raw_results.
    Returns [] on any failure so the calling code falls back gracefully.
    """
    if not raw_results:
        return []
    try:
        from src.services.llm_service import get_legal_response

        case_blocks = ""
        for i, r in enumerate(raw_results):
            summary = (r.get("summary") or "").strip()
            if summary:
                case_blocks += f"\nCase {i + 1}:\n{summary[:800]}\n"

        if not case_blocks.strip():
            return []

        prompt = (
            "You are a legal analyst reviewing Indian court case excerpts.\n"
            "For each excerpt below, provide four fields:\n"
            "1. TITLE: A concise headline (5–10 words) naming the legal dispute "
            "(e.g. 'SARFAESI Bank Recovery — NPA Challenge', "
            "'Tenant Eviction — Arrears and Unauthorised Subletting').\n"
            "2. DESCRIPTION: Exactly 2–3 complete sentences in plain English "
            "explaining what the case is about. Every sentence must end with a full stop. "
            "Do NOT use '...' or leave sentences incomplete. "
            "If the excerpt ends mid-sentence, infer a logical conclusion from context.\n"
            "3. LAWS_CITED: A JSON array of strings listing every Act, Code, Section, or Rule "
            "explicitly mentioned or clearly applicable to this case "
            "(e.g. [\"SARFAESI Act 2002\", \"Companies Act 1956\", \"Code of Civil Procedure\"]). "
            "Return an empty array [] if none are identifiable.\n"
            "4. DECISION: One complete sentence stating what the court decided or ordered, "
            "or what relief was granted/refused. "
            "If the excerpt does not reveal the final outcome, write what stage the case was at.\n\n"
            "Rules:\n"
            "- Title must be specific to this case, not a generic label.\n"
            "- Do not put judge names or citation numbers in the title.\n"
            "- Respond with ONLY valid JSON — no markdown fences, no extra text.\n\n"
            f"{case_blocks}\n"
            "Return a JSON array with one object per case in the same order:\n"
            '[\n'
            '  {"title": "...", "description": "...", "laws_cited": [...], "decision": "..."},\n'
            '  {"title": "...", "description": "...", "laws_cited": [...], "decision": "..."}\n'
            ']'
        )

        raw_response = get_legal_response(
            prompt,
            language="en",
            max_tokens=1200,
            temperature=0.15,
            timeout=60,
            system_prompt=(
                "You are a legal analyst. Respond ONLY with a valid JSON array exactly "
                "matching the structure the user specifies. "
                "No extra text, no markdown fences, no prose outside the JSON array."
            ),
        )
        cleaned = raw_response.strip()

        # Strip markdown fences if the model wrapped the output
        if "```" in cleaned:
            for block in cleaned.split("```"):
                b = block.strip()
                if b.startswith("json"):
                    b = b[4:].strip()
                if b.startswith("["):
                    cleaned = b
                    break

        # Try direct parse
        try:
            result = _json.loads(cleaned)
            if isinstance(result, list):
                return result
        except _json.JSONDecodeError:
            pass

        # Fallback: find array bounds and parse substring
        try:
            start = cleaned.index("[")
            end = cleaned.rindex("]") + 1
            result = _json.loads(cleaned[start:end])
            if isinstance(result, list):
                return result
        except Exception:
            pass

        logger.warning("[Precedent] LLM enrichment: could not parse JSON from response")
        return []

    except Exception as e:
        logger.warning("[Precedent] LLM title enrichment failed: %s", e)
        return []


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=200,
    summary="Health Check",
    description="Check if the case outcome prediction service is healthy and ready"
)
def health_check():
    """
    Health check endpoint for case outcome prediction service.
    
    Verifies:
    - Service is running
    - Model is loaded
    - All components are available
    
    Returns:
        HealthCheckResponse with service status
    """
    try:
        # Get predictor service to check if model is loaded
        service = get_predictor_service()
        
        return HealthCheckResponse(
            status="healthy",
            model_loaded=True,
            model_version="RandomForest v1.0",
            features_available=5,
            last_update="2026-03-15",
            message="Case outcome prediction service is operational with model in memory"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Case outcome prediction service is not available"
        )


# ============================================================================
# SINGLE PREDICTION ENDPOINT
# ============================================================================

@router.post(
    "/predict",
    response_model=CaseOutcomePredictionResponse,
    status_code=200,
    summary="Predict Case Outcome",
    description="Predict the likely outcome of a legal case with detailed explanation"
)
async def predict_case_outcome(
    case_input: CaseInputModel,
    request: Request,
    include_explanation: bool = True,
    include_similar_cases: bool = False
) -> Dict[str, Any]:
    """
    Predict the outcome of a legal case.
    
    This endpoint:
    1. Validates case input
    2. Preprocesses case data into features
    3. Generates prediction using trained LightGBM model
    4. Computes confidence and probabilities
    5. Optionally generates SHAP explanation
    6. Returns comprehensive prediction result
    
    Args:
        case_input: CaseInputModel with case details
        request: HTTP request object
        include_explanation: Whether to include SHAP explanation (slower but more detailed)
        include_similar_cases: Whether to find similar historical cases (requires database)
    
    Returns:
        CaseOutcomePredictionResponse with prediction, confidence, and explanation
    
    Example Request:
        ```json
        {
            "case_name": "State v. John Doe - Criminal Appeal",
            "case_type": "appeal",
            "year": 2023,
            "jurisdiction_state": "Delhi",
            "damages_awarded": 500000,
            "parties_count": 2,
            "is_appeal": true
        }
        ```
    
    Example Response:
        ```json
        {
            "prediction_id": "pred_abc123",
            "case_summary": {"case_name": "State v. John Doe...", ...},
            "verdict": "Accepted",
            "verdict_id": 0,
            "probability": 0.87,
            "confidence": {
                "level": "high",
                "score": 0.87,
                "interpretation": "Model is quite confident..."
            },
            "verdict_probabilities": {
                "accepted": 0.87,
                "acquitted": 0.02,
                ...
            },
            "explanation": {...SHAP analysis...},
            "similar_cases": [...],
            "risk_assessment": {...},
            "recommendations": [...],
            "timestamp": "2026-03-15T..."
        }
        ```
    
    Raises:
        HTTPException 400: Invalid input data
        HTTPException 500: Prediction service error
    """
    prediction_id = f"pred_{str(uuid.uuid4())[:12]}"
    request_time = datetime.utcnow()
    start_time = time.time()
    
    # PHASE 9: Initialize audit trail for prediction
    audit_service = AuditTrailService()
    audit_service.start_audit_trail(prediction_id, case_input.case_name)
    
    # PHASE 9: Get model manager and monitoring
    model_manager = get_model_manager()
    prediction_monitor = get_prediction_monitor()
    
    try:
        logger.info(f"[{prediction_id}] Prediction request: {case_input.case_name}")
        
        # Get predictor service
        try:
            service = get_predictor_service()
        except Exception as e:
            logger.error(f"[{prediction_id}] Failed to initialize predictor service: {e}")
            model_manager.record_prediction(time.time() - start_time, success=False, error_msg="Service init failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Prediction service temporarily unavailable"
            )
        
        # Convert to dictionary for service
        case_dict = {
            'case_name': case_input.case_name,
            'case_type': case_input.case_type,
            'year': case_input.year,
            'jurisdiction_state': case_input.jurisdiction_state,
            'damages_awarded': case_input.damages_awarded or 0,
            'parties_count': case_input.parties_count or 2,
            'is_appeal': case_input.is_appeal or False,
            'legal_representation': case_input.legal_representation,
            'number_of_parties': case_input.number_of_parties,
            'description': case_input.description or '',
            'role': case_input.role or 'petitioner',
            'relief_sought': case_input.relief_sought or '',
        }

        # Petition text composition — when role + relief_sought are provided (from the
        # guided predictor UI) we convert the user's plain-language statement into
        # formal Indian legal petition language before feeding to InLegalBERT.
        # This bridges the gap between informal user text and the court-document
        # register the model was trained on, improving prediction accuracy significantly.
        if case_input.role and case_input.relief_sought and case_dict['description']:
            try:
                composed_text = service.compose_petition_text(
                    statement=case_dict['description'],
                    relief_sought=case_dict['relief_sought'],
                    role=case_dict['role'],
                    jurisdiction=case_dict['jurisdiction_state'],
                    case_type=case_dict['case_type'],
                )
                case_dict['description'] = composed_text
                logger.info(
                    "[%s] Petition text composed (%d chars) — using for InLegalBERT",
                    prediction_id, len(composed_text)
                )
            except Exception as e:
                logger.warning("[%s] Petition composition skipped: %s", prediction_id, e)

        # Get prediction
        prediction_result = service.predict_outcome(case_dict)
        
        # LLM enrichment — runs in parallel with explanation logic
        llm_enrichment = None
        try:
            llm_enrichment = service.enrich_with_llm(prediction_result, case_dict)
            logger.info(f"[{prediction_id}] LLM enrichment complete")
        except Exception as e:
            logger.warning(f"[{prediction_id}] LLM enrichment skipped: {e}")

        # Get explanation if requested
        explanation_data = None
        if include_explanation:
            explanation_result = service.explain_prediction(case_dict)
            explanation_data = SHAPExplanation(
                top_positive_features=explanation_result.get('top_positive_features', []),
                top_negative_features=explanation_result.get('top_negative_features', []),
                feature_impact_summary=explanation_result.get('summary', ''),
                model_certainty=explanation_result.get('model_certainty', prediction_result.get('confidence', 50) / 100.0)
            )
        else:
            explanation_data = SHAPExplanation(
                top_positive_features=[],
                top_negative_features=[],
                feature_impact_summary="Explanation not requested",
                model_certainty=prediction_result.get('confidence', 50) / 100.0
            )
        
        # Build confidence assessment
        confidence_pct = prediction_result.get('confidence', 50)
        prob = confidence_pct / 100.0  # Convert percentage to decimal
        
        if prob > 0.85:
            confidence_level = "very_high"
            interpretation = "Model is very confident about this prediction"
        elif prob > 0.70:
            confidence_level = "high"
            interpretation = "Model is quite confident about this prediction"
        elif prob > 0.55:
            confidence_level = "medium"
            interpretation = "Prediction is somewhat uncertain - multiple outcomes possible"
        else:
            confidence_level = "low"
            interpretation = "Prediction is uncertain - this outcome is not favored"
        
        confidence = PredictionConfidence(
            level=confidence_level,
            score=prob,
            interpretation=interpretation
        )
        
        # Build verdict probabilities
        probs = prediction_result.get('probabilities', {
            'Accepted': 0.0,
            'Acquitted': 0.0,
            'Convicted': 0.0,
            'Other': 0.0,
            'Rejected': 1.0,
            'Settlement': 0.0,
            'Unknown': 0.0
        })
        
        # Convert to percentages (0-1)
        verdict_probabilities = VerdictProbabilities(
            accepted=probs.get('Accepted', 0.0) / 100.0,
            acquitted=probs.get('Acquitted', 0.0) / 100.0,
            convicted=probs.get('Convicted', 0.0) / 100.0,
            other=probs.get('Other', 0.0) / 100.0,
            rejected=probs.get('Rejected', 0.0) / 100.0,
            settlement=probs.get('Settlement', 0.0) / 100.0,
            unknown=probs.get('Unknown', 0.0) / 100.0
        )
        
        # Risk assessment - use service's calculated risk level (not just confidence-based)
        verdict_name = prediction_result.get('predicted_verdict', 'Unknown')
        risk_level = prediction_result.get('risk_level', 'medium')  # Get from service calculation
        risk_assessment = {
            'overall_risk': risk_level,
            'key_risks': _get_risk_factors(verdict_name, case_dict),
            'success_probability': prob
        }
        
        # Recommendations — use LLM-generated ones if available, else static fallback
        recommendations = (
            llm_enrichment.get('recommendations', [])
            if llm_enrichment
            else _get_recommendations(verdict_name, case_dict)
        )

        # Similar precedent cases — TF-IDF/SVD semantic search over 82k Indian judgments.
        # Gracefully returns [] if the precedent index has not been built yet.
        similar_cases_raw: List[SimilarCase] = []
        try:
            query_text = case_dict.get('description') or case_dict.get('case_name', '')

            # Primary: dense (MiniLM semantic) retrieval — better at matching
            # layperson descriptions to formal court-document language.
            raw_results: list = []
            try:
                from src.services.dense_retrieval_service import get_dense_retrieval_service
                dense_svc = get_dense_retrieval_service()
                if dense_svc.available:
                    raw_results = dense_svc.search(query=query_text, top_k=3)
                    if raw_results:
                        logger.info(
                            "[%s] Similar cases via dense retrieval (%d results)",
                            prediction_id, len(raw_results),
                        )
            except Exception as _dense_err:
                logger.warning(
                    "[%s] Dense similar-cases skipped, trying TF-IDF fallback: %s",
                    prediction_id, _dense_err,
                )

            # Fallback: TF-IDF + SVD precedent index
            if not raw_results:
                precedent_svc = get_precedent_service()
                raw_results = precedent_svc.search(
                    query=query_text,
                    case_type_filter=case_dict.get('case_type'),
                    top_k=3,
                )
                if raw_results:
                    logger.info(
                        "[%s] Similar cases via TF-IDF fallback (%d results)",
                        prediction_id, len(raw_results),
                    )

            # Generate meaningful titles and complete descriptions via Groq (single call for all 3)
            llm_enrichments = _enrich_similar_cases(raw_results)

            for i, r in enumerate(raw_results):
                outcome_raw = r.get('outcome', '')
                # Normalise to Accepted / Rejected.
                # Corpus may store labels as int (1/0) or string ("1"/"0"/"accepted"/"rejected")
                outcome_str = str(outcome_raw).strip().lower()
                if 'accept' in outcome_str or outcome_str == '1':
                    verdict_label = 'Accepted'
                elif 'reject' in outcome_str or outcome_str == '0':
                    verdict_label = 'Rejected'
                else:
                    verdict_label = 'Unknown'

                enrichment = llm_enrichments[i] if i < len(llm_enrichments) else {}
                laws_raw = enrichment.get('laws_cited')
                similar_cases_raw.append(SimilarCase(
                    case_id=f"prec_{i+1}",
                    case_name=r.get('case_name', ''),
                    case_type=r.get('case_type', case_dict.get('case_type', 'Unknown')),
                    year=2020,
                    verdict=verdict_label,
                    similarity_score=float(r.get('similarity', 0.0)),
                    jurisdiction=case_dict.get('jurisdiction_state', 'India'),
                    summary=r.get('summary') or None,
                    llm_title=enrichment.get('title') or None,
                    llm_description=enrichment.get('description') or None,
                    llm_laws_cited=laws_raw if isinstance(laws_raw, list) and laws_raw else None,
                    llm_decision=enrichment.get('decision') or None,
                ))
        except Exception as e:
            logger.warning("[%s] Precedent search skipped: %s", prediction_id, e)

        # Build response
        response = CaseOutcomePredictionResponse(
            prediction_id=prediction_id,
            case_summary={
                'case_name': case_input.case_name,
                'case_type': case_input.case_type,
                'year': case_input.year,
                'jurisdiction_state': case_input.jurisdiction_state,
                'damages_awarded': case_input.damages_awarded,
                'parties_count': case_input.parties_count,
                'is_appeal': case_input.is_appeal
            },
            verdict=verdict_name,
            verdict_id=prediction_result.get('verdict_id', 0),
            probability=prob,
            confidence=confidence,
            risk_level=risk_assessment.get('overall_risk', 'medium'),
            verdict_probabilities=verdict_probabilities,
            explanation=explanation_data,
            similar_cases=similar_cases_raw,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
            llm_analysis=llm_enrichment,
            timestamp=request_time
        )
        
        # PHASE 9: Log prediction to audit trail
        elapsed_ms = (time.time() - start_time) * 1000
        audit_service.log_case_prediction(
            request_id=prediction_id,
            case_name=case_input.case_name,
            predicted_verdict=verdict_name,
            confidence=prob,
            model_version=model_manager.get_current_version(),
            prediction_time_ms=elapsed_ms,
            similar_cases_count=len(response.similar_cases),
            input_data=case_dict,
            duration_ms=elapsed_ms
        )
        
        # PHASE 9: Record prediction metrics for monitoring
        prediction_monitor.log_prediction(
            model_version=model_manager.get_current_version(),
            prediction_time_ms=elapsed_ms,
            confidence=prob,
            input_features=case_dict,
            prediction_class=verdict_name
        )
        
        # PHASE 9: Record in model manager for performance tracking
        model_manager.record_prediction(elapsed_ms, success=True)
        
        logger.info(f"[{prediction_id}] [OK] Prediction successful: {verdict_name} (confidence: {prob:.2%})")
        logger.info(f"[{prediction_id}] Model version: {model_manager.get_current_version()} | Time: {elapsed_ms:.1f}ms")
        
        return response
        
    except HTTPException:
        elapsed_ms = (time.time() - start_time) * 1000
        model_manager.record_prediction(elapsed_ms, success=False, error_msg="HTTP exception")
        raise
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(f"[{prediction_id}] ✗ Prediction failed: {e}", exc_info=True)
        
        # PHASE 9: Record error in monitoring
        model_manager.record_prediction(elapsed_ms, success=False, error_msg=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


# ============================================================================
# BATCH PREDICTION ENDPOINT
# ============================================================================

@router.post(
    "/predict-batch",
    response_model=BatchPredictionResponse,
    status_code=202,  # Accepted (async processing)
    summary="Batch Predict Case Outcomes",
    description="Predict outcomes for multiple cases at once"
)
async def batch_predict_outcomes(
    batch_request: BatchPredictionRequest,
    request: Request
) -> Dict[str, Any]:
    """
    Predict outcomes for multiple cases in a single batch.
    
    Advantages:
    - More efficient than calling single prediction endpoint multiple times
    - Can optionally skip explanations for speed
    - Returns results for successful cases + errors for failed cases
    
    Args:
        batch_request: BatchPredictionRequest with list of cases
        request: HTTP request object
    
    Returns:
        BatchPredictionResponse with results for all cases
    
    Example Request:
        ```json
        {
            "cases": [
                {
                    "case_name": "Case 1",
                    "case_type": "appeal",
                    "year": 2023,
                    "jurisdiction_state": "Delhi"
                },
                {
                    "case_name": "Case 2",
                    "case_type": "criminal_complaint",
                    "year": 2024,
                    "jurisdiction_state": "Maharashtra"
                }
            ],
            "include_explanations": false,
            "include_similar_cases": false
        }
        ```
    
    Raises:
        HTTPException 400: Invalid input or too many cases
        HTTPException 500: Batch processing error
    """
    batch_id = f"batch_{str(uuid.uuid4())[:12]}"
    batch_start_time = time.time()
    
    # PHASE 9: Get monitoring service
    prediction_monitor = get_prediction_monitor()
    model_manager = get_model_manager()
    
    try:
        # Validate batch size
        if len(batch_request.cases) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 cases per batch allowed"
            )
        
        logger.info(f"[{batch_id}] Batch prediction requested: {len(batch_request.cases)} cases")
        
        # Get predictor service
        try:
            service = get_predictor_service()
        except Exception as e:
            logger.error(f"[{batch_id}] Service initialization failed: {e}")
            model_manager.record_prediction(
                (time.time() - batch_start_time) * 1000,
                success=False,
                error_msg="Service initialization failed"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Prediction service temporarily unavailable"
            )
        
        # Convert cases to dictionaries
        cases_dicts = [
            {
                'case_name': case.case_name,
                'case_type': case.case_type,
                'year': case.year,
                'jurisdiction_state': case.jurisdiction_state,
                'damages_awarded': case.damages_awarded or 0,
                'parties_count': case.parties_count or 2,
                'is_appeal': case.is_appeal or False,
                'legal_representation': case.legal_representation,
                'number_of_parties': case.number_of_parties,
            }
            for case in batch_request.cases
        ]
        
        # Run batch prediction (batch_start_time already set at top of function)
        batch_result = service.batch_predict(cases_dicts)
        batch_processing_time = time.time() - batch_start_time
        
        # Transform batch_result to expected format
        batch_result_transformed = {
            'total_cases': batch_result['summary']['total'],
            'successful_predictions': batch_result['summary']['successful'],
            'failed_predictions': batch_result['summary']['failed'],
            'predictions': batch_result['predictions'],
            'failures': batch_result['failures'],
            'processing_time_seconds': batch_processing_time
        }
        batch_result = batch_result_transformed
        
        # Add explanations if requested (post-process)
        if batch_request.include_explanations:
            for prediction in batch_result['predictions']:
                try:
                    case_dict = cases_dicts[prediction['case_index']]
                    explanation = service.explain_prediction(case_dict)
                    prediction['explanation'] = explanation
                except Exception as e:
                    logger.warning(f"Could not generate explanation: {e}")
        
        # Add similar cases if requested
        if batch_request.include_similar_cases:
            for prediction in batch_result['predictions']:
                verdict = prediction.get('verdict', 'Unknown')
                similar = _get_similar_cases(verdict, {})
                prediction['similar_cases'] = [s.dict() for s in similar]
        
        # PHASE 9: Log metrics for each successful prediction
        for i, prediction in enumerate(batch_result['predictions']):
            try:
                prediction_monitor.log_prediction(
                    model_version=model_manager.get_current_version(),
                    prediction_time_ms=batch_result.get('processing_time_seconds', 0) * 1000 / max(1, batch_result['successful_predictions']),
                    confidence=prediction.get('probability', 0.5),
                    input_features=cases_dicts[i] if i < len(cases_dicts) else {},
                    prediction_class=prediction.get('verdict', 'Unknown')
                )
            except Exception as e:
                logger.debug(f"Could not log batch prediction metric: {e}")
        
        # PERSISTENCE: Save each successful prediction to MongoDB
        for i, prediction in enumerate(batch_result['predictions']):
            try:
                case_dict = cases_dicts[i] if i < len(cases_dicts) else {}
                AuditTrailService.save_case_prediction(
                    request_id=f"{batch_id}_case_{i}",
                    case_name=case_dict.get('case_name', 'Unknown'),
                    predicted_verdict=prediction.get('verdict', 'Unknown'),
                    confidence=prediction.get('probability', 0.5),
                    verdict_id=prediction.get('verdict_id', 0),
                    risk_level=prediction.get('risk_level', 'medium'),
                    risk_assessment={'overall_risk': prediction.get('risk_level', 'medium'), 'confidence': prediction.get('probability', 0.5)},
                    input_data=case_dict,
                    probabilities=prediction.get('probabilities', {}),
                    model_version=model_manager.get_current_version()
                )
            except Exception as e:
                logger.warning(f"Could not persist batch prediction {i}: {e}")
        
        # Build response
        response = BatchPredictionResponse(
            batch_id=batch_id,
            total_cases=batch_result['total_cases'],
            successful_predictions=batch_result['successful_predictions'],
            failed_predictions=batch_result['failed_predictions'],
            predictions=batch_result['predictions'],
            errors=batch_result['failures'],
            processing_time_seconds=batch_result['processing_time_seconds'],
            timestamp=datetime.utcnow()
        )
        
        # PHASE 9: Record overall batch metrics
        total_elapsed_ms = (time.time() - batch_start_time) * 1000
        model_manager.record_prediction(
            total_elapsed_ms,
            success=batch_result['successful_predictions'] > 0
        )
        
        logger.info(
            f"[{batch_id}] ✓ Batch complete: {batch_result['successful_predictions']}/"
            f"{batch_result['total_cases']} successful"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        elapsed_ms = (time.time() - batch_start_time) * 1000
        logger.error(f"[{batch_id}] ✗ Batch prediction failed: {e}", exc_info=True)
        
        # PHASE 9: Record error in monitoring
        model_manager.record_prediction(elapsed_ms, success=False, error_msg=f"Batch failed: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


# ============================================================================
# EXPLANATION ENDPOINT
# ============================================================================

@router.post(
    "/explain",
    status_code=200,
    summary="Explain Prediction",
    description="Get detailed explanation of why a prediction was made"
)
async def explain_prediction(
    case_input: CaseInputModel,
    request: Request
) -> Dict[str, Any]:
    """
    Get detailed SHAP-based explanation for a case prediction.
    
    Shows:
    - Top features that increased prediction confidence
    - Top features that decreased prediction confidence
    - Summary of feature impacts
    - Model's certainty score
    
    Args:
        case_input: CaseInputModel with case details
        request: HTTP request object
    
    Returns:
        Dictionary with explanation details
    """
    explanation_id = f"exp_{str(uuid.uuid4())[:12]}"
    
    try:
        logger.info(f"[{explanation_id}] Explanation requested for: {case_input.case_name}")
        
        # Get predictor service
        service = get_predictor_service()
        
        # Convert to dictionary
        case_dict = {
            'case_name': case_input.case_name,
            'case_type': case_input.case_type,
            'year': case_input.year,
            'jurisdiction_state': case_input.jurisdiction_state,
            'damages_awarded': case_input.damages_awarded or 0,
            'parties_count': case_input.parties_count or 2,
            'is_appeal': case_input.is_appeal or False,
        }
        
        # Get explanation
        explanation = service.explain_prediction(case_dict, num_top_features=10)

        
        response = {
            'explanation_id': explanation_id,
            'case_name': case_input.case_name,
            'case_type': case_input.case_type,
            'jurisdiction': case_input.jurisdiction_state,
            'explanation': {
                'method': explanation.get('method'),
                'top_positive_features': explanation.get('top_positive_features', []),
                'top_negative_features': explanation.get('top_negative_features', []),
                'summary': explanation.get('summary'),
                'feature_count_analyzed': len(explanation.get('top_positive_features', [])) + len(explanation.get('top_negative_features', []))
            },
            'model_certainty': explanation.get('model_certainty'),
            'interpretation': {
                'primary_driver': explanation.get('top_positive_features', [{}])[0].get('feature', 'N/A') if explanation.get('top_positive_features') else 'N/A',
                'confidence_assessment': 'Shows model reasoning using SHAP values' if explanation.get('method') == 'SHAP' else 'Shows model feature importance',
                'details': f"Model analyzed {len(explanation.get('top_positive_features', []))} key features that influenced the prediction."
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"[{explanation_id}] ✓ Explanation generated using {explanation.get('method')}")
        return response
        
    except Exception as e:
        logger.error(f"[{explanation_id}] ✗ Explanation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation generation failed: {str(e)}"
        )


# ============================================================================
# MODEL INFO ENDPOINT
# ============================================================================

@router.get(
    "/model-info",
    status_code=200,
    summary="Get Model Information",
    description="Get details about the prediction model"
)
async def get_model_info(request: Request) -> Dict[str, Any]:
    """
    Get information about the loaded prediction model.
    
    Returns:
        Dictionary with model details including:
        - Model type and version
        - Number of features
        - Available verdict classes
        - Metadata about training
    """
    try:
        service = get_predictor_service()
        info = service.get_model_info()
        
        return {
            'model_type':      info['model_type'],
            'model_loaded':    info['model_loaded'],
            'feature_count':   info['feature_count'],
            'sample_features': info.get('feature_names', []),
            'verdict_classes': info['verdict_classes'],
            'shap_available':  info.get('shap_available', False),
            'metadata':        info.get('metadata', {}),
            'timestamp':       datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve model information"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_risk_factors(verdict: str, case_dict: Dict[str, Any]) -> List[str]:
    """
    Get risk factors based on predicted verdict and case characteristics.
    
    Args:
        verdict: Predicted verdict
        case_dict: Case information
    
    Returns:
        List of risk factor strings
    """
    risks = []
    
    verdict_risks = {
        'Rejected': ["Case dismissed based on case characteristics", "May need to appeal"],
        'Convicted': ["Criminal conviction likely", "Consider stronger defense strategy"],
        'Other': ["Unclear outcome - more information needed"],
        'Settlement': ["Parties may be inclined to settle"],
        'Accepted': ["Favorable outcome expected", "Proceed with confidence"],
        'Acquitted': ["Strong defense indicated", "Acquittal likely"],
        'Unknown': ["Insufficient information to assess risk"]
    }
    
    risks.extend(verdict_risks.get(verdict, []))
    
    if case_dict.get('damages_awarded', 0) > 1000000:
        risks.append("High damages amount involved")
    
    if case_dict.get('is_appeal'):
        risks.append("This is an appeal - higher legal standards may apply")
    
    return risks


def _get_recommendations(verdict: str, case_dict: Dict[str, Any]) -> List[str]:
    """
    Get recommendations based on predicted verdict.
    
    Args:
        verdict: Predicted verdict
        case_dict: Case information
    
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    verdict_recommendations = {
        'Rejected': [
            "Review case grounds before filing",
            "Consider alternative dispute resolution",
            "Consult with expert legal counsel"
        ],
        'Convicted': [
            "Prepare strong defense evidence",
            "Consider technical objections",
            "Plan for appeal if necessary"
        ],
        'Accepted': [
            "File within statutory timeline",
            "Gather supporting documentation"
        ],
        'Settlement': [
            "Evaluate settlement terms carefully",
            "Document all agreements"
        ],
        'Acquitted': [
            "Strengthen evidence of innocence",
            "Prepare character witnesses"
        ]
    }
    
    recommendations.extend(
        verdict_recommendations.get(verdict, ["Consult with legal professional"])
    )
    
    return recommendations


def _get_similar_cases(verdict: str, case_dict: Dict[str, Any]) -> List[SimilarCase]:
    """
    Retrieve similar historical cases using the TF-IDF precedent search index.
    Falls back to an empty list on any failure so the prediction response is
    never blocked by a retrieval error.
    """
    try:
        query_parts = [
            case_dict.get("case_name", ""),
            case_dict.get("case_type", ""),
            case_dict.get("jurisdiction_state", ""),
        ]
        query = " ".join(p for p in query_parts if p).strip()
        if not query:
            return []

        precedent_svc = get_precedent_service()
        raw_results = precedent_svc.search(query, top_k=3)

        similar: List[SimilarCase] = []
        for i, r in enumerate(raw_results):
            similar.append(SimilarCase(
                case_id=r.get("case_id", f"case_{i}"),
                case_name=r.get("case_name", r.get("title", "Unknown Case")),
                case_type=case_dict.get("case_type", "general"),
                year=r.get("year", 0),
                verdict=r.get("verdict", verdict),
                similarity_score=round(float(r.get("score", 0.75)), 4),
                jurisdiction=r.get("jurisdiction", case_dict.get("jurisdiction_state", "")),
            ))
        return similar

    except Exception as e:
        logger.warning(f"[SIMILAR_CASES] Retrieval failed, returning empty list: {e}")
        return []


# ============================================================================
# MONITORING & DEPLOYMENT ENDPOINTS (PHASE 9)
# ============================================================================

@router.get(
    "/monitoring/performance",
    status_code=200,
    summary="Performance Metrics",
    description="Get current model performance metrics and prediction statistics"
)
def get_performance_metrics():
    """
    Get comprehensive performance metrics for monitoring.
    
    Returns performance data including:
    - Total predictions made
    - Average confidence
    - Prediction accuracy (if feedback available)
    - Average inference time
    - Predictions by class
    
    Returns:
        Dict with performance metrics
    """
    try:
        monitor = get_prediction_monitor()
        return {
            "status": "ok",
            "data": monitor.get_performance_summary()
        }
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@router.get(
    "/monitoring/drift",
    status_code=200,
    summary="Data Drift Report",
    description="Check for data drift in recent predictions"
)
def check_data_drift():
    """
    Check for data drift in the prediction input features.
    
    Analyzes recent predictions to detect changes in:
    - Feature distributions
    - Model input patterns
    - Potential concept drift
    
    Returns:
        Dict with drift detection results and recommendations
    """
    try:
        monitor = get_prediction_monitor()
        return {
            "status": "ok",
            "data": monitor.get_drift_report()
        }
    except Exception as e:
        logger.error(f"Error checking data drift: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check data drift"
        )


@router.get(
    "/monitoring/dashboard",
    status_code=200,
    summary="Monitoring Dashboard",
    description="Get comprehensive monitoring dashboard with all metrics"
)
def get_monitoring_dashboard():
    """
    Get comprehensive monitoring dashboard data.
    
    Combines:
    - Performance metrics
    - Data drift analysis
    - Recent predictions
    - Model version info
    
    Returns:
        Dict with complete monitoring dashboard data
    """
    try:
        monitor = get_prediction_monitor()
        model_manager = get_model_manager()
        
        dashboard = monitor.get_monitoring_dashboard()
        dashboard["model_info"] = model_manager.get_model_info()
        dashboard["timestamp"] = datetime.utcnow().isoformat()
        
        return {
            "status": "ok",
            "data": dashboard
        }
    except Exception as e:
        logger.error(f"Error retrieving monitoring dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitoring dashboard"
        )


@router.get(
    "/deployment-info",
    status_code=200,
    summary="Deployment Information",
    description="Get current model version and deployment information from model manager"
)
def get_model_information():
    """
    Get detailed model version and deployment information.
    
    Returns:
    - Current active model version
    - Available model versions
    - Fallback model version
    - Model metadata
    - Performance metrics
    
    Returns:
        Dict with model information
    """
    try:
        model_manager = get_model_manager()
        return {
            "status": "ok",
            "data": model_manager.get_model_info()
        }
    except Exception as e:
        logger.error(f"Error retrieving model information: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model information"
        )


@router.post(
    "/feedback/{prediction_id}",
    status_code=200,
    summary="Log Prediction Feedback",
    description="Log user feedback on a specific prediction"
)
def log_prediction_feedback(
    prediction_id: str,
    feedback: str
):
    """
    Log user feedback on a prediction for continuous improvement.
    
    Enables:
    - Tracking correct vs incorrect predictions
    - Identifying systematic errors
    - Training data for model retraining
    
    Args:
        prediction_id: ID of the prediction
        feedback: User feedback (e.g., "correct", "incorrect", "helpful")
    
    Returns:
        Dict with feedback confirmation
    """
    try:
        monitor = get_prediction_monitor()
        audit_service = AuditTrailService()
        
        # Log feedback in monitoring
        monitor.log_user_feedback(0, feedback)  # Index 0 for most recent
        
        # Log feedback in audit trail
        audit_service.log_event(
            request_id=prediction_id,
            event_type="user_feedback",
            description=f"User feedback: {feedback}",
            details={"feedback": feedback},
            component="monitoring",
            status="success"
        )
        
        return {
            "status": "ok",
            "message": "Feedback recorded successfully",
            "prediction_id": prediction_id,
            "feedback": feedback
        }
    except Exception as e:
        logger.error(f"Error logging feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log feedback"
        )
