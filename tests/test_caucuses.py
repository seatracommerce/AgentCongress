"""Unit tests for caucus definitions and optional-caucus logic."""
from __future__ import annotations

import pytest

from backend.agents.caucuses import (
    CAUCUSES,
    OPTIONAL_CAUCUSES,
    SENATE_CAUCUSES,
    TOTAL_SEATS,
    detect_chamber,
    get_active_caucuses,
    passage_threshold,
)


def test_core_caucus_count():
    assert len(CAUCUSES) == 5


def test_total_seats():
    assert TOTAL_SEATS == 430


def test_default_passage_threshold():
    assert passage_threshold(CAUCUSES) == 216


def test_all_caucuses_have_required_fields():
    for c in CAUCUSES + OPTIONAL_CAUCUSES + SENATE_CAUCUSES:
        assert c.id, f"Caucus missing id"
        assert c.display_name, f"Caucus {c.id} missing display_name"
        assert c.seats > 0, f"Caucus {c.id} has invalid seat count"
        assert c.system_prompt, f"Caucus {c.id} missing system_prompt"
        assert c.hex_color.startswith("#"), f"Caucus {c.id} has invalid hex_color"


def test_get_active_caucuses_no_tags():
    active = get_active_caucuses()
    assert len(active) == 5
    ids = {c.id for c in active}
    assert ids == {"progressive", "new_dem", "rsc", "freedom", "problem_solvers"}


def test_get_active_caucuses_civil_rights_adds_cbc():
    active = get_active_caucuses(["civil_rights", "policing"])
    ids = {c.id for c in active}
    assert "cbc" in ids
    assert len(active) == 6


def test_get_active_caucuses_defense_adds_armed_services():
    active = get_active_caucuses(["ndaa", "defense"])
    ids = {c.id for c in active}
    assert "armed_services" in ids
    assert len(active) == 6


def test_get_active_caucuses_both_optionals():
    active = get_active_caucuses(["policing", "veterans"])
    ids = {c.id for c in active}
    assert "cbc" in ids
    assert "armed_services" in ids
    assert len(active) == 7


def test_passage_threshold_adjusts_with_optional_caucuses():
    all_seven = get_active_caucuses(["policing", "veterans"])
    total = sum(c.seats for c in all_seven)  # 430 + 57 + 60 = 547
    assert total == 547
    threshold = passage_threshold(all_seven)
    assert threshold == 274  # ceil(547/2)


def test_irrelevant_tags_dont_add_optionals():
    active = get_active_caucuses(["healthcare", "taxes"])
    assert len(active) == 5


# ── Senate caucuses ───────────────────────────────────────────────────────────

def test_senate_caucus_count():
    assert len(SENATE_CAUCUSES) == 5


def test_senate_total_seats():
    total = sum(c.seats for c in SENATE_CAUCUSES)
    assert total == 100


def test_senate_passage_threshold():
    threshold = passage_threshold(SENATE_CAUCUSES)
    assert threshold == 51  # 100 // 2 + 1


def test_senate_caucus_chamber_field():
    for c in SENATE_CAUCUSES:
        assert c.chamber == "Senate", f"{c.id} should have chamber='Senate'"


def test_house_caucus_chamber_field():
    for c in CAUCUSES + OPTIONAL_CAUCUSES:
        assert c.chamber == "House", f"{c.id} should have chamber='House'"


def test_get_active_caucuses_senate_chamber():
    active = get_active_caucuses(chamber="Senate")
    ids = {c.id for c in active}
    assert ids == {
        "senate_progressive",
        "senate_dem",
        "senate_gop",
        "senate_conservative",
        "senate_bipartisan",
    }
    assert len(active) == 5


def test_senate_tags_ignored_for_optional_caucuses():
    """Senate debates don't add optional House caucuses regardless of tags."""
    active = get_active_caucuses(bill_tags=["policing", "ndaa"], chamber="Senate")
    assert len(active) == 5
    assert all(c.chamber == "Senate" for c in active)


# ── Chamber detection ─────────────────────────────────────────────────────────

def test_detect_chamber_house_types():
    assert detect_chamber("hr") == "House"
    assert detect_chamber("HR") == "House"
    assert detect_chamber("hjres") == "House"
    assert detect_chamber("hconres") == "House"
    assert detect_chamber("hres") == "House"


def test_detect_chamber_senate_types():
    assert detect_chamber("s") == "Senate"
    assert detect_chamber("S") == "Senate"
    assert detect_chamber("sjres") == "Senate"
    assert detect_chamber("sconres") == "Senate"
    assert detect_chamber("sres") == "Senate"


def test_detect_chamber_unknown_defaults_to_house():
    assert detect_chamber("unknown") == "House"
    assert detect_chamber("") == "House"


# ── Vote extraction ───────────────────────────────────────────────────────────

def test_vote_extraction():
    """Spot-check vote parsing in CaucusAgent."""
    from backend.agents.caucus_agent import _extract_vote

    assert _extract_vote("I support this bill.\nVOTE: YEA") == "yea"
    assert _extract_vote("We oppose this.\nVOTE: NAY") == "nay"
    assert _extract_vote("Abstaining.\nVOTE: PRESENT") == "present"
    assert _extract_vote("vote: yea") == "yea"   # case-insensitive
    assert _extract_vote("No vote declared here.") == "present"  # fallback
