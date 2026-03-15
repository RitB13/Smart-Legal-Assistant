"""
Model Manager Service: Centralized model loading, versioning, and fallback management.

Provides:
1. Model loading at application startup
2. In-memory caching for fast inference
3. Model versioning system
4. Automatic fallback to previous model if new model fails
5. Model metadata and version tracking
"""

import logging
import os
import json
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import joblib
import pickle

logger = logging.getLogger(__name__)


@dataclass
class ModelVersion:
    """Model version information"""
    version_id: str
    created_at: str
    model_path: str
    scaler_path: str
    feature_names_path: str
    metadata_path: str
    accuracy: Optional[float] = None
    f1_score: Optional[float] = None
    is_active: bool = False
    status: str = "ready"  # ready, training, deprecated, failed
    notes: str = ""


class ModelManager:
    """
    Centralized model management for deployment and monitoring.
    
    Responsibilities:
    - Load and cache models in memory
    - Track and manage multiple model versions
    - Provide automatic fallback to previous models
    - Maintain model metadata and performance metrics
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, base_model_dir: str = "src/data/case_outcomes"):
        """
        Initialize model manager.
        
        Args:
            base_model_dir: Base directory containing model versions
        """
        self.base_model_dir = base_model_dir
        self.production_dir = os.path.join(base_model_dir, "production")
        self.versions_dir = os.path.join(base_model_dir, "versions")
        
        # In-memory caches
        self.active_model = None
        self.active_scaler = None
        self.active_feature_names = None
        self.active_metadata = None
        
        # Version tracking
        self.versions: Dict[str, ModelVersion] = {}
        self.current_version: Optional[str] = None
        self.fallback_version: Optional[str] = None
        
        # Performance metrics
        self.prediction_metrics = {
            "total_predictions": 0,
            "last_prediction_time": None,
            "avg_inference_time_ms": 0.0,
            "errors": []
        }
        
        logger.info("ModelManager initialized")
    
    def load_model_at_startup(self) -> bool:
        """
        Load the production model at application startup.
        
        This method:
        1. Discovers available model versions
        2. Loads the latest/active production model
        3. Caches it in memory
        4. Sets up fallback model
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info("PHASE 9 - MODEL SERVING: Loading models at startup")
            logger.info("=" * 60)
            
            # Discover available versions
            self._discover_model_versions()
            
            if not self.versions:
                logger.warning("No model versions found. Attempting to load from production directory...")
                return self._load_production_model()
            
            # Load latest version as primary
            if not self._load_latest_version():
                logger.error("Failed to load latest model version")
                return False
            
            logger.info(f"✓ Model loaded successfully. Current version: {self.current_version}")
            logger.info(f"  - Models in memory: {len(self.versions)} versions available")
            logger.info(f"  - Fallback model: {self.fallback_version if self.fallback_version else 'None'}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to load model at startup: {e}", exc_info=True)
            return False
    
    def _discover_model_versions(self) -> None:
        """Discover all available model versions in the versions directory."""
        if not os.path.exists(self.versions_dir):
            logger.warning(f"Versions directory not found: {self.versions_dir}")
            return
        
        try:
            for version_name in os.listdir(self.versions_dir):
                version_path = os.path.join(self.versions_dir, version_name)
                
                if not os.path.isdir(version_path):
                    continue
                
                # Load version metadata if available
                metadata_file = os.path.join(version_path, "version_info.json")
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        version_data = json.load(f)
                        version = ModelVersion(
                            version_id=version_name,
                            created_at=version_data.get('created_at', ''),
                            model_path=os.path.join(version_path, 'model_final.pkl'),
                            scaler_path=os.path.join(version_path, 'scaler_final.pkl'),
                            feature_names_path=os.path.join(version_path, 'feature_names.json'),
                            metadata_path=os.path.join(version_path, 'model_metadata.pkl'),
                            accuracy=version_data.get('accuracy'),
                            f1_score=version_data.get('f1_score'),
                            status=version_data.get('status', 'ready')
                        )
                        self.versions[version_name] = version
                        logger.debug(f"Discovered model version: {version_name}")
            
            logger.info(f"Found {len(self.versions)} model versions")
            
        except Exception as e:
            logger.error(f"Error discovering model versions: {e}")
    
    def _load_production_model(self) -> bool:
        """Load the production model directly from production folder."""
        try:
            if not os.path.exists(self.production_dir):
                logger.error(f"Production directory not found: {self.production_dir}")
                return False
            
            model_path = os.path.join(self.production_dir, 'model_final.pkl')
            scaler_path = os.path.join(self.production_dir, 'scaler_final.pkl')
            feature_names_path = os.path.join(self.production_dir, 'feature_names.json')
            metadata_path = os.path.join(self.production_dir, 'model_metadata.pkl')
            
            # Check if all required files exist
            required_files = [model_path, scaler_path, feature_names_path, metadata_path]
            for file_path in required_files:
                if not os.path.exists(file_path):
                    logger.error(f"Required file not found: {file_path}")
                    return False
            
            # Load model
            self.active_model = joblib.load(model_path)
            logger.debug(f"✓ Model loaded from {model_path}")
            
            # Load scaler
            self.active_scaler = joblib.load(scaler_path)
            logger.debug(f"✓ Scaler loaded from {scaler_path}")
            
            # Load feature names
            with open(feature_names_path, 'r') as f:
                self.active_feature_names = json.load(f)
            logger.debug(f"✓ Feature names loaded ({len(self.active_feature_names)} features)")
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                self.active_metadata = pickle.load(f)
            logger.debug(f"✓ Metadata loaded")
            
            # Register as a version
            version = ModelVersion(
                version_id="production_v1.0",
                created_at=datetime.utcnow().isoformat(),
                model_path=model_path,
                scaler_path=scaler_path,
                feature_names_path=feature_names_path,
                metadata_path=metadata_path,
                status="ready",
                is_active=True
            )
            self.versions["production_v1.0"] = version
            self.current_version = "production_v1.0"
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load production model: {e}", exc_info=True)
            return False
    
    def _load_latest_version(self) -> bool:
        """Load the latest available model version."""
        if not self.versions:
            return False
        
        try:
            # Sort versions by created_at timestamp
            sorted_versions = sorted(
                self.versions.items(),
                key=lambda x: x[1].created_at,
                reverse=True
            )
            
            # Try to load versions in order
            for version_id, version in sorted_versions:
                if self._load_version(version_id):
                    self.current_version = version_id
                    # Set second-latest as fallback
                    if len(sorted_versions) > 1:
                        self.fallback_version = sorted_versions[1][0]
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading latest version: {e}")
            return False
    
    def _load_version(self, version_id: str) -> bool:
        """
        Load a specific model version into memory.
        
        Args:
            version_id: Version ID to load
            
        Returns:
            True if successfully loaded, False otherwise
        """
        try:
            if version_id not in self.versions:
                logger.error(f"Version not found: {version_id}")
                return False
            
            version = self.versions[version_id]
            
            # Check if all required files exist
            if not all(os.path.exists(path) for path in [
                version.model_path,
                version.scaler_path,
                version.feature_names_path,
                version.metadata_path
            ]):
                logger.error(f"Missing files for version {version_id}")
                return False
            
            # Load components
            self.active_model = joblib.load(version.model_path)
            self.active_scaler = joblib.load(version.scaler_path)
            
            with open(version.feature_names_path, 'r') as f:
                self.active_feature_names = json.load(f)
            
            with open(version.metadata_path, 'rb') as f:
                self.active_metadata = pickle.load(f)
            
            logger.info(f"Loaded version {version_id} into memory")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load version {version_id}: {e}", exc_info=True)
            return False
    
    def try_new_model_with_fallback(self, new_version_id: str) -> bool:
        """
        Try to switch to a new model version with automatic fallback.
        
        This method:
        1. Attempts to load the new version
        2. Runs a quick validation
        3. Switches to new version if successful
        4. Falls back to previous version if loading fails
        
        Args:
            new_version_id: Version ID to try
            
        Returns:
            True if switched successfully or fallback triggered, False if both fail
        """
        try:
            old_version = self.current_version
            
            logger.info(f"Attempting to switch to model version: {new_version_id}")
            
            # Try to load new version
            if not self._load_version(new_version_id):
                logger.error(f"Failed to load new version {new_version_id}")
                
                # Try fallback
                if self.fallback_version:
                    logger.warning(f"Falling back to version: {self.fallback_version}")
                    if self._load_version(self.fallback_version):
                        self.current_version = self.fallback_version
                        logger.info(f"✓ Fallback to {self.fallback_version} successful")
                        return True
                
                return False
            
            # Quick validation (can be extended with actual inference test)
            if self.active_model is None or self.active_scaler is None:
                logger.error("Model validation failed - components not loaded")
                
                # Fallback
                if old_version:
                    logger.warning(f"Falling back to version: {old_version}")
                    self._load_version(old_version)
                    self.current_version = old_version
                
                return False
            
            # Successfully switched
            self.current_version = new_version_id
            self.fallback_version = old_version
            
            logger.info(f"✓ Successfully switched to version {new_version_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in try_new_model_with_fallback: {e}", exc_info=True)
            
            # Final fallback attempt
            if self.fallback_version and self._load_version(self.fallback_version):
                self.current_version = self.fallback_version
                return True
            
            return False
    
    def get_active_model(self):
        """Get the currently active model."""
        return self.active_model
    
    def get_active_scaler(self):
        """Get the currently active scaler."""
        return self.active_scaler
    
    def get_active_feature_names(self):
        """Get the currently active feature names."""
        return self.active_feature_names
    
    def get_active_metadata(self):
        """Get the currently active metadata."""
        return self.active_metadata
    
    def get_current_version(self) -> str:
        """Get current model version ID."""
        return self.current_version or "unknown"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information."""
        current = self.versions.get(self.current_version, {})
        
        return {
            "model_loaded": self.active_model is not None,
            "current_version": self.current_version,
            "fallback_version": self.fallback_version,
            "available_versions": list(self.versions.keys()),
            "model_metadata": self.active_metadata if self.active_metadata else {},
            "feature_count": len(self.active_feature_names) if self.active_feature_names else 0,
            "version_timestamp": getattr(current, 'created_at', 'unknown') if current else 'unknown',
            "prediction_metrics": self.prediction_metrics
        }
    
    def record_prediction(self, inference_time_ms: float, success: bool = True, error_msg: str = None):
        """Record a prediction for monitoring."""
        self.prediction_metrics["total_predictions"] += 1
        self.prediction_metrics["last_prediction_time"] = datetime.utcnow().isoformat()
        
        # Update average inference time
        old_avg = self.prediction_metrics["avg_inference_time_ms"]
        old_count = self.prediction_metrics["total_predictions"] - 1
        new_count = self.prediction_metrics["total_predictions"]
        
        self.prediction_metrics["avg_inference_time_ms"] = (
            (old_avg * old_count + inference_time_ms) / new_count
        )
        
        if not success and error_msg:
            self.prediction_metrics["errors"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "error": error_msg,
                "version": self.current_version
            })
            
            # Keep only last 100 errors
            if len(self.prediction_metrics["errors"]) > 100:
                self.prediction_metrics["errors"] = self.prediction_metrics["errors"][-100:]


def get_model_manager() -> ModelManager:
    """Get singleton instance of model manager."""
    return ModelManager()
