# Progress Report - Step 02: Modeling Pipeline

## What We Built

This step created a fully commented Python modeling pipeline for cleaning, joining, feature engineering, top-10 feature selection, and baseline model training.

## Cleaning and Feature Engineering Applied

1. Loaded raw transactions, customers, and merchants.
2. Parsed `event_ts` as a real datetime.
3. Normalized `GB` to `UK` for country consistency.
4. Preserved all transactions as the modeling grain.
5. Left joined customer and merchant profile data.
6. Added `customer_profile_missing_flag` because 822 transactions do not match a customer profile.
7. Added `merchant_profile_missing_flag`, although merchant joins are currently complete.
8. Flagged broken `tenure_months` values instead of using them as numeric months.
9. Added event month, day of week, and weekend features.
10. Added `amount_log1p` to reduce the effect of extreme transaction amounts.
11. Added `cross_border_flag` for transaction country vs home country mismatch.
12. Excluded IDs, target, and `alert_generated` from model features to avoid leakage.
13. Saved a feature schema with ranges and categories for the future app.

## Top 10 Features by Mutual Information

| Rank | Feature | Mutual information |
|---:|---|---:|
| 1 | `geo_distance_km` | 0.007031 |
| 2 | `txn_country` | 0.004632 |
| 3 | `synthetic_identity_score` | 0.003649 |
| 4 | `merchant_risk_score` | 0.002340 |
| 5 | `channel` | 0.002277 |
| 6 | `txn_hour` | 0.001992 |
| 7 | `device_risk_score` | 0.001913 |
| 8 | `merchant_profile_risk_score` | 0.001551 |
| 9 | `transaction_amount_usd` | 0.001190 |
| 10 | `amount_log1p` | 0.001190 |

## Baseline Model

The baseline model is logistic regression with:

- median imputation and standard scaling for numeric features
- most-frequent imputation and one-hot encoding for categorical features
- `class_weight="balanced"` to handle rare fraud cases
- threshold chosen on the validation set using best F1 score

Selected feature list:

- `geo_distance_km`
- `txn_country`
- `synthetic_identity_score`
- `merchant_risk_score`
- `channel`
- `txn_hour`
- `device_risk_score`
- `merchant_profile_risk_score`
- `transaction_amount_usd`
- `amount_log1p`

## Validation Threshold

- Threshold: `0.6028`
- Validation precision: `0.1058`
- Validation recall: `0.2750`
- Validation F1: `0.1528`

## Test Performance

- Accuracy: `0.8680`
- Precision: `0.1034`
- Recall: `0.3000`
- F1: `0.1538`
- ROC-AUC: `0.6610`
- PR-AUC: `0.0908`
- True positives: `12`
- False positives: `104`
- False negatives: `28`
- True negatives: `856`

## Existing Alert Benchmark on the Same Test Set

- Precision: `0.3636`
- Recall: `0.2000`
- F1: `0.2581`
- True positives: `8`
- False positives: `14`
- False negatives: `32`
- True negatives: `946`

## Interview Talking Point

This model is not positioned as a final production model. It is a controlled baseline that demonstrates disciplined fraud modeling: leakage prevention, class imbalance handling, feature selection on training data only, validation-based thresholding, and an operational comparison against existing alerts.

## Artifacts Created

- `top_10_features_mutual_info.csv`
- `metrics.json`
- `test_predictions.csv`
- `feature_schema.json`
- `fraud_baseline_model.pkl`
