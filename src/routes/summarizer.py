from fastapi import APIRouter, HTTPException, UploadFile, File, status, Request
from src.services.document_processor import DocumentProcessor
from src.services.llm_service import get_legal_response_with_jurisdiction
from src.services.parser import parse_llm_output
from src.services.language_service import detect_language, get_language_name
from src.services.feature_extractor import LegalFeatureExtractor
from src.services.legal_impact_scorer import LegalImpactScorer
from src.services.jurisdiction_detector import get_jurisdiction_detector
from src.services.law_matcher import get_law_matcher
from src.services.checklist_generator import get_checklist_generator
from src.services.template_generator import get_template_generator
from src.services.explainability_service import get_explainability_service
from src.services.audit_trail_service import get_audit_trail_service
from src.models.query_model import (
    QueryResponse, ImpactScoreModel, JurisdictionInfo, LegalReference, 
    Checklist, ChecklistItem, DocumentTemplate, ScoreExplanation, 
    LawMatchingExplanation, JurisdictionExplanation, ChecklistPriorityExplanation, 
    AuditEvent, AuditTrailSummary
)
import logging
import uuid
import time
import tempfile
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
document_processor = DocumentProcessor()
feature_extractor = LegalFeatureExtractor()
impact_scorer = LegalImpactScorer()


