# Model Card - Explainable Fraud Alert Prioritization

## Model Overview

| Item | Detail |
|---|---|
| Project | Explainable Fraud Alert Prioritization and Investigation Control Tower |
| Model purpose | Score transaction fraud risk and prioritize investigator review queues |
| Triage layer | `risk_triage_engine` |
| Scoring approach | Explainable risk-ranking layer with weighted training |
| Primary users | Fraud operations analysts, investigators, risk analytics reviewers |
| Decision type | Decision-support, not fully automated adverse action |
| Current status | Prototype / capstone model using synthetic data |

## Intended Use

The model is intended to help fraud operations teams rank transaction alerts by predicted fraud risk. It supports queue prioritization, capacity planning, and investigator explanation. It should be used as a decision-support tool where a human reviewer confirms the final action.

Appropriate uses:

- Prioritize which suspicious transactions investigators review first.
- Estimate the trade-off between fraud capture and review capacity.
- Provide plain-English rationale for why a transaction is considered risky.
- Compare the model against existing alert logic.

Out-of-scope uses:

- Automatically freezing accounts without human review.
- Making credit, lending, employment, or eligibility decisions.
- Using synthetic prototype metrics as production performance evidence.
- Using the model without monitoring drift, false positives, and customer impact.

## Data Summary

| Dataset | Description |
|---|---|
| `transactions.csv` | Transaction-level data with channel, amount, country, device risk, velocity, geo distance, alert flag, and fraud label |
| `customers.csv` | Customer profile fields including segment, home country, KYC risk band, and synthetic identity score |
| `merchants.csv` | Merchant category, channel default, and merchant risk score |

Primary modeling grain:

- One row per transaction.

Target:

- `fraud_label`

Important data quality notes:

- `tenure_months` was documented as numeric but contained date-like values such as `1970-01-01`, so it was not used as a numeric feature.
- Some transaction rows did not match customer profile data, so missing-profile flags were created.
- `alert_generated` was excluded from model features to avoid leakage from existing operational alert logic.

## Features Used

The final app and risk triage layer use the selected top 10 features:

1. `geo_distance_km`
2. `txn_country`
3. `synthetic_identity_score`
4. `merchant_risk_score`
5. `channel`
6. `txn_hour`
7. `device_risk_score`
8. `merchant_profile_risk_score`
9. `transaction_amount_usd`
10. `amount_log1p`

Excluded fields:

- `transaction_id`
- `customer_id`
- `merchant_id`
- `fraud_label`
- `alert_generated`
- `event_ts` raw timestamp

## Feature Engineering Uplift Audit

During the final evidence-led iteration, the pipeline was extended with a second feature-engineering and feature-audit pass. The goal was to make the model less dependent on raw fields alone and to test behavior-based fraud signals that are easier to explain in a banking review.

Additional candidate features tested:

| Feature | Business meaning |
|---|---|
| `velocity_ratio` | Short-term activity compared with the last 24 hours |
| `amt_per_txn_24h` | Transaction amount adjusted for recent transaction volume |
| `far_and_new` | High geographic distance combined with a new device |
| `night_crossborder` | Night-time activity outside the customer's home country |
| `hour_sin`, `hour_cos` | Cyclical encoding of transaction hour |
| `merchant_cat_fraud_rate` | Leakage-aware merchant category fraud-rate encoding |

Selection discipline:

- Mutual information is used as the first training-only shortlist.
- Validation permutation importance is then used as a model-aware check.
- Features with negative validation contribution are not promoted simply because they appeared in the initial shortlist.
- The live app model was kept stable because the uplift experiment improved feature discipline but did not clearly beat the current operating backtest.

This is the important analyst decision: new features were tested and documented, but the production-facing demo was not changed unless the evidence justified it.

## Training and Validation

Data was split into:

| Split | Rows |
|---|---:|
| Train | 3,000 |
| Validation | 1,000 |
| Test | 1,000 |

Class imbalance:

- Fraud rate: `4.02%`

Modeling controls:

- Stratified train, validation, and test split.
- Feature selection performed on training data only.
- Threshold selected on validation data.
- Final performance measured on held-out test data.
- Class imbalance handled with weighted training.

## Operating Performance

Operating policy:

- Triage layer: `risk_triage_engine`
- Threshold: `0.7977`
- Target review capacity: `5%`

Held-out test performance at the selected threshold:

