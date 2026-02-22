"""Tests for debate engine with mocked Claude API — no Anthropic key required."""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.debate_engine import run_debate, _extract_rationale
from backend.agents.caucuses import CAUCUSES, passage_threshold


# --- _extract_rationale ---

def test_extract_rationale_finds_sentence_before_vote():
    content = "We have considered the evidence carefully.\nThis bill serves our constituents.\nVOTE: YEA"
    rationale = _extract_rationale(content)
    assert rationale == "This bill serves our constituents."


def test_extract_rationale_no_vote_returns_last_line():
    content = "We support this bill.\nThis is good policy."
    rationale = _extract_rationale(content)
    assert rationale == "This is good policy."


def test_extract_rationale_empty_string():
    assert _extract_rationale("") == ""


def test_extract_rationale_only_vote_line():
    rationale = _extract_rationale("VOTE: NAY")
    assert rationale == ""


# --- run_debate (mocked Claude) ---

def _make_mock_agent_response(text: str):
    """Return a mock anthropic message response."""
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


OPENING_TEXT = "We strongly support this bill for working families."
CLOSING_YEA = "This bill must pass.\nVOTE: YEA"
CLOSING_NAY = "We must oppose this spending.\nVOTE: NAY"


@pytest.mark.asyncio
async def test_run_debate_creates_statements_and_votes(db_session):
    """Full debate engine test with all Claude calls mocked."""

    async def mock_create(**kwargs):
        system = kwargs.get("system", "")
        user_msg = str(kwargs.get("messages", [{}])[-1].get("content", ""))
        is_closing = "final vote" in user_msg.lower() or "closing statement" in user_msg.lower()
        if is_closing and ("Republican Study" in system or "Freedom" in system):
            text = CLOSING_NAY
        elif is_closing:
            text = CLOSING_YEA
        else:
            text = OPENING_TEXT
        return _make_mock_agent_response(text)

    with patch("backend.agents.caucus_agent.anthropic.AsyncAnthropic") as mock_anthropic_cls, \
         patch("backend.agents.debate_engine.anthropic.AsyncAnthropic") as mock_engine_anthropic:

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=mock_create)
        mock_anthropic_cls.return_value = mock_client
        mock_engine_anthropic.return_value = mock_client

        # Seed a real bill via the session so FK constraints are satisfied
        from backend.models.bill import Bill as BillModel
        bill = BillModel(
            congress_bill_id="119-hr-test-1",
            title="Test Universal Healthcare Act",
            summary="A bill for universal healthcare.",
            importance_score=100.0,
            debate_triggered=True,
        )
        db_session.add(bill)
        await db_session.commit()
        await db_session.refresh(bill)

        debate = await run_debate(db_session, bill)

    # Verify debate was persisted
    assert debate.id is not None
    assert debate.status == "completed"
    assert debate.result in ("passed", "failed")
    assert debate.yea_seats is not None
    assert debate.nay_seats is not None
    assert debate.present_seats is not None
    assert (debate.yea_seats + debate.nay_seats + debate.present_seats) == sum(
        c.seats for c in CAUCUSES
    )

    # Verify statements: 5 openings + 5*2 debate rounds + 5 closings = 25
    from sqlalchemy import select
    from backend.models.statement import Statement
    result = await db_session.execute(
        select(Statement).where(Statement.debate_id == debate.id)
    )
    statements = result.scalars().all()
    assert len(statements) == 5 + 5 * 2 + 5  # 25 total

    opening_count = sum(1 for s in statements if s.turn_type == "opening")
    debate_count = sum(1 for s in statements if s.turn_type == "debate")
    closing_count = sum(1 for s in statements if s.turn_type == "closing")
    assert opening_count == 5
    assert debate_count == 10
    assert closing_count == 5

    # Verify votes
    from backend.models.debate import Vote
    vote_result = await db_session.execute(
        select(Vote).where(Vote.debate_id == debate.id)
    )
    votes = vote_result.scalars().all()
    assert len(votes) == 5
    assert all(v.choice in ("yea", "nay", "present") for v in votes)
    assert all(v.weighted_seats > 0 for v in votes)
