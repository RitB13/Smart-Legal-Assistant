"""
Data Preparation Script for Case Outcome Prediction Model

This script:
1. Loads raw case data from CSV
2. Performs feature engineering
3. Handles missing values and encoding
4. Splits data into train/test/validation sets
5. Saves processed data and encoders for model training and prediction
"""

import os
import pandas as pd
import numpy as np
import pickle
import json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from pathlib import Path


class CaseOutcomeDataPreparation:
    def __init__(self, input_file='src/data/case_outcomes/cleaned_dataset.csv', 
                 output_dir='src/data/case_outcomes/split_data'):
        self.input_file = input_file
        self.output_dir = output_dir
        self.encoders = {}
        self.scaler = None
        self.feature_names = None
        
        # Create output directory if needed
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
    def load_data(self):
        """Load and display basic statistics about the dataset."""
        print(f"\n📥 Loading data from {self.input_file}...")
        df = pd.read_csv(self.input_file)
        print(f"✓ Loaded {len(df):,} cases with {len(df.columns)} columns")
        print(f"\nColumns: {df.columns.tolist()}")
        print(f"\nData types:\n{df.dtypes}")
        print(f"\nMissing values:\n{df.isnull().sum()}")
        print(f"\nTarget variable (verdict) distribution:\n{df['verdict'].value_counts()}")
        return df
    
    def feature_engineering(self, df):
        """
        Engineer features from raw data.
        
        Features created:
        - Categorical: case_type, jurisdiction_country, jurisdiction_state, legal_representation (encoded)
        - Numerical: year, damages_awarded, number_of_parties
        - Derived: case complexity indicators
        """
        print("\n🔧 Feature Engineering...")
        df_features = df.copy()
        
        # 1. Infer legal_representation and number_of_parties from case patterns
        df_features['legal_representation'] = df_features['case_type'].apply(self._infer_legal_representation)
        df_features['number_of_parties'] = df_features['case_type'].apply(self._infer_number_of_parties)
        
        # 2. Extract features we'll use
        features_to_use = ['case_type', 'jurisdiction_country', 'jurisdiction_state', 'year', 'damages_awarded', 'legal_representation', 'number_of_parties']
        
        # Create feature dataframe
        X = df_features[features_to_use].copy()
        
        # Get target variable
        y = df_features['verdict'].copy()
        
        print(f"   Features selected: {features_to_use}")
        print(f"\n   Before handling missing values:")
        print(f"   {X.isnull().sum()}")
        
        # 3. Handle missing values
        X['damages_awarded'] = X['damages_awarded'].fillna(X['damages_awarded'].median())
        
        print(f"\n   After handling missing values:")
        print(f"   {X.isnull().sum()}")
        
        # 4. Encode categorical features
        categorical_cols = ['case_type', 'jurisdiction_country', 'jurisdiction_state', 'legal_representation']
        for col in categorical_cols:
            le = LabelEncoder()
            # Handle any remaining missing values
            X[col] = X[col].fillna('UNKNOWN')
            X[col] = le.fit_transform(X[col].astype(str))
            self.encoders[col] = le
            print(f"   ✓ Encoded {col}: {len(le.classes_)} unique values")
        
        # 5. Encode target variable (y)
        le_target = LabelEncoder()
        y_encoded = le_target.fit_transform(y)
        self.encoders['target'] = le_target
        print(f"   ✓ Encoded target (verdict): {le_target.classes_.tolist()}")
        
        self.feature_names = X.columns.tolist()
        
        return X, y_encoded, le_target
    
    def _infer_legal_representation(self, case_type):
        """Infer legal representation based on case type."""
        case_type = str(case_type).lower()
        
        # High representation cases
        if any(x in case_type for x in ['appeal', 'petition', 'writ', 'transfer']):
            return 'both_sides'  # Appeals usually have both sides represented
        elif any(x in case_type for x in ['criminal', 'dowry', 'harassment']):
            return 'both_sides'  # Criminal cases usually have counsel
        elif any(x in case_type for x in ['divorce', 'property']):
            return 'both_sides'  # Civil disputes usually have counsel
        else:
            return 'partial'  # Default to partial representation
    
    def _infer_number_of_parties(self, case_type):
        """Infer number of parties based on case type."""
        case_type = str(case_type).lower()
        
        # Multi-party cases
        if any(x in case_type for x in ['class action', 'multi-party']):
            return 3
        # Standard two-party cases
        elif any(x in case_type for x in ['divorce', 'property', 'contract', 'criminal', 'dowry', 'harassment']):
            return 2
        # Petition/appeal (usually involves state)
        elif any(x in case_type for x in ['petition', 'writ', 'appeal', 'election']):
            return 2
        else:
            return 2  # Default to 2
    
    def split_data(self, X, y, test_size=0.15, validation_size=0.1, random_state=42):
        """
        Split data into train, validation, and test sets.
        
        - Train: 75% (used for model training)
        - Validation: 10% (used for hyperparameter tuning)
        - Test: 15% (held out for final evaluation)
        """
        print("\n✂️  Splitting data...")
        
        # First split: separate test set (15%)
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            stratify=y
        )
        
        # Second split: separate validation from train
        # validation_size relative to remaining data
        val_size_relative = validation_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=val_size_relative,
            random_state=random_state,
            stratify=y_temp
        )
        
        print(f"   Training set:   {len(X_train):,} samples ({len(X_train)/len(X)*100:.1f}%)")
        print(f"   Validation set: {len(X_val):,} samples ({len(X_val)/len(X)*100:.1f}%)")
        print(f"   Test set:       {len(X_test):,} samples ({len(X_test)/len(X)*100:.1f}%)")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def scale_features(self, X_train, X_val, X_test):
        """Scale numerical features using StandardScaler."""
        print("\n📊 Scaling features...")
        
        self.scaler = StandardScaler()
        
        # Fit on training data only, then transform all sets
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Convert back to DataFrames to preserve column names
        X_train_scaled = pd.DataFrame(X_train_scaled, columns=self.feature_names, index=X_train.index)
        X_val_scaled = pd.DataFrame(X_val_scaled, columns=self.feature_names, index=X_val.index)
        X_test_scaled = pd.DataFrame(X_test_scaled, columns=self.feature_names, index=X_test.index)
        
        print(f"   ✓ Features scaled using StandardScaler")
        print(f"   ✓ Fit on training data, transformed all sets")
        
        return X_train_scaled, X_val_scaled, X_test_scaled
    
    def save_splits(self, X_train, X_val, X_test, y_train, y_val, y_test, y_encoder):
        """Save all data splits and metadata to disk."""
        print("\n💾 Saving data splits...")
        
        output_files = {
            'X_train.csv': (X_train, 'features'),
            'X_val.csv': (X_val, 'features'),
            'X_test.csv': (X_test, 'features'),
            'y_train.csv': (pd.DataFrame(y_train, columns=['verdict']), 'target'),
            'y_val.csv': (pd.DataFrame(y_val, columns=['verdict']), 'target'),
            'y_test.csv': (pd.DataFrame(y_test, columns=['verdict']), 'target'),
        }
        
        for filename, (data, dtype) in output_files.items():
            filepath = os.path.join(self.output_dir, filename)
            data.to_csv(filepath, index=False)
            print(f"   ✓ {filename:<15} ({dtype}): {len(data):,} samples")
        
        # Save encoders
        encoders_path = os.path.join(self.output_dir, 'encoders.pkl')
        with open(encoders_path, 'wb') as f:
            pickle.dump(self.encoders, f)
        print(f"   ✓ encoders.pkl: {len(self.encoders)} encoders saved")
        
        # Save scaler
        scaler_path = os.path.join(self.output_dir, 'scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        print(f"   ✓ scaler.pkl: StandardScaler saved")
        
        # Save metadata
        metadata = {
            'feature_names': self.feature_names,
            'train_size': len(X_train),
            'val_size': len(X_val),
            'test_size': len(X_test),
            'n_features': len(self.feature_names),
            'target_classes': y_encoder.classes_.tolist(),
            'categorical_features': ['case_type', 'jurisdiction_country', 'jurisdiction_state'],
            'numerical_features': ['year', 'damages_awarded']
        }
        metadata_path = os.path.join(self.output_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"   ✓ metadata.json: Dataset metadata saved")
    
    def generate_summary_report(self, X_train, X_val, X_test, y_train, y_val, y_test, y_encoder):
        """Generate a summary report of the data preparation."""
        print("\n" + "="*70)
        print("📋 DATA PREPARATION SUMMARY REPORT")
        print("="*70)
        
        print(f"\n📊 Dataset Statistics:")
        print(f"   Total samples: {len(X_train) + len(X_val) + len(X_test):,}")
        print(f"   Total features: {len(self.feature_names)}")
        print(f"   Target classes: {len(y_encoder.classes_)}")
        print(f"   Class labels: {y_encoder.classes_.tolist()}")
        
        print(f"\n🎯 Target Distribution:")
        for i, class_label in enumerate(y_encoder.classes_):
            train_count = (y_train == i).sum()
            val_count = (y_val == i).sum()
            test_count = (y_test == i).sum()
            print(f"   {class_label}:")
            print(f"      Train: {train_count:,} ({train_count/len(y_train)*100:.1f}%)")
            print(f"      Val:   {val_count:,} ({val_count/len(y_val)*100:.1f}%)")
            print(f"      Test:  {test_count:,} ({test_count/len(y_test)*100:.1f}%)")
        
        print(f"\n📁 Features ({len(self.feature_names)}):")
        for feat in self.feature_names:
            print(f"   - {feat}")
        
        print(f"\n📦 Output Files:")
        for filename in ['X_train.csv', 'X_val.csv', 'X_test.csv', 
                         'y_train.csv', 'y_val.csv', 'y_test.csv',
                         'encoders.pkl', 'scaler.pkl', 'metadata.json']:
            filepath = os.path.join(self.output_dir, filename)
            if os.path.exists(filepath):
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                print(f"   ✓ {filename:<20} ({size_mb:.2f} MB)")
            else:
                print(f"   ✗ {filename:<20} (NOT FOUND)")
        
        print("\n" + "="*70)
        print("✅ Data preparation complete!")
        print("="*70 + "\n")
    
    def run(self):
        """Execute the complete data preparation pipeline."""
        print("\n" + "="*70)
        print("🚀 CASE OUTCOME DATA PREPARATION PIPELINE")
        print("="*70)
        
        try:
            # Step 1: Load data
            df = self.load_data()
            
            # Step 2: Feature engineering
            X, y_encoded, y_encoder = self.feature_engineering(df)
            
            # Step 3: Split data
            X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(X, y_encoded)
            
            # Step 4: Scale features
            X_train_scaled, X_val_scaled, X_test_scaled = self.scale_features(X_train, X_val, X_test)
            
            # Step 5: Save splits
            self.save_splits(X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test, y_encoder)
            
            # Step 6: Generate report
            self.generate_summary_report(X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test, y_encoder)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error during data preparation: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    prepare = CaseOutcomeDataPreparation(
        input_file='src/data/case_outcomes/cleaned_dataset.csv',
        output_dir='src/data/case_outcomes/split_data'
    )
    success = prepare.run()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
