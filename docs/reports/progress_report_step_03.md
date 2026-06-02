# Progress Report - Step 03: Model Comparison and Capacity Thresholding

## What We Built

This step compared stronger models and converted fraud probabilities into investigator-capacity thresholds. The model is now evaluated as a queue prioritization system, not only as a classifier.

## Features Used

We kept the Step 2 top-10 feature constraint so the final app remains explainable and input-friendly:

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

## Models Compared

| Model | Validation PR-AUC | Test precision | Test recall | Test F1 | Test ROC-AUC | Test PR-AUC | Test reviews |
|---|---:|---:|---:|---:|---:|---:|---:|
| adaboost_depth2_weighted | 0.1223 | 0.1529 | 0.3250 | 0.2080 | 0.6578 | 0.1414 | 85 |
| logistic_regression_balanced | 0.1029 | 0.1034 | 0.3000 | 0.1538 | 0.6610 | 0.0908 | 116 |
| adaboost_weighted | 0.0888 | 0.1489 | 0.3500 | 0.2090 | 0.6351 | 0.0982 | 94 |
| gradient_boosting_weighted | 0.0776 | 0.1159 | 0.4000 | 0.1798 | 0.6386 | 0.1298 | 138 |
| random_forest_balanced | 0.0640 | 0.0766 | 0.5000 | 0.1329 | 0.6634 | 0.0920 | 261 |
| extra_trees_balanced | 0.0550 | 0.0584 | 0.3750 | 0.1010 | 0.6212 | 0.0890 | 257 |

## Capacity Tuning at 5% Review Capacity

The primary operating assumption is that investigators can review about 5% of transactions. Thresholds are chosen on validation data and then applied to the held-out test set. The last two columns also show an exact top-K queue policy, where the team simply reviews the highest-risk 5% of test transactions.

| Model | Validation PR-AUC | Validation threshold | Validation hit rate | Validation fraud capture | Validation F1 | Test reviews | Test hit rate | Test fraud capture | Exact top-K hit rate | Exact top-K fraud capture |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| adaboost_depth2_weighted | 0.1223 | 0.7977 | 0.1400 | 0.1750 | 0.1556 | 74 | 0.1351 | 0.2500 | 0.1800 | 0.2250 |
| logistic_regression_balanced | 0.1029 | 0.6942 | 0.0800 | 0.1000 | 0.0889 | 53 | 0.1132 | 0.1500 | 0.1200 | 0.1500 |
| adaboost_weighted | 0.0888 | 0.7795 | 0.1800 | 0.2250 | 0.2000 | 74 | 0.1351 | 0.2500 | 0.2000 | 0.2500 |
| gradient_boosting_weighted | 0.0776 | 0.6535 | 0.1000 | 0.1250 | 0.1111 | 54 | 0.1481 | 0.2000 | 0.1600 | 0.2000 |
| random_forest_balanced | 0.0640 | 0.4875 | 0.0600 | 0.0750 | 0.0667 | 70 | 0.1000 | 0.1750 | 0.1200 | 0.1500 |
| extra_trees_balanced | 0.0550 | 0.6023 | 0.0400 | 0.0500 | 0.0444 | 58 | 0.1207 | 0.1750 | 0.1200 | 0.1500 |

## Champion Choice

- Champion model: `adaboost_depth2_weighted`
- Selected operating threshold: `0.7977`
- Target capacity: `5%`
- Test review count after applying threshold: `74`
- Test hit rate: `0.1351`
- Test fraud capture: `0.2500`
- Test F1: `0.1754`
- Exact top-K test hit rate: `0.1800`
- Exact top-K test fraud capture: `0.2250`

## Existing Alert Benchmark

On the same test split, the existing `alert_generated` rule had:

- Precision / hit rate: `0.3636`
- Recall / fraud capture: `0.2000`
- F1: `0.2581`
- True positives: `8`
- False positives: `14`
- False negatives: `32`

## Interview Talking Point

This is the fraud-operations story: a model can be tuned for different staffing levels. If leadership wants a smaller queue, we can raise the threshold and improve hit rate. If leadership wants to catch more fraud, we can lower the threshold and accept more false positives. That threshold discipline is exactly what turns a data science model into an operational control.

## Artifacts Created

- `model_comparison.csv`
- `capacity_thresholds.csv`
- `champion_test_predictions.csv`
- `champion_model.pkl`
- `metrics.json`
