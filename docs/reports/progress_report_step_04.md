# Progress Report - Step 04: Explainability Layer

## What We Built

This step added a model-agnostic explainability layer for the Step 3 champion model.

The method has two parts:

1. Global permutation importance, which shows which features affect model performance most overall.
2. Local reference-value sensitivity, which explains an individual transaction by replacing each feature with a typical training-set value and measuring the change in fraud probability.

## Champion Model

- Model: `adaboost_depth2_weighted`
- Threshold: `0.7977`
- Capacity policy: `validation_top_k_capacity`

## Global Feature Importance

Permutation importance is measured using held-out test-set PR-AUC, which is better than accuracy for rare fraud.

| Feature | Mean PR-AUC importance | Std |
|---|---:|---:|
| geo_distance_km | 0.080645 | 0.013072 |
| channel | 0.013804 | 0.003404 |
| amount_log1p | 0.013607 | 0.014000 |
| transaction_amount_usd | 0.006126 | 0.013127 |
| txn_hour | 0.002593 | 0.005548 |
| merchant_profile_risk_score | 0.000427 | 0.008817 |
| txn_country | -0.000384 | 0.000669 |
| merchant_risk_score | -0.003397 | 0.008153 |
| device_risk_score | -0.005277 | 0.008441 |
| synthetic_identity_score | -0.010814 | 0.017026 |

## Example Local Explanations

| Transaction | Fraud probability | Priority | Top reason |
|---|---:|---|---|
| T9042990 | 0.8457 | Critical | geographic distance was 1370.600 compared with a typical value of 17.600; this increased the model risk score by 0.317. |
| T9051526 | 0.8444 | Critical | geographic distance was 3163.700 compared with a typical value of 17.600; this increased the model risk score by 0.318. |
| T9060368 | 0.8393 | Critical | geographic distance was 1475.600 compared with a typical value of 17.600; this increased the model risk score by 0.322. |
| T9030658 | 0.8364 | Critical | geographic distance was 1287.700 compared with a typical value of 17.600; this increased the model risk score by 0.325. |
| T9038232 | 0.8358 | Critical | geographic distance was 976.000 compared with a typical value of 17.600; this increased the model risk score by 0.309. |

## How To Explain This In An Interview

I did not just output a black-box fraud score. I created a reviewer-facing explanation layer: global importance tells risk leadership which signals matter across the portfolio, while local sensitivity tells an investigator why a specific case moved into the queue.

## Artifacts Created

- `global_feature_importance.csv`
- `local_explanations_top_cases.csv`
- `case_review_explanations.csv`
- `reference_profile.json`
- `progress_report_step_04.md`
