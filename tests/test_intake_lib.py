import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import intake_lib as il


def test_derive_envelope_buckets():
    assert il.derive_envelope(None) == "Unknown"
    assert il.derive_envelope(10_000) == "$0-25k"
    assert il.derive_envelope(25_000) == "$25-250k"
    assert il.derive_envelope(249_999) == "$25-250k"
    assert il.derive_envelope(600_000) == "$250k-1M"
    assert il.derive_envelope(2_000_000) == ">$1M"


def test_next_intake_id_first_of_year():
    assert il.next_intake_id(["INT-2025-0117"], 2026) == "INT-2026-0001"


def test_next_intake_id_increments_within_year():
    existing = ["INT-2026-0042", None, "INT-2026-0063", "INT-2025-0117"]
    assert il.next_intake_id(existing, 2026) == "INT-2026-0064"


def test_next_project_code_per_department():
    existing = ["THG-CLN-014", None, "THG-RND-007", "THG-CLN-002"]
    assert il.next_project_code("CLN", existing) == "THG-CLN-015"
    assert il.next_project_code("OPS", existing) == "THG-OPS-001"


def test_triage_to_status_mapping():
    assert il.triage_to_status("Submitted") == "Proposed"
    assert il.triage_to_status("Approved") == "Active"
    assert il.triage_to_status("Rejected") == "Cancelled"
    assert il.triage_to_status("On Hold") == "Paused"
    assert il.triage_to_status("Garbage") is None


def test_validate_item_passes_complete():
    fields = {
        "Title": "New PHI dashboard", "RequestType": "Project / Initiative",
        "Department": "IT / Data / Security",
        "BusinessProblem": "x", "DesiredOutcome": "y",
        "SponsorEmail": "n.hassan@theragen.com",
        "ProjectManagerEmail": "s.delgado@theragen.com",
    }
    assert il.validate_item(fields) == []


def test_validate_item_flags_missing_people_and_title():
    errs = il.validate_item({"RequestType": "Other", "Department": "HR / People",
                             "BusinessProblem": "x", "DesiredOutcome": "y"})
    joined = " | ".join(errs)
    assert "Title" in joined
    assert "Sponsor" in joined
    assert "Project Manager" in joined


def test_validate_item_handles_whitespace_and_nonstring():
    errs = il.validate_item({"Title": "   ", "RequestType": 7,
                             "Department": "HR / People",
                             "BusinessProblem": "x", "DesiredOutcome": "y"})
    joined = " | ".join(errs)
    assert "Title" in joined          # whitespace-only is missing
    assert "Request Type" not in joined  # non-string but truthy passes via str()
