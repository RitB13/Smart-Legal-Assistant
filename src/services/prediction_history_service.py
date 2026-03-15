"""
Prediction History Service - Manages case prediction storage and retrieval.

This service provides methods to:
- Save predictions to the database
- Retrieve predictions by ID or user
- Search predictions
- Get prediction statistics
- Delete predictions
"""

from pymongo import DESCENDING
from bson import ObjectId
from datetime import datetime
import logging
from typing import Optional, List
from src.models.db_models import (
    CasePrediction, CasePredictionCreate, CasePredictionInDB,
    CasePredictionMetadata, PredictionResult
)
from src.services.db_connection import get_collection

logger = logging.getLogger(__name__)


class PredictionHistoryService:
    """Service for managing case predictions in MongoDB"""
    
    @staticmethod
    def save_prediction(pred_data: CasePredictionCreate) -> Optional[CasePredictionInDB]:
        """
        Save a case prediction to the database.
        
        Args:
            pred_data: Prediction information (user_id, metadata, result)
            
        Returns:
            CasePredictionInDB if successful, None if failed
            
        Example:
            >>> pred = PredictionHistoryService.save_prediction(
            ...     CasePredictionCreate(
            ...         user_id="507f1f77bcf86cd799439011",
            ...         metadata=CasePredictionMetadata(...),
            ...         result=PredictionResult(...)
            ...     )
            ... )
        """
        collection = get_collection("case_predictions")
        
        pred_dict = {
            "user_id": pred_data.user_id,
            "metadata": pred_data.metadata.dict(),
            "result": pred_data.result.dict(),
            "created_at": datetime.utcnow(),
        }
        
        try:
            result = collection.insert_one(pred_dict)
            pred_dict["_id"] = result.inserted_id
            logger.info(f"✅ [PRED] Saved prediction: {result.inserted_id}")
            return CasePredictionInDB(**pred_dict)
        except Exception as e:
            logger.error(f"❌ [PRED] Error saving prediction: {e}")
            return None
    
    @staticmethod
    def get_prediction(pred_id: str) -> Optional[CasePredictionInDB]:
        """
        Get a prediction by ID.
        
        Args:
            pred_id: Prediction's MongoDB ObjectId as string
            
        Returns:
            CasePredictionInDB if found, None if not found
            
        Example:
            >>> pred = PredictionHistoryService.get_prediction("507f1f77bcf86cd799439011")
        """
        collection = get_collection("case_predictions")
        
        try:
            pred_dict = collection.find_one({"_id": ObjectId(pred_id)})
            if pred_dict:
                logger.info(f"✅ [PRED] Found prediction: {pred_id}")
                return CasePredictionInDB(**pred_dict)
            else:
                logger.warning(f"⚠️  [PRED] Prediction not found: {pred_id}")
                return None
        except Exception as e:
            logger.error(f"❌ [PRED] Error getting prediction: {e}")
            return None
    
    @staticmethod
    def get_user_predictions(user_id: str, limit: int = 50) -> List[CasePredictionInDB]:
        """
        Get all predictions for a user, sorted by newest first.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            limit: Maximum number of predictions to return (default 50)
            
        Returns:
            List of CasePredictionInDB objects (newest first)
            
        Example:
            >>> predictions = PredictionHistoryService.get_user_predictions(
            ...     "507f1f77bcf86cd799439011",
            ...     limit=20
            ... )
        """
        collection = get_collection("case_predictions")
        
        try:
            predictions = list(collection.find(
                {"user_id": user_id}
            ).sort("created_at", DESCENDING).limit(limit))
            
            logger.info(f"✅ [PRED] Found {len(predictions)} prediction(s) for user")
            return [CasePredictionInDB(**pred) for pred in predictions]
        except Exception as e:
            logger.error(f"❌ [PRED] Error getting predictions: {e}")
            return []
    
    @staticmethod
    def get_predictions_by_verdict(user_id: str, verdict: str) -> List[CasePredictionInDB]:
        """
        Get predictions filtered by verdict type.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            verdict: Verdict to filter by (e.g., "Accepted", "Convicted")
            
        Returns:
            List of matching CasePredictionInDB objects
            
        Example:
            >>> accepted = PredictionHistoryService.get_predictions_by_verdict(
            ...     "507f1f77bcf86cd799439011",
            ...     "Accepted"
            ... )
        """
        collection = get_collection("case_predictions")
        
        try:
            predictions = list(collection.find({
                "user_id": user_id,
                "result.verdict": verdict
            }).sort("created_at", DESCENDING))
            
            logger.info(f"✅ [PRED] Found {len(predictions)} {verdict} prediction(s)")
            return [CasePredictionInDB(**pred) for pred in predictions]
        except Exception as e:
            logger.error(f"❌ [PRED] Error filtering predictions: {e}")
            return []
    
    @staticmethod
    def get_predictions_by_case_type(user_id: str, case_type: str) -> List[CasePredictionInDB]:
        """
        Get predictions filtered by case type.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            case_type: Case type to filter by (e.g., "Criminal", "Civil")
            
        Returns:
            List of matching CasePredictionInDB objects
            
        Example:
            >>> criminal = PredictionHistoryService.get_predictions_by_case_type(
            ...     "507f1f77bcf86cd799439011",
            ...     "Criminal"
            ... )
        """
        collection = get_collection("case_predictions")
        
        try:
            predictions = list(collection.find({
                "user_id": user_id,
                "metadata.case_type": case_type
            }).sort("created_at", DESCENDING))
            
            logger.info(f"✅ [PRED] Found {len(predictions)} {case_type} case(s)")
            return [CasePredictionInDB(**pred) for pred in predictions]
        except Exception as e:
            logger.error(f"❌ [PRED] Error getting predictions by case type: {e}")
            return []
    
    @staticmethod
    def search_predictions(user_id: str, query: str) -> List[CasePredictionInDB]:
        """
        Search predictions by case name (case-insensitive).
        
        Args:
            user_id: User's MongoDB ObjectId as string
            query: Search query string
            
        Returns:
            List of matching CasePredictionInDB objects
            
        Example:
            >>> results = PredictionHistoryService.search_predictions(
            ...     "507f1f77bcf86cd799439011",
            ...     "John vs State"
            ... )
        """
        collection = get_collection("case_predictions")
        
        try:
            predictions = list(collection.find({
                "user_id": user_id,
                "metadata.case_name": {"$regex": query, "$options": "i"}  # Case-insensitive search
            }).sort("created_at", DESCENDING))
            
            logger.info(f"✅ [PRED] Found {len(predictions)} matching prediction(s)")
            return [CasePredictionInDB(**pred) for pred in predictions]
        except Exception as e:
            logger.error(f"❌ [PRED] Error searching predictions: {e}")
            return []
    
    @staticmethod
    def delete_prediction(pred_id: str) -> bool:
        """
        Delete a prediction.
        
        Args:
            pred_id: Prediction's MongoDB ObjectId as string
            
        Returns:
            True if successful, False if failed
            
        Example:
            >>> success = PredictionHistoryService.delete_prediction("507f1f77bcf86cd799439011")
        """
        collection = get_collection("case_predictions")
        
        try:
            result = collection.delete_one({"_id": ObjectId(pred_id)})
            
            if result.deleted_count > 0:
                logger.info(f"✅ [PRED] Deleted prediction: {pred_id}")
                return True
            else:
                logger.warning(f"⚠️  [PRED] Prediction not found to delete: {pred_id}")
                return False
        except Exception as e:
            logger.error(f"❌ [PRED] Error deleting prediction: {e}")
            return False
    
    @staticmethod
    def get_user_stats(user_id: str) -> dict:
        """
        Get prediction statistics for a user.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            
        Returns:
            Dictionary with prediction statistics
            
        Example:
            >>> stats = PredictionHistoryService.get_user_stats("507f1f77bcf86cd799439011")
            >>> print(stats)
            {
                'total_predictions': 15,
                'by_verdict': {'Accepted': 8, 'Rejected': 5, 'Convicted': 2},
                'by_case_type': {'Criminal': 10, 'Civil': 5}
            }
        """
        collection = get_collection("case_predictions")
        
        try:
            total = collection.count_documents({"user_id": user_id})
            
            # Count by verdict
            verdict_aggregation = list(collection.aggregate([
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$result.verdict",
                    "count": {"$sum": 1}
                }}
            ]))
            verdict_counts = {item["_id"]: item["count"] for item in verdict_aggregation}
            
            # Count by case type
            case_type_aggregation = list(collection.aggregate([
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$metadata.case_type",
                    "count": {"$sum": 1}
                }}
            ]))
            case_type_counts = {item["_id"]: item["count"] for item in case_type_aggregation}
            
            # Get average confidence
            confidence_aggregation = list(collection.aggregate([
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": None,
                    "avg_confidence": {"$avg": "$result.confidence"}
                }}
            ]))
            avg_confidence = confidence_aggregation[0]["avg_confidence"] if confidence_aggregation else 0
            
            return {
                "total_predictions": total,
                "by_verdict": verdict_counts,
                "by_case_type": case_type_counts,
                "average_confidence": round(avg_confidence, 2),
            }
        except Exception as e:
            logger.error(f"❌ [PRED] Error getting stats: {e}")
            return {
                "total_predictions": 0,
                "by_verdict": {},
                "by_case_type": {},
                "average_confidence": 0,
            }
