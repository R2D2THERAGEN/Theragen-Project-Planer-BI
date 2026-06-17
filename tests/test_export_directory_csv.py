"""Tests for tools/export_directory_csv.py (pure row formatting)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import export_directory_csv as ed  # noqa: E402


def test_directory_csv_rows_header_and_active():
    recs = [
        {"upn": "a@theragen.com", "display_name": "Abby R", "email": "a@theragen.com",
         "department": "Unassigned", "job_title": "Data Analyst", "active": True},
        {"upn": "b@theragen.com", "display_name": "Bob", "email": "b@theragen.com",
         "department": "Finance / Procurement", "job_title": None, "active": False},
    ]
    rows = ed.directory_csv_rows(recs)
    assert rows[0] == ["UPN", "DisplayName", "Email", "Department", "JobTitle", "Active"]
    assert rows[1] == ["a@theragen.com", "Abby R", "a@theragen.com", "Unassigned", "Data Analyst", "Yes"]
    assert rows[2][5] == "No"   # active False -> No
    assert rows[2][4] == ""     # blank job_title -> ""


def test_directory_csv_rows_empty_is_header_only():
    assert ed.directory_csv_rows([]) == [["UPN", "DisplayName", "Email", "Department", "JobTitle", "Active"]]
