from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    from src.services.db_connection import get_collection as _get_collection
    _HAS_DB = True
except ImportError:
    _HAS_DB = False


class ScoreFeedback(BaseModel):
    """Model for user feedback on impact score accuracy."""
    request_id: str = Field(..., description="Request ID being rated")
    overall_score_given: int = Field(..., ge=0, le=100, description="Score that was given")
    user_rating: int = Field(
        ..., ge=1, le=5,
        description="User's rating of accuracy (1-5 stars: 1=very inaccurate, 5=very accurate)"
    )
    comment: Optional[str] = Field(
        None, max_length=500,
        description="Optional user feedback/explanation"
    )
    actual_score_expected: Optional[int] = Field(
        None, ge=0, le=100,
        description="What score user thinks it should have been"
    )
    feedback_type: str = Field(
        default="accuracy",
        description="Type of feedback: accuracy, too_high, too_low, missing_factor"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "a1b2c3d4-e5f6",
                "overall_score_given": 72,
                "user_rating": 3,
                "comment": "Score was reasonable but underestimated financial impact",
                "actual_score_expected": 80,
                "feedback_type": "too_low"
            }
        }


class ScoreFeedbackResponse(BaseModel):
    """Response model for feedback submission."""
    status: str = Field(..., description="Status of feedback submission")
    message: str = Field(..., description="Response message")
    feedback_id: Optional[str] = Field(None, description="ID of stored feedback")


class FeedbackProcessor:
    """
    Processes and stores user feedback for continuous improvement of scoring.
    Feedback is persisted to MongoDB (score_feedback collection) so it survives
    container restarts in Docker / Hugging Face Spaces.
    """

    def __init__(self):
        logger.info("FeedbackProcessor initialised (MongoDB backend)")

    def submit_feedback(self, feedback: ScoreFeedback) -> dict:
        """Store user feedback in MongoDB."""
        try:
            score_diff = (
                feedback.actual_score_expected - feedback.overall_score_given
                if feedback.actual_score_expected is not None
                else None
            )
            logger.info(
                f"[FEEDBACK] request={feedback.request_id} "
                f"rating={feedback.user_rating} score_diff={score_diff}"
            )

            if _HAS_DB:
                col = _get_collection("score_feedback")
                doc = feedback.model_dump()
                doc["created_at"] = feedback.created_at  # already a datetime
                col.insert_one(doc)
                logger.info(f"[FEEDBACK] Persisted to MongoDB for request {feedback.request_id}")
            else:
                logger.warning("[FEEDBACK] No DB connection — feedback not persisted")

            return {
                "status": "success",
                "message": "Thank you for your feedback! It helps us improve.",
                "feedback_id": feedback.request_id,
            }
        except Exception as exc:
            logger.error(f"[FEEDBACK] Failed to store: {exc}", exc_info=True)
            return {
                "status": "error",
                "message": "Failed to store feedback. Please try again.",
                "feedback_id": None,
            }

    def get_analysis(self) -> dict:
        """
        Compute a live feedback analysis from MongoDB.
        Returns aggregated counts and average rating.
        """
        if not _HAS_DB:
            return {"message": "Database not available"}
        try:
            col = _get_collection("score_feedback")
            total = col.count_documents({})
            if total == 0:
                return {"message": "No feedback collected yet", "total_feedback_count": 0}

            pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_rating": {"$avg": "$user_rating"},
                    "overestimated": {"$sum": {
                        "$cond": [{"$lt": [{"$subtract": [
                            {"$ifNull": ["$actual_score_expected", "$overall_score_given"]},
                            "$overall_score_given"
                        ]}, -5]}, 1, 0]
                    }},
                    "underestimated": {"$sum": {
                        "$cond": [{"$gt": [{"$subtract": [
                            {"$ifNull": ["$actual_score_expected", "$overall_score_given"]},
                            "$overall_score_given"
                        ]}, 5]}, 1, 0]
                    }},
                }}
            ]
            agg = list(col.aggregate(pipeline))
            agg_row = agg[0] if agg else {}

            # Count by feedback_type
            type_pipeline = [
                {"$group": {"_id": "$feedback_type", "count": {"$sum": 1}}}
            ]
            by_type = {r["_id"]: r["count"] for r in col.aggregate(type_pipeline)}

            analysis = {
                "total_feedback_count": total,
                "average_user_rating": round(agg_row.get("avg_rating", 0), 2),
                "feedback_by_type": by_type,
                "score_accuracy": {
                    "overestimated": agg_row.get("overestimated", 0),
                    "underestimated": agg_row.get("underestimated", 0),
                    "accurate": total - agg_row.get("overestimated", 0) - agg_row.get("underestimated", 0),
                },
            }
            return analysis
        except Exception as exc:
            logger.error(f"[FEEDBACK] Analysis failed: {exc}")
            return {"error": str(exc)}
