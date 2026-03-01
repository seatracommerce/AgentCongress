from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Header, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.models.bill import Bill

router = APIRouter()
logger = logging.getLogger(__name__)


def _check_scheduler_auth(x_scheduler_secret: str | None = Header(None, alias="X-Scheduler-Secret")) -> None:
    """Raise 401 if scheduler_secret is set and request does not provide it."""
    settings = get_settings()
    if not settings.scheduler_secret:
        return
    if x_scheduler_secret != settings.scheduler_secret:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Scheduler-Secret")


@router.get("/check-secrets")
async def check_secrets():
    """Verify Cloud Run can read from GCP Secret Manager (for post-deploy checks). Returns ok/fail only, no secret values."""
    from fastapi.responses import JSONResponse

    settings = get_settings()
    if settings.env != "production":
        return {"status": "ok", "checks": {"secret_manager": "n/a"}, "detail": "ENV is not production; secrets from env"}
    project_id = (__import__("os").environ.get("GCP_PROJECT_ID") or "").strip()
    if not project_id:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "GCP_PROJECT_ID not set"},
        )
    try:
        from google.cloud import secretmanager  # type: ignore

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/ANTHROPIC_API_KEY/versions/latest"
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("UTF-8")
        if not value or value.strip() == "" or value == "replace-me":
            return JSONResponse(
                status_code=503,
                content={"status": "error", "checks": {"secret_manager": "fail"}, "detail": "Secret exists but is empty or placeholder"},
            )
        return {"status": "ok", "checks": {"secret_manager": "ok"}}
    except Exception as e:
        logger.exception("Secret Manager check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "checks": {"secret_manager": "fail"}, "detail": str(e)},
        )


@router.get("/check-congress")
async def check_congress():
    """Verify Congress.gov API connectivity (for post-deploy checks). Returns ok/fail only."""
    from fastapi.responses import JSONResponse

    settings = get_settings()
    if not settings.congress_api_key:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "CONGRESS_API_KEY not configured"},
        )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.congress.gov/v3/bill",
                params={"api_key": settings.congress_api_key, "format": "json", "limit": 1},
            )
            resp.raise_for_status()
        return {"status": "ok", "checks": {"congress_api": "ok"}}
    except Exception as e:
        logger.exception("Congress API check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "checks": {"congress_api": "fail"}, "detail": str(e)},
        )


@router.get("/check-twitter")
async def check_twitter():
    """Verify Twitter/X API credentials (for post-deploy checks). Returns ok/fail and @username only."""
    from fastapi.responses import JSONResponse

    from backend.services.social_publisher import _make_tweepy_client

    settings = get_settings()
    if not all([settings.twitter_api_key, settings.twitter_api_secret, settings.twitter_access_token, settings.twitter_access_secret]):
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Twitter credentials not configured"},
        )
    try:
        client = _make_tweepy_client(settings)
        me = client.get_me()
        username = getattr(me.data, "username", None) if me and me.data else None
        return {"status": "ok", "checks": {"twitter_api": "ok"}, "detail": f"@{username}" if username else "ok"}
    except Exception as e:
        logger.exception("Twitter API check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "checks": {"twitter_api": "fail"}, "detail": str(e)},
        )


@router.post("/trigger-poll")
async def trigger_poll(
    x_scheduler_secret: str | None = Header(None, alias="X-Scheduler-Secret"),
):
    """Run the bill poll and debate pipeline to completion (sync).

    Use this when the app runs on Cloud Run with no in-process scheduler: have Cloud Scheduler
    POST here every 2 hours (with X-Scheduler-Secret if SCHEDULER_SECRET is set).
    """
    _check_scheduler_auth(x_scheduler_secret)
    from backend.scheduler.tasks import poll_bill_actions

    logger.info("Triggering poll via POST /admin/trigger-poll (sync)")
    await poll_bill_actions()
    return {"status": "ok", "message": "Poll completed"}


@router.post("/schedule-poll")
async def schedule_poll(
    x_scheduler_secret: str | None = Header(None, alias="X-Scheduler-Secret"),
):
    """Enqueue a single 'poll' task to Cloud Tasks (returns immediately).

    Use with Cloud Scheduler: Scheduler POSTs here every 2 hours; we enqueue one task and return.
    The task will run fetch + rank and enqueue one 'debate' task per qualifying bill.
    Requires SERVICE_URL, CLOUD_TASKS_* env vars.
    """
    _check_scheduler_auth(x_scheduler_secret)
    from backend.services.cloud_tasks_client import enqueue_poll_task, is_cloud_tasks_configured

    if not is_cloud_tasks_configured():
        raise HTTPException(
            status_code=503,
            detail="Cloud Tasks not configured (set SERVICE_URL, CLOUD_TASKS_PROJECT_ID, CLOUD_TASKS_LOCATION, CLOUD_TASKS_QUEUE_NAME)",
        )
    task_name = await asyncio.to_thread(enqueue_poll_task)
    return {"status": "ok", "message": "Poll task enqueued", "task_name": task_name}


