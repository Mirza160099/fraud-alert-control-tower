# Publish And Rehearse Guide

This is the exact next-step checklist for taking the clean project folder public.

## 1. Review The README

Open `README.md` and check:

- the screenshots render
- the problem statement is clear
- the synthetic-data disclaimer is visible
- the model metrics match the project outputs
- the live demo line still says `TODO` until Vercel is deployed

## 2. Create GitHub Repository

Recommended repository name:

```text
fraud-alert-control-tower
```

Recommended visibility:

```text
Public, after you confirm no private files are included.
```

## 3. Push This Folder To GitHub

From this folder:

```powershell
git init
git add .
git commit -m "Add fraud alert control tower portfolio project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fraud-alert-control-tower.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## 4. Deploy The App To Vercel

In Vercel:

1. Import the GitHub repository.
2. Set the project root directory to `./`.
3. Set framework preset to `Other`.
4. Deploy.
5. Open the deployed URL and test all tabs.

Expected smoke test:

- Score tab loads.
- High-risk scenario returns around `0.841`.
- Decision says `Review as fraud risk`.
- Priority is `Critical`.
- Queue, Metrics, and Governance tabs render.

If Vercel shows a 404, check that the project root is `./` and that `index.html` is visible in the deployment file list. The static app files are also duplicated in `app/` as a fallback.

## 5. Update README With Live Link

Current live demo:

```text
https://fraud-alert-control-tower-5cic.vercel.app
```

Then commit and push:

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
