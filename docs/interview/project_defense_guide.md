# Project Defense Guide

Use this guide to explain the project confidently and honestly in interviews.

## The Main Message

Do not try to prove ownership by saying "I typed every line from memory." Prove ownership by showing that you understand every major decision, can navigate the codebase, can explain trade-offs, and can modify the project live if asked.

Best framing:

> I built this project end to end as a portfolio capstone. I structured the folders, developed the modeling pipeline, evaluated multiple models, exported the model into a static app, created the governance documents, and deployed it on Vercel. The key learning was treating fraud detection as an operational control problem, not just a prediction task.

If asked whether you used AI tools:

> I used AI as a coding assistant and reviewer, but I owned the project decisions, reviewed the code, ran the outputs, fixed deployment issues, and can explain the pipeline end to end.

## How To Walk Through The Repo

Start with the README.

Say:

> The README is the recruiter-facing summary. It explains the business problem, screenshots, top features, model comparison, threshold strategy, explainability, governance, and live demo.

Then open `src/`.

Say:

> The `src` folder contains the Python pipeline. `fraud_pipeline.py` handles cleaning, joining, feature engineering, and reusable helpers. `train_model.py` trains the baseline. `compare_models.py` compares stronger models. `explain_model.py` creates explainability outputs. `export_model_for_web.py` exports the model to browser-readable JSON.

Then open `app/` or root `index.html`.

Say:

> The app is static HTML, CSS, and JavaScript. It loads `model.json` and `dashboard-data.json`, takes user inputs, calculates fraud risk in the browser, assigns a priority tier, and explains the main drivers.

Then open `docs/governance/`.

Say:

> This is the responsible-AI layer: model card, threshold memo, and governance summary. It explains intended use, limitations, human review, monitoring, and why this should not be treated as production-ready.

Then open `presentation/`.

Say:

> This is the executive story deck. It turns the technical project into a business and controls narrative.

## 2-Minute Explanation

> I started with a synthetic fraud dataset containing transactions, customers, and merchants. The business problem was that investigators cannot review every transaction, so the goal was not just fraud prediction but alert prioritization.
>
> First, I profiled the data and cleaned it. I normalized country labels, preserved all transactions at transaction grain, left-joined customer and merchant profiles, added missing-profile flags, handled broken tenure values, created time features, created log amount, and removed leakage fields like IDs, target, and the old alert flag.
>
> Then I selected the top 10 features using mutual information on training data only. The strongest signals included geographic distance, transaction country, synthetic identity score, merchant risk score, channel, transaction hour, device risk, merchant profile risk, and transaction amount.
>
> I trained a baseline and compared stronger models including logistic regression, random forest, extra trees, gradient boosting, and AdaBoost. I selected AdaBoost because it had the strongest F1 among the tested models while keeping the review queue more disciplined than the highest-recall random forest.
>
> After that, I tuned the threshold around investigator capacity. This is important because in fraud operations the threshold controls workload, false positives, missed fraud, and customer friction. The recommended threshold was 0.7795.
>
> Finally, I exported the model into a static Vercel-style app. The user can enter transaction details, get a fraud probability, priority tier, and explanation. I also created governance documents and an executive deck to show how the model should be used responsibly.

## Questions They Might Ask

### Why did you remove `alert_generated`?

Because it represents an existing alert decision. If I train on it, the model may learn the old alert rule instead of learning transaction risk. That would create leakage and make the model look better than it really is.

### Why mutual information?

Mutual information is useful for ranking both numeric and categorical signals against the target without assuming a linear relationship. I used it on training data only to avoid test leakage.

### Why AdaBoost?

AdaBoost gave the strongest F1 among the tested models while keeping the queue smaller than the random forest. Random forest captured more fraud but created a much larger review queue, which is operationally expensive.

### Why is the threshold a business decision?

Because the threshold controls how many cases investigators review. A lower threshold catches more fraud but increases false positives and workload. A higher threshold reduces workload but may miss fraud.

### Is this production-ready?

No. It is a disciplined synthetic-data prototype. Production would require real transaction validation, monitoring, fairness/proxy review, model-risk approval, audit logs, calibration, and human-in-the-loop controls.

### What would you improve next?

I would add time-based validation, probability calibration, drift monitoring, cost-sensitive optimization, investigator feedback loops, and more robust fairness/proxy testing.

## How To Prove You Understand It

Be ready to do these live:

1. Open `src/fraud_pipeline.py` and point to the cleaning steps.
2. Open `artifacts/modeling/step_02_baseline/top_10_features_mutual_info.csv` and explain the top features.
3. Open `artifacts/modeling/step_03_model_selection/model_comparison.csv` and explain why AdaBoost was chosen.
4. Open the Vercel app and score the high-risk scenario.
5. Open `docs/governance/model_card.md` and explain why it is decision support only.

## How To Build Your Next Project Yourself

Use this repeatable blueprint:

1. Define the business problem in one sentence.
2. Identify the user of the system.
3. Inspect the data shape, missingness, target rate, and obvious leakage.
4. Write a cleaning pipeline.
5. Join data carefully and keep the modeling grain clear.
6. Create features that match the business problem.
7. Split train, validation, and test.
8. Select features using training data only.
9. Train a simple baseline.
10. Compare stronger models.
11. Tune the threshold based on business cost or capacity.
12. Add explainability.
13. Build a simple app.
14. Write governance and limitations.
15. Create a README, screenshots, and interview story.
16. Deploy.
17. Rehearse the demo.

## The Confidence Rule

You are ready when you can answer:

- What problem did I solve?
- What data did I use?
- What cleaning did I apply?
- What features mattered?
- What model won and why?
- What threshold did I choose and why?
- How does the app make predictions?
- What are the limitations?
- What would I improve next?

If you can answer those without reading a script, you can defend the project.
