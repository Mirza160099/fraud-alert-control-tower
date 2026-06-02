# Final Rehearsal Packet

Use this file before interviews, recruiter calls, LinkedIn posts, and demo recordings.

## Your Core Positioning

Say this clearly:

> This is a JPMorgan-inspired synthetic-data prototype. I built it to demonstrate explainable fraud alert prioritization, threshold governance, and investigator workflow design.

Do not say:

> This is a production JPMorgan model.

## 15-Second Version

> I built a fraud alert control tower that scores transactions, ranks investigator queues, explains why a case is risky, and documents the governance needed before a banking model could be used responsibly.

## 30-Second Version

> I built a JPMorgan-inspired fraud alert control tower using synthetic transaction, customer, and merchant data. The project includes data cleaning, joins, feature engineering, top-10 feature selection, model comparison, threshold tuning around investigator capacity, local explanations, a Vercel app, and governance documentation. The main idea is that fraud detection is not only a prediction problem. It is an operating-control problem because the threshold affects review workload, missed fraud, false positives, and customer friction.

## 2-Minute Version

> I started with a synthetic fraud dataset containing transactions, customers, and merchants. The business problem was that investigators cannot review every transaction, so the goal was to prioritize alerts, not just predict fraud.
>
> First, I profiled and cleaned the data. I parsed timestamps, normalized country labels, preserved the transaction grain, left-joined customer and merchant profiles, added missing-profile flags, handled broken tenure data, created time features, created log amount, and removed leakage fields like IDs, target, and the old alert flag.
>
> Next, I selected the top 10 features using mutual information on training data only. The key signals included geographic distance, transaction country, synthetic identity score, merchant risk score, channel, transaction hour, device risk, merchant profile risk, and transaction amount.
>
> Then I compared several models: logistic regression, random forest, extra trees, gradient boosting, standard AdaBoost, and enhanced depth-2 AdaBoost. I selected the enhanced AdaBoost because it improved PR-AUC and produced smoother risk scores while keeping the review queue disciplined.
>
> After that, I tuned the threshold around investigator capacity. The recommended threshold was 0.7977. On the held-out test set, it routed 74 transactions for review and captured 25.0% of known fraud. This matters because thresholding is a business-control decision, not just a model setting.
>
> I added an alert-economics sensitivity as the final business layer. With illustrative assumptions of $8 review cost and $500 avoided loss per captured fraud, the champion policy catches two more fraud cases than the existing alert benchmark and produces an illustrative net impact of $584. I would not call that production ROI, but it shows I understand the financial trade-off behind thresholds.
>
> Finally, I exported the trained model into a static Vercel-style app. The app lets a user enter transaction details, returns a fraud probability, assigns a priority tier, and explains the main drivers. I also created a model card, threshold strategy memo, governance summary, and executive deck to show how the model should be reviewed responsibly.

## Live Demo Click Path

1. Open the GitHub README.
2. Point to the live Vercel demo link.
3. Open the live app.
4. On the Score tab, show that the app opens on a low-risk normal transaction.
5. Click Medium, High, and Critical to show escalation.
6. Point to the live fraud probability, risk tier, and recommended action.
7. Read the explanation: geographic distance and P2P channel.
8. Open Queue.
9. Explain the review queue and hit rate.
10. Open Metrics.
11. Explain why enhanced AdaBoost was chosen.
12. Open Governance.
13. Say this is decision support only and not production-ready.

## What To Say On Each Tab

### Score

> This is where a user enters transaction details. The app runs the exported model in the browser and returns a fraud-risk probability, priority tier, and explanation.
> I added Low, Medium, High, and Critical presets so reviewers can see the model separate normal activity from escalating fraud risk.

### Queue

> This turns model scores into an investigator workflow. Fraud teams have limited capacity, so the model has to prioritize which cases enter the queue.

### Metrics

> This shows the model comparison. I did not just pick the highest recall model because that can flood investigators with false positives. I selected the model with better queue discipline.

### Governance

> This is the responsible-AI layer. The model is decision support only, requires human review, and would need real-data validation, drift monitoring, audit logs, and model-risk approval before production.

## Questions You Must Be Ready For

### Did you code this yourself?

Best answer:

> I built the project end to end as a portfolio capstone. I structured the repo, developed and reviewed the modeling pipeline, generated the outputs, built the static app, deployed it, and documented governance. I also used AI as a coding assistant and reviewer, but I own the project decisions and can explain or modify the code.

### Where is data cleaning?

> The main cleaning pipeline is in `src/fraud_pipeline.py`. The explanation is in `docs/reports/progress_report_step_02.md`. The outputs are in `artifacts/modeling/step_02_baseline`.

### What did you clean?

> I parsed timestamps, normalized country labels, joined customer and merchant profiles, preserved missing-profile flags, handled broken tenure values, added time and amount features, and removed leakage fields.

### Why did you exclude `alert_generated`?

> Because it represents the old alerting system. If I trained on it, the model could learn the old rule instead of learning independent fraud-risk signals.

### Why use top 10 features?

> I wanted the model and app to remain explainable. A small feature set makes it easier to explain why a transaction enters the review queue.

### Why Enhanced AdaBoost?

> The first AdaBoost model was too jumpy in the live app because it used stumps. The enhanced depth-2 version improved PR-AUC, gave smoother probabilities, and still kept the queue smaller than the highest-recall random forest.

### Why not random forest if it had higher recall?

> Random forest captured more fraud but created a much larger review queue. In a real fraud team, capacity matters, so I selected a model with better operating discipline.

### What does threshold 0.7977 mean?

> It is the probability cutoff used to decide which cases enter review. It was selected around investigator-capacity assumptions, not just model accuracy.

### Why did you add alert economics?

> Because a fraud model changes both investigation workload and financial risk. The economics panel shows the incremental reviews, incremental fraud caught, review-cost assumption, and illustrative net impact, so the project feels like a banking decision tool rather than only a model demo.

### What is the biggest limitation?

> The data is synthetic, so this is not production-ready. It demonstrates the workflow and controls, but real deployment would require real-data validation, calibration, monitoring, and model-risk approval.

### What would you improve next?

> I would add time-based validation, probability calibration, cost-sensitive modeling, drift monitoring, fairness/proxy testing, and investigator feedback loops.

## 5-Minute Practice Routine

1. Read the 15-second version once.
2. Read the 30-second version once.
3. Say the 2-minute version without reading.
4. Open the live app and click through all four tabs.
5. Answer these five questions aloud:
   - What problem did I solve?
   - What cleaning did I do?
   - Why enhanced AdaBoost?
   - Why does thresholding matter?
   - Why is this not production-ready?

## Confidence Checklist

You are ready when you can explain:

- the business problem
- the data cleaning
- the top 10 features
- the model comparison
- the threshold strategy
- the Vercel app
- the governance docs
- the limitations
- what you would improve next

## Closing Line

> The strongest part of this project is that it does not stop at prediction. It shows how fraud risk is scored, prioritized, explained, deployed, and governed in a banking-style workflow.
