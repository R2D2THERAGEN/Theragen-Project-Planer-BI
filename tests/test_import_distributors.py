"""Tests for tools/import_distributors.py (pure normalizers + dedup)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import import_distributors as imp  # noqa: E402


def test_normalize_status():
    assert imp.normalize_distributor_status("Terminated 2023") == "Terminated"
    assert imp.normalize_distributor_status("Terminated Aug 1 2017") == "Terminated"
    assert imp.normalize_distributor_status("Gone") == "Terminated"
    assert imp.normalize_distributor_status("Do Not Pay") == "Inactive"
    assert imp.normalize_distributor_status("PENDING INVENTORY") == "Pending"
    assert imp.normalize_distributor_status("BGS") == "Active"
    assert imp.normalize_distributor_status("") == "Unknown"


def test_canonical_rsm():
    assert imp.canonical_rsm("Tom Milory") == "Tom Milroy"   # typo fixed
    assert imp.canonical_rsm("Jeff Williams") == "Jeff Williams"
    assert imp.canonical_rsm("  ") == "Unknown"


def test_normalize_region():
    assert imp.normalize_region("Southeast") == "Southeast"
    assert imp.normalize_region("  ") == "Unknown"


def test_dedupe_keeps_most_complete_and_drops_blank_name():
    rows = [
        {"name": "Acme", "region": "", "rsm": "", "status_raw": ""},
        {"name": "acme", "region": "Southeast", "rsm": "Jeff Williams", "status_raw": "BGS"},
        {"name": "Beta", "region": "Midwest"},
        {"name": "", "region": "x"},  # blank name -> dropped
    ]
    out = imp.dedupe_distributors(rows)
    assert sorted(r["name"].lower() for r in out) == ["acme", "beta"]
    acme = next(r for r in out if r["name"].lower() == "acme")
    assert acme["region"] == "Southeast"  # the more-complete duplicate won
