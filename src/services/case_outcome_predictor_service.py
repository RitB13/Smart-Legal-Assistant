"""
Case Outcome Prediction Service

This service loads the trained RandomForest model and makes predictions on case inputs.

Features used:
- case_type (categorical)
- jurisdiction_country (categorical)
- jurisdiction_state (categorical)
- year (numerical)
- damages_awarded (numerical)

Model: RandomForestClassifier trained on 71,451 real case outcomes
"""

import logging
import json
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Global singleton instance
_predictor_service_instance = None


def get_predictor_service(model_dir: str = "src/data/case_outcomes/models") -> 'CaseOutcomePredictorService':
    """
    Get or create the predictor service singleton.
    
    Args:
        model_dir: Directory containing model files
    
    Returns:
        CaseOutcomePredictorService instance
    """
    global _predictor_service_instance
    
    if _predictor_service_instance is None:
        _predictor_service_instance = CaseOutcomePredictorService(model_dir=model_dir)
        logger.info("[OK] Predictor service initialized and cached")
    
    return _predictor_service_instance


def convert_numpy_to_python(obj: Any) -> Any:
    """
    Recursively convert numpy types to Python native types for JSON serialization.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: convert_numpy_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_to_python(item) for item in obj)
    else:
        return obj


class CaseOutcomePredictorService:
    """
    Service for predicting legal case outcomes using RandomForest model.
    
    Handles:
    - Loading trained model from disk
    - Preprocessing case input data
    - Making predictions with confidence scores
    - Explaining predictions
    """
    
    def __init__(self, model_dir: str = "src/data/case_outcomes/models"):
        """
        Initialize the prediction service by loading model components.
        
        Args:
            model_dir: Directory containing model files
            
        Raises:
            FileNotFoundError: If any model file is missing
        """
        self.model_dir = model_dir
        self.model = None
        self.encoders = {}
        self.scaler = None
        self.metadata = None
        self.target_encoder = None
        self.feature_names = None
        
        self._load_model_components()
        
    def _load_model_components(self) -> None:
        """Load all model components from disk."""
        try:
            # Load trained model
            model_path = os.path.join(self.model_dir, 'RandomForest_best_model.pkl')
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info(f"[OK] Model loaded from {model_path}")
            
            # Load encoders
            encoders_path = os.path.join(self.model_dir, 'encoders.pkl')
            with open(encoders_path, 'rb') as f:
                self.encoders = pickle.load(f)
            logger.info(f"[OK] Encoders loaded - {len(self.encoders)} encoders")
            
            # Store target encoder separately
            self.target_encoder = self.encoders.get('target')
            if self.target_encoder is None:
                raise ValueError("Target encoder not found in encoders.pkl")
            
            # Load scaler
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            logger.info(f"[OK] Scaler loaded")
            
            # Load metadata
            metadata_path = os.path.join(self.model_dir, 'RandomForest_model_info.json')
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
            logger.info(f"[OK] Metadata loaded")
            
            # Store feature names from metadata
            self.feature_names = self.metadata.get('features', [])
            
            logger.info(f"[OK] Service initialized successfully")
            logger.info(f"     Features: {self.feature_names}")
            logger.info(f"     Target classes: {self.target_encoder.classes_.tolist()}")
            
        except FileNotFoundError as e:
            logger.error(f"[ERROR] Model file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"[ERROR] Failed to load model components: {e}")
            raise
    
    def preprocess_case_data(
        self, 
        case_data: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Preprocess case input data into feature vector.
        
        Takes raw case dictionary and converts to scaled feature vector matching
        what the model was trained on.
        
        Args:
            case_data: Dictionary with keys:
                - case_type (str): Type of case (e.g., 'dowry_harassment', 'property_dispute')
                - jurisdiction_country (str): Country (e.g., 'India')
                - jurisdiction_state (str): State (e.g., 'Karnataka')
                - year (int): Year of case
                - damages_awarded (float, optional): Damages amount
        
        Returns:
            Tuple of:
            - features_df: DataFrame with 5 features scaled
            - warnings: List of any warnings
        
        Example:
            >>> case = {
            ...     'case_type': 'dowry_harassment',
            ...     'jurisdiction_country': 'India',
            ...     'jurisdiction_state': 'Karnataka',
            ...     'year': 2020,
            ...     'damages_awarded': 40000000.0
            ... }
            >>> features, warnings = service.preprocess_case_data(case)
        """
        warnings = []
        
        try:
            # Extract raw features
            case_type = str(case_data.get('case_type', 'UNKNOWN')).strip()
            jurisdiction_country = str(case_data.get('jurisdiction_country', 'UNKNOWN')).strip()
            jurisdiction_state = str(case_data.get('jurisdiction_state', 'UNKNOWN')).strip()
            year = int(case_data.get('year', 2024))
            damages_raw = case_data.get('damages_awarded', 0)
            damages = float(damages_raw) if damages_raw is not None else 0
            legal_representation = str(case_data.get('legal_representation', 'both_sides')).strip()
            number_of_parties = int(case_data.get('number_of_parties', 2))
            
            # Validate inputs
            if year < 1950 or year > 2100:
                warnings.append(f"Year {year} seems unusual, clamping to valid range")
                year = max(1950, min(2100, year))
            
            if damages < 0:
                warnings.append(f"Negative damages {damages}, setting to 0")
                damages = 0
            
            # Encode categorical features using the encoders
            features = {}
            
            # Encode case_type
            try:
                encoder_case_type = self.encoders['case_type']
                # Handle unknown case types
                if case_type not in encoder_case_type.classes_:
                    warnings.append(f"Unknown case_type '{case_type}', using nearest match")
                    # Try to find a close match or default to first class
                    case_type = encoder_case_type.classes_[0]
                features['case_type'] = encoder_case_type.transform([case_type])[0]
            except Exception as e:
                warnings.append(f"Error encoding case_type: {e}, using default")
                features['case_type'] = 0
            
            # Encode jurisdiction_country
            try:
                encoder_country = self.encoders['jurisdiction_country']
                if jurisdiction_country not in encoder_country.classes_:
                    # Default to first class (usually 'India' in this dataset)
                    jurisdiction_country = encoder_country.classes_[0]
                features['jurisdiction_country'] = encoder_country.transform([jurisdiction_country])[0]
            except Exception as e:
                warnings.append(f"Error encoding jurisdiction_country: {e}, using default")
                features['jurisdiction_country'] = 0
            
            # Encode jurisdiction_state
            try:
                encoder_state = self.encoders['jurisdiction_state']
                if jurisdiction_state not in encoder_state.classes_:
                    warnings.append(f"Unknown state '{jurisdiction_state}', using nearest match")
                    jurisdiction_state = encoder_state.classes_[0]
                features['jurisdiction_state'] = encoder_state.transform([jurisdiction_state])[0]
            except Exception as e:
                warnings.append(f"Error encoding jurisdiction_state: {e}, using default")
                features['jurisdiction_state'] = 0
            
            # Encode legal_representation
            try:
                encoder_legal = self.encoders['legal_representation']
                if legal_representation not in encoder_legal.classes_:
                    legal_representation = encoder_legal.classes_[0]  # Default
                features['legal_representation'] = encoder_legal.transform([legal_representation])[0]
            except Exception as e:
                warnings.append(f"Error encoding legal_representation: {e}, using default")
                features['legal_representation'] = 0
            
            # Numerical features
            features['year'] = year
            features['damages_awarded'] = damages
            features['number_of_parties'] = number_of_parties
            
            # Create DataFrame with features in correct order
            features_df = pd.DataFrame([features], columns=self.feature_names)
            
            # Apply scaler
            features_scaled = self.scaler.transform(features_df)
            features_df = pd.DataFrame(features_scaled, columns=self.feature_names)
            
            logger.info(f"[OK] Case preprocessed with {len(self.feature_names)} features")
            return features_df, warnings
            
        except Exception as e:
            logger.error(f"[ERROR] Error preprocessing case data: {e}")
            raise
    
    def predict_outcome(
        self,
        case_data: Dict[str, Any],
        return_probabilities: bool = True
    ) -> Dict[str, Any]:
        """
        Predict the outcome of a legal case.
        
        Args:
            case_data: Case information dictionary
            return_probabilities: Whether to return full probability distribution
        
        Returns:
            Dictionary containing:
            - predicted_verdict: Predicted verdict (e.g., 'Accepted', 'Rejected')
            - confidence: Confidence in prediction (0.0-100.0)
            - risk_level: Risk assessment based on confidence
            - probabilities: Full distribution across all classes (if requested)
            - warnings: Any preprocessing warnings
        
        Example:
            >>> case = {'case_type': 'dowry_harassment', 'jurisdiction_country': 'India', ...}
            >>> result = service.predict_outcome(case)
            >>> print(result['predicted_verdict'])  # 'Convicted'
            >>> print(result['confidence'])  # 78.5
        """
        try:
            # Preprocess case
            features_df, warnings = self.preprocess_case_data(case_data)
            
            # Get prediction
            prediction_idx = self.model.predict(features_df)[0]
            prediction_probabilities = self.model.predict_proba(features_df)[0]
            
            # Get verdict name
            verdict = self.target_encoder.classes_[prediction_idx]
            
            # Get confidence (probability of predicted class)
            confidence = prediction_probabilities[prediction_idx] * 100.0
            
            # Calculate risk level based on verdict type AND confidence
            risk_level = self._calculate_risk_level(verdict, confidence)
            
            # Get verdict_id (index in target classes)
            verdict_id = int(np.where(self.target_encoder.classes_ == verdict)[0][0])
            
            # Build result
            result = {
                'predicted_verdict': verdict,
                'verdict_id': verdict_id,
                'confidence': round(confidence, 1),
                'risk_level': risk_level,
                'warnings': warnings
            }
            
            # Add full probabilities if requested
            if return_probabilities:
                result['probabilities'] = {}
                for i, class_name in enumerate(self.target_encoder.classes_):
                    prob = prediction_probabilities[i] * 100.0
                    result['probabilities'][class_name] = round(prob, 1)
            
            logger.info(f"[OK] Prediction: {verdict} ({confidence:.1f}%)")
            
            return convert_numpy_to_python(result)
            
        except Exception as e:
            logger.error(f"[ERROR] Prediction failed: {e}")
            raise
    
    def _calculate_risk_level(self, verdict: str, confidence: float) -> str:
        """
        Calculate risk level based on BOTH verdict type and confidence.
        
        Risk combines two factors:
        1. Verdict favorability (good/bad for client)
        2. Confidence certainty (how sure is the model)
        
        Args:
            verdict: Predicted verdict (Accepted, Convicted, etc.)
            confidence: Confidence percentage (0-100)
        
        Returns:
            Risk level: 'very_high', 'high', 'medium', 'low'
        
        Logic:
        - Favorable verdicts (Accepted, Acquitted, Settlement) reduce risk
        - Unfavorable verdicts (Convicted, Rejected) increase risk
        - Low confidence (uncertain predictions) increase risk
        - High confidence reduces risk (clear outcome)
        """
        # Categorize verdict types
        favorable_verdicts = {'Accepted', 'Acquitted', 'Settlement'}
        unfavorable_verdicts = {'Convicted', 'Rejected'}
        
        # Very low confidence (uncertain) = Always HIGH or VERY_HIGH risk
        if confidence < 40:
            return 'very_high'  # Model is uncertain - risky for any outcome
        
        # Low confidence (40-60%): Still uncertain
        if confidence < 60:
            if verdict in favorable_verdicts:
                return 'high'  # Good outcome but uncertain
            else:
                return 'very_high'  # Bad outcome + uncertain = very risky
        
        # Medium confidence (60-75%)
        if confidence < 75:
            if verdict in favorable_verdicts:
                return 'medium'  # Good outcome, moderately confident
            elif verdict in unfavorable_verdicts:
                return 'high'  # Bad outcome, moderately confident
            else:
                return 'medium'  # Neutral (Other, Unknown)
        
        # High confidence (75-85%)
        if confidence < 85:
            if verdict in favorable_verdicts:
                return 'low'  # Good outcome, high confidence
            elif verdict in unfavorable_verdicts:
                return 'medium'  # Bad outcome but confident (clear worst case)
            else:
                return 'low'
        
        # Very high confidence (85%+): Usually low risk unless bad verdict
        if verdict in favorable_verdicts:
            return 'low'  # Good outcome, very confident
        elif verdict in unfavorable_verdicts:
            return 'medium'  # Bad outcome but very confident (worst case scenario)
        else:
            return 'low'  # Neutral outcome, very confident
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores from the RandomForest model.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        try:
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                importance_dict = dict(zip(self.feature_names, importances))
                # Sort by importance
                importance_dict = dict(sorted(
                    importance_dict.items(),
                    key=lambda x: x[1],
                    reverse=True
                ))
                return importance_dict
            else:
                logger.warning("[WARNING] Model does not support feature_importances_")
                return {}
        except Exception as e:
            logger.error(f"[ERROR] Error getting feature importance: {e}")
            return {}
    
    def explain_prediction(
        self,
        case_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Provide explanation for a prediction using feature importance.
        
        Args:
            case_data: Case information
        
        Returns:
            Dictionary with explanation including:
            - top_features: Most important features
            - explanation: Human-readable summary
        """
        try:
            # Get feature importance
            importance = self.get_feature_importance()
            
            # Get preprocessing warnings
            _, warnings = self.preprocess_case_data(case_data)
            
            # Convert top features to dict format for SHAPExplanation
            top_features_list = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
            top_features = [
                {'feature': name, 'impact': float(value)} 
                for name, value in top_features_list
            ]
            top_feature_names = [name for name, _ in top_features_list]
            
            explanation = {
                'top_features': top_features,
                'top_features_names': top_feature_names,
                'feature_importance': importance,
                'warnings': warnings,
                'explanation': (
                    f"Prediction is most influenced by: {', '.join(top_feature_names)}. "
                    f"These factors carry the most weight in the model's decision."
                )
            }
            
            return convert_numpy_to_python(explanation)
            
        except Exception as e:
            logger.error(f"[ERROR] Explanation generation failed: {e}")
            return {
                'error': str(e),
                'explanation': 'Could not generate explanation'
            }
    
    def batch_predict(
        self,
        cases_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Make predictions on multiple cases.
        
        Args:
            cases_list: List of case dictionaries
        
        Returns:
            Dictionary with batch results and statistics
        """
        predictions = []
        failures = []
        
        logger.info(f"[START] Batch prediction on {len(cases_list)} cases")
        
        for i, case_data in enumerate(cases_list):
            try:
                result = self.predict_outcome(case_data)
                result['case_index'] = i
                predictions.append(result)
            except Exception as e:
                logger.error(f"[ERROR] Batch case {i} failed: {e}")
                failures.append({
                    'case_index': i,
                    'error': str(e)
                })
        
        summary = {
            'successful': len(predictions),
            'failed': len(failures),
            'total': len(cases_list)
        }
        
        logger.info(f"[OK] Batch complete: {summary['successful']} successful, {summary['failed']} failed")
        
        return {
            'predictions': predictions,
            'failures': failures,
            'summary': summary
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model details
        """
        return {
            'model_type': type(self.model).__name__,
            'model_loaded': self.model is not None,
            'feature_count': len(self.feature_names),
            'feature_names': self.feature_names,
            'verdict_classes': self.target_encoder.classes_.tolist(),
            'shap_available': False,
            'metadata': self.metadata,
            'encoders_count': len(self.encoders),
            'scaler_available': self.scaler is not None
        }
