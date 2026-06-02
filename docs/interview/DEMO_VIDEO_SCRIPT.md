# Demo Video Script

Target length: 90 seconds to 2 minutes.

## Recording Setup

Open these before recording:

1. GitHub README
2. Live Vercel app
3. `docs/governance/model_card.md`

## Script

### 0:00-0:15 - Intro

Say:

> This is my Fraud Alert Control Tower, a JPMorgan-inspired synthetic-data project for explainable fraud alert prioritization.

Show:

- GitHub README title
- Live demo link

### 0:15-0:35 - Problem

Say:

> The business problem is that fraud investigators cannot review every transaction. So the goal is not just predicting fraud, but prioritizing which cases enter the review queue and explaining why.

Show:

- README business problem section

### 0:35-1:05 - App Demo

Say:

> In the app, a user can enter transaction details. The live scenario strip updates the fraud probability, risk tier, and recommended investigator action as the inputs change.

Show:

- Score tab
- Fraud probability
- Priority
- Why section

### 1:05-1:25 - Queue And Metrics

Say:

> The Queue tab turns model scores into investigator workflow. The Metrics tab shows model comparison. I selected the enhanced depth-2 AdaBoost because it improved PR-AUC and made the live risk score smoother while keeping review queue discipline.

Show:

- Queue tab
- Metrics tab

### 1:25-1:45 - Governance

Say:

> The Governance tab explains that this is decision support only. It would require human review, monitoring, validation, and model-risk approval before production.

Show:

- Governance tab

### 1:45-2:00 - Close

Say:

> The strongest part of this project is that it does not stop at prediction. It shows how fraud risk is scored, prioritized, explained, deployed, and governed.

Show:

- README or live app final view

## Upload Caption

Use this caption on LinkedIn or portfolio:

> Demo: Fraud Alert Control Tower, an explainable fraud alert prioritization prototype with model comparison, investigator-capacity thresholding, local explanations, governance docs, and a Vercel static app.
