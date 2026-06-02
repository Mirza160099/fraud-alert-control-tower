# Publish And Rehearse Guide

This is the current checklist for confirming the published project, keeping GitHub/Vercel updated, and rehearsing the demo.

## 1. Review The README

Open `README.md` and check:

- the screenshots render
- the problem statement is clear
- the synthetic-data disclaimer is visible
- the model metrics match the project outputs
- the live demo link points to `https://fraud-alert-control-tower-5cic.vercel.app`

## 2. Confirm GitHub Repository

Repository:

```text
https://github.com/Mirza160099/fraud-alert-control-tower
```

Current visibility:

```text
Public
```

## 3. Push Updates To GitHub

From this folder:

```powershell
git status
git push origin main
```

Use this whenever local commits are ahead of GitHub.

## 4. Deploy The App To Vercel

In Vercel:

1. Import the GitHub repository.
2. Set the project root directory to `./`.
3. Set framework preset to `Other`.
4. Deploy.
5. Open the deployed URL and test all tabs.

Expected smoke test:

- Score tab loads.
- Critical scenario returns around `0.850`.
- Decision says `Review as fraud risk`.
- Priority is `Critical`.
- Queue, Metrics, and Governance tabs render.

If Vercel shows a 404, check that the project root is `./` and that `index.html` is visible in the deployment file list. The static app files are also duplicated in `app/` as a fallback.

## 5. Confirm README Live Link

Current live demo:

```text
https://fraud-alert-control-tower-5cic.vercel.app
```

If the link changes, update `README.md`, then commit and push:

```powershell
git add README.md
git commit -m "Add live Vercel demo link"
git push
```

## 6. Rehearse The Demo

Use this order:

1. README: explain the business problem.
2. Score tab: show transaction input and fraud risk result.
3. Queue tab: explain investigator capacity.
4. Metrics tab: explain model comparison.
5. Governance tab: explain responsible use.
6. Executive deck: close with the operating-control story.

## 7. Say This In Interviews

> I treated the model as an operational control, not just a classifier. The project shows how fraud risk is scored, how review capacity drives thresholds, how investigators receive explanations, and what governance would be required before production use.

## 8. Do Not Say This

Avoid:

- "This is production ready."
- "This was built for JPMorgan."
- "The model can automatically block transactions."

Use:

> This is a JPMorgan-inspired synthetic-data prototype demonstrating explainable fraud alert prioritization, threshold governance, and investigator workflow design.
