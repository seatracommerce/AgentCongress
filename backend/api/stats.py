"""Stats dashboard API — simulation vs real-world aggregates."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.bill import Bill
from backend.models.debate import Debate
from backend.schemas.stats import (
    ComparisonTotals,
    DailyRealStat,
    DailySimStat,
    StatsResponse,
)

router = APIRouter()


def _normalize_real_result(raw: str | None) -> str | None:
    """Map real_vote_result to passed/failed or None."""
    if not raw:
        return None
    r = raw.lower().strip()
    if r in ("passed", "voice_vote_passed"):
        return "passed"
    if r in ("failed", "voice_vote_failed"):
        return "failed"
    return None


@router.get("", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Return stats for dashboard: sim daily, real daily, comparison totals."""
    # 1. Simulation daily: GROUP BY date(completed_at), status=completed, result NOT NULL
    date_sim = cast(Debate.completed_at, Date)
    sim_query = (
        select(
            date_sim.label("date"),
            func.count().label("total"),
            func.sum(case((Debate.result == "passed", 1), else_=0)).label("passed"),
            func.sum(case((Debate.result == "failed", 1), else_=0)).label("failed"),
        )
        .where(
            Debate.status == "completed",
            Debate.completed_at.isnot(None),
            Debate.result.isnot(None),
        )
        .group_by(date_sim)
        .order_by(date_sim.desc())
    )
    sim_result = await db.execute(sim_query)
    sim_rows = sim_result.all()
    sim_daily = [
        DailySimStat(
            date=row.date.isoformat() if hasattr(row.date, "isoformat") else str(row.date),
            total=row.total or 0,
            passed=int(row.passed or 0),
            failed=int(row.failed or 0),
        )
        for row in sim_rows
    ]

    # 2. Real-world daily: GROUP BY date(real_vote_date), real_vote_date NOT NULL
    date_real = cast(Bill.real_vote_date, Date)
    real_passed = case(
        (Bill.real_vote_result.in_(["passed", "voice_vote_passed"]), 1),
        else_=0,
    )
    real_failed = case(
        (Bill.real_vote_result.in_(["failed", "voice_vote_failed"]), 1),
        else_=0,
    )
    real_query = (
        select(
            date_real.label("date"),
            func.count().label("total"),
            func.sum(real_passed).label("passed"),
            func.sum(real_failed).label("failed"),
        )
        .where(Bill.real_vote_date.isnot(None))
        .group_by(date_real)
        .order_by(date_real.desc())
    )
    real_result = await db.execute(real_query)
    real_rows = real_result.all()
    real_daily = [
        DailyRealStat(
            date=row.date.isoformat() if hasattr(row.date, "isoformat") else str(row.date),
            total=row.total or 0,
            passed=int(row.passed or 0),
            failed=int(row.failed or 0),
        )
        for row in real_rows
    ]

    # 3. Comparison: Debate JOIN Bill, Python loop
    comp_query = (
        select(Debate, Bill)
        .join(Bill, Debate.bill_id == Bill.id)
        .where(Debate.status == "completed", Debate.result.isnot(None))
    )
    comp_result = await db.execute(comp_query)
    rows = comp_result.all()

    both_passed = both_failed = sim_passed_real_failed = sim_failed_real_passed = no_real_vote = 0
    for debate, bill in rows:
        sim = (debate.result or "").lower()
        real = _normalize_real_result(bill.real_vote_result)
        if real is None:
            no_real_vote += 1
            continue
        if sim == "passed" and real == "passed":
            both_passed += 1
        elif sim == "failed" and real == "failed":
            both_failed += 1
        elif sim == "passed" and real == "failed":
            sim_passed_real_failed += 1
        elif sim == "failed" and real == "passed":
            sim_failed_real_passed += 1

    comparison = ComparisonTotals(
        both_passed=both_passed,
        both_failed=both_failed,
        sim_passed_real_failed=sim_passed_real_failed,
        sim_failed_real_passed=sim_failed_real_passed,
        no_real_vote=no_real_vote,
    )

    return StatsResponse(
        sim_daily=sim_daily,
        real_daily=real_daily,
        comparison=comparison,
    )
