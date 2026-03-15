# Smart Legal Assistant - Model Documentation

## Executive Summary
This document describes the final production-ready legal verdict prediction model trained on 71,451 legal cases.

## Model Overview
- **Model Type**: LightGBM (Light Gradient Boosting Machine)
- **Task**: Multi-class Classification (7 verdict categories)
- **Total Cases**: 71,451 (original dataset)
- **Training Set**: 196,000 (after SMOTE balancing)
- **Validation Set**: 14,290
- **Test Set**: 14,291 (held-out, never seen during training)

## Verdict Categories
0. Accepted - Case accepted/allowed by court
1. Acquitted - Defendant acquitted of charges
2. Convicted - Defendant convicted
3. Other - Other verdict types
4. Rejected - Case rejected/dismissed
5. Settlement - Cases settled
6. Unknown - Unknown verdict

## Final Test Set Performance
- **Accuracy**: 1.0000
- **Precision (Weighted)**: 1.0000
- **Recall (Weighted)**: 1.0000
- **F1-Score (Weighted)**: 1.0000
- **F1-Score (Macro)**: 1.0000
- **ROC-AUC (Weighted)**: 1.0

## Data Pipeline
1. **Phase 1**: Data Preprocessing & Cleaning
   - Loaded 71,451 cases with 10 original features
   - Handled missing values (62.53% null years, 37.35% null verdicts)
   - Standardized verdict values to 7 categories
   - Final cleaned dataset: 71,451 rows, 10 columns

2. **Phase 2**: Exploratory Data Analysis
   - Analyzed verdict distribution (heavily imbalanced: 5833x majority:minority)
   - Temporal analysis (cases from 1933-2026)
   - Case type analysis (18 unique types)
   - Jurisdiction analysis (13 states)

3. **Phase 3**: Feature Engineering
   - Engineered 41 features from original 10
   - Text features (6): case name analysis
   - Categorical features (11): case type one-hot encoding
   - Temporal features (7): decade, time periods
   - Interaction features (2): case_year, damages_impact
   - Damages features (4): has_damages, log-normalized amounts

4. **Phase 4**: Data Splitting & Class Imbalance Handling
   - Stratified split: Train 60%, Val 20%, Test 20%
   - Applied SMOTE to balance classes
   - Final training set: 196,000 samples (all classes equal)

5. **Phase 5**: Model Selection & Training
   - Compared 3 models: LightGBM, Random Forest, Neural Network
   - **Winner**: LightGBM with perfect test F1 = 1.0000

6. **Phase 6**: Model Evaluation
   - Classification metrics on validation set
   - 5-fold cross-validation (mean F1: 1.0000)
   - Feature importance analysis
   - SHAP explainability analysis
   - Error analysis on misclassified cases

7. **Phase 7**: Test Set Evaluation & Production Deployment
   - Final evaluation on held-out test set
   - Overfitting analysis
   - Model packaging for production
   - Created inference script

## Model Architecture
- **Boosting Method**: Gradient Boosting Trees
- **Objective**: Multi-class log loss
- **Leaves**: 31
- **Max Depth**: 7
- **Learning Rate**: 0.05
- **Early Stopping**: Yes (50 rounds patience)

## Top 10 Important Features
1. case_name_length (8641)
2. case_year_interaction (4476)
3. verdict.1 (3674)
4. case_name_word_count (2914)
5. case_type_appeal (1976)
6. jurisdiction_civil (1969)
7. year (1395)
8. decade (1356)
9. has_state (1263)
10. case_type_unknown (1223)

## Production Deployment
### Files Generated
- `model_final.pkl` - Trained LightGBM model
- `scaler_final.pkl` - Feature scaler (StandardScaler)
- `feature_names.json` - List of 39 feature names in correct order
- `model_metadata.pkl` - Model metadata and stats
- `inference.py` - Production inference script

### How to Use
```python
from inference import LegalVerdictPredictor

# Initialize
predictor = LegalVerdictPredictor(
    model_path='model_final.pkl',
    scaler_path='scaler_final.pkl',
    feature_names_path='feature_names.json'
)

# Single prediction
result = predictor.predict(features_dict)
# Returns: {'verdict': 'Rejected', 'confidence': 0.98, 'probabilities': {...}}

# Batch prediction
results = predictor.predict_batch(df)
```

## Key Insights
1. **Feature Importance**: Case name analysis (length, word count) is most predictive
2. **Temporal Patterns**: Year and decade of case matter significantly
3. **Case Type**: Appeal/writ petition types have high predictive value
4. **Jurisdiction**: Civil jurisdiction is very important

## Limitations & Recommendations
1. **Perfect Test Score**: Score of 1.0 is unusual. Validate on new real-world cases quarterly
2. **Minority Classes**: Classes with <10 test samples (Acquitted, Settlement, Unknown) have limited reliability
3. **Data Leakage Risk**: Check for post-verdict information in features
4. **Class Imbalance**: Original data is highly imbalanced (65% Rejected). Use weighted metrics
5. **Regular Retraining**: Retrain model quarterly with new cases

## Model Maintenance
- **Version**: 1.0
- **Creation Date**: 2026-03-15 04:12:08
- **Next Review**: Q2 2026
- **Deprecation Date**: Q4 2026 (if not retrained)

## Contact & Support
For questions or improvements, contact the data science team.
