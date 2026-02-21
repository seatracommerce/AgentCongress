"""Debate engine — orchestrates multi-turn debate across all caucus agents."""
from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.caucus_agent import CaucusAgent, CLAUDE_MODEL
from backend.agents.caucuses import detect_chamber, get_active_caucuses, passage_threshold
from backend.config import get_settings
from backend.models.bill import Bill
from backend.models.debate import Debate, Vote
from backend.models.statement import Statement

logger = logging.getLogger(__name__)

DEBATE_ROUNDS = 2


async def run_debate(db: AsyncSession, bill: Bill) -> Debate:
    """Run a full multi-turn debate for the given bill.

    Creates and persists: Debate, Statement (per turn), Vote (per caucus).
    Returns the completed Debate object.
    """
    bill_type = getattr(bill, "bill_type", None) or "hr"
    chamber = detect_chamber(bill_type)
    bill_tags = getattr(bill, "tags", None) or []
    active_caucuses = get_active_caucuses(bill_tags, chamber=chamber)

    debate = Debate(
        bill_id=bill.id,
        status="running",
        chamber=chamber,
        started_at=datetime.now(tz=timezone.utc),
    )
    db.add(debate)
    await db.flush()  # get debate.id

    agents = [CaucusAgent(c) for c in active_caucuses]
    threshold = passage_threshold(active_caucuses)
    total_seats = sum(c.seats for c in active_caucuses)
    sequence = 0
    all_statements: list[dict[str, str]] = []
    bill_summary = bill.summary or "No summary available."

    # --- Phase 1: Opening statements (randomized order) ---
    opening_order = list(agents)
    random.shuffle(opening_order)
    logger.info("Starting opening statements for bill %s (debate %d)", bill.congress_bill_id, debate.id)

    for agent in opening_order:
        content = await agent.opening_statement(bill.title, bill_summary)
        stmt = Statement(
            debate_id=debate.id,
            caucus_id=agent.caucus.id,
            turn_type="opening",
            content=content,
            sequence=sequence,
        )
        db.add(stmt)
        sequence += 1
        all_statements.append({
            "caucus_id": agent.caucus.id,
            "caucus_name": agent.caucus.display_name,
            "content": content,
        })

    await db.flush()

    # --- Phase 2: Debate rounds ---
    for round_num in range(1, DEBATE_ROUNDS + 1):
        logger.info("Debate round %d for debate %d", round_num, debate.id)
        for agent in agents:
            content = await agent.debate_response(bill.title, bill_summary, all_statements)
            stmt = Statement(
                debate_id=debate.id,
                caucus_id=agent.caucus.id,
                turn_type="debate",
                content=content,
                sequence=sequence,
            )
            db.add(stmt)
            sequence += 1
            all_statements.append({
                "caucus_id": agent.caucus.id,
                "caucus_name": agent.caucus.display_name,
                "content": content,
            })

        await db.flush()

    # --- Phase 3: Closing statements + votes ---
    logger.info("Starting closing statements and votes for debate %d", debate.id)
    votes: list[Vote] = []

    for agent in agents:
        content, vote_choice = await agent.closing_and_vote(bill.title, bill_summary, all_statements)

        stmt = Statement(
            debate_id=debate.id,
            caucus_id=agent.caucus.id,
            turn_type="closing",
            content=content,
            sequence=sequence,
        )
        db.add(stmt)
        sequence += 1

        rationale = _extract_rationale(content)

        vote = Vote(
            debate_id=debate.id,
            caucus_id=agent.caucus.id,
            choice=vote_choice,
            rationale=rationale,
            weighted_seats=agent.caucus.seats,
        )
        db.add(vote)
        votes.append(vote)
        all_statements.append({
            "caucus_id": agent.caucus.id,
            "caucus_name": agent.caucus.display_name,
            "content": content,
        })

    await db.flush()

    # --- Tally votes ---
    yea_seats = sum(v.weighted_seats for v in votes if v.choice == "yea")
    nay_seats = sum(v.weighted_seats for v in votes if v.choice == "nay")
    present_seats = total_seats - yea_seats - nay_seats
    result = "passed" if yea_seats >= threshold else "failed"

    logger.info(
        "Debate %d result: %s (Yea=%d, Nay=%d, Present=%d)",
        debate.id, result.upper(), yea_seats, nay_seats, present_seats,
    )

    summary = await _generate_summary(bill.title, all_statements, yea_seats, nay_seats, result)

    debate.status = "completed"
    debate.summary = summary
    debate.yea_seats = yea_seats
    debate.nay_seats = nay_seats
    debate.present_seats = present_seats
    debate.result = result
    debate.completed_at = datetime.now(tz=timezone.utc)

    await db.commit()
    logger.info("Debate %d completed and persisted.", debate.id)
    return debate


async def _generate_summary(
    bill_title: str,
    all_statements: list[dict[str, str]],
    yea_seats: int,
    nay_seats: int,
    result: str,
) -> str:
    """Generate a 2-3 sentence debate summary for social posts."""
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    transcript_excerpt = "\n".join(
        f"{s['caucus_name']}: {s['content'][:200]}..." for s in all_statements[-5:]
    )

    prompt = (
        f"Summarize this congressional debate on '{bill_title}' in 2-3 sentences suitable for a social media post. "
        f"Include the final vote result ({result.upper()}: {yea_seats} Yea vs {nay_seats} Nay seats) "
        f"and the key fault lines between caucuses.\n\n"
        f"Recent statements:\n{transcript_excerpt}"
    )

    message = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _extract_rationale(closing_content: str) -> str:
    """Extract a short rationale — the sentence just before the VOTE: declaration."""
    lines = [ln.strip() for ln in closing_content.split("\n") if ln.strip()]
    for i, line in enumerate(lines):
        if line.upper().startswith("VOTE:"):
            if i > 0:
                return lines[i - 1][:300]
            break
    for line in reversed(lines):
        if not line.upper().startswith("VOTE:"):
            return line[:300]
    return ""
