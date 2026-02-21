from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    _scheduler.add_job(
        poll_bill_actions,
        trigger=IntervalTrigger(hours=2),
        id="poll_bill_actions",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("APScheduler started — polling every 2 hours")


async def shutdown_scheduler() -> None:
    _scheduler.shutdown(wait=False)
    logger.info("APScheduler shut down")


async def poll_bill_actions() -> None:
    """Job 1: Fetch recent bill actions and trigger debates for qualifying bills."""
    from backend.services.bill_fetcher import fetch_recent_bills
    from backend.services.bill_ranker import rank_and_flag_bills

    logger.info("Running poll_bill_actions")
    async with AsyncSessionLocal() as db:
        try:
            bills = await fetch_recent_bills(db)
            candidates = await rank_and_flag_bills(db, bills)
            logger.info("Poll found %d bills, %d qualify for debate", len(bills), len(candidates))
            for bill in candidates:
                await run_debate_for_bill(bill.id)
        except Exception:
            logger.exception("Error in poll_bill_actions")


async def run_debate_for_bill(bill_id: int) -> None:
    """Job 2: Run a debate for the given bill id (idempotent)."""
    from sqlalchemy import select

    from backend.agents.debate_engine import run_debate
    from backend.models.bill import Bill
    from backend.models.debate import Debate

    logger.info("run_debate_for_bill called for bill_id=%d", bill_id)
    async with AsyncSessionLocal() as db:
        try:
            # Check if debate already exists for this bill+action
            bill_result = await db.execute(select(Bill).where(Bill.id == bill_id))
            bill = bill_result.scalar_one_or_none()
            if not bill:
                logger.error("Bill %d not found", bill_id)
                return

            existing_result = await db.execute(
                select(Debate)
                .where(Debate.bill_id == bill_id, Debate.status == "completed")
                .limit(1)
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                logger.info("Bill %d already has a completed debate (%d), skipping.", bill_id, existing.id)
                return

            debate = await run_debate(db, bill)
            logger.info("Debate %d completed for bill %d", debate.id, bill_id)

            await publish_debate_job(debate.id)
        except Exception:
            logger.exception("Error running debate for bill %d", bill_id)


async def publish_debate_job(debate_id: int) -> None:
    """Job 3: Publish debate to X immediately after completion."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from backend.models.debate import Debate
    from backend.services.social_publisher import publish_debate

    logger.info("Publishing debate %d to X", debate_id)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Debate)
                .where(Debate.id == debate_id)
                .options(selectinload(Debate.votes))
            )
            debate = result.scalar_one_or_none()
            if not debate:
                logger.error("Debate %d not found for publishing", debate_id)
                return
            published = await publish_debate(db, debate)
            if published:
                logger.info("Debate %d published successfully", debate_id)
        except Exception:
            logger.exception("Error publishing debate %d", debate_id)
