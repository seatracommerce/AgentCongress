# AgentCongress

AI-simulated multi-caucus debates on active US Congress bills.

Five real-world House caucus personas (powered by Claude) debate bills that reach the floor or pass committee. Results are posted as tweet threads and displayed on a web app with full transcripts and weighted vote tallies.

---

## How it works

1. **Bill Fetcher** polls Congress.gov API v3 every 2 hours for major bill actions
2. **Bill Ranker** scores each bill (floor vote = 100, cloture = 80, committee passage = 70); bills ≥ 70 trigger a debate
3. **Debate Engine** runs a multi-turn debate across 5–7 caucus agents (opening → 2 debate rounds → closing + vote)
4. **Vote Tally** is seat-weighted (430 total simulated seats, 216 to pass)
5. **Social Publisher** posts a 5-tweet thread to X; full transcript lives at `/debates/{id}`

### Caucuses (always active)

| Caucus | Seats | Color |
|---|---|---|
| Congressional Progressive Caucus | 100 | Purple |
| New Democrat Coalition | 100 | Blue |
| Republican Study Committee | 125 | Red |
| House Freedom Caucus | 45 | Dark Red |
| Problem Solvers Caucus | 60 | Green |

### Optional caucuses (bill-type triggered)

| Caucus | Seats | Triggers |
|---|---|---|
| Congressional Black Caucus | 57 | civil rights, policing, voting bills |
| House Armed Services Bloc | 60 | defense, NDAA, veterans bills |

---

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic, APScheduler
- **AI**: Anthropic Claude API (`claude-sonnet-4-6`)
- **Frontend**: Next.js 14, Tailwind CSS
- **Database**: PostgreSQL 15 (Cloud SQL in production)
- **Infra**: GCP Compute Engine + Cloud SQL + Secret Manager; Docker Compose

---

## Local development

### Prerequisites
- Python 3.12+, Node.js 20+
- PostgreSQL running locally (or Docker)
- API keys: `ANTHROPIC_API_KEY`, `CONGRESS_API_KEY` (optional for testing)

### Setup

```bash
# Clone and enter
cd AgentCongress

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Copy env
cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY, DATABASE_URL at minimum

# Run DB migrations
alembic upgrade head

# Start backend
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev        # → http://localhost:3000
```

### Trigger a debate manually

```bash
# Start a full bill poll + debate pipeline
curl -X POST http://localhost:8000/admin/trigger-poll

# Trigger debate for a specific bill ID
curl -X POST http://localhost:8000/admin/trigger-debate/1

# Check debates
curl http://localhost:8000/debates | jq
```

---

## Docker Compose

```bash
# Copy and fill env
cp .env.example .env

# Build and run (backend + frontend + nginx)
docker compose up --build

# Apply migrations
docker compose exec backend alembic upgrade head
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Nginx (SSL): `https://your-domain.com`

---

## Environment variables

| Variable | Description |
|---|---|
| `ENV` | `development` or `production` |
| `ANTHROPIC_API_KEY` | Claude API key |
| `CONGRESS_API_KEY` | Congress.gov API key (get free at api.congress.gov) |
| `TWITTER_API_KEY` | X/Twitter OAuth 1.0a consumer key |
| `TWITTER_API_SECRET` | X/Twitter OAuth 1.0a consumer secret |
| `TWITTER_ACCESS_TOKEN` | X/Twitter access token |
| `TWITTER_ACCESS_SECRET` | X/Twitter access secret |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` |
| `DRY_RUN` | `true` = log tweet thread, don't post |
| `WEBAPP_URL` | Base URL for debate links in tweets |
| `NEXT_PUBLIC_API_URL` | FastAPI base URL (used by frontend) |
| `DISABLE_SCHEDULER` | `true` = do not start in-process scheduler (use with Cloud Scheduler) |
| `SCHEDULER_SECRET` | Optional; require `X-Scheduler-Secret` header on `POST /admin/trigger-poll` and task workers |
| `SERVICE_URL` | Backend base URL (e.g. `https://xxx.run.app`) for Cloud Tasks target URLs |
| `CLOUD_TASKS_PROJECT_ID` | GCP project ID for the Cloud Tasks queue |
| `CLOUD_TASKS_LOCATION` | Queue location (e.g. `us-central1`) |
| `CLOUD_TASKS_QUEUE_NAME` | Queue name (e.g. `agentcongress`) |

---

## GCP Deployment

### Secret Manager (do this before or right after first deploy)

If you run the backend with **ENV=production** on Cloud Run, it reads API keys from GCP Secret Manager. Do this once:

