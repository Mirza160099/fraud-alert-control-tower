# Fraud Alert Control Tower - Vercel App

Static prediction interface for the fraud alert prioritization project.

## Views

- `Score`: transaction input, prediction, priority, and local explanation.
- `Queue`: investigator queue summary and highest-risk cases.
- `Metrics`: model comparison, global drivers, and capacity thresholds.
- `Governance`: model-card summary, threshold policy, and monitoring controls.

## Run Locally

```powershell
python -m http.server 4173
```

Then open:

```text
http://localhost:4173
```

## Deploy To Vercel

Deploy this folder as the Vercel project root:

```text
outputs/step_05_vercel_app
```

The app runs entirely in the browser using `model.json`, which was exported from the Step 3 champion model. Dashboard and queue data are loaded from `dashboard-data.json`.
