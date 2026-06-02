# Mock Interview Q&A

Practice these until you can answer naturally.

## 1. Tell me about your project.

I built a JPMorgan-inspired fraud alert control tower. It uses synthetic transaction, customer, and merchant data to score fraud risk, rank investigator queues, explain high-risk transactions, and document governance controls. The project includes Python data cleaning, feature engineering, model comparison, threshold tuning, explainability, a Vercel app, and responsible-AI documentation.

## 2. What problem were you solving?

Fraud teams cannot review every transaction. The problem is not only predicting fraud; it is deciding which cases deserve limited investigator attention and explaining why they entered the queue.

## 3. What are the main folders?

`src` contains Python code. `artifacts` contains model outputs. `app` contains the static web app. `assets` contains screenshots. `docs` contains governance, deployment, and interview docs. `presentation` contains the executive deck.

## 4. Where is the data cleaning?

The main cleaning code is in `src/fraud_pipeline.py`. The explanation is in `docs/reports/progress_report_step_02.md`.

## 5. What cleaning did you do?

I parsed timestamps, normalized countries, joined customer and merchant profiles, preserved missing joins using flags, handled broken tenure data, created time features, created log amount, created cross-border indicators, and removed leakage columns.

## 6. What was leakage in this project?

The old `alert_generated` field could leak the previous alerting system into the model. IDs and target columns were also removed from the model features.

## 7. What were the top features?

The top features included geographic distance, transaction country, synthetic identity score, merchant risk score, channel, transaction hour, device risk score, merchant profile risk score, transaction amount, and log amount.

## 8. Why mutual information?

Mutual information can rank numeric and categorical features without assuming a linear relationship. I used it on training data only to avoid test leakage.

## 9. What models did you compare?

I compared logistic regression, random forest, extra trees, gradient boosting, standard AdaBoost, and enhanced depth-2 AdaBoost.

## 10. Why did enhanced AdaBoost win?

The enhanced depth-2 AdaBoost improved PR-AUC and made the live risk score smoother than the original stump-based AdaBoost, while still keeping the review queue disciplined.

## 11. What does queue discipline mean?

It means the model does not simply flag too many cases. In fraud operations, investigators have limited capacity, so a useful model must balance fraud capture with review volume.

## 12. What does threshold 0.7977 mean?

It is the fraud-risk probability cutoff used to route a transaction into review. It was selected around investigator-capacity assumptions.

## 13. What happened at that threshold?

On the held-out test set, it routed 74 transactions for review and captured 25.0% of known fraud.

## 14. Why is accuracy not enough?

Fraud is rare, so a high-accuracy model can still miss many fraud cases. Precision, recall, F1, PR-AUC, and operational queue size are more useful.

## 15. How does the app work?

The Python model was exported into `model.json`. The static app loads `model.json` and `dashboard-data.json`, takes user inputs, calculates fraud risk in JavaScript, assigns a priority tier, and explains the top drivers.

## 16. Why Vercel instead of Streamlit?

The goal was a clean portfolio deployment. A static Vercel app is easy for recruiters to open, does not require a Python server, and feels more like a product interface.

## 17. What is explainability here?

Global explainability uses feature importance to show which signals matter overall. Local explainability compares a case to a reference profile and explains which feature changes increased the risk score.

## 18. What is the biggest limitation?

The dataset is synthetic, so the model is not production-ready. It demonstrates workflow and judgment, but production would require real-data validation.

## 19. What governance did you add?

I created a model card, threshold strategy memo, governance summary, human-review framing, monitoring controls, and production limitations.

## 20. What would you improve next?

I would add time-based validation, probability calibration, drift monitoring, cost-sensitive optimization, fairness/proxy testing, and investigator feedback loops.

## 21. What did you personally learn?

I learned that a banking model needs more than prediction quality. It needs explainability, threshold governance, human review, monitoring, and clear communication.

## 22. Why is this relevant to JPMorgan?

It reflects financial-services concerns: fraud risk, alert prioritization, model governance, responsible AI, and operational controls.

## 23. Can you modify it live?

Yes. I can change the threshold, add a feature to the app, update the README, explain the Python cleaning pipeline, or adjust the governance docs.

## 24. How would you explain this to a non-technical manager?

This tool helps investigators decide which suspicious transactions to review first and explains why each case is risky.

## 25. How would you explain this to a technical interviewer?

It is a scikit-learn fraud prioritization pipeline with training-only feature selection, imbalanced model comparison, threshold selection around capacity, model export to static JSON, browser-side scoring, and governance documentation.
