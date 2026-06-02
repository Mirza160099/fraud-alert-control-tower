# Progress Report - Step 06: Investigator Control Tower

## What We Added

This step upgraded the Vercel-style app from a single transaction scorer into an investigator-facing control tower.

The app now has four tabs:

1. `Score` - enter a transaction and receive a fraud-risk prediction.
2. `Queue` - review top-risk cases and operational queue KPIs.
3. `Metrics` - compare models, capacity thresholds, and global feature importance.
4. `Governance` - review model-card summary, threshold policy, and monitoring controls.

## Data Added

The new dashboard file is:

```text
dashboard-data.json
```

It is generated from the Step 3 and Step 4 artifacts:

- `model_comparison.csv`
- `capacity_thresholds.csv`
- `champion_test_predictions.csv`
- `case_review_explanations.csv`
- `global_feature_importance.csv`

The exporter script is:

```text
src/export_dashboard_data.py
```

## Queue KPIs

The queue view currently shows:

- Review queue size: `74`
- Frauds in queue: `10`
- Queue hit rate: `13.5%`
- Missed by old alert among displayed top cases: `10`

## Metrics View

The metrics tab now shows:

- model comparison table
- 5% capacity threshold table
- global feature importance bars

The capacity table is sorted by validation F1, so the Step 3 champion appears first:

- `adaboost_depth2_weighted`
- threshold `0.798`
- test reviews `74`
- test hit rate `13.5%`
- test fraud capture `25.0%`
- exact top-K hit rate `20.0%`

## Browser Verification

Verified in the in-app browser:

- Score tab loads and predicts.
- Queue tab displays KPI cards and 15 top-risk cases.
- Metrics tab displays 5 model rows and 5 capacity rows.
- Capacity table puts the champion first.
- Browser console errors: none.

## Interview Talking Point

This is now more than a model demo. It shows the operating layer a fraud team needs: case prioritization, capacity-based thresholds, model comparison, and investigator-readable rationale in one deployable interface.
