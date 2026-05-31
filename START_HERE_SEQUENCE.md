# Start Here: Folder Sequence Guide

Use this file when you want to explain the project in order or revise it later in VS Code.

## Recommended Folder Name

Keep the main project folder named:

```text
fraud-alert-control-tower
```

This name is clear, professional, and safe. Avoid naming it `JPMorgan Project` or anything that sounds like an official bank repository, because this is a JPMorgan-inspired portfolio project, not an internal JPMorgan project.

## Do Not Rename These Folders Right Now

The current folder names are professional software-project names:

```text
src/
app/
assets/
artifacts/
docs/
presentation/
```

I recommend keeping them because:

- `src` is the standard place for Python source code.
- `app` is the static Vercel app folder.
- `assets` stores README screenshots.
- `artifacts` stores model outputs and evidence.
- `docs` stores governance, interview, deployment, and progress documents.
- `presentation` stores the PowerPoint deck.

If you rename them, some README links and deployment notes may need updating.

## Project Sequence

Study the project in this order.

### 1. README: The Story

Open:

```text
README.md
```

Purpose:

- explains the business problem
- shows screenshots
- links the live Vercel demo
- summarizes the model and governance

How to explain it:

> This README is the recruiter-facing summary of the project.

### 2. Source Code: The Python Pipeline

Open:

```text
src/
```

Most important files:

```text
src/fraud_pipeline.py
src/train_model.py
src/compare_models.py
src/explain_model.py
src/export_model_for_web.py
```

Purpose:

- clean the data
- join transactions, customers, and merchants
- engineer features
- select top features
- train models
- compare stronger models
- create explanations
- export the model for the browser app

How to explain it:

> The `src` folder is where the actual Python modeling work lives.

### 3. Modeling Artifacts: The Evidence

Open:

```text
artifacts/modeling/
```

Important folders:

```text
step_02_baseline/
step_03_model_selection/
step_04_explainability/
```

Purpose:

- top 10 feature list
- baseline metrics
- model comparison
- threshold analysis
- explainability outputs

How to explain it:

> The `artifacts` folder contains the evidence produced by the code.

### 4. Static App: The Demo

Open:

```text
app/
```

Also note that the same static app files exist at the repo root for Vercel deployment:

```text
index.html
styles.css
app.js
model.json
dashboard-data.json
```

Purpose:

- lets a user enter transaction details
- predicts fraud probability
- assigns priority tier
- explains why a transaction looks risky
- shows queue, metrics, and governance tabs

How to explain it:

> The app turns the model into an investigator-facing workflow.

### 5. Screenshots: The Visual Proof

Open:

```text
assets/
```

Purpose:

- stores screenshots used in the README
- helps recruiters understand the app without running it first

How to explain it:

> The `assets` folder contains the screenshots that make the GitHub README easy to scan.

### 6. Governance Docs: The Banking Layer

Open:

```text
docs/governance/
```

Important files:

```text
model_card.md
threshold_strategy_memo.md
governance_summary.md
```

Purpose:

- explains intended use
- documents limitations
- explains threshold strategy
- describes human review and monitoring

How to explain it:

> This is where I show that I understand responsible AI and model-risk thinking.

### 7. Interview Docs: Your Defense

Open:

```text
docs/interview/
```

Important files:

```text
interview_script.md
project_defense_guide.md
resume_linkedin_bullets.md
```

Purpose:

- practice the pitch
- answer technical questions
- prepare resume and LinkedIn wording

How to explain it:

> This folder helps me explain the project clearly in interviews.

### 8. Deployment Docs: How It Went Live

Open:

```text
docs/deployment/
```

Purpose:

- explains GitHub publishing
- explains Vercel deployment
- records deployment settings

How to explain it:

> The app is deployed as a static Vercel site, not as a Python server.

### 9. Progress Reports: The Build Journey

Open:

```text
docs/reports/
```

Purpose:

- shows the step-by-step project build history
- helps you remember how the work evolved

How to explain it:

> These reports document how I approached the project one step at a time.

### 10. Presentation: The Executive Story

Open:

```text
presentation/
```

Purpose:

- gives a polished executive walkthrough
- turns the project into a business story

How to explain it:

> The presentation is for a hiring manager or business stakeholder who wants the project story, not just the code.

## If You Really Want Numbered Folder Names

I do not recommend changing the live GitHub folder names right now, but for learning you can think of them like this:

```text
01_README_story              -> README.md
02_python_modeling_code      -> src/
03_model_outputs             -> artifacts/
04_static_web_app            -> app/ and root static files
05_screenshots               -> assets/
06_governance_docs           -> docs/governance/
07_interview_preparation     -> docs/interview/
08_deployment_docs           -> docs/deployment/
09_progress_reports          -> docs/reports/
10_executive_presentation    -> presentation/
```

## One-Line Explanation Of The Whole Project

> This project starts with raw fraud transaction data, cleans and models it in Python, compares models, chooses an investigator-capacity threshold, exports the model into a Vercel app, explains each prediction, and documents governance for responsible banking use.

## Best Study Routine

1. Read `README.md`.
2. Open the live Vercel demo.
3. Read `src/fraud_pipeline.py`.
4. Read `artifacts/modeling/step_03_model_selection/model_comparison.csv`.
5. Read `docs/governance/model_card.md`.
6. Practice with `docs/interview/project_defense_guide.md`.
7. Present with the PowerPoint in `presentation/`.
