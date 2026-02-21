"""Integration tests for FastAPI routes — uses in-memory SQLite, no API keys needed."""
from __future__ import annotations

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from backend.models.bill import Bill
from backend.models.debate import Debate, Vote
from backend.models.statement import Statement


# --- Helpers ---

async def seed_bill(db_session, **kwargs) -> Bill:
    defaults = dict(
        congress_bill_id="119-hr-42",
        title="Test Healthcare Reform Act",
        chamber="House",
        status="Roll call vote: passed 220-210",
        sponsor="Rep. Test, A.",
        bill_type="hr",
        congress_number=119,
        importance_score=100.0,
        debate_triggered=True,
    )
    defaults.update(kwargs)
    bill = Bill(**defaults)
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    return bill


async def seed_debate(db_session, bill_id: int, **kwargs) -> Debate:
    defaults = dict(
        bill_id=bill_id,
        status="completed",
        summary="A lively debate concluded with a narrow passage.",
        yea_seats=250,
        nay_seats=180,
        present_seats=0,
        result="passed",
        started_at=datetime.now(tz=timezone.utc),
        completed_at=datetime.now(tz=timezone.utc),
    )
    defaults.update(kwargs)
    debate = Debate(**defaults)
    db_session.add(debate)
    await db_session.commit()
    await db_session.refresh(debate)
    return debate


async def seed_statement(db_session, debate_id: int, seq: int, turn: str = "opening") -> Statement:
    stmt = Statement(
        debate_id=debate_id,
        caucus_id="progressive",
        turn_type=turn,
        content="We strongly support this bill for working families.",
        sequence=seq,
    )
    db_session.add(stmt)
    await db_session.commit()
    return stmt


async def seed_vote(db_session, debate_id: int) -> Vote:
    vote = Vote(
        debate_id=debate_id,
        caucus_id="progressive",
        choice="yea",
        rationale="This serves working families.",
        weighted_seats=100,
    )
    db_session.add(vote)
    await db_session.commit()
    return vote


# --- Health ---

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- Bills ---

@pytest.mark.asyncio
async def test_list_bills_empty(client):
    resp = await client.get("/bills")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_bills_returns_seeded(client, db_session):
    await seed_bill(db_session)
    resp = await client.get("/bills")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Test Healthcare Reform Act"


@pytest.mark.asyncio
async def test_get_bill_not_found(client):
    resp = await client.get("/bills/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_bill_detail(client, db_session):
    bill = await seed_bill(db_session, congress_bill_id="119-hr-99")
    resp = await client.get(f"/bills/{bill.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == bill.id
    assert data["chamber"] == "House"
    assert data["debate_id"] is None  # no debate yet


@pytest.mark.asyncio
async def test_get_bill_with_debate_id(client, db_session):
    bill = await seed_bill(db_session, congress_bill_id="119-hr-100")
    debate = await seed_debate(db_session, bill_id=bill.id)
    resp = await client.get(f"/bills/{bill.id}")
    assert resp.status_code == 200
    assert resp.json()["debate_id"] == debate.id


@pytest.mark.asyncio
async def test_list_bills_filter_by_chamber(client, db_session):
    await seed_bill(db_session, congress_bill_id="119-hr-200", chamber="House")
    await seed_bill(db_session, congress_bill_id="119-s-200", chamber="Senate")
    resp = await client.get("/bills?chamber=Senate")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["chamber"] == "Senate" for i in items)


# --- Debates ---

@pytest.mark.asyncio
async def test_list_debates_empty(client):
    resp = await client.get("/debates")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_debates_returns_seeded(client, db_session):
    bill = await seed_bill(db_session, congress_bill_id="119-hr-300")
    await seed_debate(db_session, bill_id=bill.id)
    resp = await client.get("/debates")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    item = resp.json()["items"][0]
    assert item["result"] == "passed"
    assert item["yea_seats"] == 250


@pytest.mark.asyncio
async def test_get_debate_not_found(client):
    resp = await client.get("/debates/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_debate_detail_with_statements_and_votes(client, db_session):
    bill = await seed_bill(db_session, congress_bill_id="119-hr-400")
    debate = await seed_debate(db_session, bill_id=bill.id)
    await seed_statement(db_session, debate_id=debate.id, seq=0, turn="opening")
    await seed_statement(db_session, debate_id=debate.id, seq=1, turn="debate")
    await seed_statement(db_session, debate_id=debate.id, seq=2, turn="closing")
    await seed_vote(db_session, debate_id=debate.id)

    resp = await client.get(f"/debates/{debate.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["statements"]) == 3
    assert len(data["votes"]) == 1
    assert data["statements"][0]["turn_type"] == "opening"
    assert data["votes"][0]["choice"] == "yea"
    assert data["votes"][0]["weighted_seats"] == 100


@pytest.mark.asyncio
async def test_debate_statements_ordered_by_sequence(client, db_session):
    bill = await seed_bill(db_session, congress_bill_id="119-hr-500")
    debate = await seed_debate(db_session, bill_id=bill.id)
    # Seed out of order
    await seed_statement(db_session, debate_id=debate.id, seq=2)
    await seed_statement(db_session, debate_id=debate.id, seq=0)
    await seed_statement(db_session, debate_id=debate.id, seq=1)

    resp = await client.get(f"/debates/{debate.id}")
    seqs = [s["sequence"] for s in resp.json()["statements"]]
    assert seqs == sorted(seqs)


# --- Admin ---

@pytest.mark.asyncio
async def test_admin_trigger_poll_returns_200(client, mocker):
    # Mock the actual poll so it doesn't call Congress.gov
    mocker.patch("backend.scheduler.tasks.poll_bill_actions", return_value=None)
    resp = await client.post("/admin/trigger-poll")
    assert resp.status_code == 200
    assert resp.json()["status"] == "triggered"


@pytest.mark.asyncio
async def test_admin_trigger_debate_returns_200(client, db_session, mocker):
    bill = await seed_bill(db_session, congress_bill_id="119-hr-600")
    mocker.patch("backend.scheduler.tasks.run_debate_for_bill", return_value=None)
    resp = await client.post(f"/admin/trigger-debate/{bill.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "triggered"
