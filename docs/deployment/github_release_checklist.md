# GitHub Release Checklist

## Repository Name

Recommended:

```text
fraud-alert-control-tower
```

## Recommended Repository Structure

```text
fraud-alert-control-tower/
  README.md
  requirements.txt
  src/
    fraud_pipeline.py
    train_model.py
    model_selection.py
    compare_models.py
    explainability.py
    explain_model.py
    export_model_for_web.py
    export_dashboard_data.py
  app/
  assets/
  artifacts/modeling/
  docs/governance/
  docs/deployment/
  docs/reports/
  presentation/
```

## Files To Highlight

- `README.md`
- `docs/governance/model_card.md`
- `docs/governance/threshold_strategy_memo.md`
- `docs/governance/governance_summary.md`
- `presentation/fraud-alert-control-tower-executive-story.pptx`
- `index.html`
- `app/index.html`

## README Must Include

- Clear problem statement
- Synthetic-data disclaimer
- Screenshots
- Top 10 features
- Model comparison table
- Threshold strategy
- Explainability explanation
- Governance summary
- Local run instructions
- Vercel deployment instructions

## Suggested GitHub Topics

```text
fraud-detection
explainable-ai
machine-learning
model-governance
responsible-ai
financial-services
scikit-learn
vercel
portfolio-project
```

## Commit Sequence

Use clear commits:

1. `Add fraud modeling pipeline`
2. `Add model comparison and threshold tuning`
3. `Add explainability outputs`
4. `Add static fraud control tower app`
5. `Add governance documentation`
6. `Add executive presentation`
7. `Polish recruiter portfolio package`

## Before Making The Repo Public

- Confirm no private data or personal secrets are present.
- Confirm `.venv` is not committed.
- Confirm raw data is allowed to be shared.
- Confirm README says the project is synthetic and not affiliated with JPMorgan Chase.
- Confirm screenshots render correctly on GitHub.
- Confirm the Vercel deployment URL works.

## Recruiter Review Test

Ask whether a recruiter can answer these questions in under 60 seconds:

- What problem does this project solve?
- What did you build?
- What model did you use?
- How does the app work?
- What makes it responsible and banking-relevant?
- Where is the demo?

If the answer is yes, the project is GitHub-ready.
