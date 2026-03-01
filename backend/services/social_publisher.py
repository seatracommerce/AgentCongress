"""X (Twitter) social publisher — posts debate summaries as tweet threads."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import tweepy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.debate import Debate, Vote

logger = logging.getLogger(__name__)

RESULT_EMOJI = {"passed": "✅", "failed": "❌"}
CHOICE_EMOJI = {"yea": "✅", "nay": "❌", "present": "⚪"}

# Short display names for tweet caucus line
_CAUCUS_SHORT = {
    "progressive": "Prog.",
    "new_dem": "NewDem",
    "rsc": "RSC",
    "freedom": "Freedom",
    "problem_solvers": "PS",
    "cbc": "CBC",
    "armed_services": "ArmedSvc",
    "senate_progressive": "S.Prog.",
    "senate_dem": "S.Dem",
    "senate_gop": "S.GOP",
    "senate_conservative": "S.Cons.",
    "senate_bipartisan": "S.Bip.",
}


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

    votes = list(debate.votes) if debate.votes else []
    result = debate.result or "unknown"
    result_emoji = RESULT_EMOJI.get(result, "\U0001f5f3\ufe0f")

    yea = debate.yea_seats or 0
    nay = debate.nay_seats or 0
    present = debate.present_seats or 0

    # Build compact caucus votes line: "Prog. ✅ · NewDem ✅ · RSC ❌ · Freedom ❌ · PS ✅"
    caucus_parts = []
    for v in sorted(votes, key=lambda v: v.weighted_seats, reverse=True):
        short = _CAUCUS_SHORT.get(v.caucus_id, v.caucus_id)
        emoji = CHOICE_EMOJI.get(v.choice, "?")
        caucus_parts.append(f"{short} {emoji}")
    caucus_line = " · ".join(caucus_parts)

    tweet = (
        f"🏛️ AgentCongress: {_truncate(bill.title, 100)}\n\n"
        f"{result_emoji} {result.upper()} · {yea} yea / {nay} nay"
        + (f" / {present} present" if present else "")
        + f"\n\n{caucus_line}\n\n"
        f"Full transcript & vote breakdown 👇\n"
        f"{settings.webapp_url}/debates/{debate.id}\n"
        f"#Congress #AI #AgentCongress"
    )

    thread: list[str] = [tweet]

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
        for tweet_text in thread:
            response = client.create_tweet(text=tweet_text)
            logger.info("Posted tweet ID %s", response.data["id"])

        debate.published_to_x_at = datetime.now(tz=timezone.utc)
        await db.commit()
        logger.info("Published debate %d to X successfully.", debate.id)
        return True

    except tweepy.TweepyException as exc:
        logger.error("Tweepy error publishing debate %d: %s", debate.id, exc)
        return False
