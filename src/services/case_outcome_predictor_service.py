import logging
import json
import pickle
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import uuid
import os

# Try to import ShapExplainer if available
try:
    from shap import TreeExplainer
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP library not available. Explainability features will be limited.")

logger = logging.getLogger(__name__)


def convert_numpy_to_python(obj: Any) -> Any:
    """
    Recursively convert numpy types to Python native types.
    
    This is essential for Pydantic serialization which doesn't handle
    numpy scalars and arrays well.
    
    Args:
        obj: Object to convert (can be dict, list, numpy type, or primitive)
    
    Returns:
        Converted object with all numpy types converted to Python types
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
    Service for predicting legal case outcomes using the trained LightGBM model.
    
    Functionality:
    - Preprocess case input data into feature vectors
    - Make predictions with confidence scores
    - Explain predictions using SHAP values
    - Batch predict multiple cases
    """
    
    # Verdict class mapping
    VERDICT_CLASSES = {
        0: 'Accepted',
        1: 'Acquitted',
        2: 'Convicted',
        3: 'Other',
        4: 'Rejected',
        5: 'Settlement',
        6: 'Unknown'
    }
    
    # Reverse mapping
    VERDICT_TO_ID = {v: k for k, v in VERDICT_CLASSES.items()}
    
    def __init__(self, model_dir: str = "src/data/case_outcomes/production"):
        """
        Initialize the prediction service by loading all model components.
        
        Args:
            model_dir: Directory containing model files
            
        Raises:
            FileNotFoundError: If any model file is missing
            Exception: If model loading fails
        """
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_metadata = None
        self.shap_explainer = None
        
        self._load_model_components()
        self._initialize_shap_explainer()
        
    def _load_model_components(self) -> None:
        """Load all model components from disk."""
        try:
            # Load model
            model_path = os.path.join(self.model_dir, 'model_final.pkl')
            self.model = joblib.load(model_path)
            logger.info(f"✓ Model loaded from {model_path}")
            
            # Load scaler
            scaler_path = os.path.join(self.model_dir, 'scaler_final.pkl')
            self.scaler = joblib.load(scaler_path)
            logger.info(f"✓ Scaler loaded from {scaler_path}")
            
            # Load feature names
            feature_names_path = os.path.join(self.model_dir, 'feature_names.json')
            with open(feature_names_path, 'r') as f:
                self.feature_names = json.load(f)
            logger.info(f"✓ Feature names loaded ({len(self.feature_names)} features)")
            
            # Load metadata
            metadata_path = os.path.join(self.model_dir, 'model_metadata.pkl')
            with open(metadata_path, 'rb') as f:
                self.model_metadata = pickle.load(f)
            logger.info(f"✓ Metadata loaded")
            
        except FileNotFoundError as e:
            logger.error(f"✗ Model file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ Failed to load model components: {e}")
            raise
    
    def _initialize_shap_explainer(self) -> None:
        """Initialize SHAP explainer for model interpretability."""
        if not SHAP_AVAILABLE:
            logger.warning("SHAP not available - explainability features will use fallback")
            return
        
        try:
            # Try to load pre-computed SHAP explainer
            shap_path = os.path.join(self.model_dir, '../evaluation/shap_values.pkl')
            if os.path.exists(shap_path):
                with open(shap_path, 'rb') as f:
                    data = pickle.load(f)
                    # Extract explainer if available
                    if isinstance(data, dict) and 'explainer' in data:
                        self.shap_explainer = data['explainer']
                logger.info("✓ SHAP explainer loaded from disk")
            else:
                logger.info("SHAP explainer not pre-computed, will use TreeExplainer")
        except Exception as e:
            logger.warning(f"Could not load SHAP explainer: {e}")
    
    def preprocess_case_data(
        self, 
        case_dict: Dict[str, Any]
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Preprocess case input data into feature vector.
        
        This function:
        1. Extracts text features from case name
        2. Encodes categorical variables
        3. Creates temporal features
        4. Combines all features in correct order
        5. Applies StandardScaler normalization
        
        Args:
            case_dict: Dictionary containing case information:
                - case_name: str
                - case_type: str
                - year: int
                - jurisdiction_state: str
                - damages_awarded: Optional[float]
                - parties_count: Optional[int]
                - is_appeal: Optional[bool]
        
        Returns:
            Tuple of:
            - feature_vector: np.ndarray of shape (1, 39) - scaled features
            - warnings: List of any preprocessing warnings
        
        Example:
            >>> case = {
            ...     'case_name': 'State v. John Doe',
            ...     'case_type': 'appeal',
            ...     'year': 2023,
            ...     'jurisdiction_state': 'Delhi'
            ... }
            >>> features, warnings = service.preprocess_case_data(case)
            >>> print(features.shape)  # (1, 39)
        """
        warnings = []
        features_dict = {}
        
        try:
            # ===== TEXT FEATURES =====
            case_name = str(case_dict.get('case_name', 'Unknown')).lower()
            
            # Case name length
            features_dict['case_name_length'] = len(case_name)
            
            # Case name word count
            features_dict['case_name_word_count'] = len(case_name.split())
            
            # Keywords in case name
            features_dict['has_state'] = 1 if 'state' in case_name else 0
            features_dict['has_government'] = 1 if 'govt' in case_name or 'government' in case_name else 0
            features_dict['has_vs'] = 1 if ' vs ' in case_name or ' v. ' in case_name else 0
            
            # ===== CATEGORICAL FEATURES =====
            case_type = str(case_dict.get('case_type', 'unknown')).lower()
            
            # One-hot encode case types
            case_types = [
                'appeal', 'criminal_complaint', 'divorce_contested', 'divorce_mutual',
                'dowry_harassment', 'harassment_civil', 'property_dispute', 'writ_petition', 'unknown'
            ]
            for ct in case_types:
                features_dict[f'case_type_{ct}'] = 1 if ct in case_type else 0
            
            # Jurisdiction encoding
            jurisdiction = str(case_dict.get('jurisdiction_state', 'unknown')).lower()
            jurisdictions = ['delhi', 'maharashtra', 'karnataka', 'tamil_nadu', 'uttar_pradesh', 'unknown']
            for j in jurisdictions:
                features_dict[f'jurisdiction_{j}'] = 1 if j in jurisdiction else 0
            
            # ===== TEMPORAL FEATURES =====
            year = int(case_dict.get('year', 2024))
            
            # Validate year
            if year < 1950 or year > 2100:
                warnings.append(f"Case year {year} seems unusual, clamping to valid range")
                year = max(1950, min(2100, year))
            
            features_dict['year'] = year
            
            # Decade
            features_dict['decade'] = (year // 10) * 10
            
            # Time periods
            features_dict['pre_2000'] = 1 if year < 2000 else 0
            features_dict['post_2000'] = 1 if year >= 2000 else 0
            features_dict['post_2010'] = 1 if year >= 2010 else 0
            features_dict['post_2020'] = 1 if year >= 2020 else 0
            features_dict['period_2010_2020'] = 1 if 2010 <= year < 2020 else 0
            
            # ===== DAMAGES & FINANCIAL FEATURES =====
            damages = float(case_dict.get('damages_awarded', 0))
            features_dict['damages_awarded'] = damages
            features_dict['has_damages'] = 1 if damages > 0 else 0
            features_dict['high_damages'] = 1 if damages > 1000000 else 0
            
            # Damages categories
            features_dict['damages_range_0'] = 1 if damages == 0 else 0
            features_dict['damages_range_1'] = 1 if 0 < damages <= 100000 else 0
            features_dict['damages_range_2'] = 1 if 100000 < damages <= 1000000 else 0
            features_dict['damages_range_3'] = 1 if damages > 1000000 else 0
            
            # ===== PARTY & CASE CHARACTERISTICS =====
            parties = int(case_dict.get('parties_count', 2))
            features_dict['party_count'] = parties
            features_dict['is_single_party'] = 1 if parties == 1 else 0
            features_dict['is_multi_party'] = 1 if parties > 2 else 0
            
            is_appeal = case_dict.get('is_appeal', False)
            features_dict['case_type_appeal'] = 1 if is_appeal else 0
            
            # ===== INTERACTION FEATURES =====
            features_dict['case_name_year_interaction'] = features_dict['case_name_length'] * features_dict['year']
            features_dict['case_year_interaction'] = (1 if case_type in ['appeal', 'writ_petition'] else 0) * features_dict['year']
            
            # ===== DATA QUALITY FEATURES =====
            # Count non-null provided fields (for data quality indicator)
            features_dict['data_completeness'] = sum([
                1 if case_dict.get('case_name') else 0,
                1 if case_dict.get('case_type') else 0,
                1 if case_dict.get('year') else 0,
                1 if case_dict.get('jurisdiction_state') else 0,
                1 if case_dict.get('damages_awarded') is not None else 0,
            ]) / 5.0
            
            # ===== SPECIAL CASE VERDICTS (for feature engineering reference) =====
            # Add dummy verdict encoding (all zeros - these are engineered from previous cases)
            for i in range(7):
                features_dict[f'verdict.{i}'] = 0
            
            # ===== CREATE FEATURE VECTOR =====
            # Ensure features are in same order as training
            feature_vector = []
            missing_features = []
            
            for feature_name in self.feature_names:
                if feature_name in features_dict:
                    feature_vector.append(features_dict[feature_name])
                else:
                    logger.warning(f"Missing feature during preprocessing: {feature_name}")
                    missing_features.append(feature_name)
                    feature_vector.append(0)  # Default to 0 for missing features
            
            if missing_features:
                warnings.append(f"Missing {len(missing_features)} features during preprocessing")
            
            # Convert to numpy array and reshape
            feature_array = np.array(feature_vector, dtype=np.float32).reshape(1, -1)
            
            # Apply StandardScaler normalization
            if self.scaler is not None:
                feature_array = self.scaler.transform(feature_array)
            
            logger.info(f"✓ Case preprocessed: {len(self.feature_names)} features extracted")
            return feature_array, warnings
            
        except Exception as e:
            logger.error(f"✗ Error preprocessing case data: {e}")
            raise
    
    def predict_outcome(
        self,
        case_dict: Dict[str, Any],
        return_probabilities: bool = True
    ) -> Dict[str, Any]:
        """
        Predict the outcome of a legal case.
        
        Pipeline:
        1. Preprocess case input
        2. Get model predictions
        3. Extract confidence and probabilities
        4. Assess confidence level
        
        Args:
            case_dict: Case information dictionary
            return_probabilities: Whether to return full probability distribution
        
        Returns:
            Dictionary containing:
            - verdict: Predicted verdict class name
            - verdict_id: Verdict class ID (0-6)
            - probability: Confidence in predicted verdict (0.0-1.0)
            - probabilities: Full distribution across all classes
            - confidence_level: High/Medium/Low assessment
            - warnings: Any preprocessing warnings
        
        Example:
            >>> case = {'case_name': '...', 'case_type': 'appeal', ...}
            >>> result = service.predict_outcome(case)
            >>> print(result['verdict'])  # 'Accepted'
            >>> print(result['probability'])  # 0.87
        """
        try:
            # Preprocess
            feature_vector, warnings = self.preprocess_case_data(case_dict)
            
            # Predict using the model's predict method
            # For this LightGBM model, predict() returns probabilities, not class labels
            try:
                proba = self.model.predict(feature_vector)
                logger.info(f"Model predict output shape: {proba.shape}, dtype: {proba.dtype}")
                
                # Extract probabilities for the first (and only) sample
                sample_proba = proba[0] if len(proba.shape) > 1 else proba
                prediction_idx = np.argmax(sample_proba)
                
                # Convert numpy types to Python types immediately
                if hasattr(prediction_idx, 'item'):
                    verdict_id = int(prediction_idx.item())
                else:
                    verdict_id = int(prediction_idx)
                    
                # Get probability of predicted class
                prob_value = sample_proba[verdict_id]
                if hasattr(prob_value, 'item'):
                    probability = float(prob_value.item())
                else:
                    probability = float(prob_value)
                    
                logger.info(f"Prediction - class: {verdict_id}, probability: {probability}")
                
            except Exception as e:
                logger.error(f"Model prediction error: {e}", exc_info=True)
                raise
            
            # Get verdict name from ID
            verdict = self.VERDICT_CLASSES.get(verdict_id, 'Unknown')
            
            # Assess confidence level
            if probability > 0.8:
                confidence_level = 'very_high'
            elif probability > 0.6:
                confidence_level = 'high'
            elif probability > 0.4:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'
            
            # Build result
            result = {
                'verdict': verdict,
                'verdict_id': verdict_id,
                'probability': probability,
                'confidence_level': confidence_level,
                'warnings': warnings
            }
            
            # Add full probabilities if requested
            if return_probabilities:
                result['probabilities'] = {}
                for i in range(min(len(self.VERDICT_CLASSES), len(sample_proba))):
                    prob_val = sample_proba[i]
                    # Safely extract scalar value from numpy array
                    if hasattr(prob_val, 'item'):
                        result['probabilities'][self.VERDICT_CLASSES[i]] = float(prob_val.item())
                    else:
                        result['probabilities'][self.VERDICT_CLASSES[i]] = float(prob_val)
            
            logger.info(f"✓ Prediction: verdict={verdict}, probability={probability:.2%}")
            # Convert all numpy types to Python types before returning
            return convert_numpy_to_python(result)
            
        except Exception as e:
            logger.error(f"✗ Prediction failed: {e}")
            raise
    
    def explain_prediction(
        self,
        case_dict: Dict[str, Any],
        num_top_features: int = 5
    ) -> Dict[str, Any]:
        """
        Explain a prediction using SHAP values or fallback feature importance.
        
        Method 1 (Preferred): TreeExplainer SHAP values
        - Shows exact contribution of each feature to predicted output
        
        Method 2 (Fallback): Feature importance
        - Shows which features are globally important
        
        Args:
            case_dict: Case information
            num_top_features: Number of top features to return
        
        Returns:
            Dictionary with explanation:
            - method: 'SHAP' or 'FeatureImportance'
            - top_positive_features: Features that increase prediction
            - top_negative_features: Features that decrease prediction
            - summary: Human-readable explanation
        
        Example:
            >>> result = service.explain_prediction(case)
            >>> for feat in result['top_positive_features']:
            ...     print(f"{feat['name']}: +{feat['impact']:.4f}")
        """
        try:
            feature_vector, _ = self.preprocess_case_data(case_dict)
            
            explanation = {
                'method': 'FeatureImportance',  # Default
                'warning': None,
                'top_positive_features': [],
                'top_negative_features': [],
                'summary': ''
            }
            
            # Try SHAP first
            if SHAP_AVAILABLE and self.shap_explainer is not None:
                try:
                    # Get SHAP values
                    shap_values = self.shap_explainer.shap_values(feature_vector)
                    
                    # Get prediction
                    prediction = self.predict_outcome(case_dict, return_probabilities=False)
                    verdict_id = prediction['verdict_id']
                    
                    # Extract feature importance from SHAP
                    shap_feature_importance = np.abs(shap_values[verdict_id][0])
                    
                    # Get top features
                    top_indices = np.argsort(shap_feature_importance)[-num_top_features:][::-1]
                    
                    explanation['method'] = 'SHAP'
                    explanation['top_positive_features'] = [
                        {
                            'feature': self.feature_names[idx],
                            'impact': float(shap_feature_importance[idx]),
                            'value': float(feature_vector[0][idx])
                        }
                        for idx in top_indices
                    ]
                    
                    logger.info("✓ Used SHAP explainer for explanation")
                    
                except Exception as e:
                    logger.warning(f"SHAP explanation failed, falling back to feature importance: {e}")
                    explanation['warning'] = str(e)
            
            # Fallback: Use LightGBM feature importance
            if not explanation['top_positive_features']:
                if hasattr(self.model, 'feature_importance'):
                    importance = self.model.feature_importance(importance_type='gain')
                    top_indices = np.argsort(importance)[-num_top_features:][::-1]
                    
                    explanation['top_positive_features'] = [
                        {
                            'feature': self.feature_names[idx],
                            'importance_score': float(importance[idx]),
                            'value': float(feature_vector[0][idx])
                        }
                        for idx in top_indices if idx < len(self.feature_names)
                    ]
                    
                    explanation['method'] = 'FeatureImportance'
                    logger.info("✓ Used LightGBM feature importance for explanation")
            
            # Generate summary
            if explanation['top_positive_features']:
                top_feat = explanation['top_positive_features'][0]
                explanation['summary'] = (
                    f"The prediction was primarily driven by '{top_feat.get('feature', 'unknown')}'."
                )
            else:
                explanation['summary'] = "Explanation could not be generated due to model limitations."
            
            # Convert all numpy types to Python types before returning
            return convert_numpy_to_python(explanation)
            
        except Exception as e:
            logger.error(f"✗ Explanation generation failed: {e}")
            return {
                'method': 'Error',
                'error': str(e),
                'summary': f"Could not explain prediction: {str(e)}"
            }
    
    def batch_predict(
        self,
        cases_list: List[Dict[str, Any]],
        include_explanations: bool = False,
        include_similar_cases: bool = False
    ) -> Dict[str, Any]:
        """
        Make predictions on multiple cases efficiently.
        
        Args:
            cases_list: List of case dictionaries
            include_explanations: Whether to generate SHAP explanations
            include_similar_cases: Whether to find similar historical cases
        
        Returns:
            Dictionary with batch results:
            - batch_id: Unique batch identifier
            - predictions: List of prediction results
            - failures: List of failed cases
            - summary: Statistics about batch
        
        Example:
            >>> cases = [case1, case2, case3]
            >>> results = service.batch_predict(cases)
            >>> print(f"Success: {results['summary']['successful']}")
        """
        batch_id = str(uuid.uuid4())[:8]
        predictions = []
        failures = []
        start_time = datetime.utcnow()
        
        logger.info(f"Starting batch prediction: {batch_id} ({len(cases_list)} cases)")
        
        for i, case_dict in enumerate(cases_list):
            try:
                # Get prediction
                pred_result = self.predict_outcome(case_dict)
                
                result = {
                    'case_index': i,
                    'case_name': case_dict.get('case_name', f'Case_{i}'),
                    'verdict': pred_result['verdict'],
                    'verdict_id': pred_result['verdict_id'],
                    'probability': pred_result['probability'],
                    'confidence_level': pred_result['confidence_level'],
                }
                
                # Add probabilities
                if 'probabilities' in pred_result:
                    result['verdict_probabilities'] = pred_result['probabilities']
                
                # Add explanation if requested
                if include_explanations:
                    result['explanation'] = self.explain_prediction(case_dict)
                
                # Add similar cases placeholder (would need database)
                if include_similar_cases:
                    result['similar_cases'] = []  # Would query database here
                
                predictions.append(result)
                
            except Exception as e:
                logger.error(f"Batch prediction failed for case {i}: {e}")
                failures.append({
                    'case_index': i,
                    'case_name': case_dict.get('case_name', f'Case_{i}'),
                    'error': str(e)
                })
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        result = {
            'batch_id': batch_id,
            'total_cases': len(cases_list),
            'successful_predictions': len(predictions),
            'failed_predictions': len(failures),
            'predictions': predictions,
            'failures': failures,
            'processing_time_seconds': processing_time,
            'timestamp': start_time.isoformat()
        }
        
        logger.info(
            f"✓ Batch complete: {len(predictions)}/{len(cases_list)} successful, "
            f"{processing_time:.2f}s"
        )
        
        # Convert all numpy types to Python types before returning
        return convert_numpy_to_python(result)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model metadata
        """
        return {
            'model_type': 'LightGBM',
            'model_loaded': self.model is not None,
            'feature_count': len(self.feature_names) if self.feature_names else 0,
            'feature_names': self.feature_names[:5] if self.feature_names else [],  # First 5
            'verdict_classes': self.VERDICT_CLASSES,
            'metadata': self.model_metadata if self.model_metadata else {},
            'shap_available': SHAP_AVAILABLE and self.shap_explainer is not None
        }


# Global service instance
_predictor_service = None


def get_predictor_service() -> CaseOutcomePredictorService:
    """
    Get or create the global predictor service instance.
    Implements lazy loading to avoid loading model at startup.
    
    Returns:
        CaseOutcomePredictorService instance
    """
    global _predictor_service
    
    if _predictor_service is None:
        try:
            logger.info("Initializing Case Outcome Predictor Service...")
            _predictor_service = CaseOutcomePredictorService()
            logger.info("✓ Service initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to initialize predictor service: {e}")
            raise
    
    return _predictor_service