| Metric | Value |
|---|---:|
| Test review count | 74 |
| Queue rate | 7.4% |
| Precision / hit rate | 13.5% |
| Recall / fraud capture | 25.0% |
| F1 | 17.5% |
| True positives | 10 |
| False positives | 64 |
| False negatives | 30 |

Exact top-5% queue performance:

| Metric | Value |
|---|---:|
| Review count | 50 |
| Precision / hit rate | 18.0% |
| Recall / fraud capture | 22.5% |
| F1 | 20.0% |
| True positives | 9 |
| False positives | 41 |

## Existing Alert Benchmark

Existing `alert_generated` performance on the same test split:

| Metric | Value |
|---|---:|
| Precision / hit rate | 36.4% |
| Recall / fraud capture | 20.0% |
| F1 | 25.8% |
| True positives | 8 |
| False positives | 14 |
| False negatives | 32 |

Interpretation:

- The existing alert rule is more precise but catches fewer fraud cases.
- The risk triage policy catches more fraud cases than the existing alert rule at the selected capacity setting, but increases false positives.
- This is a business trade-off, not a purely technical win.

## Business Impact Sensitivity

Using the review-cost economics assumption of `GBP 8` review cost per case:

| Item | Value |
|---|---:|
| Additional reviewed cases vs existing alert | 52 |
| Additional fraud cases caught | 2 |
| Additional review spend | GBP 416 |
| Break-even avoided loss per extra captured fraud | GBP 208 |

Interpretation:

- If each additional fraud case prevented avoids more than GBP 208 of loss, the extra review load is financially justified.
- If avoided loss is below GBP 208, the model should be used more selectively as a top-K prioritization overlay.
- A production model would require real loss amounts, review-cost data, customer-friction measurement, and legal/compliance review before any ROI conclusion.

## Explainability

Global explainability:

- Permutation importance on held-out test PR-AUC.
- Strongest global driver: `geo_distance_km`.

Local explainability:

- Each scored transaction is compared against typical training-set reference values.
- The app explains which actual feature values increased the transaction's risk score.

Example rationale pattern:

- A transaction with unusually high geographic distance compared with a typical value may receive a higher fraud-risk score.

## Calibration, Segment, And SLA Evidence

Additional validation-evidence artifacts are saved in `artifacts/modeling/validation_evidence`.

Calibration evidence:

| Metric | Value |
|---|---:|
| Brier score | 0.2192 |
| Expected calibration error | 0.4132 |
| Largest calibration gap band | 0.80-1.00 |

Interpretation: the score is suitable for ranking and queue thresholding in this prototype, but it should not be represented as production odds until calibrated on real validation data.

Fairness / segment false-positive evidence:

| Segment view | Highest observed false-positive concentration |
|---|---|
| Country | `BR` at 60.3% across 78 non-fraud scored transactions |
| Channel | `P2P` at 7.5% across 801 non-fraud scored transactions |

Interpretation: this is a monitoring control, not a legal fairness conclusion. It highlights segments that would need closer false-positive and customer-friction review during a pilot.

SLA / turnaround evidence:

| Metric | Value |
|---|---:|
| Routed scored cases with SLA policy assigned | 390 |
| SLA policy coverage | 100.0% |
| Measured breach rate | Not available in current synthetic data |

True SLA breach rate requires investigation created, assigned, and closed timestamps. The prototype therefore shows SLA policy coverage and names timestamp capture as a production instrumentation requirement.

## Limitations

1. The dataset is synthetic, so model metrics should not be represented as production evidence.
2. The fraud rate is low, so precision, recall, and PR-AUC are more informative than accuracy.
3. The model has a meaningful false-positive burden at wider review thresholds.
4. Some customer profile joins are missing, which should be investigated before production use.
5. The model should be monitored for drift by geography, channel, merchant category, and customer segment.
6. The model should not be used as the sole basis for customer-impacting action.

## Recommended Production Controls

- Human review before blocking or escalating a customer-impacting case.
- Monitoring for recall, precision, queue size, and false positives.
- Segment-level performance monitoring by country, channel, merchant category, and customer cohort.
- Threshold review when investigation staffing changes.
- Drift monitoring for amount distributions, geo-distance patterns, and channel mix.
- Periodic benchmark and policy comparison.
- Audit logging of model score, threshold, top reasons, and investigator decision.

## Approval Recommendation

Approved for portfolio prototype and controlled demonstration.

Not approved for production deployment without:

- Real production data validation.
- Bias and fairness review.
- Security review.
- Model risk management review.
- Monitoring and incident response procedures.



