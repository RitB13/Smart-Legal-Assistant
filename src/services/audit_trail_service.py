"""
Audit Trail Service: Maintains complete audit log of all decisions, calculations, and reasoning
during legal query processing.

Provides:
1. Complete request/response logging
2. Decision point logging
3. Calculation trace logging
4. Timestamp and metadata tracking
5. Compliance audit trail for legal proceedings
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import json
from pymongo.errors import PyMongoError

# Import MongoDB connection
try:
    from src.services.db_connection import get_collection
    HAS_DB_CONNECTION = True
except ImportError:
    HAS_DB_CONNECTION = False
    def get_collection(name):
        raise RuntimeError("Database connection not available")

logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    """Single audit event in the trail"""
    timestamp: str
    event_type: str  # "jurisdiction_detection", "law_matching", "score_calculation", etc.
    description: str
    details: Dict[str, Any]
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    duration_ms: float
    component: str
    status: str  # "success", "error", "partial"


@dataclass
class AuditTrail:
    """Complete audit trail for a request"""
    request_id: str
    timestamp_start: str
    timestamp_end: str
    total_duration_ms: float
    events: List[AuditEvent]
    user_query: str
    user_location: str
    language_detected: str
    jurisdiction_result: str
    final_score: float
    checklist_generated: bool
    templates_generated: bool
    status: str


class AuditTrailService:
    """Service for maintaining complete audit trail of legal analysis"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuditTrailService, cls).__new__(cls)
            cls._instance.trails = {}  # Store audit trails by request_id
        return cls._instance
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.trails: Dict[str, List[AuditEvent]] = {}
    
    def start_audit_trail(self, request_id: str, query: str, client_ip: Optional[str] = None):
        """
        Start a new audit trail for a request.
        
        Args:
            request_id: Unique request identifier
            query: User's legal query
            client_ip: Client IP address
        """
        self.trails[request_id] = []
        
        self.log_event(
            request_id=request_id,
            event_type="request_received",
            description="New legal query received",
            details={
                "query_length": len(query),
                "query_preview": query[:100] + "..." if len(query) > 100 else query,
                "client_ip": client_ip
            }
        )
        
        self.logger.debug(f"[{request_id}] Audit trail started")
    
    def log_event(
        self,
        request_id: str,
        event_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        component: str = "core",
        duration_ms: float = 0,
        status: str = "success"
    ):
        """
        Log an event in the audit trail.
        
        Args:
            request_id: Request identifier
            event_type: Type of event
            description: Human-readable description
            details: Additional details
            input_data: Input to the operation
            output_data: Output from the operation
            component: Component responsible
            duration_ms: Duration of operation in milliseconds
            status: Success/error/partial status
        """
        if request_id not in self.trails:
            self.trails[request_id] = []
        
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            description=description,
            details=details or {},
            input_data=input_data or {},
            output_data=output_data or {},
            duration_ms=duration_ms,
            component=component,
            status=status
        )
        
        self.trails[request_id].append(event)
        
        self.logger.debug(
            f"[{request_id}] Event logged: {event_type} ({status}) - {description} [{duration_ms:.0f}ms]"
        )
    
    def log_jurisdiction_detection(
        self,
        request_id: str,
        detected_country: str,
        detected_state: str,
        detected_method: str,
        confidence: float,
        signals_evaluated: Dict[str, Any],
        duration_ms: float
    ):
        """Log jurisdiction detection event"""
        self.log_event(
            request_id=request_id,
            event_type="jurisdiction_detection",
            description=f"Detected jurisdiction: {detected_country}/{detected_state}",
            details={
                "method": detected_method,
                "confidence": confidence,
                "confidence_percentage": f"{confidence * 100:.0f}%"
            },
            input_data=signals_evaluated,
            output_data={
                "country": detected_country,
                "state": detected_state,
                "method": detected_method,
                "confidence": confidence
            },
            component="jurisdiction_detector",
            duration_ms=duration_ms
        )
    
    def log_law_matching(
        self,
        request_id: str,
        matched_laws: List[Dict[str, Any]],
        total_available_laws: int,
        duration_ms: float
    ):
        """Log law matching event"""
        law_ids = [law.get("law_id") for law in matched_laws[:5]]
        relevance_scores = [law.get("relevance_score", 0) for law in matched_laws[:5]]
        
        self.log_event(
            request_id=request_id,
            event_type="law_matching",
            description=f"Matched {len(matched_laws)} relevant laws from {total_available_laws} available",
            details={
                "laws_matched": len(matched_laws),
                "total_available": total_available_laws,
                "top_law_ids": law_ids,
                "top_relevance_scores": [round(s, 3) for s in relevance_scores],
                "matching_algorithm": "weighted_relevance (keyword 40% + category 30% + severity 20% + name 10%)"
            },
            output_data={
                "matched_law_count": len(matched_laws),
                "top_5_laws": law_ids
            },
            component="law_matcher",
            duration_ms=duration_ms
        )
    
    def log_feature_extraction(
        self,
        request_id: str,
        extracted_features: Dict[str, Any],
        true_feature_count: int,
        duration_ms: float
    ):
        """Log feature extraction event"""
        # Get features that are true/active
        active_features = {k: v for k, v in extracted_features.items() 
                          if v is True or (isinstance(v, (int, float)) and v > 0)}
        
        self.log_event(
            request_id=request_id,
            event_type="feature_extraction",
            description=f"Extracted {true_feature_count} legal features from query",
            details={
                "total_features_checked": len(extracted_features),
                "features_detected": true_feature_count,
                "active_feature_names": list(active_features.keys())
            },
            output_data=extracted_features,
            component="feature_extractor",
            duration_ms=duration_ms
        )
    
    def log_impact_score_calculation(
        self,
        request_id: str,
        overall_score: float,
        financial_risk: float,
        legal_exposure: float,
        long_term_impact: float,
        rights_lost: float,
        risk_level: str,
        features_used: List[str],
        duration_ms: float
    ):
        """Log impact score calculation event"""
        self.log_event(
            request_id=request_id,
            event_type="impact_score_calculation",
            description=f"Calculated impact score: {overall_score:.1f}/100 ({risk_level})",
            details={
                "overall_score": round(overall_score, 1),
                "risk_level": risk_level,
                "formula": "Overall = (F×0.40) + (L×0.30) + (LT×0.20) + (R×0.10)",
                "component_scores": {
                    "financial_risk": round(financial_risk, 1),
                    "legal_exposure": round(legal_exposure, 1),
                    "long_term_impact": round(long_term_impact, 1),
                    "rights_lost": round(rights_lost, 1)
                },
                "weights": {
                    "financial_risk": "40%",
                    "legal_exposure": "30%",
                    "long_term_impact": "20%",
                    "rights_lost": "10%"
                }
            },
            input_data={
                "features_used": features_used,
                "feature_count": len(features_used)
            },
            output_data={
                "overall_score": overall_score,
                "financial_risk": financial_risk,
                "legal_exposure": legal_exposure,
                "long_term_impact": long_term_impact,
                "rights_lost": rights_lost,
                "risk_level": risk_level
            },
            component="legal_impact_scorer",
            duration_ms=duration_ms
        )
    
    def log_checklist_generation(
        self,
        request_id: str,
        issue_type: str,
        checklist_items_count: int,
        critical_items: int,
        high_items: int,
        duration_ms: float
    ):
        """Log checklist generation event"""
        self.log_event(
            request_id=request_id,
            event_type="checklist_generation",
            description=f"Generated {checklist_items_count}-step checklist for {issue_type}",
            details={
                "issue_type": issue_type,
                "total_steps": checklist_items_count,
                "critical_priority_steps": critical_items,
                "high_priority_steps": high_items,
                "priority_breakdown": {
                    "🔴 Critical": critical_items,
                    "🟠 High": high_items,
                    "🟡 Medium": checklist_items_count - critical_items - high_items
                }
            },
            output_data={
                "checklist_generated": True,
                "issue_type": issue_type,
                "item_count": checklist_items_count
            },
            component="checklist_generator",
            duration_ms=duration_ms
        )
    
    def log_template_generation(
        self,
        request_id: str,
        templates_generated: int,
        template_categories: List[str],
        duration_ms: float
    ):
        """Log template generation event"""
        unique_categories = list(set(template_categories))
        
        self.log_event(
            request_id=request_id,
            event_type="template_generation",
            description=f"Generated {templates_generated} relevant document templates",
            details={
                "templates_count": templates_generated,
                "template_categories": unique_categories,
                "category_count": len(unique_categories)
            },
            output_data={
                "templates_generated": templates_generated,
                "categories": unique_categories
            },
            component="template_generator",
            duration_ms=duration_ms
        )
    
    def log_llm_call(
        self,
        request_id: str,
        model: str,
        tokens_used: int,
        temperature: float,
        duration_ms: float
    ):
        """Log LLM API call event"""
        self.log_event(
            request_id=request_id,
            event_type="llm_call",
            description=f"Called LLM {model} for legal guidance generation",
            details={
                "model": model,
                "tokens_used": tokens_used,
                "temperature": temperature,
                "approx_cost": f"${tokens_used * 0.0000008:.6f}" if "groq" in model.lower() else "Unknown"
            },
            component="llm_service",
            duration_ms=duration_ms
        )
    
    def log_case_prediction(
        self,
        request_id: str,
        case_name: str,
        predicted_verdict: str,
        confidence: float,
        model_version: str,
        prediction_time_ms: float,
        similar_cases_count: int,
        input_data: Dict[str, Any],
        duration_ms: float
    ):
        """
        Log a case outcome prediction event (PHASE 9: Monitoring).
        
        Tracks:
        - Prediction time
        - Model version used
        - Prediction confidence
        - Similar cases found
        """
        self.log_event(
            request_id=request_id,
            event_type="case_prediction",
            description=f"Predicted verdict: {predicted_verdict} (confidence: {confidence:.1%})",
            details={
                "predicted_verdict": predicted_verdict,
                "confidence": f"{confidence:.1%}",
                "model_version": model_version,
                "prediction_time_ms": prediction_time_ms,
                "similar_cases_found": similar_cases_count,
                "confidence_score": round(confidence, 4)
            },
            input_data={
                "case_name": case_name,
                **input_data
            },
            output_data={
                "verdict": predicted_verdict,
                "confidence": confidence,
                "model_version": model_version
            },
            component="case_outcome_predictor",
            duration_ms=duration_ms,
            status="success"
        )
        
        # PERSISTENCE: Save to MongoDB audit_logs collection
        self._persist_to_mongodb(
            request_id=request_id,
            case_name=case_name,
            predicted_verdict=predicted_verdict,
            confidence=confidence,
            model_version=model_version,
            input_data=input_data
        )
    
    def _persist_to_mongodb(
        self,
        request_id: str,
        case_name: str,
        predicted_verdict: str,
        confidence: float,
        model_version: str,
        input_data: Dict[str, Any]
    ) -> bool:
        """
        Persist case prediction to MongoDB audit_logs collection.
        
        Args:
            request_id: Unique request identifier
            case_name: Name of the case
            predicted_verdict: Predicted verdict
            confidence: Confidence level (0-1)
            model_version: Version of the model used
            input_data: Input features used for prediction
            
        Returns:
            True if persisted successfully, False otherwise
        """
        if not HAS_DB_CONNECTION:
            self.logger.warning("[AUDIT] Database connection not available - audit log not persisted")
            return False
        
        try:
            collection = get_collection("audit_logs")
            
            # Convert input_data to serializable format (handle Pydantic models)
            def serialize_value(obj):
                """Convert Pydantic models and other objects to JSON-serializable format"""
                if hasattr(obj, 'dict'):
                    return obj.dict()  # Pydantic model
                elif isinstance(obj, dict):
                    return {k: serialize_value(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [serialize_value(item) for item in obj]
                else:
                    return obj
            
            audit_document = {
                "request_id": request_id,
                "timestamp": datetime.utcnow(),
                "event_type": "case_prediction",
                "case_name": case_name,
                "predicted_verdict": predicted_verdict,
                "confidence": float(confidence),
                "model_version": model_version,
                "input_features": serialize_value(input_data),
                "status": "success"
            }
            
            result = collection.insert_one(audit_document)
            self.logger.info(f"✅ [AUDIT] Persisted audit log to MongoDB: {result.inserted_id}")
            return True
            
        except PyMongoError as e:
            self.logger.error(f"❌ [AUDIT] MongoDB error persisting audit log: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ [AUDIT] Error persisting audit log: {e}")
            return False
    
    @staticmethod
    def save_case_prediction(
        request_id: str,
        case_name: str,
        predicted_verdict: str,
        confidence: float,
        verdict_id: int,
        risk_level: str,
        risk_assessment: Dict[str, Any],
        input_data: Dict[str, Any],
        probabilities: Dict[str, float],
        model_version: str = "current"
    ) -> bool:
        """
        Save a case prediction result to MongoDB case_predictions collection.
        
        Args:
            request_id: Unique prediction request ID
            case_name: Name of the case
            predicted_verdict: The predicted verdict
            confidence: Confidence score (0-1)
            verdict_id: Numeric ID of the verdict
            risk_level: Risk level (low/medium/high/very_high)
            risk_assessment: Risk assessment details
            input_data: Input features
            probabilities: Probability distribution for all verdicts
            model_version: Version of the model used
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not HAS_DB_CONNECTION:
            logger.warning("[PREDICTION] Database connection not available - prediction not persisted")
            return False
        
        try:
            collection = get_collection("case_predictions")
            
            # Convert Pydantic models to dictionaries for MongoDB serialization
            def serialize_value(obj):
                """Convert Pydantic models and other objects to JSON-serializable format"""
                if hasattr(obj, 'dict'):
                    return obj.dict()  # Pydantic model
                elif isinstance(obj, dict):
                    return {k: serialize_value(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [serialize_value(item) for item in obj]
                else:
                    return obj
            
            prediction_document = {
                "request_id": request_id,
                "timestamp": datetime.utcnow(),
                "case_name": case_name,
                "predicted_verdict": predicted_verdict,
                "verdict_id": verdict_id,
                "confidence": float(confidence),
                "risk_level": risk_level,
                "risk_assessment": serialize_value(risk_assessment),
                "input_features": serialize_value(input_data),
                "verdict_probabilities": serialize_value(probabilities),
                "model_version": model_version,
                "status": "success"
            }
            
            result = collection.insert_one(prediction_document)
            logger.info(f"✅ [PREDICTION] Saved prediction to MongoDB: {result.inserted_id}")
            return True
            
        except PyMongoError as e:
            logger.error(f"❌ [PREDICTION] MongoDB error saving prediction: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ [PREDICTION] Error saving prediction: {e}")
            return False
    
    def log_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        component: str,
        traceback_info: Optional[str] = None
    ):
        """Log an error event"""
        self.log_event(
            request_id=request_id,
            event_type="error",
            description=f"Error in {component}: {error_message}",
            details={
                "error_type": error_type,
                "error_message": error_message,
                "traceback": traceback_info
            },
            component=component,
            status="error"
        )
    
    def finalize_trail(
        self,
        request_id: str,
        user_query: str,
        user_location: str,
        language_detected: str,
        jurisdiction_result: str,
        final_score: float,
        checklist_generated: bool,
        templates_generated: bool,
        total_duration_ms: float,
        status: str = "success"
    ) -> AuditTrail:
        """
        Finalize and return the audit trail.
        
        Args:
            request_id: Request identifier
            user_query: Original user query
            user_location: Detected user location
            language_detected: Detected language
            jurisdiction_result: Final jurisdiction decision
            final_score: Final impact score
            checklist_generated: Whether checklist was generated
            templates_generated: Whether templates were generated
            total_duration_ms: Total processing time
            status: Overall processing status
            
        Returns:
            Complete AuditTrail object
        """
        events = self.trails.get(request_id, [])
        
        audit_trail = AuditTrail(
            request_id=request_id,
            timestamp_start=events[0].timestamp if events else datetime.utcnow().isoformat(),
            timestamp_end=datetime.utcnow().isoformat(),
            total_duration_ms=total_duration_ms,
            events=events,
            user_query=user_query,
            user_location=user_location,
            language_detected=language_detected,
            jurisdiction_result=jurisdiction_result,
            final_score=final_score,
            checklist_generated=checklist_generated,
            templates_generated=templates_generated,
            status=status
        )
        
        self.logger.info(
            f"[{request_id}] Audit trail finalized: "
            f"{len(events)} events, "
            f"{total_duration_ms:.0f}ms total, "
            f"Score: {final_score:.1f}, "
            f"Status: {status}"
        )
        
        return audit_trail
    
    def get_audit_summary(self, request_id: str) -> Dict[str, Any]:
        """
        Get a summary of the audit trail for display.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Dictionary with audit summary
        """
        events = self.trails.get(request_id, [])
        
        event_types = {}
        total_duration = 0
        
        for event in events:
            event_type = event.event_type
            if event_type not in event_types:
                event_types[event_type] = {"count": 0, "duration": 0}
            
            event_types[event_type]["count"] += 1
            event_types[event_type]["duration"] += event.duration_ms
            total_duration += event.duration_ms
        
        return {
            "request_id": request_id,
            "total_events": len(events),
            "total_duration_ms": total_duration,
            "event_type_summary": event_types,
            "events": [
                {
                    "timestamp": event.timestamp,
                    "type": event.event_type,
                    "description": event.description,
                    "duration_ms": event.duration_ms,
                    "status": event.status
                }
                for event in events
            ]
        }
    
    def export_trail_to_json(self, request_id: str) -> str:
        """Export audit trail as JSON for compliance/legal purposes"""
        events = self.trails.get(request_id, [])
        
        events_dict = [
            {
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "description": event.description,
                "details": event.details,
                "input_data": event.input_data,
                "output_data": event.output_data,
                "duration_ms": event.duration_ms,
                "component": event.component,
                "status": event.status
            }
            for event in events
        ]
        
        return json.dumps(events_dict, indent=2, default=str)


def get_audit_trail_service() -> AuditTrailService:
    """Get singleton instance of AuditTrailService"""
    return AuditTrailService()
