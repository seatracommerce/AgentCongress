"""Congress.gov API v3 bill fetcher."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.bill import Bill

logger = logging.getLogger(__name__)

CONGRESS_API_BASE = "https://api.congress.gov/v3"


async def fetch_recent_bills(db: AsyncSession, lookback_hours: int = 48) -> list[Bill]:
    """Fetch bills with major actions in the last `lookback_hours` hours.

    Returns list of Bill ORM objects that were created or updated.
    """
    settings = get_settings()
    since = datetime.now(tz=timezone.utc) - timedelta(hours=lookback_hours)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    bills_updated: list[Bill] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {
            "api_key": settings.congress_api_key,
            "format": "json",
            "limit": 50,
            "fromDateTime": since_str,
            "sort": "updateDate+desc",
        }

        try:
            resp = await client.get(f"{CONGRESS_API_BASE}/bill", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Congress.gov API error: %s", exc)
            return []

        bills_data = data.get("bills", [])
        logger.info("Fetched %d bills from Congress.gov", len(bills_data))

        for bill_data in bills_data:
            bill = await _upsert_bill(db, client, bill_data, settings.congress_api_key)
            if bill:
                bills_updated.append(bill)

    await db.commit()
    return bills_updated


async def _upsert_bill(
    db: AsyncSession,
    client: httpx.AsyncClient,
    bill_data: dict[str, Any],
    api_key: str,
) -> Bill | None:
    """Upsert a bill into the database, fetching detail if needed."""
    bill_type = bill_data.get("type", "").lower()
    number = bill_data.get("number")
    congress = bill_data.get("congress")

    if not all([bill_type, number, congress]):
        return None

    congress_bill_id = f"{congress}-{bill_type}-{number}"

    result = await db.execute(select(Bill).where(Bill.congress_bill_id == congress_bill_id))
    existing = result.scalar_one_or_none()

    detail = await _fetch_bill_detail(client, congress, bill_type, number, api_key)
    if not detail:
        return None

    latest_action = detail.get("latestAction", {})
    last_action_text = latest_action.get("text", "")
    last_action_date_str = latest_action.get("actionDate")
    last_action_date = _parse_date(last_action_date_str)

    title = detail.get("title") or detail.get("shortTitle") or f"Bill {congress_bill_id}"
    sponsors = detail.get("sponsors", [])
    sponsor_name = sponsors[0].get("fullName", "") if sponsors else None
    introduced_date = _parse_date(detail.get("introducedDate"))

    summary = await _fetch_bill_summary(client, congress, bill_type, number, api_key)

    # Congress.gov URL — prefer explicit field, fall back to constructing it
    congress_url = (
        detail.get("congressDotGovUrl")
        or bill_data.get("url")
        or _build_congress_url(congress, bill_type, number)
    )

    origin_chamber = detail.get("originChamber", "")
    chamber = (
        "House"
        if origin_chamber.lower() == "house"
        else "Senate"
        if origin_chamber.lower() == "senate"
        else origin_chamber
    )

    if existing:
        action_changed = existing.last_action_text != last_action_text
        existing.title = title
        existing.summary = summary
        existing.chamber = chamber
        existing.status = last_action_text
        existing.sponsor = sponsor_name
        existing.last_action_date = last_action_date
        existing.last_action_text = last_action_text
        existing.introduced_date = introduced_date
        existing.congress_url = congress_url
        if action_changed:
            logger.info("Bill %s has new action: %s", congress_bill_id, last_action_text)
        return existing
    else:
        bill = Bill(
            congress_bill_id=congress_bill_id,
            title=title,
            summary=summary,
            chamber=chamber,
            status=last_action_text,
            sponsor=sponsor_name,
            bill_type=bill_type,
            congress_number=int(congress) if congress else None,
            introduced_date=introduced_date,
            last_action_date=last_action_date,
            last_action_text=last_action_text,
            congress_url=congress_url,
        )
        db.add(bill)
        return bill


async def _fetch_bill_detail(
    client: httpx.AsyncClient,
    congress: str,
    bill_type: str,
    number: str,
    api_key: str,
) -> dict[str, Any]:
    try:
        resp = await client.get(
            f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{number}",
            params={"api_key": api_key, "format": "json"},
        )
        resp.raise_for_status()
        return resp.json().get("bill", {})
    except httpx.HTTPError as exc:
        logger.error("Error fetching bill detail %s/%s/%s: %s", congress, bill_type, number, exc)
        return {}


async def _fetch_bill_summary(
    client: httpx.AsyncClient,
    congress: str,
    bill_type: str,
    number: str,
    api_key: str,
) -> str | None:
    try:
        resp = await client.get(
            f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{number}/summaries",
            params={"api_key": api_key, "format": "json"},
        )
        resp.raise_for_status()
        summaries = resp.json().get("summaries", [])
        if summaries:
            return summaries[-1].get("text", "")
        return None
    except httpx.HTTPError:
        return None


def _build_congress_url(congress: str, bill_type: str, number: str) -> str:
    """Construct a Congress.gov bill URL from its components.

    Example: https://www.congress.gov/bill/119th-congress/house-bill/1
    """
    ordinal = f"{congress}th"  # good enough for display; 119th, 118th, etc.
    type_map = {
        "hr": "house-bill",
        "s": "senate-bill",
        "hjres": "house-joint-resolution",
        "sjres": "senate-joint-resolution",
        "hconres": "house-concurrent-resolution",
        "sconres": "senate-concurrent-resolution",
        "hres": "house-resolution",
        "sres": "senate-resolution",
    }
    bill_path = type_map.get(bill_type.lower(), bill_type)
    return f"https://www.congress.gov/bill/{ordinal}-congress/{bill_path}/{number}"


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