@router.post("/tasks/poll")
async def task_poll(
    x_scheduler_secret: str | None = Header(None, alias="X-Scheduler-Secret"),
):
    """Cloud Tasks worker: fetch bills, rank, enqueue one debate task per candidate (no debates run here)."""
    _check_scheduler_auth(x_scheduler_secret)
    from backend.database import AsyncSessionLocal
    from backend.services.bill_fetcher import fetch_recent_bills
    from backend.services.bill_ranker import rank_and_flag_bills
    from backend.services.cloud_tasks_client import enqueue_debate_task, is_cloud_tasks_configured

    logger.info("Running tasks/poll (fetch + rank + enqueue debates)")
    async with AsyncSessionLocal() as db:
        bills = await fetch_recent_bills(db)
        candidates = await rank_and_flag_bills(db, bills)
    logger.info("Poll found %d bills, %d qualify for debate", len(bills), len(candidates))

    if not is_cloud_tasks_configured():
        # Fallback: run debates inline (same as trigger-poll for this batch)
        from backend.scheduler.tasks import run_debate_for_bill
        for bill in candidates:
            await run_debate_for_bill(bill.id)
        return {"status": "ok", "message": "Poll completed (debates run inline)", "candidates": len(candidates)}

    enqueued = 0
    for bill in candidates:
        task_name = await asyncio.to_thread(enqueue_debate_task, bill.id)
        if task_name:
            enqueued += 1
    return {"status": "ok", "message": "Poll completed; debate tasks enqueued", "candidates": len(candidates), "enqueued": enqueued}


@router.post("/tasks/debate")
async def task_debate(
    x_scheduler_secret: str | None = Header(None, alias="X-Scheduler-Secret"),
    body: dict = Body(default_factory=dict),
):
    """Cloud Tasks worker: run debate + publish for one bill_id (body: {"bill_id": int})."""
    _check_scheduler_auth(x_scheduler_secret)
    if not body or "bill_id" not in body:
        raise HTTPException(status_code=400, detail="Body must be JSON with bill_id (integer)")
    try:
        bill_id = int(body["bill_id"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="bill_id must be an integer")

    from backend.scheduler.tasks import run_debate_for_bill

    logger.info("Running tasks/debate for bill_id=%d", bill_id)
    await run_debate_for_bill(bill_id)
    return {"status": "ok", "message": f"Debate completed for bill {bill_id}", "bill_id": bill_id}


@router.post("/republish-debate/{debate_id}")
async def republish_debate(
    debate_id: int,
    db: AsyncSession = Depends(get_db),
    x_scheduler_secret: str | None = Header(None, alias="X-Scheduler-Secret"),
):
    """Re-publish a completed debate to X (clears published_to_x_at and republishes)."""
    from sqlalchemy.orm import selectinload
    from backend.models.debate import Debate
    from backend.services.social_publisher import publish_debate

    _check_scheduler_auth(x_scheduler_secret)
    result = await db.execute(
        select(Debate).where(Debate.id == debate_id).options(selectinload(Debate.votes))
    )
    debate = result.scalar_one_or_none()
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate {debate_id} not found")
    debate.published_to_x_at = None
    await db.commit()
    published = await publish_debate(db, debate)
    return {"status": "ok" if published else "skipped", "debate_id": debate_id}


@router.post("/trigger-debate/{bill_id}")
async def trigger_debate(bill_id: int, background_tasks: BackgroundTasks):
    """Manually trigger a debate for a specific bill id."""
    from backend.scheduler.tasks import run_debate_for_bill

    background_tasks.add_task(run_debate_for_bill, bill_id)
    logger.info("Manual debate triggered for bill %d", bill_id)
    return {"status": "triggered", "message": f"Debate started for bill {bill_id}"}


@router.post("/refresh-vote/{bill_id}")
async def refresh_vote(bill_id: int, db: AsyncSession = Depends(get_db)):
    """Re-fetch and store the real congressional vote for a specific bill."""
    from backend.services.bill_fetcher import _fetch_bill_actions, _parse_vote_from_actions

    result = await db.execute(select(Bill).where(Bill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail=f"Bill {bill_id} not found")

    if not all([bill.congress_number, bill.bill_type]):
        raise HTTPException(status_code=422, detail="Bill is missing congress_number or bill_type")

    settings = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        actions = await _fetch_bill_actions(
            client,
            str(bill.congress_number),
            bill.bill_type,
            bill.congress_bill_id.split("-")[-1],
            settings.congress_api_key,
        )

    vote_info = _parse_vote_from_actions(actions)
    if vote_info:
        bill.real_vote_result = vote_info["result"]
        bill.real_vote_yea = vote_info.get("yea")
        bill.real_vote_nay = vote_info.get("nay")
        bill.real_vote_date = vote_info.get("date")
        bill.real_vote_description = vote_info.get("description")
        await db.commit()
        logger.info("Refreshed real vote for bill %d: %s", bill_id, vote_info["result"])

    return {
        "bill_id": bill_id,
        "congress_bill_id": bill.congress_bill_id,
        "real_vote": vote_info,
    }
