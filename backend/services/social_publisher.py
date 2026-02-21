"""X (Twitter) social publisher — posts debate summaries as tweet threads."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import tweepy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.caucuses import ALL_CAUCUSES_BY_ID
from backend.config import get_settings
from backend.models.debate import Debate, Vote

logger = logging.getLogger(__name__)

RESULT_EMOJI = {"passed": "✅", "failed": "❌"}

# Caucus groupings for tweet thread by chamber
_HOUSE_LEFT = ["progressive", "new_dem"]
_HOUSE_RIGHT = ["rsc", "freedom"]
_HOUSE_CENTER = "problem_solvers"

_SENATE_LEFT = ["senate_progressive", "senate_dem"]
_SENATE_RIGHT = ["senate_gop", "senate_conservative"]
_SENATE_CENTER = "senate_bipartisan"


def _make_tweepy_client(settings) -> tweepy.Client:
    return tweepy.Client(
        consumer_key=settings.twitter_api_key,
        consumer_secret=settings.twitter_api_secret,
        access_token=settings.twitter_access_token,
        access_token_secret=settings.twitter_access_secret,
    )


def _truncate(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "\u2026"


def _format_vote_line(votes: list[Vote]) -> str:
    yea = sum(v.weighted_seats for v in votes if v.choice == "yea")
    nay = sum(v.weighted_seats for v in votes if v.choice == "nay")
    present = sum(v.weighted_seats for v in votes if v.choice == "present")
    return f"{yea}-{nay}" + (f"-{present}" if present else "")


def _get_caucus_excerpt(
    votes: list[Vote],
    caucus_ids: list[str],
    statements_by_caucus: dict[str, str],
) -> str:
    parts = []
    for cid in caucus_ids:
        caucus = ALL_CAUCUSES_BY_ID.get(cid)
        if not caucus:
            continue
        vote = next((v for v in votes if v.caucus_id == cid), None)
        choice_str = f"({vote.choice.upper()})" if vote else ""
        excerpt = _truncate(statements_by_caucus.get(cid, ""), 180)
        parts.append(f"{caucus.display_name} {choice_str}: {excerpt}")
    return "\n\n".join(parts)


async def publish_debate(db: AsyncSession, debate: Debate) -> bool:
    """Build and post a tweet thread about the debate.

    Returns True if published (or DRY_RUN logged), False if skipped.
    Marks debate.published_to_x_at on success.
    """
    settings = get_settings()

    if debate.published_to_x_at is not None:
        logger.info("Debate %d already published, skipping.", debate.id)
        return False

    from backend.models.bill import Bill

    bill_result = await db.execute(select(Bill).where(Bill.id == debate.bill_id))
    bill = bill_result.scalar_one_or_none()
    if not bill:
        logger.error("Bill not found for debate %d", debate.id)
        return False

    from backend.models.statement import Statement

    stmt_result = await db.execute(
        select(Statement)
        .where(Statement.debate_id == debate.id, Statement.turn_type == "closing")
        .order_by(Statement.sequence)
    )
    closing_statements = stmt_result.scalars().all()
    statements_by_caucus = {s.caucus_id: s.content for s in closing_statements}

    votes = list(debate.votes) if debate.votes else []
    result = debate.result or "unknown"
    result_emoji = RESULT_EMOJI.get(result, "\U0001f5f3\ufe0f")
    vote_line = _format_vote_line(votes)

    # Determine chamber-appropriate caucus groupings
    chamber = getattr(debate, "chamber", None) or "House"
    if chamber == "Senate":
        left_ids, right_ids, center_id = _SENATE_LEFT, _SENATE_RIGHT, _SENATE_CENTER
        chamber_label = "Senate"
    else:
        left_ids, right_ids, center_id = _HOUSE_LEFT, _HOUSE_RIGHT, _HOUSE_CENTER
        chamber_label = "House"

    yea = debate.yea_seats or 0
    nay = debate.nay_seats or 0
    present = debate.present_seats or 0
    total_seats = yea + nay + present
    vote_threshold = total_seats // 2 + 1

    thread: list[str] = []

    # Tweet 1: Headline
    thread.append(
        f"\U0001f3db\ufe0f AgentCongress debated: {_truncate(bill.title, 180)}\n\n"
        f"Result: {result_emoji} {result.upper()} ({vote_line} seats)\n\n"
        f"Here's what happened \U0001f9f5\U0001f447"
    )

    # Tweet 2: Left flank
    left_block = _get_caucus_excerpt(votes, left_ids, statements_by_caucus)
    if left_block:
        thread.append(f"\u2b05\ufe0f {chamber_label} left flank:\n\n{left_block}")

    # Tweet 3: Right flank
    right_block = _get_caucus_excerpt(votes, right_ids, statements_by_caucus)
    if right_block:
        thread.append(f"\u27a1\ufe0f {chamber_label} right flank:\n\n{right_block}")

    # Tweet 4: Center/bipartisan + final tally
    center_vote = next((v for v in votes if v.caucus_id == center_id), None)
    center_caucus = ALL_CAUCUSES_BY_ID.get(center_id)
    center_name = center_caucus.display_name if center_caucus else center_id
    center_choice = center_vote.choice.upper() if center_vote else "?"
    center_excerpt = _truncate(statements_by_caucus.get(center_id, ""), 180)

    thread.append(
        f"\U0001f91d {center_name} voted {center_choice}: {center_excerpt}\n\n"
        f"Final tally:\n"
        f"\u2705 YEA: {yea} seats\n"
        f"\u274c NAY: {nay} seats\n"
        f"\u26aa PRESENT: {present} seats\n\n"
        f"Threshold to pass: {vote_threshold} seats\n"
        f"\u2192 {result_emoji} {result.upper()}"
    )

    # Tweet 5: Link
    thread.append(
        f"\U0001f4d6 Read the full debate transcript, vote breakdown, and agent reasoning:\n"
        f"{settings.webapp_url}/debates/{debate.id}\n\n"
        f"#Congress #AI #AgentCongress"
    )

    if settings.dry_run:
        logger.info("DRY_RUN=true — would post %d-tweet thread:", len(thread))
        for i, tweet in enumerate(thread, 1):
            logger.info("Tweet %d/%d:\n%s", i, len(thread), tweet)
            print(f"\n--- Tweet {i}/{len(thread)} ---\n{tweet}")
        debate.published_to_x_at = datetime.now(tz=timezone.utc)
        await db.commit()
        return True

    # Post live thread
    client = _make_tweepy_client(settings)
    try:
        previous_id: int | None = None
        for tweet_text in thread:
            if previous_id:
                response = client.create_tweet(text=tweet_text, in_reply_to_tweet_id=previous_id)
            else:
                response = client.create_tweet(text=tweet_text)
            previous_id = response.data["id"]
            logger.info("Posted tweet ID %s", previous_id)

        debate.published_to_x_at = datetime.now(tz=timezone.utc)
        await db.commit()
        logger.info("Published debate %d to X successfully.", debate.id)
        return True

    except tweepy.TweepyException as exc:
        logger.error("Tweepy error publishing debate %d: %s", debate.id, exc)
        return False
