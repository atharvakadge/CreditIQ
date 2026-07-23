# CreditIQ — AI-Powered Credit Risk Prediction

An end-to-end credit risk prediction system that predicts loan default probability, explains every decision with SHAP, and generates PDF assessment reports. Built for real-world deployment with FastAPI and Streamlit.

---

## Problem Statement

Banks lose crores annually to loan defaults. Traditional rule-based credit scoring misses complex, non-linear patterns in applicant data. CreditIQ uses machine learning to predict default risk with 76.6% AUC-ROC and provides transparent, per-applicant explanations — critical for regulatory compliance under RBI's fair lending guidelines.

The system answers three questions for every loan application:
1. **Will this applicant default?** → Probability score
2. **Why?** → SHAP-based feature attribution
3. **What's the financial impact?** → Expected loss calculation

---

## Architecture

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  Raw Data    │────▶│  Feature Engine   │────▶│  LightGBM Model  │
│  (307K rows) │     │  (12+ features)   │     │  (tuned, 0.766)  │
└──────────────┘     └───────────────────┘     └────────┬─────────┘
                                                        │
                     ┌───────────────────┐              │
                     │   SHAP Explainer  │◀─────────────┘
                     │  (per-prediction) │
                     └────────┬──────────┘
                              │
                     ┌────────▼──────────┐     ┌──────────────────┐
                     │   FastAPI Backend │────▶│    Streamlit UI   │
                     │  /predict /health │     │  + PDF Reports    │
                     └───────────────────┘     └──────────────────┘
