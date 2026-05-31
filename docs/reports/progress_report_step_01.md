# Progress Report - Step 01: Project Understanding and Data Audit

## Project Goal

We are building an explainable fraud-alert prioritization system inspired by a JPMorganChase fraud operations use case. The final project should show more than a fraud classifier: it should show how alerts are prioritized, why a transaction looks risky, and how an investigator or risk manager can act on the output.

## Current Approach

The project will be built in small stages so every decision is understandable and interview-ready:

1. Understand the business problem and dataset.
2. Profile and clean the transaction, customer, and merchant data.
3. Select the strongest fraud-risk features using mutual information and later SHAP.
4. Train a fraud prediction model with class imbalance handled properly.
5. Convert model scores into operational alert priority tiers.
6. Explain each prediction using top contributing features.
7. Build a user-facing app where someone can enter transaction details and receive:
   - Legitimate vs fraudulent prediction
   - Fraud probability
   - Priority tier
   - Plain-English explanation
8. Package the project for deployment and portfolio presentation.

## Files Reviewed

- `B_Dataset/raw/transactions.csv`
- `B_Dataset/raw/customers.csv`
- `B_Dataset/raw/merchants.csv`
- `B_Dataset/processed/alert_queue_seed.csv`
- `B_Dataset/metadata/data_dictionary.csv`
- `B_Dataset/metadata/schema_note.txt`
- `C_Supporting_Files/notebooks/starter_notebook.ipynb`
- `C_Supporting_Files/sql/starter_queries.sql`

## Python Code Review

The starter notebook currently contains only a skeleton:

```python
import pandas as pd
import numpy as np
from pathlib import Path
base = Path.cwd().parents[1]
raw = base / 'B_Dataset' / 'raw'
meta = base / 'B_Dataset' / 'metadata'
```

Commented explanation:

```python
# Import pandas for tabular data loading, cleaning, joins, and analysis.
import pandas as pd

# Import numpy for numerical transformations such as log scaling and array operations.
import numpy as np

# Import Path so file paths work cleanly across operating systems.
from pathlib import Path

# Set the project base folder relative to the notebook location.
base = Path.cwd().parents[1]

# Create a shortcut to the raw dataset folder.
raw = base / 'B_Dataset' / 'raw'

# Create a shortcut to the metadata folder containing the schema and data dictionary.
meta = base / 'B_Dataset' / 'metadata'
```

The rest of the notebook is placeholder text. We will replace it with a fully commented professional pipeline rather than patching a mostly empty notebook.

## Data Audit Findings

### Raw Transactions

- Rows: 5,000
- Columns: 17
- Missing values: 0
- Duplicate rows: 0
- Fraud cases: 201
- Non-fraud cases: 4,799
- Fraud rate: 4.02%
- Alert-generated rows: 140
- Alert rate: 2.8%

This is a highly imbalanced fraud dataset, which is realistic. Accuracy alone would be misleading because a model could predict "not fraud" most of the time and still appear strong.

### Alert vs Fraud Quality Check

| alert_generated | non_fraud | fraud |
|---:|---:|---:|
| 0 | 4,701 | 159 |
| 1 | 98 | 42 |

Important interpretation:

- Existing alert logic catches only 42 of 201 fraud cases.
- 159 fraud cases were not alerted.
- Among generated alerts, 42 out of 140 are true fraud, giving an alert hit rate of 30%.

This is a strong business story: the project can improve both missed fraud detection and investigator prioritization.

### Customers

- Rows: 5,000
- Missing values: 0
- Duplicate rows: 0
- Data quality issue: `tenure_months` is documented as an integer but appears as `1970-01-01`.

Cleaning decision:

- Do not use `tenure_months` as a normal numeric feature yet.
- Add a data quality note explaining why it was excluded.
- Optionally create a `tenure_months_invalid_flag`, but this may not help because it appears invalid throughout the file.

### Merchants

