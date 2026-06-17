"""Tests for tools/backfill_directory_from_ease.py (pure crosswalk + name norm)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import backfill_directory_from_ease as bf  # noqa: E402
import artifact_lib as al  # noqa: E402


def test_crosswalk_known_and_unknown():
    assert bf.crosswalk_department("100-Direct Sales") == "Commercial / Marketing"
    assert bf.crosswalk_department("9-Quality Control") == "Regulatory / Quality"
    assert bf.crosswalk_department("7-Finance and Accounting") == "Finance / Procurement"
    assert bf.crosswalk_department("200-Order Fulfillment") == "Operations / PMO"
    assert bf.crosswalk_department("999-Unknown Dept") is None
    assert bf.crosswalk_department("") is None


def test_norm_name():
    assert bf.norm_name("Sherrard", "Adams") == "sherrard adams"
    assert bf.norm_name(" Abby ", " Rozelsky ") == "abby rozelsky"
    assert bf.norm_name("Bob", "") == "bob"


def test_every_crosswalk_target_is_a_real_department():
    for v in set(bf.EASE_DEPARTMENT_CROSSWALK.values()):
        assert v in al.DEPARTMENTS, f"crosswalk target not a real department: {v}"