```

---

## Key Results

| Metric | Value |
|---|---|
| AUC-ROC | **0.7664** |
| Recall (Defaulters) | **68%** |
| Precision (Defaulters) | 17% |
| Dataset | 307,511 applicants |
| Features Used | 88 (76 numerical + 12 categorical) |
| Features Engineered | 12+ |
| Models Evaluated | 4 (LR, RF, XGBoost, LightGBM) |

**Why recall over precision?** In credit risk, missing a defaulter (≈ ₹5L loss) is far more expensive than rejecting a good applicant (≈ ₹50K lost revenue). The model is deliberately tuned to catch more defaulters at the cost of higher false positives. The decision threshold is adjustable based on a bank's risk appetite.

---

## Model Comparison

| Model | AUC-ROC | Std Dev | Notes |
|---|---|---|---|
| Logistic Regression | 0.7490 | ±0.0045 | Baseline — linear decision boundary |
| Random Forest | 0.7482 | ±0.0046 | Underperformed without extensive tuning |
| XGBoost | 0.7630 | ±0.0045 | Strong but slower training |
| **LightGBM (tuned)** | **0.7664** | **±0.0039** | **Winner — fastest, most consistent** |

LightGBM was selected as the final model for its superior AUC-ROC, lowest variance across folds, and fastest training time. Hyperparameters were tuned using RandomizedSearchCV (30 iterations × 5-fold stratified CV).

**Tuned hyperparameters:**
- `n_estimators`: 500
- `max_depth`: 8
- `learning_rate`: 0.03
- `subsample`: 0.9
- `colsample_bytree`: 0.6
- `min_child_samples`: 100
- `reg_alpha`: 0.1
- `is_unbalance`: True

---

## Feature Engineering

Features were engineered based on domain knowledge from credit risk assessment and personal experience with equity/derivatives trading on NSE/BSE.

| Feature | Formula | Business Logic | Correlation with Default |
|---|---|---|---|
| `EXT_SOURCE_MEAN` | mean(EXT_SOURCE_1, 2, 3) | Combined credit score — smooths noise across sources | **-0.2208** (strongest) |
| `AGE_YEARS` | DAYS_BIRTH / -365 | Younger applicants default 2x more (11.5% vs 5%) | -0.0782 |
| `CREDIT_GOODS_RATIO` | AMT_CREDIT / AMT_GOODS_PRICE | Overborrowing indicator — loan exceeds goods value | 0.0685 |
| `EMPLOYED_YEARS` | DAYS_EMPLOYED / -365 | Employment stability — longer tenure = lower risk | -0.0634 |
| `PREV_ACTIVE_LOANS` | count from bureau.csv | Juggling multiple debts increases default risk | 0.0436 |
| `EMPLOYED_ANOMALY` | flag for sentinel value | Retirees/pensioners — counterintuitively safer (5.4% vs 8.7%) | -0.027 |
| `DTI_RATIO` | AMT_ANNUITY / AMT_INCOME_TOTAL | Debt-to-income — weak alone, strong in combination | 0.0143 |
| `CREDIT_INCOME_RATIO` | AMT_CREDIT / AMT_INCOME_TOTAL | Overall leverage — years of income the loan represents | -0.0077 |

**Key insight:** `EXT_SOURCE_MEAN` alone (-0.22 correlation) outperforms any individual external score (-0.15 to -0.18). Combining three noisy signals into one amplified the predictive power — the single most impactful feature engineering decision.

---

## SHAP Explainability

SHAP (SHapley Additive exPlanations) provides two levels of interpretability:

### Global Feature Importance
The top 5 features driving model decisions across all predictions:
1. **EXT_SOURCE_MEAN** — combined credit score dominates
2. **EXT_SOURCE_3** — individual credit score
3. **EXT_SOURCE_2** — individual credit score
4. **CREDIT_GOODS_RATIO** — engineered overborrowing indicator
5. **CODE_GENDER** — demographic factor

### Per-Prediction Explanation
Every prediction includes a breakdown of which features pushed the decision toward approval or rejection, and by how much. Example for a rejected applicant:
- `PREV_ACTIVE_LOANS = 2.35` → **+0.25** (increases risk — multiple active debts)
- `EXT_SOURCE_MEAN = -0.716` → **+0.20** (increases risk — poor credit score)
- `NAME_CONTRACT_TYPE = Revolving` → **-0.16** (decreases risk — pre-filtered safer pool)

This level of transparency is critical for RBI regulatory compliance, which requires banks to explain lending decisions.

---

## Data Pipeline

### Dataset
Home Credit Default Risk dataset from Kaggle — 307,511 loan applications with 122 raw features and a binary TARGET column (8% default rate).

### Cleaning Steps
1. **Dropped 44 columns** with >40% missing values and <0.1 correlation with TARGET (building-related features with ~70% missing data)
2. **Fixed sentinel value** in DAYS_EMPLOYED: 365,243 (≈1000 years) used as "unemployed" placeholder → replaced with NaN + created binary flag
3. **Fill + Flag strategy** for important columns with significant missing data (EXT_SOURCE_1 at 56%, EXT_SOURCE_3 at 20%): filled with median, created `_MISSING` flag column
4. **Median fill** for numerical columns with <5% missing
5. **Mode fill** for categorical columns with <5% missing
6. **Bureau merge**: aggregated 1.7M rows from bureau.csv (previous loan history) into per-applicant features using left join on SK_ID_CURR

### Class Imbalance Handling
92% non-default vs 8% default. Handled with `is_unbalance=True` in LightGBM, which penalizes misclassification of the minority class proportionally (~11.5x weight).

---

## Tech Stack

| Component | Technology | Why This Choice |
|---|---|---|
| **Model** | LightGBM | Fastest training, leaf-wise growth, best AUC on this dataset |
| **Explainability** | SHAP | Per-prediction attribution, regulatory compliance |
| **Preprocessing** | sklearn Pipeline + ColumnTransformer | No data leakage, reproducible, production-ready |
| **API** | FastAPI + Pydantic | Async-ready, automatic validation, auto-generated Swagger docs |
| **Frontend** | Streamlit | Rapid prototyping, interactive widgets, built-in deployment |
| **Reports** | ReportLab | Programmatic PDF generation with professional formatting |
| **Containerization** | Docker | Environment consistency, one-command deployment |
| **Language** | Python 3.11 | Ecosystem support for ML/data science |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns `{"status": "healthy"}` |
| `GET` | `/model-info` | Model metadata — version, feature count, metrics |
| `POST` | `/predict` | Takes applicant JSON, returns prediction + probability + SHAP explanation |

### Sample Request

```json
POST /predict
{
  "AMT_INCOME_TOTAL": 200000,
  "AMT_CREDIT": 500000,
  "AMT_ANNUITY": 25000,
  "AMT_GOODS_PRICE": 450000,
  "NAME_CONTRACT_TYPE": "Cash loans",
  "CODE_GENDER": "M",
  "FLAG_OWN_CAR": "N",
  "FLAG_OWN_REALTY": "Y",
  "NAME_INCOME_TYPE": "Working",
  "NAME_EDUCATION_TYPE": "Secondary / secondary special",
  "NAME_FAMILY_STATUS": "Married",
  "NAME_HOUSING_TYPE": "House / apartment",
  "DAYS_BIRTH": -10000,
  "DAYS_EMPLOYED": -1500,
  "EXT_SOURCE_1": 0.3,
  "EXT_SOURCE_2": 0.4,
  "EXT_SOURCE_3": 0.3,
  "PREV_LOAN_COUNT": 3,
  "PREV_ACTIVE_LOANS": 2,
  "PREV_TOTAL_DEBT": 150000
}
```

### Sample Response

```json
{
  "prediction": "REJECTED",
  "default_probability": 0.765,
  "confidence": 76.5,
  "top_risk_factors": [
    {"feature": "EXT_SOURCE_MEAN", "impact": 0.7193, "direction": "increases risk"},
    {"feature": "DAYS_ID_PUBLISH", "impact": 0.2815, "direction": "increases risk"},
    {"feature": "PREV_TOTAL_CREDIT", "impact": 0.2361, "direction": "increases risk"},
    {"feature": "EXT_SOURCE_3", "impact": 0.217, "direction": "increases risk"},
    {"feature": "EXT_SOURCE_2", "impact": 0.1885, "direction": "increases risk"}
  ]
}
```

Input validation is handled by Pydantic — income must be positive, age must be negative days, credit scores between 0 and 1. Invalid inputs return 422 with descriptive error messages.

---

## Business Impact

| Metric | Value |
|---|---|
| Average default cost | ₹5,00,000 |
| Total applicants in dataset | 307,511 |
| Actual defaulters | ~24,800 (8%) |
| Defaulters caught by model (68% recall) | ~16,900 |
| **Estimated annual savings** | **₹845 crore** |

The model's 68% recall means it catches roughly 16,900 out of 24,800 defaulters. At ₹5L average default cost, that's ₹845 crore in prevented losses — a conservative estimate since it doesn't account for partial recovery or varying loan sizes.

---

## EDA Key Findings

| Finding | Detail |
|---|---|
| **Class Imbalance** | 92% repaid vs 8% default — accuracy metric is meaningless (92% by predicting all non-default) |
| **Age vs Default** | Monotonic decrease: 20-30 year olds default at 11.5%, 60-70 at 5% |
| **Income vs Default** | Weak predictor — only 9% gap between defaulters and non-defaulters |
| **Education vs Default** | Strong: lower secondary defaults at 10.9%, higher education at 5.4% |
| **Contract Type Surprise** | Cash loans default MORE than revolving loans (8.3% vs 5.5%) — selection bias, not product risk |
| **External Scores** | Dominant predictors — 23-31% gap between defaulter and non-defaulter medians |
| **DAYS_EMPLOYED Anomaly** | Sentinel value 365,243 (≈1000 years) for ~55K applicants — flagged as binary feature, these applicants actually default LESS (5.4% vs 8.7%) |

---

## How to Run

### Prerequisites
- Python 3.11+
- pip

### Local Setup

```bash
# Clone
git clone https://github.com/atharvakadge/CreditIQ.git
cd CreditIQ

# Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Download dataset from Kaggle
# Place application_train.csv and bureau.csv in data/

# Run notebooks in order to generate model
# notebooks/01_exploration.ipynb
# notebooks/02_cleaning_and_features.ipynb
# notebooks/03_modeling.ipynb

# Start API (terminal 1)
uvicorn app.app:app --reload

# Start Dashboard (terminal 2)
streamlit run app/dashboard.py
```

### Docker

```bash
docker build -t creditiq .
docker run -p 8000:8000 -p 8501:8501 creditiq
```

- API: http://localhost:8000/docs
- Dashboard: http://localhost:8501

---

## Project Structure

```
CreditIQ/
├── app/
│   ├── app.py                  # FastAPI backend — /predict, /health, /model-info
│   └── dashboard.py            # Streamlit frontend with PDF report generation
├── data/
│   ├── application_train.csv   # Main dataset (307K rows, not in repo)
│   ├── application_clean.csv   # Cleaned dataset (not in repo)
│   └── bureau.csv              # Previous loan history (not in repo)
├── model/
│   ├── best_lgbm_pipeline.pkl  # Trained model pipeline (not in repo)
│   └── feature_names.pkl       # Feature list for inference (not in repo)
├── notebooks/
│   ├── 01_exploration.ipynb    # EDA — hypotheses, visualizations, correlations
│   ├── 02_cleaning_and_features.ipynb  # Data cleaning + feature engineering
│   └── 03_modeling.ipynb       # Model training, tuning, SHAP analysis
├── .gitignore
├── Dockerfile
├── README.md
└── requirements.txt
```

---

## Future Improvements

- **MLflow integration** — experiment tracking for model versioning and comparison across retraining cycles
- **Data drift detection** — monitor feature distributions in production to flag when retraining is needed
- **Batch prediction endpoint** — POST /predict-batch for bulk processing of loan applications
- **Advanced bureau features** — payment history patterns, credit utilization trends, time-since-last-default
- **Threshold optimization** — A/B testing framework to find optimal decision threshold balancing approval rate vs default rate
- **Model fairness audit** — test for disparate impact across demographic groups to ensure compliance with fair lending regulations

---

## Dataset

Home Credit Default Risk — [Kaggle Competition](https://www.kaggle.com/c/home-credit-default-risk/data)

The dataset is not included in this repository due to size. Download `application_train.csv` and `bureau.csv` from Kaggle and place them in the `data/` directory.

---

## Author

**Atharva Kadge**
B.Tech Computer Engineering, Sardar Patel Institute of Technology, Mumbai (2023-2027)