- Rows: 5,000
- Missing values: 0
- Duplicate rows: 0

Merchant fields can help explain fraud risk because merchant risk, category, and default channel are business-readable.

### Join Quality

- Transaction rows: 5,000
- Unique transaction IDs: 5,000
- Unique customer IDs in transactions: 5,000
- Unique merchant IDs in transactions: 5,000
- Missing merchant joins: 0
- Missing customer joins: 822

Cleaning decision:

- Keep all transactions.
- Left join customer and merchant data.
- Impute missing customer profile fields.
- Add a `customer_profile_missing_flag` so the model can learn whether missing customer profile information is itself operationally meaningful.

## Leakage and Modeling Controls

We should not use these fields directly as model features:

- `transaction_id`: identifier, no generalizable fraud signal.
- `customer_id`: each customer appears only once in the transaction table, so this risks memorization.
- `merchant_id`: each merchant appears only once in the transaction table, so this also risks memorization.
- `fraud_label`: target, never a feature.
- `alert_generated`: operational output/rule indicator, likely leakage for a fresh transaction fraud model.

We can use `alert_generated` later for operations analysis, threshold comparison, and control tower metrics, but not as an input to the main prediction model.

## Preliminary Top Features

Because scikit-learn is not installed in the bundled Python runtime yet, this first ranking uses manual binned mutual information. This is good enough for early direction, but we will rerun feature selection with scikit-learn and SHAP once the modeling environment is ready.

Top preliminary features, excluding leakage:

| Rank | Feature | Reason it matters |
|---:|---|---|
| 1 | `geo_distance_km` | Large travel distance can signal account takeover or unusual behavior. |
| 2 | `txn_country` | Certain cross-border patterns may be higher risk. |
| 3 | `device_risk_score` | Device-level risk is directly relevant to fraud detection. |
| 4 | `channel` | Wire, P2P, card-not-present, and online channels can carry different risk. |
| 5 | `transaction_amount_usd` | Unusually large or unusual spend can increase risk. |
| 6 | `amount_log1p` | Log-scaled amount helps reduce outlier distortion. |
| 7 | `txn_hour` | Night-time or unusual-hour behavior can be suspicious. |
| 8 | `synthetic_identity_score` | Higher synthetic identity risk may indicate fake or manipulated identity. |
| 9 | `is_night_flag` | Simple operational signal for after-hours risk. |
| 10 | `new_device_flag` | New device usage can indicate account compromise. |

## Data Cleaning Plan

1. Parse `event_ts` as datetime.
2. Confirm transaction grain is one row per transaction.
3. Remove or ignore duplicate rows if any appear.
4. Left join customer and merchant profile fields.
5. Add missing-profile flags for customer joins.
6. Exclude broken `tenure_months` until corrected.
7. Engineer time features:
   - event month
   - day of week
   - hour already provided
   - night flag already provided
8. Engineer amount feature:
   - `amount_log1p`
9. Keep categorical features readable:
   - channel
   - country
   - customer segment
   - KYC risk band
   - merchant category
10. Impute missing values after joins.
11. Split train/test with stratification because fraud is only 4.02%.
12. Use class imbalance handling such as class weights or resampling.

## Recommended Next Step

Build a fully commented Python modeling pipeline that:

1. Loads the three raw tables.
2. Cleans and joins the data.
3. Engineers the selected features.
4. Runs proper mutual information feature selection.
5. Trains a baseline model.
6. Evaluates precision, recall, F1, ROC-AUC, PR-AUC, and confusion matrix.
7. Saves the trained model and top feature list for the app.

Deployment note: Vercel is excellent for a polished web frontend, but it is not the natural home for a Python Streamlit app. The stronger portfolio architecture is likely:

- Python model training pipeline
- Saved model artifact
- Lightweight prediction API or serverless-compatible endpoint
- Vercel frontend for the transaction form and investigator explanation view

We should decide this architecture before writing the app.
