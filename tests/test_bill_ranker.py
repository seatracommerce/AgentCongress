"""Unit tests for bill_ranker — no DB, no API keys required."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.services.bill_ranker import score_bill, rank_bills, DEBATE_THRESHOLD


def make_bill(action: str, debate_triggered: bool = False):
    """Use SimpleNamespace — avoids SQLAlchemy instrumentation in unit tests."""
    return SimpleNamespace(
        congress_bill_id="119-hr-1",
        title="Test Bill",
        last_action_text=action,
        importance_score=0.0,
        debate_triggered=debate_triggered,
    )


# --- score_bill ---

@pytest.mark.parametrize("action,expected_min", [
    ("Roll call vote: passed 220-210", 100),
    ("Final passage agreed to by yeas and nays", 100),
    ("Conference report filed", 100),
    ("Cloture motion filed by Senator Smith", 80),
    ("Motion to proceed to consideration", 80),
    ("Ordered to be reported favorably by the committee", 70),
    ("Markup session held", 70),
    ("Placed on the Union Calendar", 65),
    ("Referred to Subcommittee on Health", 0),   # no trigger
    ("", 0),
])
def test_score_bill(action: str, expected_min: float):
    bill = make_bill(action)
    score = score_bill(bill)
    assert score >= expected_min, f"Action {action!r} should score >= {expected_min}, got {score}"


def test_floor_vote_wins_over_cloture():
    """Floor vote pattern takes precedence — score should be 100, not 80."""
    bill = make_bill("Roll call vote after cloture was invoked")
    assert score_bill(bill) == 100.0


def test_empty_action_scores_zero():
    bill = make_bill("")
    assert score_bill(bill) == 0.0


# --- rank_bills ---

def test_rank_bills_qualifies_correct_bills():
    bills = [
        make_bill("Roll call vote: passed 215-213"),   # score 100 → qualifies
        make_bill("Cloture filed"),                    # score 80 → qualifies
        make_bill("Referred to committee"),             # score 0 → does not qualify
    ]
    candidates = rank_bills(bills)
    assert len(candidates) == 2
    # scores were set on the bill objects
    assert bills[0].importance_score == 100.0
    assert bills[2].importance_score == 0.0


def test_rank_bills_skips_already_triggered():
    bill = make_bill("Roll call vote: passed", debate_triggered=True)
    candidates = rank_bills([bill])
    assert candidates == []


def test_rank_bills_updates_importance_score():
    bill = make_bill("Ordered to be reported by committee")
    rank_bills([bill])
    assert bill.importance_score >= DEBATE_THRESHOLD
