"""Bill importance ranker — scores bills and flags them for debate."""
from __future__ import annotations

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.bill import Bill

logger = logging.getLogger(__name__)

DEBATE_THRESHOLD = 70.0

FLOOR_VOTE_PATTERNS = [
    r"roll call",
    r"passed",
    r"failed",
    r"agreed to",
    r"conference report",
    r"final passage",
    r"third reading",
    r"yeas and nays",
]

COMMITTEE_PASSAGE_PATTERNS = [
    r"ordered to be reported",
    r"reported by",
    r"favorably reported",
    r"committee on.*passed",
    r"markup",
]

CLOTURE_PATTERNS = [
    r"cloture",
    r"unanimous consent",
    r"motion to proceed",
]


def score_bill(bill: Bill) -> float:
    """Compute importance score for a bill based on its latest action text."""
    action = (bill.last_action_text or "").lower()
    score = 0.0

    for pattern in FLOOR_VOTE_PATTERNS:
        if re.search(pattern, action):
            score = max(score, 100.0)
            break

    if score < 80:
        for pattern in CLOTURE_PATTERNS:
            if re.search(pattern, action):
                score = max(score, 80.0)
                break

    if score < 70:
        for pattern in COMMITTEE_PASSAGE_PATTERNS:
            if re.search(pattern, action):
                score = max(score, 70.0)
                break

    if re.search(r"(scheduled|set for|placed on|calendar)", action):
        score = max(score, 65.0)

    return score


def rank_bills(bills: list[Bill]) -> list[Bill]:
    """Score all bills and return those that qualify for debate.

    Returns bills that crossed the threshold and haven't had a debate triggered yet.
    """
    debate_candidates: list[Bill] = []

    for bill in bills:
        score = score_bill(bill)
        bill.importance_score = score

        has_real_vote = bill.real_vote_result is not None
        if (score >= DEBATE_THRESHOLD or has_real_vote) and not bill.debate_triggered:
            debate_candidates.append(bill)
            logger.info(
                "Bill %s qualifies for debate (score=%.0f, real_vote=%s, action=%r)",
                bill.congress_bill_id,
                score,
                bill.real_vote_result,
                bill.last_action_text,
            )

    return debate_candidates


async def rank_and_flag_bills(db: AsyncSession, bills: list[Bill]) -> list[Bill]:
    """Score bills, flag qualifying ones, and persist scores to DB."""
    candidates = rank_bills(bills)
    for bill in candidates:
        bill.debate_triggered = True
    await db.commit()
    return candidates
