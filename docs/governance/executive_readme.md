# Step 07 Executive README - Governance Pack

## Deliverables

This folder contains the responsible-AI and control documentation for the fraud alert prioritization project.

Files:

- `model_card.md`
- `threshold_strategy_memo.md`
- `governance_summary.md`

## How These Help In An Interview

These documents show that the project goes beyond modeling. They demonstrate:

- awareness of leakage and model risk
- ability to explain threshold trade-offs
- understanding of fraud operations capacity
- human-in-the-loop governance thinking
- responsible AI communication

## Suggested Interview Framing

Use this line:

> I treated the model as an operational control, not just a classifier. I documented how it should be used, what its limits are, how thresholds affect investigator workload, and what monitoring would be required before production use.

## Key Numbers

- Champion model: `adaboost_depth2_weighted`
- Recommended threshold: `0.7977`
- Target review capacity: `5%`
- Test hit rate at threshold: `13.5%`
- Test fraud capture at threshold: `25.0%`
- Exact top-5% queue hit rate: `18.0%`
- Exact top-5% fraud capture: `22.5%`
- Illustrative alert-economics net impact: `$584`

## Important Honesty Point

Do not claim this model is production-ready. The strongest professional framing is:

> This is a disciplined prototype that demonstrates the full lifecycle: data cleaning, feature selection, model comparison, thresholding, explainability, dashboarding, and governance.
