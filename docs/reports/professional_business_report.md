# Professional Business Report - Fraud Alert Control Tower

## 1. Problem And Objective

Fraud investigation teams cannot review every transaction. The objective of this project is to prioritize the highest-risk transactions, explain why they are risky, and show the business trade-off between catching more fraud and creating more manual-review work.

This is positioned as a decision-support and prioritization tool, not an automatic blocking system.

## 2. Data And Modeling Approach

The project uses synthetic transaction, customer, and merchant data from the project kit. The pipeline:

1. Cleans and joins transaction, customer, and merchant tables at transaction level.
2. Removes identifiers, labels, and existing alert outputs from the model feature set to prevent leakage.
3. Engineers fraud-risk features such as transaction amount pattern, geographic distance, transaction hour, velocity-based activity, cross-border behavior, and merchant/category context.
4. Uses training-only feature selection and validation/test splits so the model is evaluated on unseen data.
5. Converts scores into an investigator queue using threshold and capacity policy instead of presenting the model as an automatic decision engine.

## 3. Professor Feedback Improvements Applied

The latest uplift work directly addressed the feedback received:

- Added behavioral features: `velocity_ratio`, `amt_per_txn_24h`, `far_and_new`, `night_crossborder`, `hour_sin`, and `hour_cos`.
- Added a leakage-aware merchant category fraud-rate feature using out-of-fold target encoding on training data only.
- Added model-aware validation permutation importance after mutual-information shortlisting.
- Added SQL production logic in `features/fraud_feature_view.sql` so the feature engineering can be explained as a warehouse-ready analyst workflow.
- Added measured validation evidence: calibration bins, false-positive rate by country/channel, and SLA policy coverage.
- Added this business report so the project leads with the trade-off, not only model scores.

The feature audit was treated as a disciplined improvement exercise: engineered features were tested, but the live app model was not replaced unless the uplift version clearly improved operational performance.

## 4. Key Findings

At the current operating policy shown in the app:

| Measure | Current Model Queue | Existing Alert Rule |
|---|---:|---:|
| Reviewed transactions | 74 | 22 |
| Fraud cases captured | 10 | 8 |
| False positives | 64 | 14 |
| Queue hit rate | 13.5% | 36.4% |
| Fraud capture | 25.0% | 20.0% |

The model finds more fraud cases, but it also creates more manual-review load. This is why the correct business framing is not "replace the old alert rule immediately." The correct framing is "use the model as a prioritization overlay or top-K pilot to help investigators work the riskiest alerts first."

## 5. Break-Even Review Economics

The current model queue captures 2 additional fraud cases compared with the existing alert rule, but it creates 52 additional reviews.

Assumption:

- Manual review cost: GBP 8 per case

Calculation:

- Extra review cost: 52 x GBP 8 = GBP 416
- Extra fraud cases captured: 2
- Break-even avoided loss per extra captured fraud: GBP 416 / 2 = GBP 208

Interpretation:

If each additional fraud case prevented avoids more than GBP 208 of loss, the additional review workload is financially justified. If avoided loss is below GBP 208, the model should be used more selectively, for example as a top-K prioritization layer rather than a broad replacement rule.

## 6. Validation Evidence

Additional evidence has been added to protect the uplift and answer likely risk-analyst questions.

| Evidence item | Result | Interpretation |
|---|---:|---|
| Brier score | 0.2192 | Score is useful for ranking, but not production odds |
| Expected calibration error | 0.4132 | Real-data calibration remains an approval gate |
| Highest country false-positive rate | BR 60.3% | Segment needs pilot monitoring for customer friction |
| Highest channel false-positive rate | P2P 7.5% | Channel-level friction should be tracked weekly |
| SLA policy coverage | 100.0% | Every routed case receives an urgency policy |

True SLA breach rate cannot be measured from the current synthetic dataset because it does not contain investigation created, assigned, and closed timestamps. That timestamp capture is listed as a production instrumentation requirement.

## 7. Recommendation

Recommended path:

- Use the model as a shadow-mode prioritization overlay.
- Keep human investigator review before any customer-impacting action.
- Compare the model queue against the existing alert rule for fraud capture, false positives, and investigator workload.
- Start with a limited top-K pilot so the highest-risk cases are reviewed first without overwhelming the team.

Not recommended:

- Do not use the model for automatic blocking.
- Do not claim production readiness from synthetic data.
- Do not replace the incumbent rule until real-data validation, calibration, and segment monitoring are complete.

## 8. Risks And Assumptions

| Risk | Control |
|---|---|
| Synthetic data may not represent real fraud behavior | Validate on real historical data before production |
| Scores are useful for ranking but not fully calibrated probabilities | Add probability calibration before production use |
| False positives create investigator workload and customer friction | Tune threshold by capacity and review cost |
| Country/channel features can behave like proxy-risk signals | Monitor false positives and fraud capture by segment |
| Fraud patterns can drift over time | Monitor score distribution, top drivers, queue hit rate, and fraud capture weekly |

## 9. Conclusion

The strongest value of this project is not just the model. It is the full control-tower workflow: score a transaction, explain the reason, route it into a capacity-aware queue, compare it against the old alert rule, and document the governance limits.

The final recommendation is a controlled pilot: use the model to prioritize suspicious cases and measure whether the extra fraud captured justifies the additional review cost.
