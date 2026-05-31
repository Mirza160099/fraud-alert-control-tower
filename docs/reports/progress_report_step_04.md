# Progress Report - Step 04: Explainability Layer

## What We Built

This step added a model-agnostic explainability layer for the Step 3 champion model.

The method has two parts:

1. Global permutation importance, which shows which features affect model performance most overall.
2. Local reference-value sensitivity, which explains an individual transaction by replacing each feature with a typical training-set value and measuring the change in fraud probability.

## Champion Model

- Model: `adaboost_weighted`
- Threshold: `0.7795`
- Capacity policy: `validation_top_k_capacity`

## Global Feature Importance

Permutation importance is measured using held-out test-set PR-AUC, which is better than accuracy for rare fraud.

| Feature | Mean PR-AUC importance | Std |
|---|---:|---:|
| geo_distance_km | 0.047041 | 0.007455 |
| transaction_amount_usd | 0.003613 | 0.007524 |
| txn_country | 0.000000 | 0.000000 |
| txn_hour | 0.000000 | 0.000000 |
| device_risk_score | 0.000000 | 0.000000 |
| merchant_profile_risk_score | 0.000000 | 0.000000 |
| merchant_risk_score | -0.000198 | 0.000893 |
| channel | -0.001443 | 0.015881 |
| amount_log1p | -0.005690 | 0.007858 |
| synthetic_identity_score | -0.022101 | 0.010949 |

## Example Local Explanations

| Transaction | Fraud probability | Priority | Top reason |
|---|---:|---|---|
| T9007602 | 0.8415 | Critical | geographic distance was 1525.900 compared with a typical value of 17.600; this increased the model risk score by 0.324. |
| T9031208 | 0.8415 | Critical | geographic distance was 2131.000 compared with a typical value of 17.600; this increased the model risk score by 0.324. |
| T9010735 | 0.8415 | Critical | geographic distance was 2848.100 compared with a typical value of 17.600; this increased the model risk score by 0.324. |
| T9007479 | 0.8415 | Critical | geographic distance was 4862.800 compared with a typical value of 17.600; this increased the model risk score by 0.324. |
| T9053891 | 0.8415 | Critical | geographic distance was 3169.700 compared with a typical value of 17.600; this increased the model risk score by 0.324. |

## How To Explain This In An Interview

I did not just output a black-box fraud score. I created a reviewer-facing explanation layer: global importance tells risk leadership which signals matter across the portfolio, while local sensitivity tells an investigator why a specific case moved into the queue.

## Artifacts Created

- `global_feature_importance.csv`
- `local_explanations_top_cases.csv`
- `case_review_explanations.csv`
- `reference_profile.json`
- `progress_report_step_04.md`
