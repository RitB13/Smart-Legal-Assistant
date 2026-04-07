"""
Model Training Script for Case Outcome Prediction

This script:
1. Loads prepared data splits
2. Trains multiple models with proper evaluation
3. Handles class imbalance using appropriate techniques
4. Evaluates on validation and test sets
5. Selects and saves the best model
6. Generates detailed performance reports
"""

import os
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    balanced_accuracy_score, confusion_matrix, classification_report,
    roc_auc_score, roc_curve
)
import matplotlib.pyplot as plt
import seaborn as sns

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    
try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


class CaseOutcomeModelTrainer:
    def __init__(self, data_dir='src/data/case_outcomes/split_data',
                 model_dir='src/data/case_outcomes/models',
                 output_dir='src/data/case_outcomes/training_reports'):
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.output_dir = output_dir
        
        # Create directories if needed
        Path(self.model_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        self.models = {}
        self.results = {}
        self.best_model = None
        self.best_model_name = None
        self.encoders = None
        self.scaler = None
        self.metadata = None
        self.y_encoder = None
        
    def load_data(self):
        """Load all prepared data splits."""
        print("\n[LOADING] Prepared data splits...")
        
        # Load features
        self.X_train = pd.read_csv(os.path.join(self.data_dir, 'X_train.csv'))
        self.X_val = pd.read_csv(os.path.join(self.data_dir, 'X_val.csv'))
        self.X_test = pd.read_csv(os.path.join(self.data_dir, 'X_test.csv'))
        
        # Load targets
        self.y_train = pd.read_csv(os.path.join(self.data_dir, 'y_train.csv')).values.ravel()
        self.y_val = pd.read_csv(os.path.join(self.data_dir, 'y_val.csv')).values.ravel()
        self.y_test = pd.read_csv(os.path.join(self.data_dir, 'y_test.csv')).values.ravel()
        
        # Load encoders and scaler
        with open(os.path.join(self.data_dir, 'encoders.pkl'), 'rb') as f:
            self.encoders = pickle.load(f)
        
        with open(os.path.join(self.data_dir, 'scaler.pkl'), 'rb') as f:
            self.scaler = pickle.load(f)
        
        with open(os.path.join(self.data_dir, 'metadata.json'), 'r') as f:
            self.metadata = json.load(f)
        
        # Store target encoder for later use
        self.y_encoder = self.encoders['target']
        
        print(f"   [OK] X_train: {self.X_train.shape}")
        print(f"   [OK] X_val:   {self.X_val.shape}")
        print(f"   [OK] X_test:  {self.X_test.shape}")
        print(f"   [OK] Encoders loaded: {list(self.encoders.keys())}")
        print(f"   [OK] Target classes: {self.y_encoder.classes_.tolist()}")
        
    def build_models(self):
        """Build multiple models with appropriate configurations for imbalanced data."""
        print("\n[BUILDING] Models...")
        
        # 1. Logistic Regression with class weights
        print("   Building: Logistic Regression (balanced class weights)...")
        self.models['LogisticRegression'] = LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        
        # 2. Random Forest with class weights
        print("   Building: Random Forest (balanced class weights)...")
        self.models['RandomForest'] = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1,
            verbose=0
        )
        
        # 3. Gradient Boosting
        print("   Building: Gradient Boosting...")
        self.models['GradientBoosting'] = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            min_samples_split=10,
            subsample=0.8,
            random_state=42
        )
        
        # 4. XGBoost (if available)
        if HAS_XGBOOST:
            print("   Building: XGBoost...")
            # Calculate scale_pos_weight for imbalanced classes
            neg, pos = np.bincount(self.y_train)
            scale_pos_weight = neg / pos if pos > 0 else 1
            
            self.models['XGBoost'] = xgb.XGBClassifier(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                eval_metric='mlogloss'
            )
        
        # 5. LightGBM (if available)
        if HAS_LIGHTGBM:
            print("   Building: LightGBM...")
            self.models['LightGBM'] = lgb.LGBMClassifier(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=7,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )
        
        print(f"   [OK] {len(self.models)} models built")
        return list(self.models.keys())
    
    def train_models(self):
        """Train all models."""
        print("\n[TRAINING] Models...")
        
        for model_name, model in self.models.items():
            print(f"\n   Training: {model_name}...", end=" ")
            try:
                model.fit(self.X_train, self.y_train)
                print("[OK]")
            except Exception as e:
                print(f"[ERROR] {str(e)}")
                del self.models[model_name]
    
    def evaluate_model(self, model, model_name, X_set, y_set, set_name='Validation'):
        """Evaluate a single model on a dataset."""
        y_pred = model.predict(X_set)
        y_proba = model.predict_proba(X_set)
        
        results = {
            'set': set_name,
            'accuracy': accuracy_score(y_set, y_pred),
            'balanced_accuracy': balanced_accuracy_score(y_set, y_pred),
            'precision_weighted': precision_score(y_set, y_pred, average='weighted', zero_division=0),
            'recall_weighted': recall_score(y_set, y_pred, average='weighted', zero_division=0),
            'f1_weighted': f1_score(y_set, y_pred, average='weighted', zero_division=0),
            'precision_macro': precision_score(y_set, y_pred, average='macro', zero_division=0),
            'recall_macro': recall_score(y_set, y_pred, average='macro', zero_division=0),
            'f1_macro': f1_score(y_set, y_pred, average='macro', zero_division=0),
            'y_pred': y_pred,
            'y_proba': y_proba,
            'confusion_matrix': confusion_matrix(y_set, y_pred)
        }
        
        return results
    
    def validate_and_test_models(self):
        """Evaluate all models on validation and test sets."""
        print("\n[EVALUATING] Models on validation and test sets...")
        
        for model_name, model in self.models.items():
            print(f"\n   {model_name}:")
            
            # Validate
            val_results = self.evaluate_model(model, model_name, self.X_val, self.y_val, 'Validation')
            
            # Test
            test_results = self.evaluate_model(model, model_name, self.X_test, self.y_test, 'Test')
            
            self.results[model_name] = {
                'validation': val_results,
                'test': test_results
            }
            
            print(f"      Validation - Accuracy: {val_results['accuracy']:.4f}, F1 (weighted): {val_results['f1_weighted']:.4f}, Balanced Acc: {val_results['balanced_accuracy']:.4f}")
            print(f"      Test       - Accuracy: {test_results['accuracy']:.4f}, F1 (weighted): {test_results['f1_weighted']:.4f}, Balanced Acc: {test_results['balanced_accuracy']:.4f}")
    
    def select_best_model(self):
        """Select best model based on validation F1 score (weighted)."""
        print("\n[SELECTING] Best model...")
        
        best_f1 = -1
        best_name = None
        
        for model_name, results in self.results.items():
            val_f1 = results['validation']['f1_weighted']
            print(f"   {model_name}: F1 = {val_f1:.4f}")
            
            if val_f1 > best_f1:
                best_f1 = val_f1
                best_name = model_name
        
        self.best_model_name = best_name
        self.best_model = self.models[best_name]
        
        print(f"\n   [OK] Best Model: {self.best_model_name}")
        print(f"   [OK] Validation F1 Score: {best_f1:.4f}")
        
        return self.best_model_name
    
    def save_best_model(self):
        """Save the best model and associated artifacts."""
        print("\n[SAVING] Best model and artifacts...")
        
        # Save model
        model_path = os.path.join(self.model_dir, f'{self.best_model_name}_best_model.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(self.best_model, f)
        print(f"   [OK] Model saved: {model_path}")
        
        # Save model info
        model_info = {
            'model_name': self.best_model_name,
            'model_type': type(self.best_model).__name__,
            'training_date': datetime.now().isoformat(),
            'validation_results': {
                'accuracy': float(self.results[self.best_model_name]['validation']['accuracy']),
                'balanced_accuracy': float(self.results[self.best_model_name]['validation']['balanced_accuracy']),
                'f1_weighted': float(self.results[self.best_model_name]['validation']['f1_weighted']),
                'precision_weighted': float(self.results[self.best_model_name]['validation']['precision_weighted']),
                'recall_weighted': float(self.results[self.best_model_name]['validation']['recall_weighted']),
            },
            'test_results': {
                'accuracy': float(self.results[self.best_model_name]['test']['accuracy']),
                'balanced_accuracy': float(self.results[self.best_model_name]['test']['balanced_accuracy']),
                'f1_weighted': float(self.results[self.best_model_name]['test']['f1_weighted']),
                'precision_weighted': float(self.results[self.best_model_name]['test']['precision_weighted']),
                'recall_weighted': float(self.results[self.best_model_name]['test']['recall_weighted']),
            },
            'features': self.metadata['feature_names'],
            'target_classes': self.metadata['target_classes'],
            'n_training_samples': len(self.X_train),
            'n_validation_samples': len(self.X_val),
            'n_test_samples': len(self.X_test),
        }
        
        info_path = os.path.join(self.model_dir, f'{self.best_model_name}_model_info.json')
        with open(info_path, 'w') as f:
            json.dump(model_info, f, indent=2)
        print(f"   [OK] Model info saved: {info_path}")
        
        # Copy encoders and scaler
        encoders_path_dest = os.path.join(self.model_dir, 'encoders.pkl')
        scaler_path_dest = os.path.join(self.model_dir, 'scaler.pkl')
        
        with open(encoders_path_dest, 'wb') as f:
            pickle.dump(self.encoders, f)
        with open(scaler_path_dest, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        print(f"   [OK] Encoders and scaler saved to model directory")
    
    def generate_detailed_report(self):
        """Generate comprehensive training report."""
        print("\n[REPORT] Generating detailed report...")
        
        dataset_stats = [
            "=" * 80,
            "CASE OUTCOME PREDICTION MODEL - TRAINING REPORT",
            "=" * 80,
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "",
            "DATASET OVERVIEW",
            "-" * 80,
            f"Training samples:   {len(self.X_train):,}",
            f"Validation samples: {len(self.X_val):,}",
            f"Test samples:       {len(self.X_test):,}",
            f"Total samples:      {len(self.X_train) + len(self.X_val) + len(self.X_test):,}",
            f"\nFeatures ({len(self.metadata['feature_names'])}):",
        ]
        
        for feat in self.metadata['feature_names']:
            dataset_stats.append(f"  - {feat}")
        
        dataset_stats.append(f"\nTarget classes ({len(self.metadata['target_classes'])}):")
        for cls in self.metadata['target_classes']:
            dataset_stats.append(f"  - {cls}")
        
        dataset_stats.append(f"\nTarget distribution in training set:")
        unique, counts = np.unique(self.y_train, return_counts=True)
        for cls_idx, count in zip(unique, counts):
            cls_name = self.y_encoder.classes_[cls_idx]
            pct = count / len(self.y_train) * 100
            dataset_stats.append(f"  {cls_name}: {count:,} ({pct:.1f}%)")
        
        report = dataset_stats
        
        report.append("")
        report.append("=" * 80)
        report.append("MODEL COMPARISON")
        report.append("=" * 80)
        
        comparison_data = []
        for model_name in self.results.keys():
            val_results = self.results[model_name]['validation']
            test_results = self.results[model_name]['test']
            comparison_data.append({
                'Model': model_name,
                'Val_Acc': val_results['accuracy'],
                'Val_F1': val_results['f1_weighted'],
                'Val_Bal_Acc': val_results['balanced_accuracy'],
                'Test_Acc': test_results['accuracy'],
                'Test_F1': test_results['f1_weighted'],
                'Test_Bal_Acc': test_results['balanced_accuracy'],
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        report.append("")
        report.append(comparison_df.to_string(index=False))
        
        # Best Model Details
        report.append("")
        report.append("=" * 80)
        report.append(f"BEST MODEL: {self.best_model_name}")
        report.append("=" * 80)
        
        best_results = self.results[self.best_model_name]
        
        report.append("\nValidation Set Performance:")
        report.append(f"  Accuracy:           {best_results['validation']['accuracy']:.4f}")
        report.append(f"  Balanced Accuracy:  {best_results['validation']['balanced_accuracy']:.4f}")
        report.append(f"  Precision (weighted): {best_results['validation']['precision_weighted']:.4f}")
        report.append(f"  Recall (weighted):  {best_results['validation']['recall_weighted']:.4f}")
        report.append(f"  F1 Score (weighted): {best_results['validation']['f1_weighted']:.4f}")
        report.append(f"  F1 Score (macro):   {best_results['validation']['f1_macro']:.4f}")
        
        report.append("\nTest Set Performance:")
        report.append(f"  Accuracy:           {best_results['test']['accuracy']:.4f}")
        report.append(f"  Balanced Accuracy:  {best_results['test']['balanced_accuracy']:.4f}")
        report.append(f"  Precision (weighted): {best_results['test']['precision_weighted']:.4f}")
        report.append(f"  Recall (weighted):  {best_results['test']['recall_weighted']:.4f}")
        report.append(f"  F1 Score (weighted): {best_results['test']['f1_weighted']:.4f}")
        report.append(f"  F1 Score (macro):   {best_results['test']['f1_macro']:.4f}")
        
        # Detailed Classification Report
        report.append("")
        report.append("=" * 80)
        report.append("DETAILED CLASSIFICATION REPORT (Test Set)")
        report.append("=" * 80)
        
        y_pred = best_results['test']['y_pred']
        report.append("")
        report.append(classification_report(
            self.y_test, y_pred,
            target_names=self.y_encoder.classes_
        ))
        
        # Confusion Matrix
        report.append("")
        report.append("=" * 80)
        report.append("CONFUSION MATRIX (Test Set)")
        report.append("=" * 80 + "\n")
        
        cm = best_results['test']['confusion_matrix']
        cm_df = pd.DataFrame(
            cm,
            index=[f"True_{cls}" for cls in self.y_encoder.classes_],
            columns=[f"Pred_{cls}" for cls in self.y_encoder.classes_]
        )
        report.append(cm_df.to_string())
        
        # Model Configuration
        report.append("")
        report.append("=" * 80)
        report.append("MODEL CONFIGURATION")
        report.append("=" * 80)
        report.append(f"\nModel Type: {type(self.best_model).__name__}")
        report.append(f"\nHyperparameters:")
        for param, value in self.best_model.get_params().items():
            report.append(f"  {param}: {value}")
        
        # Save report
        report_path = os.path.join(self.output_dir, 'training_report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"   [OK] Report saved: {report_path}")
        
        # Also print to console
        print("\n" + "\n".join(report))
        
        return '\n'.join(report)
    
    def generate_visualizations(self):
        """Generate visualization plots."""
        print("\n[VISUALIZATIONS] Generating plots...")
        
        best_results = self.results[self.best_model_name]
        
        # 1. Confusion Matrix Heatmap
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        
        for idx, (set_name, set_results) in enumerate([
            ('Validation', best_results['validation']),
            ('Test', best_results['test'])
        ]):
            cm = set_results['confusion_matrix']
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[idx],
                       xticklabels=self.y_encoder.classes_,
                       yticklabels=self.y_encoder.classes_)
            axes[idx].set_title(f'Confusion Matrix - {set_name} Set')
            axes[idx].set_ylabel('True Label')
            axes[idx].set_xlabel('Predicted Label')
        
        plt.tight_layout()
        cm_path = os.path.join(self.output_dir, 'confusion_matrices.png')
        plt.savefig(cm_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"   [OK] Confusion matrices saved: {cm_path}")
        
        # 2. Model Comparison Bar Chart
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        metrics = ['accuracy', 'f1_weighted', 'balanced_accuracy']
        metric_labels = ['Accuracy', 'F1 Score (Weighted)', 'Balanced Accuracy']
        
        for idx, (metric, label) in enumerate(zip(metrics, metric_labels)):
            model_names = []
            val_scores = []
            test_scores = []
            
            for model_name in self.results.keys():
                model_names.append(model_name)
                val_scores.append(self.results[model_name]['validation'][metric])
                test_scores.append(self.results[model_name]['test'][metric])
            
            x = np.arange(len(model_names))
            width = 0.35
            
            axes[idx].bar(x - width/2, val_scores, width, label='Validation', alpha=0.8)
            axes[idx].bar(x + width/2, test_scores, width, label='Test', alpha=0.8)
            axes[idx].set_ylabel(label)
            axes[idx].set_title(label)
            axes[idx].set_xticks(x)
            axes[idx].set_xticklabels(model_names, rotation=45, ha='right')
            axes[idx].legend()
            axes[idx].set_ylim([0, 1])
        
        plt.tight_layout()
        comparison_path = os.path.join(self.output_dir, 'model_comparison.png')
        plt.savefig(comparison_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"   [OK] Model comparison chart saved: {comparison_path}")
        
        # 3. Feature Importance (if available)
        if hasattr(self.best_model, 'feature_importances_'):
            importances = self.best_model.feature_importances_
            feature_names = self.metadata['feature_names']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            sorted_idx = np.argsort(importances)
            ax.barh(range(len(sorted_idx)), importances[sorted_idx])
            ax.set_yticklabels([feature_names[i] for i in sorted_idx])
            ax.set_xlabel('Importance')
            ax.set_title(f'Feature Importance - {self.best_model_name}')
            plt.tight_layout()
            
            importance_path = os.path.join(self.output_dir, 'feature_importance.png')
            plt.savefig(importance_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"   [OK] Feature importance chart saved: {importance_path}")
    
    def run(self):
        """Execute the complete training pipeline."""
        print("\n" + "="*80)
        print("[START] CASE OUTCOME MODEL TRAINING PIPELINE")
        print("="*80)
        
        try:
            # Step 1: Load data
            self.load_data()
            
            # Step 2: Build models
            model_names = self.build_models()
            
            # Step 3: Train models
            self.train_models()
            
            # Step 4: Evaluate models
            self.validate_and_test_models()
            
            # Step 5: Select best model
            self.select_best_model()
            
            # Step 6: Save best model
            self.save_best_model()
            
            # Step 7: Generate report
            self.generate_detailed_report()
            
            # Step 8: Generate visualizations
            self.generate_visualizations()
            
            print("\n" + "="*80)
            print("[SUCCESS] MODEL TRAINING COMPLETE!")
            print("="*80)
            print(f"\n[BEST] Model: {self.best_model_name}")
            print(f"[FILES] Model saved to: src/data/case_outcomes/models/")
            print(f"[REPORTS] Reports saved to: src/data/case_outcomes/training_reports/")
            print("\n" + "="*80 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Error during model training: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    trainer = CaseOutcomeModelTrainer(
        data_dir='src/data/case_outcomes/split_data',
        model_dir='src/data/case_outcomes/models',
        output_dir='src/data/case_outcomes/training_reports'
    )
    success = trainer.run()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
