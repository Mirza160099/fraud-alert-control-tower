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
  outputs/
    step_02_modeling/
    step_03_model_selection/
    step_04_explainability/
    step_05_vercel_app/
    step_07_governance/
    step_08_executive_presentation/
    step_09_portfolio_package/
```

## Files To Highlight

- `outputs/step_09_portfolio_package/README.md`
- `outputs/step_09_portfolio_package/interview_script.md`
- `outputs/step_09_portfolio_package/resume_linkedin_bullets.md`
- `outputs/step_07_governance/model_card.md`
- `outputs/step_07_governance/threshold_strategy_memo.md`
- `outputs/step_08_executive_presentation/fraud-alert-control-tower-executive-story.pptx`
- `outputs/step_05_vercel_app/index.html`

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
7. `Add recruiter portfolio package`

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
