from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db

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
