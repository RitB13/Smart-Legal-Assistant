from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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
    Processes and stores user feedback for continuous improvement of scoring algorithm.
    In production, this would connect to a database. For now, uses JSON file storage.
    """
    
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.feedback_file = self.storage_dir / "score_feedback.jsonl"
        self.analysis_file = self.storage_dir / "feedback_analysis.json"
        logger.info(f"Initialized FeedbackProcessor with storage: {self.storage_dir}")
    
    def submit_feedback(self, feedback: ScoreFeedback) -> dict:
        """
        Store user feedback and trigger analysis.
        
        Args:
            feedback: ScoreFeedback object
            
        Returns:
            Dictionary with status and feedback_id
        """
        try:
            # Store feedback in JSONL format (one JSON per line)
            with open(self.feedback_file, "a", encoding="utf-8") as f:
                f.write(feedback.model_dump_json() + "\n")
            
            logger.info(
                f"Stored feedback for request {feedback.request_id}: "
                f"rating={feedback.user_rating}, score_diff={feedback.actual_score_expected - feedback.overall_score_given if feedback.actual_score_expected else 'N/A'}"
            )
            
            # Analyze feedback patterns
            self._analyze_feedback()
            
            return {
                "status": "success",
                "message": "Thank you for your feedback! It helps us improve.",
                "feedback_id": feedback.request_id
            }
        except Exception as e:
            logger.error(f"Failed to store feedback: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": "Failed to store feedback. Please try again.",
                "feedback_id": None
            }
    
    def _analyze_feedback(self) -> None:
        """
        Analyze feedback patterns and generate insights for algorithm improvement.
        This identifies systematic biases in the scoring algorithm.
        """
        try:
            if not self.feedback_file.exists():
                return
            
            # Read all feedback
            feedbacks = []
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        feedbacks.append(json.loads(line))
            
            if not feedbacks:
                return
            
            # Analyze patterns
            analysis = {
                "total_feedback_count": len(feedbacks),
                "average_user_rating": sum(f["user_rating"] for f in feedbacks) / len(feedbacks),
                "feedback_by_type": {},
                "score_accuracy": {
                    "overestimated": 0,  # Given score > expected
                    "underestimated": 0,
                    "accurate": 0
                },
                "improvement_areas": []
            }
            
            # Count feedback by type
            for feedback in feedbacks:
                feedback_type = feedback.get("feedback_type", "accuracy")
                analysis["feedback_by_type"][feedback_type] = \
                    analysis["feedback_by_type"].get(feedback_type, 0) + 1
                
                # Track accuracy patterns
                if feedback.get("actual_score_expected"):
                    diff = feedback["actual_score_expected"] - feedback["overall_score_given"]
                    if diff > 5:
                        analysis["score_accuracy"]["underestimated"] += 1
                    elif diff < -5:
                        analysis["score_accuracy"]["overestimated"] += 1
                    else:
                        analysis["score_accuracy"]["accurate"] += 1
            
            # Identify improvement areas based on feedback
            ratings_below_3 = [f for f in feedbacks if f["user_rating"] < 3]
            if len(ratings_below_3) / len(feedbacks) > 0.2:  # >20% low ratings
                analysis["improvement_areas"].append(
                    "Significant portion of scores rated as inaccurate. Consider revising weights."
                )
            
            overestimated = analysis["score_accuracy"]["overestimated"]
            if overestimated / len(feedbacks) > 0.3:  # >30% overestimated
                analysis["improvement_areas"].append(
                    "Tendency to overestimate risk. Consider reducing weight on severity keywords."
                )
            
            # Save analysis
            with open(self.analysis_file, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, default=str)
            
            logger.info(f"Updated feedback analysis: {len(feedbacks)} total feedback entries")
            logger.info(f"Avg user rating: {analysis['average_user_rating']:.2f}/5.0")
            
        except Exception as e:
            logger.error(f"Failed to analyze feedback: {str(e)}", exc_info=True)
    
    def get_analysis(self) -> dict:
        """
        Get current feedback analysis.
        
        Returns:
            Dictionary with feedback patterns and insights
        """
        try:
            if self.analysis_file.exists():
                with open(self.analysis_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"message": "No feedback analysis available yet"}
        except Exception as e:
            logger.error(f"Failed to read analysis: {str(e)}")
            return {"error": str(e)}
