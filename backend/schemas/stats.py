"""Stats dashboard response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class DailySimStat(BaseModel):
    date: str
    total: int
    passed: int
    failed: int


class DailyRealStat(BaseModel):
    date: str
    total: int
    passed: int
    failed: int


class ComparisonTotals(BaseModel):
    both_passed: int
    both_failed: int
    sim_passed_real_failed: int
    sim_failed_real_passed: int
    no_real_vote: int


class StatsResponse(BaseModel):
    sim_daily: list[DailySimStat]
    real_daily: list[DailyRealStat]
    comparison: ComparisonTotals
