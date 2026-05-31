# Deployment Notes

Use the repository root, `./`, as the Vercel project root.

The app is static and runs in the browser using:

- `model.json`
- `dashboard-data.json`
- `app.js`

No Python server is required for the deployed app.

Fallback: the same static app files also exist under `app/`. If you deploy from that folder, set the Vercel root directory to `app`.
