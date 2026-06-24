# Professor Feedback Completion Checklist

This checklist maps the uplift plan to the final project evidence.

| Feedback item | Status | Evidence |
|---|---|---|
| Prune/review harmful features | Complete | `src/model_selection.py`, `artifacts/modeling/step_03_professor_uplift/validation_permutation_importance.csv` |
| Add behavioral-ratio features | Complete | `src/fraud_pipeline.py` |
| Add cyclical hour encoding | Complete | `src/fraud_pipeline.py` |
| Add leakage-aware merchant category encoding | Complete | `src/fraud_pipeline.py` |
| Use MI then validation permutation importance | Complete | `src/model_selection.py`, `artifacts/modeling/step_03_professor_uplift` |
| Add SQL feature view | Complete | `features/fraud_feature_view.sql` |
| Add feature dictionary/reconciliation narrative | Complete | `docs/governance/model_card.md` |
| Lead with honest trade-off | Complete | `README.md`, `docs/reports/professional_business_report.md` |
| Add break-even analysis | Complete | `README.md`, `docs/governance/threshold_strategy_memo.md`, `docs/reports/professional_business_report.md` |
| Recommend overlay/top-K pilot, not replacement | Complete | `README.md`, `docs/governance/threshold_strategy_memo.md`, `docs/reports/professional_business_report.md` |
| Create standalone business report | Complete | `docs/reports/professional_business_report.docx` |
| Add calibration evidence | Complete | `artifacts/modeling/validation_evidence/calibration_curve.csv` |
| Add measured false-positive segment table | Complete | `artifacts/modeling/validation_evidence/false_positive_rate_by_country.csv`, `false_positive_rate_by_channel.csv` |
| Add SLA/turnaround evidence | Complete with data limitation disclosed | `artifacts/modeling/validation_evidence/sla_policy_coverage.csv`, Metrics tab validation evidence |
| Add real SHAP | Not added in this environment | Current app uses local sensitivity explanations; real SHAP remains the next production-grade technical upgrade |

## Final Positioning

The final project should be presented as a fraud-prioritization control tower:

- It ranks suspicious transactions for investigator review.
- It explains why a case is risky.
- It compares the model against the incumbent alert rule.
- It converts thresholds into review capacity, false-positive load, and break-even economics.
- It documents governance limits, calibration needs, segment monitoring, and human-review controls.

The project is intentionally framed as a monitored pilot / prioritization overlay, not an automatic fraud-blocking system.
