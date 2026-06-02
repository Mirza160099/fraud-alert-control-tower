# Interview Script

## 30-Second Pitch

I built a JPMorgan-inspired fraud alert control tower that prioritizes suspicious transactions for investigator review. The project covers the full lifecycle: data cleaning, joins, feature engineering, top-10 feature selection, model comparison, threshold tuning for investigator capacity, local explanations, a Vercel-style prediction app, and governance documentation. I positioned the model as decision support rather than automatic enforcement, which is important in banking because fraud models need auditability, human review, and operational controls.

## 2-Minute Walkthrough

The business problem is that fraud teams cannot review every transaction, so a model should rank cases by risk and explain why a case deserves attention.

I started by profiling the synthetic transaction, customer, and merchant data. I found a 4.02% fraud rate, missing customer joins, and broken tenure values. Instead of dropping those records, I preserved the transaction grain and added missing-profile flags. I also excluded IDs, target fields, and the old `alert_generated` flag from model inputs to prevent leakage.

For feature selection, I used training-only mutual information and kept the top 10 source features. The strongest features included geographic distance, transaction country, synthetic identity score, merchant risk score, channel, transaction hour, device risk score, merchant profile risk, amount, and log amount.

I compared logistic regression, random forest, extra trees, gradient boosting, standard AdaBoost, and an enhanced depth-2 AdaBoost. The enhanced AdaBoost became the champion because it improved PR-AUC and produced smoother risk scores while still keeping the review queue disciplined.

Then I tuned the threshold as a business-control decision. At the recommended threshold of 0.7977, the model routed 74 test transactions for review, captured 25.0% of fraud, and produced a 13.5% hit rate. I also documented the exact top-5% queue, which had an 18.0% hit rate and 22.5% fraud capture.

I also added an alert-economics sensitivity. Using illustrative assumptions of $8 per review and $500 avoided loss per captured fraud, the champion policy catches two more fraud cases than the existing alert benchmark, adds 52 reviews, and produces an illustrative net impact of $584. I would not present that as production ROI, but it shows how thresholding becomes a business decision.

Finally, I exported the model to a static browser app. The app lets a user enter transaction details, predicts fraud risk, assigns a priority tier, produces an investigator brief, explains the top risk drivers, and recommends practical next actions such as monitoring, investigator review, step-up verification, or escalation. I also created a model card, threshold strategy memo, governance summary, and executive deck.

## Technical Deep Dive

The pipeline uses a controlled train-validation-test split. Feature selection is performed on training data only, which avoids leaking test-set information into the feature list. Numeric variables are imputed and scaled where needed, categorical variables are imputed and one-hot encoded, and model comparison is evaluated on the held-out test set.

The explainability layer uses global permutation importance to show which features influence model performance overall, plus local reference-value sensitivity to explain individual cases. For example, the app can show that a transaction is high risk because geographic distance is thousands of kilometers above the reference value and because the payment channel differs from the typical low-risk profile.

## Banking Framing

The banking point is that the threshold is not just a machine-learning setting. It controls review volume, staffing pressure, false positives, missed fraud, and customer friction. That is why I documented capacity thresholds, human review requirements, synthetic-data limitations, and monitoring controls.

## Strong Answer To "Why This Project?"

I chose fraud alert prioritization because it is a realistic banking analytics problem where model performance alone is not enough. A bank needs explainability, threshold governance, investigator workflow design, and model-risk controls. This project let me demonstrate both technical machine-learning ability and the judgment needed to deploy analytics responsibly in a financial-services environment.

## Strong Answer To "What Would You Improve Next?"

I would validate on real transaction data, add time-based backtesting, monitor drift by channel and country, calibrate probabilities, compare cost-sensitive objectives, add fairness and proxy-risk testing, and connect the queue to investigator feedback so the model can be monitored and retrained responsibly.

## Demo Flow

1. Open the README and explain the business problem.
2. Show that the app opens on a low-risk normal transaction.
3. Click Medium, High, and Critical presets to show the risk score escalating.
4. Point to the live probability, risk tier, investigator brief, reasons, and recommended next actions.
5. Open the Queue tab and explain review capacity.
6. Open Metrics and explain why the enhanced depth-2 AdaBoost was selected.
7. Open Governance and explain why this is decision support only.
8. Close with the executive deck and the model-card/threshold memo.
