"""
Monitoring Service: Track prediction metrics and detect data drift.

Provides:
1. Prediction tracking and logging
2. Performance metric collection
3. Data drift detection
4. Model monitoring dashboard data
5. Alert generation for anomalies
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from collections import deque
import statistics

logger = logging.getLogger(__name__)


@dataclass
class PredictionMetric:
    """Single prediction metric for monitoring"""
    timestamp: str
    model_version: str
    prediction_time_ms: float
    confidence: float
    input_features: Dict[str, Any]
    prediction_class: str
    actual_outcome: Optional[str] = None
    user_feedback: Optional[str] = None
    feedback_timestamp: Optional[str] = None


@dataclass
class DriftIndicator:
    """Data drift indicator"""
    metric_name: str
    old_mean: float
    new_mean: float
    old_std: float
    new_std: float
    drift_percentage: float
    is_drift_detected: bool
    threshold: float = 0.15  # 15% threshold


class PredictionMonitor:
    """
    Monitor prediction performance and detect data drift.
    
    Features:
    - Track prediction confidence over time
    - Monitor inference time performance
    - Detect input feature distribution changes
    - Identify potential model degradation
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PredictionMonitor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize prediction monitor.
        
        Args:
            window_size: Number of recent predictions to keep in memory
        """
        self.window_size = window_size
        
        # Track predictions
        self.predictions: deque = deque(maxlen=window_size)
        
        # Performance metrics
        self.metrics = {
            "total_predictions": 0,
            "total_correct": 0,
            "confidence_scores": [],
            "inference_times": [],
            "predictions_by_class": {},
            "errors": 0
        }
        
        # Feature statistics for drift detection
        self.feature_stats = {}
        
        # Historical data drift
        self.drift_history: List[DriftIndicator] = []
        
        logger.info(f"PredictionMonitor initialized (window_size={window_size})")
    
    def log_prediction(
        self,
        model_version: str,
        prediction_time_ms: float,
        confidence: float,
        input_features: Dict[str, Any],
        prediction_class: str,
        actual_outcome: Optional[str] = None
    ) -> None:
        """
        Log a prediction for monitoring.
        
        Args:
            model_version: Version of model used
            prediction_time_ms: Time taken for inference (milliseconds)
            confidence: Confidence score of prediction (0-1)
            input_features: Input features used
            prediction_class: Predicted class/outcome
            actual_outcome: Actual outcome (if known from feedback)
        """
        try:
            metric = PredictionMetric(
                timestamp=datetime.utcnow().isoformat(),
                model_version=model_version,
                prediction_time_ms=prediction_time_ms,
                confidence=confidence,
                input_features=input_features,
                prediction_class=prediction_class,
                actual_outcome=actual_outcome
            )
            
            self.predictions.append(metric)
            self._update_metrics(metric)
            
            logger.debug(f"Prediction logged: {prediction_class} (conf={confidence:.2f})")
            
        except Exception as e:
            logger.error(f"Error logging prediction: {e}")
    
    def _update_metrics(self, metric: PredictionMetric) -> None:
        """Update aggregated metrics."""
        self.metrics["total_predictions"] += 1
        self.metrics["confidence_scores"].append(metric.confidence)
        self.metrics["inference_times"].append(metric.prediction_time_ms)
        
        # Track predictions by class
        if metric.prediction_class not in self.metrics["predictions_by_class"]:
            self.metrics["predictions_by_class"][metric.prediction_class] = 0
        self.metrics["predictions_by_class"][metric.prediction_class] += 1
        
        # Track correctness if actual_outcome provided
        if metric.actual_outcome:
            if metric.prediction_class == metric.actual_outcome:
                self.metrics["total_correct"] += 1
            else:
                self.metrics["errors"] += 1
        
        # Update feature statistics
        self._update_feature_stats(metric.input_features)
    
    def _update_feature_stats(self, features: Dict[str, Any]) -> None:
        """Update feature statistics for drift detection."""
        for feature_name, feature_value in features.items():
            if isinstance(feature_value, (int, float)):
                if feature_name not in self.feature_stats:
                    self.feature_stats[feature_name] = deque(maxlen=self.window_size)
                
                self.feature_stats[feature_name].append(feature_value)
    
    def log_user_feedback(
        self,
        prediction_index: int,
        feedback: str
    ) -> bool:
        """
        Log user feedback on a prediction.
        
        Args:
            prediction_index: Index of prediction in recent history
            feedback: User feedback (e.g., "correct", "incorrect", "helpful")
            
        Returns:
            True if feedback logged successfully
        """
        try:
            if prediction_index >= len(self.predictions):
                logger.warning(f"Prediction index out of range: {prediction_index}")
                return False
            
            # Access by index from the end (most recent predictions)
            predictions_list = list(self.predictions)
            if prediction_index >= len(predictions_list):
                return False
            
            # Update the prediction
            predictions_list[prediction_index].user_feedback = feedback
            predictions_list[prediction_index].feedback_timestamp = datetime.utcnow().isoformat()
            
            logger.info(f"User feedback logged: {feedback}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging user feedback: {e}")
            return False
    
    def check_data_drift(self, threshold: float = 0.15) -> List[DriftIndicator]:
        """
        Detect data drift by comparing recent feature distributions.
        
        Algorithm:
        1. Split recent predictions into two halves
        2. Calculate mean and std for each feature
        3. Calculate percentage change
        4. Flag as drift if change > threshold
        
        Args:
            threshold: Drift detection threshold (default 15%)
            
        Returns:
            List of DriftIndicator objects for features showing drift
        """
        try:
            if len(self.predictions) < 100:
                logger.debug("Not enough predictions for drift detection")
                return []
            
            drift_indicators = []
            
            for feature_name, values in self.feature_stats.items():
                if len(values) < 50:
                    continue
                
                values_list = list(values)
                mid_point = len(values_list) // 2
                
                old_values = values_list[:mid_point]
                new_values = values_list[mid_point:]
                
                if not old_values or not new_values:
                    continue
                
                try:
                    old_mean = statistics.mean(old_values)
                    new_mean = statistics.mean(new_values)
                    
                    old_std = statistics.stdev(old_values) if len(old_values) > 1 else 0
                    new_std = statistics.stdev(new_values) if len(new_values) > 1 else 0
                    
                    # Calculate percentage change
                    if old_mean != 0:
                        drift_pct = abs((new_mean - old_mean) / old_mean)
                    else:
                        drift_pct = abs(new_mean - old_mean)
                    
                    is_drift = drift_pct > threshold
                    
                    indicator = DriftIndicator(
                        metric_name=feature_name,
                        old_mean=old_mean,
                        new_mean=new_mean,
                        old_std=old_std,
                        new_std=new_std,
                        drift_percentage=drift_pct,
                        is_drift_detected=is_drift,
                        threshold=threshold
                    )
                    
                    if is_drift:
                        drift_indicators.append(indicator)
                        logger.warning(f"Data drift detected in {feature_name}: {drift_pct:.2%} change")
                
                except (ValueError, ZeroDivisionError):
                    continue
            
            # Store drift history
            if drift_indicators:
                self.drift_history.extend(drift_indicators)
                # Keep only recent 100 drift detections
                if len(self.drift_history) > 100:
                    self.drift_history = self.drift_history[-100:]
            
            return drift_indicators
            
        except Exception as e:
            logger.error(f"Error checking data drift: {e}")
            return []
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of model performance metrics."""
        total = self.metrics["total_predictions"]
        if total == 0:
            return {
                "total_predictions": 0,
                "message": "No predictions recorded yet"
            }
        
        accuracy = (self.metrics["total_correct"] / 
                   (self.metrics["total_correct"] + self.metrics["errors"]) 
                   if (self.metrics["total_correct"] + self.metrics["errors"]) > 0 else 0)
        
        confidence_scores = self.metrics["confidence_scores"]
        inference_times = self.metrics["inference_times"]
        
        return {
            "total_predictions": total,
            "accuracy": round(accuracy, 4),
            "correct_predictions": self.metrics["total_correct"],
            "errors": self.metrics["errors"],
            "average_confidence": round(statistics.mean(confidence_scores), 4) if confidence_scores else 0,
            "confidence_std": round(statistics.stdev(confidence_scores), 4) if len(confidence_scores) > 1 else 0,
            "average_inference_time_ms": round(statistics.mean(inference_times), 2) if inference_times else 0,
            "max_inference_time_ms": round(max(inference_times), 2) if inference_times else 0,
            "min_inference_time_ms": round(min(inference_times), 2) if inference_times else 0,
            "predictions_by_class": self.metrics["predictions_by_class"],
            "total_feedback_received": sum(
                1 for p in self.predictions if p.user_feedback is not None
            )
        }
    
    def get_recent_predictions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get most recent predictions."""
        recent = list(self.predictions)[-count:]
        return [asdict(p) for p in recent]
    
    def get_drift_report(self) -> Dict[str, Any]:
        """Get data drift report."""
        recent_drift = self.check_data_drift()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "drift_detected": len(recent_drift) > 0,
            "features_with_drift": [
                {
                    "feature": d.metric_name,
                    "old_mean": round(d.old_mean, 4),
                    "new_mean": round(d.new_mean, 4),
                    "drift_percentage": f"{d.drift_percentage:.2%}",
                    "threshold": f"{d.threshold:.2%}"
                }
                for d in recent_drift
            ],
            "total_predictions_in_window": len(self.predictions),
            "recommendation": (
                "Consider retraining model" if len(recent_drift) > 2
                else "Monitor for further drift" if recent_drift
                else "Model performing normally"
            )
        }
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data."""
        return {
            "performance": self.get_performance_summary(),
            "drift": self.get_drift_report(),
            "recent_predictions": self.get_recent_predictions(5),
            "total_drift_events": len(self.drift_history)
        }


def get_prediction_monitor() -> PredictionMonitor:
    """Get singleton instance of prediction monitor."""
    return PredictionMonitor()
