from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.models.bill import Bill

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/trigger-poll")
async def trigger_poll(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Manually trigger a bill poll and debate pipeline (dev/testing)."""
    from backend.scheduler.tasks import poll_bill_actions

    background_tasks.add_task(poll_bill_actions)
    logger.info("Manual poll triggered via /admin/trigger-poll")
    return {"status": "triggered", "message": "Bill poll started in background"}


@router.post("/trigger-debate/{bill_id}")
async def trigger_debate(bill_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
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