@router.post("/document/analyze")
async def analyze_document(file: UploadFile = File(...), request: Request = None):
    """
    Upload and analyze a legal document with complete Phase 1, 2, 3 features.
    Extracts text, generates summary, score, checklists, templates, and explanations.
    
    Args:
        file: Uploaded document file (PDF, DOCX, image, etc.)
        request: HTTP request object
        
    Returns:
        QueryResponse with complete analysis including jurisdiction, laws, checklists, templates, and explanations
        
    Raises:
        HTTPException: For various error conditions
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    temp_file_path = None
    
    # Initialize additional services for Phase 1, 2, 3
    jurisdiction_detector = get_jurisdiction_detector()
    law_matcher = get_law_matcher()
    checklist_generator = get_checklist_generator()
    template_generator = get_template_generator()
    explainability_service = get_explainability_service()
    audit_trail_service = get_audit_trail_service()
    
    try:
        logger.info(f"[{request_id}] Document upload received: {file.filename}")
        
        # Start audit trail
        audit_trail_service.start_audit_trail(request_id, f"Document: {file.filename}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File name is required"
            )
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"{request_id}_{file.filename}")
        
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"[{request_id}] File saved temporarily: {temp_file_path}")
        
        # Extract text from document
        logger.debug(f"[{request_id}] Processing document: {file.filename}...")
        extracted_text = document_processor.process_file(temp_file_path)
        
        if not extracted_text or len(extracted_text.strip()) == 0:
            raise ValueError("No text could be extracted from the document")
        
        logger.info(f"[{request_id}] Extracted {len(extracted_text)} characters")
        
        # Limit extracted text to reasonable length
        if len(extracted_text) > 5000:
            extracted_text = extracted_text[:5000]
            logger.info(f"[{request_id}] Truncated extracted text to 5000 characters")
        
        # STEP 1: Detect language
        logger.debug(f"[{request_id}] Detecting language...")
        language = detect_language(extracted_text)
        logger.info(f"[{request_id}] Language detected: {language} ({get_language_name(language)})")
        
        # STEP 2: Detect jurisdiction
        logger.debug(f"[{request_id}] Detecting jurisdiction...")
        try:
            client_ip = request.client.host if request and request.client else None
        except:
            client_ip = None
        
        jurisdiction_dict = jurisdiction_detector.detect_jurisdiction(
            ip_address=client_ip,
            browser_language=None,
            explicit_jurisdiction=None
        )
        
        country = jurisdiction_dict.get("country", "India")
        state = jurisdiction_dict.get("state_or_region", "National")
        detected_method = jurisdiction_dict.get("detected_method", "default")
        confidence = jurisdiction_dict.get("confidence", 0.5)
        
        logger.info(f"[{request_id}] Jurisdiction detected: {country}/{state}")
        
        # Phase 3: Log jurisdiction to audit trail
        audit_trail_service.log_jurisdiction_detection(
            request_id=request_id,
            detected_country=country,
            detected_state=state,
            detected_method=detected_method,
            confidence=confidence,
            signals_evaluated={"client_ip": client_ip},
            duration_ms=(time.time() - start_time) * 1000
        )
        
        # STEP 3: Extract features
        logger.debug(f"[{request_id}] Extracting legal features...")
        feature_start = time.time()
        features = feature_extractor.extract_features(
            query=extracted_text[:2000],
            summary="",
            laws=[]
        )
        feature_duration = (time.time() - feature_start) * 1000
        
        true_features = [k for k, v in features.items() if v is True or (isinstance(v, (int, float)) and v > 0)]
        
        # Phase 3: Log feature extraction
        audit_trail_service.log_feature_extraction(
            request_id=request_id,
            extracted_features=features,
            true_feature_count=len(true_features),
            duration_ms=feature_duration
        )
        
        # STEP 4: Match relevant laws
        logger.debug(f"[{request_id}] Matching relevant laws...")
        law_match_start = time.time()
        matched_laws = law_matcher.match_laws(features, country, state)
        law_match_duration = (time.time() - law_match_start) * 1000
        logger.info(f"[{request_id}] Matched {len(matched_laws)} relevant laws")
        
        # Phase 3: Log law matching
        audit_trail_service.log_law_matching(
            request_id=request_id,
            matched_laws=matched_laws,
            total_available_laws=21,
            duration_ms=law_match_duration
        )
        
        # STEP 5: Get LLM response with jurisdiction context
        logger.debug(f"[{request_id}] Calling LLM service with jurisdiction context...")
        raw_output = get_legal_response_with_jurisdiction(
            user_query=extracted_text[:2000],
            language=language,
            country=country,
            state=state,
            relevant_laws=matched_laws
        )
        
        # STEP 6: Parse LLM output
        logger.debug(f"[{request_id}] Parsing LLM response...")
        parsed = parse_llm_output(raw_output)
        
        # STEP 7: Re-extract features with full context
        logger.debug(f"[{request_id}] Re-extracting features with summary...")
        features = feature_extractor.extract_features(
            query=extracted_text[:2000],
            summary=parsed.get("summary", ""),
            laws=parsed.get("laws", [])
        )
        
        # STEP 8: Calculate impact score
        logger.debug(f"[{request_id}] Calculating impact score...")
        score_start = time.time()
        impact_score = impact_scorer.calculate_score(features)
        score_duration = (time.time() - score_start) * 1000
        
        # Phase 3: Log impact score calculation
        audit_trail_service.log_impact_score_calculation(
            request_id=request_id,
            overall_score=impact_score.overall_score,
            financial_risk=impact_score.financial_risk_score,
            legal_exposure=impact_score.legal_exposure_score,
            long_term_impact=impact_score.long_term_impact_score,
            rights_lost=impact_score.rights_lost_score,
            risk_level=impact_score.risk_level,
            features_used=true_features,
            duration_ms=score_duration
        )
        
        # Convert matched laws to LegalReference model
        applicable_laws = [
            LegalReference(
                law_id=law.get("law_id", ""),
                name=law.get("name", ""),
                section=law.get("law_id", "").replace("IPC_", "IPC Section ").replace("USC_", "USC Title "),
                jurisdiction=law.get("jurisdiction", country),
                statute_text=law.get("statute_text", "")[:200] if law.get("statute_text") else None,
                url=law.get("url"),
                relevance="high" if law.get("relevance_score", 0) > 0.7 else "medium" if law.get("relevance_score", 0) > 0.4 else "low",
                relevance_score=law.get("relevance_score", 0)
            )
            for law in matched_laws[:5]
        ]
        
        # Convert impact score to model with explanation and laws
        impact_score_model = ImpactScoreModel(
            overall_score=impact_score.overall_score,
            financial_risk_score=impact_score.financial_risk_score,
            legal_exposure_score=impact_score.legal_exposure_score,
            long_term_impact_score=impact_score.long_term_impact_score,
            rights_lost_score=impact_score.rights_lost_score,
            risk_level=impact_score.risk_level,
            breakdown=impact_score.breakdown,
            key_factors=impact_score.key_factors,
            mitigating_factors=impact_score.mitigating_factors,
            recommendation=impact_score.recommendation,
            calculation_details=impact_score.calculation_details,
            applicable_laws=applicable_laws
        )
        
        # Build jurisdiction info
        jurisdiction_info = JurisdictionInfo(
            country=country,
            state_or_region=state,
            detected_method=detected_method,
            confidence=confidence
        )
        
        # STEP 9: Generate checklist
        logger.debug(f"[{request_id}] Generating checklist...")
        checklist_items = checklist_generator.generate_checklist(features, country, state)
        
        # Convert to ChecklistItem models
        checklist_items_models = [
            ChecklistItem(
                step_number=item.step_number,
                action=item.action,
                details=item.details,
                priority=item.priority,
                timeline=item.timeline,
                reference_law=item.reference_law
            )
            for item in checklist_items
        ]
        
        # Create Checklist model
        checklist_model = Checklist(
            issue_type=checklist_generator._determine_issue_type(features),
            items=checklist_items_models,
            total_items=len(checklist_items_models),
            jurisdiction=country,
            note="Follow these steps in order. Timeline may vary based on case complexity." if checklist_items_models else None
        ) if checklist_items_models else None
        
        logger.info(f"[{request_id}] Generated {len(checklist_items_models)} checklist items")
        
        # STEP 10: Generate document templates
        logger.debug(f"[{request_id}] Generating templates...")
        templates = template_generator.generate_templates(features, country)
        
        # Convert to DocumentTemplate models
        templates_models = [
            DocumentTemplate(
                template_id=template.template_id,
                name=template.name,
                description=template.description,
                file_format=template.file_format,
                jurisdiction=template.jurisdiction,
                applicable_issues=template.applicable_issues,
                category=template.category,
                download_url=f"/api/templates/{template.template_id}"
            )
            for template in templates
        ]
        
        logger.info(f"[{request_id}] Generated {len(templates_models)} templates")
        
        # STEP 11: Generate explainability
        logger.debug(f"[{request_id}] Generating explanations...")
        explain_start = time.time()
        
        # Score explanation
        score_explanation = explainability_service.explain_score_calculation(
            financial_score=impact_score.financial_risk_score,
            legal_exposure_score=impact_score.legal_exposure_score,
            long_term_impact_score=impact_score.long_term_impact_score,
            rights_lost_score=impact_score.rights_lost_score,
            features=features
        )
        score_explanation_model = ScoreExplanation(**score_explanation)
        impact_score_model.score_explanation = score_explanation_model
        
        # Law explanations
        law_explanations_raw = explainability_service.explain_law_matching(
            matched_laws=matched_laws,
            features=features,
            country=country
        )
        law_explanations = [
            LawMatchingExplanation(**explanation)
            for explanation in law_explanations_raw
        ]
        
        # Jurisdiction explanation
        jurisdiction_explanation_raw = explainability_service.explain_jurisdiction_detection(
            detected_country=country,
            detected_state=state,
            detected_method=detected_method,
            confidence=confidence,
            signals={"client_ip": client_ip}
        )
        jurisdiction_explanation = JurisdictionExplanation(**jurisdiction_explanation_raw)
        
        # Checklist explanations
        checklist_explanations_raw = explainability_service.explain_checklist_priorities(
            checklist_items=[item.dict() for item in checklist_items_models]
        )
        checklist_explanations = [
            ChecklistPriorityExplanation(**explanation)
            for explanation in checklist_explanations_raw
        ]
        
        explain_duration = (time.time() - explain_start) * 1000
        
        # Phase 3: Log explainability
        audit_trail_service.log_event(
            request_id=request_id,
            event_type="explainability_generation",
            description="Generated detailed explanations for all decisions",
            details={
                "score_components": len(score_explanation["components"]),
                "law_explanations": len(law_explanations),
                "jurisdiction_explanation": jurisdiction_explanation is not None,
                "checklist_explanations": len(checklist_explanations)
            },
            component="explainability_service",
            duration_ms=explain_duration
        )
        
        # Phase 3: Log other events
        audit_trail_service.log_checklist_generation(
            request_id=request_id,
            issue_type=checklist_model.issue_type if checklist_model else "unknown",
            checklist_items_count=len(checklist_items_models),
            critical_items=sum(1 for item in checklist_items_models if item.priority == "critical"),
            high_items=sum(1 for item in checklist_items_models if item.priority == "high"),
            duration_ms=0
        )
        
        audit_trail_service.log_template_generation(
            request_id=request_id,
            templates_generated=len(templates_models),
            template_categories=[t.category for t in templates_models],
            duration_ms=0
        )
        
        # Add all to response
        parsed["request_id"] = request_id
        parsed["language"] = language
        parsed["impact_score"] = impact_score_model
        parsed["jurisdiction"] = jurisdiction_info
        parsed["applicable_laws"] = applicable_laws
        parsed["checklist"] = checklist_model
        parsed["document_templates"] = templates_models
        parsed["law_explanations"] = law_explanations
        parsed["jurisdiction_explanation"] = jurisdiction_explanation
        parsed["checklist_explanations"] = checklist_explanations
        
        # STEP 12: Finalize audit trail
        total_elapsed = time.time() - start_time
        audit_summary = audit_trail_service.finalize_trail(
            request_id=request_id,
            user_query=f"Document: {file.filename}",
            user_location=f"{country}/{state}",
            language_detected=language,
            jurisdiction_result=f"{country}/{state}",
            final_score=impact_score.overall_score,
            checklist_generated=checklist_model is not None,
            templates_generated=len(templates_models) > 0,
            total_duration_ms=total_elapsed * 1000,
            status="success"
        )
        
        # Convert audit summary to model
        audit_events = [
            AuditEvent(
                timestamp=event.timestamp,
                type=event.event_type,
                description=event.description,
                duration_ms=event.duration_ms,
                status=event.status
            )
            for event in audit_summary.events
        ]
        
        audit_trail_model = AuditTrailSummary(
            request_id=request_id,
            total_events=len(audit_events),
            total_duration_ms=total_elapsed * 1000,
            event_types={event.type: next((e for e in audit_events if e.type == event.type), None) for event in audit_events},
            events=audit_events
        )
        
        parsed["audit_trail"] = audit_trail_model
        
        # Final log
        logger.info(
            f"[{request_id}] Document analyzed successfully in {total_elapsed:.2f}s "
            f"(file: {file.filename}, impact_score: {impact_score.overall_score}/100, "
            f"checklist: {len(checklist_items_models)}, templates: {len(templates_models)})"
        )
        
        # Create and return response
        response = QueryResponse(**parsed)
        return response
        
    except ValueError as e:
        elapsed = time.time() - start_time
        logger.error(
            f"[{request_id}] Validation error after {elapsed:.2f}s: {str(e)}",
            exc_info=True
        )
        audit_trail_service.log_error(request_id, "ValueError", str(e), "document_processing")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(
            f"[{request_id}] Unexpected error after {elapsed:.2f}s: {str(e)}"
        )
        audit_trail_service.log_error(request_id, type(e).__name__, str(e), "document_processing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the document. Please try again."
        )
        
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"[{request_id}] Temporary file cleaned up")
            except Exception as e:
                logger.warning(f"[{request_id}] Could not delete temporary file: {str(e)}")
