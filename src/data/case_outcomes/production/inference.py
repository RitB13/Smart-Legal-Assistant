import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

class LegalVerdictPredictor:
    """Production inference for legal verdict prediction"""
    
    def __init__(self, model_path, scaler_path, feature_names_path):
        """Load model and preprocessing objects"""
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        
        with open(feature_names_path) as f:
            self.feature_names = json.load(f)
        
        self.verdict_mapping = {
            0: 'Accepted',
            1: 'Acquitted',
            2: 'Convicted',
            3: 'Other',
            4: 'Rejected',
            5: 'Settlement',
            6: 'Unknown'
        }
    
    def predict(self, features_dict):
        """
        Predict verdict for a single case
        
        Args:
            features_dict: Dictionary with 39 features
            
        Returns:
            dict with verdict, confidence, and probabilities
        """
        # Create feature array in correct order
        X = np.array([features_dict[feat] for feat in self.feature_names]).reshape(1, -1)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        proba = self.model.predict(X_scaled)
        verdict_id = np.argmax(proba[0])
        confidence = proba[0][verdict_id]
        
        result = {
            'verdict': self.verdict_mapping[verdict_id],
            'verdict_id': int(verdict_id),
            'confidence': float(confidence),
            'probabilities': {
                self.verdict_mapping[i]: float(proba[0][i])
                for i in range(7)
            }
        }
        
        return result
    
    def predict_batch(self, df):
        """Predict for multiple cases"""
        X = df[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        proba = self.model.predict(X_scaled)
        
        predictions = []
        for i in range(len(df)):
            verdict_id = np.argmax(proba[i])
            predictions.append({
                'case_id': df.iloc[i].get('case_id', f'case_{i}'),
                'verdict': self.verdict_mapping[verdict_id],
                'confidence': float(proba[i][verdict_id])
            })
        
        return predictions

# Example usage:
if __name__ == "__main__":
    # Initialize predictor
    predictor = LegalVerdictPredictor(
        model_path='model_final.pkl',
        scaler_path='scaler_final.pkl',
        feature_names_path='feature_names.json'
    )
    
    # Example: Predict for a single case
    # features = {...}  # 39 features
    # result = predictor.predict(features)
    # print(result)
