# Vercel Deployment Checklist

## Deployment Folder

Use the repository root as the Vercel project root:

```text
.
```

The root contains:

- `index.html`
- `styles.css`
- `app.js`
- `model.json`
- `dashboard-data.json`
- `vercel.json`
- `README.md`

## Why This Works On Vercel

The app is fully static. The trained Python model was exported into `model.json`, and the browser app runs the scoring logic directly in JavaScript.

No Streamlit server is required.

No Python backend is required at runtime.

## Local Smoke Test

From the repository root:

```powershell
python -m http.server 4173
```

Open:

```text
http://localhost:4173
```

Expected smoke-test result:

- The Score tab loads.
- The high-risk scenario returns fraud probability around `0.841`.
- The decision says `Review as fraud risk`.
- Priority is `Critical`.
- Queue, Metrics, and Governance tabs render.

## Vercel Steps

1. Push the project to GitHub.
2. Go to Vercel.
3. Import the GitHub repository.
4. Set the project root to `./`.
5. Set framework preset to `Other`.
6. Deploy.
7. Open the deployed URL.
8. Test Score, Queue, Metrics, and Governance views.

## Post-Deployment Checks

- `model.json` loads successfully.
- `dashboard-data.json` loads successfully.
- Score tab produces the same high-risk result as local testing.
- No browser console errors.
- README links to the deployed Vercel URL.

## Important Framing

Do not describe this as a production banking model. Use this phrasing:

> This is a synthetic-data prototype that demonstrates the full lifecycle of explainable fraud alert prioritization, including model development, thresholding, dashboarding, and governance.
