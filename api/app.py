from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import joblib
import pandas as pd
import numpy as np
import shap
import os

# Load model and feature names
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model', 'best_lgbm_pipeline.pkl')
FEATURES_PATH = os.path.join(os.path.dirname(__file__), '..', 'model', 'feature_names.pkl')

model = joblib.load(MODEL_PATH)
feature_names = joblib.load(FEATURES_PATH)

# SHAP explainer
explainer = shap.TreeExplainer(model.named_steps['model'])

app = FastAPI(title="CreditIQ", description="Credit Risk Prediction API")


# Input validation — Pydantic enforces types and ranges
class ApplicantData(BaseModel):
    AMT_INCOME_TOTAL: float = Field(gt=0, description="Annual income")
    AMT_CREDIT: float = Field(gt=0, description="Loan amount")
    AMT_ANNUITY: float = Field(gt=0, description="Loan annuity (EMI)")
    AMT_GOODS_PRICE: float = Field(gt=0, description="Price of goods")
    NAME_CONTRACT_TYPE: str = Field(description="Cash loans or Revolving loans")
    CODE_GENDER: str = Field(description="M or F")
    FLAG_OWN_CAR: str = Field(description="Y or N")
    FLAG_OWN_REALTY: str = Field(description="Y or N")
    NAME_INCOME_TYPE: str = Field(description="Income type")
    NAME_EDUCATION_TYPE: str = Field(description="Education level")
    NAME_FAMILY_STATUS: str = Field(description="Family status")
    NAME_HOUSING_TYPE: str = Field(description="Housing type")
    DAYS_BIRTH: float = Field(lt=0, description="Age in days (negative)")
    DAYS_EMPLOYED: float = Field(description="Employment duration in days")
    EXT_SOURCE_1: float = Field(ge=0, le=1, description="External score 1")
    EXT_SOURCE_2: float = Field(ge=0, le=1, description="External score 2")
    EXT_SOURCE_3: float = Field(ge=0, le=1, description="External score 3")
    PREV_LOAN_COUNT: int = Field(ge=0, description="Previous loan count")
    PREV_ACTIVE_LOANS: int = Field(ge=0, description="Active loans count")
    PREV_TOTAL_DEBT: float = Field(ge=0, description="Total outstanding debt")


@app.get("/health")
def health():
    return {"status": "healthy", "model": "LightGBM"}


@app.get("/model-info")
def model_info():
    return {
        "model": "LightGBM (tuned)",
        "features": len(feature_names),
        "metrics": {
            "auc_roc": 0.7664,
            "recall_default": 0.68,
            "precision_default": 0.17
        }
    }


@app.post("/predict")
def predict(applicant: ApplicantData):
    try:
        data = applicant.model_dump()

        # Engineer features
        data['CREDIT_INCOME_RATIO'] = data['AMT_CREDIT'] / data['AMT_INCOME_TOTAL']
        data['DTI_RATIO'] = data['AMT_ANNUITY'] / data['AMT_INCOME_TOTAL']
        data['AGE_YEARS'] = data['DAYS_BIRTH'] / -365
        data['EMPLOYED_YEARS'] = data['DAYS_EMPLOYED'] / -365
        data['INCOME_PER_FAMILY'] = data['AMT_INCOME_TOTAL'] / 1
        data['CREDIT_GOODS_RATIO'] = data['AMT_CREDIT'] / data['AMT_GOODS_PRICE']
        data['EXT_SOURCE_MEAN'] = np.mean([data['EXT_SOURCE_1'], data['EXT_SOURCE_2'], data['EXT_SOURCE_3']])
        data['EMPLOYED_ANOMALY'] = 1 if data['DAYS_EMPLOYED'] == 365243 else 0

        # Separate num and cat feature names from pipeline
        preprocessor = model.named_steps['preprocessor']
        num_features = preprocessor.transformers_[0][2]
        cat_features = preprocessor.transformers_[1][2]

        # Build DataFrame with correct defaults
        df = pd.DataFrame([data])
        for col in num_features:
            if col not in df.columns:
                df[col] = 0.0
        for col in cat_features:
            if col not in df.columns:
                df[col] = "Unknown"

        # Ensure correct column order
        all_features = list(num_features) + list(cat_features)
        df = df[all_features]

        # Predict
        probability = model.predict_proba(df)[:, 1][0]
        prediction = "REJECTED" if probability > 0.5 else "APPROVED"

        # SHAP explanation
        processed = preprocessor.transform(df)
        shap_vals = explainer.shap_values(processed)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]

        # Top 5 risk factors
        shap_importance = list(zip(all_features, shap_vals[0]))
        shap_importance.sort(key=lambda x: abs(x[1]), reverse=True)
        top_factors = [
            {"feature": name, "impact": round(float(val), 4),
             "direction": "increases risk" if val > 0 else "decreases risk"}
            for name, val in shap_importance[:5]
        ]

        return {
            "prediction": prediction,
            "default_probability": round(float(probability), 4),
            "confidence": round(float(max(probability, 1 - probability)) * 100, 1),
            "top_risk_factors": top_factors
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))