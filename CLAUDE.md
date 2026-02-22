# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgentCongress — multi-agent AI simulation of US congressional debates. Five (optionally seven) Claude-powered caucus personas debate active bills from Congress.gov and post results to X.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy async, Alembic, APScheduler, Anthropic SDK, httpx, Tweepy
- **Frontend**: Next.js 14, Tailwind CSS (App Router, TypeScript, no UI library)
- **DB**: PostgreSQL 15 via asyncpg
- **Infra**: GCP Compute Engine + Cloud SQL + Secret Manager, Docker Compose

## Key commands

```bash
# Backend dev
uvicorn backend.main:app --reload --port 8000

# DB migrations (run from project root)
alembic upgrade head
alembic revision --autogenerate -m "description"

# Frontend dev
cd frontend && npm run dev

# Docker
docker compose up --build
docker compose exec backend alembic upgrade head
```

## Git Workflow
After completing any feature, fix, or meaningful unit of work:
1. Run `git add -A`
2. Write a descriptive commit message following conventional commits (feat:, fix:, chore: etc.)
3. Run `git commit -m "..."`

Never leave completed work uncommitted.

## Architecture decisions

- **Alembic migrations** live in `backend/alembic/`, config at `alembic.ini` (project root)
- **Optional caucuses**: CBC (57 seats) and Armed Services (60 seats) activate per bill tags; passage threshold adjusts dynamically to 50% of active seats
- **DRY_RUN=true**: social publisher logs tweet thread to stdout without posting to X
- **Debate structure**: opening (randomized order) → 2 debate rounds → closing + VOTE declaration parsed with regex
- **GCP secrets**: `config.py` reads from GCP Secret Manager when `ENV=production`; otherwise from `.env`

## File map

```
backend/
├── main.py                  FastAPI entry + CORS + scheduler startup
├── config.py                pydantic-settings, GCP secret resolution
├── database.py              async engine + session factory + Base
├── models/                  Bill, Debate, Vote, Statement ORM models
├── schemas/                 Pydantic response schemas
├── api/                     bills.py, debates.py, admin.py routers
├── agents/
│   ├── caucuses.py          Caucus dataclass, 5 core + 2 optional, get_active_caucuses()
│   ├── caucus_agent.py      CaucusAgent wrapping Claude API
│   └── debate_engine.py     run_debate() orchestration
├── services/
│   ├── bill_fetcher.py      Congress.gov API v3 client
│   ├── bill_ranker.py       score_bill(), rank_and_flag_bills()
│   └── social_publisher.py  Tweepy tweet thread formatter
└── scheduler/tasks.py       APScheduler jobs: poll → debate → publish

frontend/
├── app/page.tsx             Home: debate card grid
├── app/debates/[id]/page.tsx  Full transcript + sidebar
├── components/
│   ├── DebateCard.tsx
│   ├── StatementBubble.tsx  Color-coded per caucus
│   ├── VoteBoard.tsx        Seat-weighted bar chart + per-caucus breakdown
│   └── BillSummary.tsx      Bill metadata sidebar
└── lib/api.ts               fetch wrappers + TypeScript types
```
