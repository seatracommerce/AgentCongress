"""Unit tests for _parse_vote_from_actions — no DB, no network required."""
from __future__ import annotations

import pytest

from backend.services.bill_fetcher import _parse_vote_from_actions


def make_action(text: str, action_type: str = "Floor", date: str = "2024-03-15") -> dict:
    return {"type": action_type, "text": text, "actionDate": date}


# --- Roll-call: House ---

def test_house_rollcall_passed():
    actions = [make_action("On passage Passed by the Yeas and Nays: 220 - 210")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "passed"
    assert result["yea"] == 220
    assert result["nay"] == 210


def test_house_rollcall_failed():
    actions = [make_action("On motion to recommit Failed by the Yeas and Nays: 195 - 230")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "failed"
    assert result["yea"] == 195
    assert result["nay"] == 230


def test_house_rollcall_agreed_to():
    actions = [make_action("On agreeing to the resolution Agreed to by the Yeas and Nays: 300 - 100")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "passed"


def test_house_rollcall_rejected():
    actions = [make_action("On the amendment Rejected by the Yeas and Nays: 150 - 270")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "failed"


# --- Roll-call: Senate ---

def test_senate_rollcall_passed():
    actions = [make_action("Passed Senate by Yea-Nay Vote. 67 - 33")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "passed"
    assert result["yea"] == 67
    assert result["nay"] == 33


def test_senate_rollcall_failed():
    actions = [make_action("Failed of passage in Senate by Yea-Nay Vote. 45 - 55")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "failed"
    assert result["yea"] == 45
    assert result["nay"] == 55


# --- Voice votes ---

def test_voice_vote_passed():
    actions = [make_action("Passed Senate without objection")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "voice_vote_passed"
    assert result["yea"] is None
    assert result["nay"] is None


def test_voice_vote_passed_unanimous():
    actions = [make_action("Agreed to by unanimous consent")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "voice_vote_passed"


def test_voice_vote_passed_explicit():
    actions = [make_action("Passed by voice vote")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "voice_vote_passed"


def test_voice_vote_failed():
    actions = [make_action("Failed by voice vote")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "voice_vote_failed"


def test_voice_vote_failed_takes_priority_over_passed_pattern():
    """A text like 'failed...voice vote' must resolve to failed, not passed."""
    actions = [make_action("Motion to table failed by voice vote")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "voice_vote_failed"


# --- Non-floor actions skipped ---

def test_non_floor_action_skipped():
    actions = [
        make_action("Referred to the Subcommittee on Health", action_type="Committee"),
        make_action("Passed Senate without objection", action_type="Floor"),
    ]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "voice_vote_passed"


def test_all_non_floor_returns_none():
    actions = [
        make_action("Introduced in Senate", action_type="IntroReferral"),
        make_action("Referred to committee", action_type="Committee"),
    ]
    result = _parse_vote_from_actions(actions)
    assert result is None


def test_empty_actions_returns_none():
    assert _parse_vote_from_actions([]) is None


# --- Newest-first ordering — first match wins ---

def test_returns_first_floor_action():
    """Actions list is newest-first; the first Floor action with a vote is returned."""
    actions = [
        make_action("Passed Senate without objection", date="2024-05-01"),
        make_action("Failed by Yea-Nay Vote. 45 - 55", date="2024-03-01"),
    ]
    result = _parse_vote_from_actions(actions)
    assert result["result"] == "voice_vote_passed"


# --- Date parsing ---

def test_vote_date_populated():
    actions = [make_action("Passed by voice vote", date="2024-06-15")]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["date"] is not None


def test_vote_date_none_when_missing():
    action = {"type": "Floor", "text": "Passed by voice vote"}  # no actionDate key
    result = _parse_vote_from_actions([action])
    assert result is not None
    assert result["date"] is None


# --- Description stored ---

def test_description_is_raw_action_text():
    text = "Passed Senate without objection"
    actions = [make_action(text)]
    result = _parse_vote_from_actions(actions)
    assert result["description"] == text


def test_house_rollcall_with_supermajority_annotation():
    """Handles 'Yeas and Nays: (2/3 required): 413 - 0' format."""
    text = "On motion to suspend the rules and pass the bill, as amended Agreed to by the Yeas and Nays: (2/3 required): 413 - 0 (Roll no. 47)."
    actions = [make_action(text)]
    result = _parse_vote_from_actions(actions)
    assert result is not None
    assert result["result"] == "passed"
    assert result["yea"] == 413
    assert result["nay"] == 0
