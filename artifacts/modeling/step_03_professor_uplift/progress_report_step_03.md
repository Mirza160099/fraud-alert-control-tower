# Progress Report - Step 03: Model Comparison and Capacity Thresholding

## What We Built

This step compared stronger models and converted fraud probabilities into investigator-capacity thresholds. The model is now evaluated as a queue prioritization system, not only as a classifier.

## Features Used

We kept the Step 2 top-10 feature constraint so the final app remains explainable and input-friendly:

- `geo_distance_km`
- `amt_per_txn_24h`
- `channel`
- `synthetic_identity_score`

## Models Compared

| Model | Validation PR-AUC | Test precision | Test recall | Test F1 | Test ROC-AUC | Test PR-AUC | Test reviews |
|---|---:|---:|---:|---:|---:|---:|---:|
| logistic_regression_balanced | 0.1446 | 0.1026 | 0.2000 | 0.1356 | 0.6358 | 0.0836 | 78 |
| adaboost_depth2_weighted | 0.1158 | 0.1148 | 0.3500 | 0.1728 | 0.6417 | 0.1231 | 122 |
| adaboost_weighted | 0.0949 | 0.1240 | 0.3750 | 0.1863 | 0.6655 | 0.1023 | 121 |
| gradient_boosting_weighted | 0.0940 | 0.0833 | 0.1250 | 0.1000 | 0.6460 | 0.0869 | 60 |
| extra_trees_balanced | 0.0808 | 0.1159 | 0.2000 | 0.1468 | 0.5944 | 0.0730 | 69 |
| random_forest_balanced | 0.0762 | 0.0826 | 0.2500 | 0.1242 | 0.5990 | 0.0665 | 121 |

## Capacity Tuning at 5% Review Capacity

The primary operating assumption is that investigators can review about 5% of transactions. Thresholds are chosen on validation data and then applied to the held-out test set. The last two columns also show an exact top-K queue policy, where the team simply reviews the highest-risk 5% of test transactions.

| Model | Validation PR-AUC | Validation threshold | Validation hit rate | Validation fraud capture | Validation F1 | Test reviews | Test hit rate | Test fraud capture | Exact top-K hit rate | Exact top-K fraud capture |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| logistic_regression_balanced | 0.1446 | 0.6777 | 0.1600 | 0.2000 | 0.1778 | 60 | 0.1000 | 0.1500 | 0.1200 | 0.1500 |
| adaboost_depth2_weighted | 0.1158 | 0.7911 | 0.1800 | 0.2250 | 0.2000 | 59 | 0.1356 | 0.2000 | 0.1400 | 0.1750 |
| adaboost_weighted | 0.0949 | 0.7794 | 0.1800 | 0.2250 | 0.2000 | 76 | 0.1316 | 0.2500 | 0.2000 | 0.2500 |
| gradient_boosting_weighted | 0.0940 | 0.6853 | 0.1800 | 0.2250 | 0.2000 | 58 | 0.0862 | 0.1250 | 0.0600 | 0.0750 |
| extra_trees_balanced | 0.0808 | 0.6053 | 0.1000 | 0.1250 | 0.1111 | 60 | 0.1167 | 0.1750 | 0.1200 | 0.1500 |
| random_forest_balanced | 0.0762 | 0.5462 | 0.1200 | 0.1500 | 0.1333 | 69 | 0.0580 | 0.1000 | 0.0600 | 0.0750 |

## Champion Choice

- Champion model: `adaboost_depth2_weighted`
- Selected operating threshold: `0.7911`
- Target capacity: `5%`
- Test review count after applying threshold: `59`
- Test hit rate: `0.1356`
- Test fraud capture: `0.2000`
- Test F1: `0.1616`
- Exact top-K test hit rate: `0.1400`
- Exact top-K test fraud capture: `0.1750`

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
