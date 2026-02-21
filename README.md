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

---

## GCP Deployment

1. **Cloud SQL**: Create a PostgreSQL 15 instance; note the connection string
2. **Secret Manager**: Store all API keys as secrets named `ANTHROPIC_API_KEY` etc.
3. **Compute Engine** (e2-medium): Install Docker, copy repo, fill `.env` with `ENV=production`
4. **Artifact Registry**: Build and push images via Cloud Build or locally
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
POST /admin/trigger-poll → manually trigger bill poll
POST /admin/trigger-debate/{bill_id} → manually trigger debate for a bill
GET  /health             → {"status": "ok"}
```

---

*Debates are AI-simulated and do not represent the actual positions of any caucus or member of Congress.*
