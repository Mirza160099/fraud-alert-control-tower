# Resume And LinkedIn Bullets

## Resume Bullets

- Built an explainable fraud alert prioritization system using synthetic transaction, customer, and merchant data, covering data cleaning, joins, feature engineering, model comparison, threshold tuning, and governance documentation.
- Selected top 10 fraud-risk features using training-only mutual information, including geographic distance, transaction country, synthetic identity score, merchant risk score, channel, transaction hour, device risk, and transaction amount.
- Compared logistic regression, random forest, extra trees, gradient boosting, standard AdaBoost, and enhanced depth-2 AdaBoost models for imbalanced fraud detection; selected an enhanced AdaBoost champion based on PR-AUC and queue discipline.
- Tuned fraud review thresholds around investigator capacity, routing 74 held-out test transactions for review and capturing 25.0% of known fraud at the recommended threshold.
- Developed a Vercel-style static prediction app that accepts transaction inputs, returns fraud probability, priority tier, queue policy, and local model explanations without requiring a Python server at runtime.
- Created a responsible-AI governance pack including a model card, threshold strategy memo, monitoring controls, and decision-support limitations for fraud investigation use cases.

## Short LinkedIn Project Post

I completed a JPMorgan-inspired fraud alert prioritization project focused on explainable banking analytics.

The project goes beyond a basic fraud classifier. I built a full workflow that cleans and joins transaction, customer, and merchant data, selects the top 10 fraud-risk features, compares multiple models, tunes thresholds around investigator capacity, and deploys a Vercel-style browser app where users can score transactions and see why a case is risky.

Key components:

- Enhanced depth-2 AdaBoost champion model for fraud alert prioritization
- Top-10 feature selection using mutual information
- Investigator queue and threshold strategy
- Local explanations for high-risk cases
- Model card, governance summary, and threshold memo
- Static browser app for transaction scoring

The most important lesson: in banking, the model is only one part of the system. The threshold, review queue, human oversight, and monitoring controls are just as important as the prediction.

## GitHub Repo Description

Explainable fraud alert prioritization system with model comparison, capacity-based thresholding, local explanations, governance docs, and a Vercel-style static prediction app.

## Portfolio Card Text

Fraud Alert Control Tower: an explainable fraud-risk prioritization app that turns transaction data into investigator queues, model explanations, threshold policies, and responsible-AI governance artifacts.