1. **Create secrets and grant access:**  
   `./scripts/gcp-setup-secrets.sh`  
   (Optional: `--project YOUR_PROJECT_ID`; default is `agentcongress`.)
2. **Add your real keys:** In GCP Console → Secret Manager, open each secret and add a **new version** with your actual API key / token value (the script creates placeholders).
3. **Set Cloud Run env:** `ENV=production`, `GCP_PROJECT_ID=agentcongress` (or your project). Deploy with these set (e.g. in `.env.production` and `--env-vars-file .env.production`).

If you prefer not to use Secret Manager yet, keep **ENV=development** and set the API keys as plain Cloud Run environment variables (simpler but less secure).

### Free / low-cost database (good for small projects)

To save cost, use a **hosted PostgreSQL with a free tier** instead of Cloud SQL. Set `DATABASE_URL` to the provider’s connection string (use `postgresql+asyncpg://...` so the app keeps using asyncpg). No code changes; no Cloud SQL connection or `CLOUD_SQL_INSTANCE` needed on Cloud Run.

| Provider | Free tier | Notes |
|----------|-----------|--------|
| **[Neon](https://neon.tech)** | 0.5 GB storage, compute scales to zero | Serverless Postgres. Create a project, copy the connection string, and replace the scheme with `postgresql+asyncpg://` (e.g. `postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`). |
| **[Supabase](https://supabase.com)** | 500 MB database, 2 projects | Postgres included. In Project → Settings → Database use the “Connection string” (URI); switch to `postgresql+asyncpg://` and add `?sslmode=require` if needed. |
| **[Render](https://render.com)** | 90-day free Postgres, then spins down | Good for short-term trials; after 90 days you can export and move to Neon/Supabase. |

Use the same `DATABASE_URL` in `.env.production` or Secret Manager. Run migrations once (e.g. from your machine or a one-off Cloud Run job with the same `DATABASE_URL`): `alembic upgrade head`.

### Option A: Cloud Run (backend) + Cloud Scheduler (low traffic)

Good when you don’t need a 24/7 VM. Backend scales to zero; Cloud Scheduler hits the API every 2 hours to run the poll.

1. **Cloud SQL**: Create a PostgreSQL 15 instance (or use Cloud SQL Auth Proxy). From repo root run once:  
   `./scripts/gcp-setup-cloud-sql.sh`  
   (Optional: `--project`, `--region`, `--instance`, `--database`, `--tier`; you will be prompted for the postgres password.)  
   Then set `DATABASE_URL` (see `scripts/env.production.example`) and, when deploying, pass the Cloud SQL connection so the backend can reach the DB, e.g.  
   `CLOUD_SQL_INSTANCE=agentcongress:us-central1:agentcongress-db ./scripts/deploy-backend.sh --env-vars-file .env.production`  
   or add `--cloud-sql-instance=PROJECT:REGION:INSTANCE` to the deploy script.
2. **Secret Manager**: Store API keys and (optionally) a scheduler secret: `ANTHROPIC_API_KEY`, `CONGRESS_API_KEY`, `TWITTER_*`, `DATABASE_URL`, and optionally `SCHEDULER_SECRET`.
3. **Build and push** the backend image (e.g. to Artifact Registry). Cloud Run sets `PORT=8080`; use a start command that listens on `$PORT`, e.g. `uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}` (override the default CMD in Cloud Run if your Dockerfile uses port 8000).
4. **Deploy to Cloud Run** (or use the script):
   - **Script:** From repo root: `./scripts/deploy-backend.sh --project PROJECT_ID --region us-central1`. Optionally `--env-vars-file .env.production` (see `scripts/env.production.example`). Sets timeout 15 min, memory 1Gi, and builds from `backend/`.
   - If you see **PERMISSION_DENIED** (build failed, default service account missing IAM permissions), run once: `./scripts/gcp-setup-build-permissions.sh` to grant the default compute SA `roles/run.builder`.
   - If the backend URL returns **403 Forbidden**, run once: `./scripts/gcp-allow-public-backend.sh` to grant public (unauthenticated) invoker access.
   - Or deploy manually: set env vars (or reference Secret Manager): `ENV=production`, `DISABLE_SCHEDULER=true`, `DATABASE_URL`, etc. Set **Request timeout** to at least 10–15 minutes. Allow unauthenticated if the API is public.
5. **Cloud Scheduler** (optional): To run the bill poll automatically, create a job that runs every 2 hours (e.g. `0 */2 * * *`), HTTP target = your Cloud Run URL + `/admin/trigger-poll`, method = POST. If you set `SCHEDULER_SECRET`, add a header: `X-Scheduler-Secret: <your-secret>`. You can skip this and trigger the poll manually when needed: `curl -X POST https://YOUR-BACKEND.run.app/admin/trigger-poll`.
6. **Frontend**: Deploy with the script (from repo root):
   - **Vercel** (free tier): `NEXT_PUBLIC_API_URL=https://your-backend.run.app ./scripts/deploy-frontend.sh vercel`. Requires [Vercel CLI](https://vercel.com/cli) (`npm i -g vercel`). On first run, link the project.
   - **Cloud Run**: `./scripts/deploy-frontend.sh cloudrun --api-url https://your-backend.run.app` (optional: `--project`, `--region`, `--service-name`). Builds from `frontend/` and deploys to the same GCP project.
   See `scripts/env.frontend.example` for the required env var.

### Option A2: Cloud Run + Cloud Tasks (shorter requests, retries per debate)

Same as Option A, but work is split into tasks so each Cloud Run request is shorter and each debate can be retried independently.

1. **Cloud Tasks**: Run once: `./scripts/gcp-setup-cloud-tasks.sh` (creates queue `agentcongress` in us-central1 and grants the Cloud Run service account `roles/cloudtasks.enqueuer`). Or manually: `gcloud tasks queues create agentcongress --location=us-central1`, then grant the default compute SA `roles/cloudtasks.enqueuer` on the queue.
2. **Env**: Set `SERVICE_URL` to your Cloud Run backend URL, and `CLOUD_TASKS_PROJECT_ID`, `CLOUD_TASKS_LOCATION`, `CLOUD_TASKS_QUEUE_NAME`. Keep `DISABLE_SCHEDULER=true` and optional `SCHEDULER_SECRET`.
3. **Cloud Scheduler**: Point the job at **`/admin/schedule-poll`** (not `/admin/trigger-poll`). That endpoint enqueues one “poll” task and returns immediately.
4. **Flow**: Cloud Tasks delivers the poll task → your backend runs fetch + rank, then enqueues one “debate” task per qualifying bill. Each debate task runs in a separate request (~1–5 min each). Request timeout on Cloud Run can be ~10 min per request instead of 15+ for the full pipeline.
5. **Worker URLs**: Cloud Tasks will POST to `SERVICE_URL/admin/tasks/poll` and `SERVICE_URL/admin/tasks/debate` (with optional `X-Scheduler-Secret` if set). Configure the queue to add that header when creating tasks, or set it in the app when enqueueing (the client sends it for you).

### Option B: Compute Engine (single VM)

1. **Cloud SQL**: Create a PostgreSQL 15 instance; note the connection string.
2. **Secret Manager**: Store all API keys as secrets named `ANTHROPIC_API_KEY` etc.
3. **Compute Engine** (e2-medium): Install Docker, copy repo, fill `.env` with `ENV=production`.
4. **Artifact Registry**: Build and push images via Cloud Build or locally.
5. **Deploy**:
   ```bash
   docker compose pull && docker compose up -d
   docker compose exec backend alembic upgrade head
   ```
6. **TLS**: Point your domain to the static IP; run certbot for Let's Encrypt certs in `./certs/`

---

## API reference

```
GET  /bills              → paginated bill list (?chamber=House|Senate&page=1)
GET  /bills/{id}         → bill detail + linked debate_id
GET  /debates            → paginated debate list, newest first
GET  /debates/{id}       → full debate: statements[], votes[], result
POST /admin/trigger-poll     → run bill poll + debates (sync). Header: X-Scheduler-Secret if set
POST /admin/schedule-poll    → enqueue one poll task (Cloud Tasks). Header: X-Scheduler-Secret if set
POST /admin/tasks/poll       → worker: fetch + rank, enqueue debate tasks. Header: X-Scheduler-Secret if set
POST /admin/tasks/debate    → worker: run debate for one bill (body: {"bill_id": int})
POST /admin/trigger-debate/{bill_id} → manually trigger debate for a bill
GET  /health                 → liveness (no dependency checks)
GET  /ready                  → readiness: DB (e.g. Neon) connectivity
GET  /admin/check-secrets   → verify Cloud Run can read GCP Secret Manager (public, ok/fail only)
GET  /admin/check-congress   → verify Congress.gov API (public, ok/fail only)
GET  /admin/check-twitter   → verify Twitter/X API (public, ok/fail and @username only)
```

After deploying the backend, run the verification script (no auth needed for the check endpoints):

```bash
./scripts/verify-deployment.sh https://agentcongress-backend-xxxx.run.app
```

This checks: liveness, DB (Neon), Secret Manager access, Congress.gov API, and **Twitter/X API** (whether the app can call the Twitter API with the configured credentials).

---

*Debates are AI-simulated and do not represent the actual positions of any caucus or member of Congress.*
