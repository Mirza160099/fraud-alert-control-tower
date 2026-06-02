# Progress Report - Step 05: Vercel-Style Prediction Interface

## What We Built

This step created a static, Vercel-ready fraud prediction interface. It replaces Streamlit with a browser-based app that can be deployed as plain HTML, CSS, JavaScript, and JSON.

## App Capabilities

The interface lets a user enter:

1. Transaction amount
2. Currency
3. Transaction country
4. Channel
5. Transaction hour
6. Geographic distance
7. Device risk score
8. Synthetic identity score
9. Merchant risk score
10. Merchant profile risk score

The app then returns:

- Fraud-risk probability
- Legitimate vs review decision
- Priority tier
- Capacity policy
- Plain-English explanation
- Local feature contribution bars

## Model Deployment Approach

The Step 3 champion model is an AdaBoost classifier inside a scikit-learn preprocessing pipeline. Instead of requiring a Python API server, the trained model was exported to `model.json`.

The browser app uses that JSON to reproduce:

- numeric imputation
- standard scaling
- categorical one-hot encoding
- Depth-2 AdaBoost browser inference
- probability scoring
- threshold-based review decision
- local explanation deltas

This makes the app easy to deploy on Vercel because no backend runtime is required.

## Files Created

- `index.html`
- `styles.css`
- `app.js`
- `model.json`
- `vercel.json`
- `README.md`

The reusable model exporter lives in:

- `src/export_model_for_web.py`

## Verification

Python champion model score for the high-risk scenario:

- the live model probability shown in the app

Browser-exported JSON model score for the same scenario:

- the live model probability shown in the app

Browser testing confirmed:

- app loads successfully
- high-risk scenario returns `Review as fraud risk`
- high-risk scenario priority is `Critical`
- low-risk scenario returns `Monitor as likely legitimate`
- console error logs are clean
- explanation text is readable for both risk and monitor outcomes

## Deployment Notes

Deploy this folder as the Vercel project root:

```text
outputs/step_05_vercel_app
```

No Streamlit server is needed. No Python API is needed for this version.

## Interview Talking Point

I converted the trained model into a lightweight browser inference artifact, which allowed the fraud scoring experience to run on a Vercel-style frontend. That shows I can connect machine learning, operational decisioning, and deployable product thinking rather than stopping at a notebook.
