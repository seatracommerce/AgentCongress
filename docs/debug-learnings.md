# Debug Learnings

## NEXT_PUBLIC_API_URL not reaching Next.js on Cloud Run

- **Problem**: Frontend deployed to Cloud Run showed "No debates yet" and backend received no requests from frontend.
- **Symptoms**: Frontend page loaded fine (200 OK), backend had zero GET /debates or GET /bills logs, `NEXT_PUBLIC_API_URL` not visible in Cloud Run environment variables.
- **Root cause**: Three compounding issues:
  1. `deploy-frontend.sh` writes `frontend/.env.production.local` to pass `NEXT_PUBLIC_API_URL`, but that file is excluded by `frontend/.dockerignore` (`.env*.local` rule), so it never reaches the Docker build.
  2. `--set-build-env-vars` in `gcloud run deploy` does not automatically pass values as Docker `ARG` — the Dockerfile was missing `ARG NEXT_PUBLIC_API_URL` and `ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL` in the builder stage.
  3. Without the value baked in, Next.js inlines `undefined` and falls back to `http://localhost:8000`, which fails silently (errors caught and return empty array).
- **Solution**: Set `NEXT_PUBLIC_API_URL` as a **runtime environment variable** on the Cloud Run frontend service. Since `page.tsx` is a server component running in Node.js, it reads `process.env` at runtime:
  ```bash
  gcloud run services update agentcongress-frontend \
    --region=us-central1 \
    --project=agentcongress \
    --set-env-vars="NEXT_PUBLIC_API_URL=https://your-backend.run.app"
  ```
  No redeploy needed — takes effect immediately.
- **Alternative (build-time fix)**: Add to `frontend/Dockerfile` builder stage:
  ```dockerfile
  ARG NEXT_PUBLIC_API_URL
  ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
  ```
  Then deploy with `--set-build-env-vars="NEXT_PUBLIC_API_URL=..."`. Or create `frontend/.env.production` (not `.env.production.local`) — this file is NOT in `.dockerignore` and gets picked up at build time.
- **Date**: 2026-02-24
