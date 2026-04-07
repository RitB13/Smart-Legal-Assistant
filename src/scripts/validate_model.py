"""
Quick validation script to verify the trained RandomForest model works correctly
"""

import pickle
import pandas as pd
import json
import os

data_dir = 'src/data/case_outcomes/split_data'
model_dir = 'src/data/case_outcomes/models'

print("\n" + "="*80)
print("[VALIDATION] Verifying trained RandomForest model...")
print("="*80)

try:
    # Load model
    with open(os.path.join(model_dir, 'RandomForest_best_model.pkl'), 'rb') as f:
        model = pickle.load(f)
    print("[OK] Model loaded successfully")
    
    # Load encoders
    with open(os.path.join(model_dir, 'encoders.pkl'), 'rb') as f:
        encoders = pickle.load(f)
    print("[OK] Encoders loaded successfully")
    
    # Load scaler
    with open(os.path.join(model_dir, 'scaler.pkl'), 'rb') as f:
        scaler = pickle.load(f)
    print("[OK] Scaler loaded successfully")
    
    # Load model info
    with open(os.path.join(model_dir, 'RandomForest_model_info.json'), 'r') as f:
        model_info = json.load(f)
    print("[OK] Model info loaded successfully")
    
    # Load test data
    X_test = pd.read_csv(os.path.join(data_dir, 'X_test.csv'))
    y_test = pd.read_csv(os.path.join(data_dir, 'y_test.csv')).values.ravel()
    print(f"[OK] Test data loaded: {X_test.shape}")
    
    # Make predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)
    print(f"[OK] Predictions made on {len(X_test)} test samples")
    
    # Get target encoder
    y_encoder = encoders['target']
    
    print("\n" + "="*80)
    print("[RESULTS] MODEL PERFORMANCE SUMMARY")
    print("="*80 + "\n")
    
    print(f"Model Type: {model_info['model_type']}")
    print(f"Training Date: {model_info['training_date']}")
    
    print("\n--- VALIDATION SET RESULTS ---")
    print(f"  Accuracy: {model_info['validation_results']['accuracy']:.4f}")
    print(f"  F1 Score (weighted): {model_info['validation_results']['f1_weighted']:.4f}")
    print(f"  Balanced Accuracy: {model_info['validation_results']['balanced_accuracy']:.4f}")
    print(f"  Precision (weighted): {model_info['validation_results']['precision_weighted']:.4f}")
    print(f"  Recall (weighted): {model_info['validation_results']['recall_weighted']:.4f}")
    
    print("\n--- TEST SET RESULTS ---")
    print(f"  Accuracy: {model_info['test_results']['accuracy']:.4f}")
    print(f"  F1 Score (weighted): {model_info['test_results']['f1_weighted']:.4f}")
    print(f"  Balanced Accuracy: {model_info['test_results']['balanced_accuracy']:.4f}")
    print(f"  Precision (weighted): {model_info['test_results']['precision_weighted']:.4f}")
    print(f"  Recall (weighted): {model_info['test_results']['recall_weighted']:.4f}")
    
    print(f"\n--- DATASET INFO ---")
    print(f"  Features: {', '.join(model_info['features'])}")
    print(f"  Target Classes: {', '.join(model_info['target_classes'])}")
    print(f"  Training Samples: {model_info['n_training_samples']:,}")
    print(f"  Validation Samples: {model_info['n_validation_samples']:,}")
    print(f"  Test Samples: {model_info['n_test_samples']:,}")
    
    # Test with sample data
    print(f"\n--- SAMPLE PREDICTIONS ---")
    sample_indices = [0, 100, 500, 1000]
    for idx in sample_indices:
        if idx < len(X_test):
            pred_idx = y_pred[idx]
            pred_label = y_encoder.classes_[pred_idx]
            true_idx = y_test[idx]
            true_label = y_encoder.classes_[true_idx]
            confidence = y_proba[idx][pred_idx] * 100
            
            print(f"  Sample {idx}: Predicted={pred_label} ({confidence:.1f}%), True={true_label}")
    
    print("\n" + "="*80)
    print("[SUCCESS] Model validation complete!")
    print("[FILES] Model files location: src/data/case_outcomes/models/")
    print("="*80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] Validation failed: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
