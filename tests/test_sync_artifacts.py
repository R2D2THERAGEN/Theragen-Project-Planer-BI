# tests/test_sync_artifacts.py
"""Dry-run probes for the sync_artifacts processors.

The processors are I/O-bound (they take a live psycopg connection + Graph
client), so the lookups themselves are not pure-function unit tests. Instead we
drive them through a FakeConn that stands in for the DB boundary and run them in
--dry-run mode (no writes, Graph is never touched) to confirm control flow:
specifically that a typo'd/unknown IntakeID airlocks as a clean
``Unknown IntakeID`` validation error — the same graceful airlock the other FK
fields (project, person, type, dept) already get — instead of escaping as a raw
psycopg ForeignKeyViolation. Items with a blank or known IntakeID must produce
byte-identical dry-run output.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))
import sync_artifacts as sa


# ---------------------------------------------------------------------------
# Test doubles for the DB / Graph boundary
# ---------------------------------------------------------------------------

class _Result:
    """Minimal psycopg cursor stand-in: fetchone()/fetchall() over fixed rows."""

    def __init__(self, rows):
        self._rows = list(rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    """Dispatches the handful of SELECTs the dry-run new-item path issues.

    Anything unexpected raises, so the probe stays honest about which queries
    each processor actually runs in dry mode.
    """

    def __init__(self, projects=None, persons=None, intakes=None,
                 doc_types=None, departments=None):
        self.projects = projects or {}        # code -> (project_id, dept)
        self.persons = set(persons or ())     # set of known emails
        self.intakes = set(intakes or ())     # set of known intake ids
        self.doc_types = doc_types or {}      # code -> (id, phase, cycle)
        self.departments = departments or {}  # name -> (dept_id, code)
        self.intake_queries = []              # intake_ids actually looked up

    def execute(self, sql, params=()):
        p0 = params[0] if params else None
        if "doc_mgmt.intake_submission" in sql:
            self.intake_queries.append(p0)
            return _Result([(1,)] if p0 in self.intakes else [])
        if "FROM doc_mgmt.person" in sql:
            return _Result([(f"person:{p0}",)] if p0 in self.persons else [])
        if "FROM doc_mgmt.document_type" in sql:
            row = self.doc_types.get(p0)
            return _Result([row] if row else [])
        if "FROM doc_mgmt.department" in sql:
            row = self.departments.get(p0)
            return _Result([row] if row else [])
        if "doc_id FROM doc_mgmt.document" in sql:
            return _Result([])  # no existing doc_ids -> mint -001
        if "FROM pmbok.project" in sql:
            row = self.projects.get(p0)
            return _Result([row] if row else [])
        if "cr_code FROM pmbok.change_request" in sql:
            return _Result([])  # no existing cr_codes -> mint C-001
        raise AssertionError(f"unexpected SQL in dry-run probe: {sql!r}")


class _Graph:
    """Graph stand-in: writeback must never fire in dry mode."""

    def patch(self, *a, **k):  # pragma: no cover - asserts misuse
        raise AssertionError("writeback attempted during --dry-run")


# ---------------------------------------------------------------------------
# Fixtures (normalized items, as the processors receive them)
# ---------------------------------------------------------------------------

def _cr(**over):
    base = {
        "item_id": "1",
        "ProjectCode": "THG-IT-001",
        "RequestedDate": "2026-06-01",
        "RequestedByEmail": "pm@theragen.com",
        "CRClass": "B - Substantive",
        "ChangeType": "Scope",
        "AffectedArtifacts": "WBS 1.2",
        "Description": "Extend scope to include module Y.",
        "Reason": "Client requested additional capability.",
        "ImpactScope": "Medium",
        "ImpactQuality": "Low",
        "ImpactScheduleDays": None,
        "ImpactCost": None,
        "IntakeID": None,
        "Decision": "Pending",
        "DecidedByEmail": None,
        "DecidedDate": None,
        "ImplementationVerified": False,
        "LinkedArtifactsUpdated": False,
        "CRStatus": "Open",
        "CRCode": "",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


def _document(**over):
    base = {
        "item_id": "5",
        "Title": "Backup runbook",
        "DocTypeCode": "SOP",
        "Subtitle": None,
        "PrimaryDepartment": "Operations / PMO",
        "OwnerEmail": "pm@theragen.com",
        "ApproverEmail": None,
        "LifecyclePhase": "",
        "Status": "",
        "ReviewCycle": "",
        "Classification": "",
        "StorageSystem": "",
        "StoragePath": "",
        "NextReviewDue": None,
        "IntakeID": None,
        "DocID": "",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


def _cr_conn(**over):
    kw = {"projects": {"THG-IT-001": ("p1", "IT")},
          "persons": {"pm@theragen.com"}}
    kw.update(over)
    return FakeConn(**kw)


def _doc_conn(**over):
    kw = {"persons": {"pm@theragen.com"},
          "doc_types": {"SOP": ("dt-sop", "Operating", "Annual")},
          "departments": {"Operations / PMO": ("dept-ops", "OPS")}}
    kw.update(over)
    return FakeConn(**kw)


# The exact dry-run create strings for an otherwise-valid item. Unaffected
# IntakeID cases (blank or known) must reproduce these byte-for-byte.
CR_DRY = "DRY change_request item 1: would create C-001 (THG-IT-001)"
DOC_DRY = "DRY document item 5: would create THG-OPS-SOP-001 'Backup runbook'"


# ---------------------------------------------------------------------------
# intake_exists helper
# ---------------------------------------------------------------------------

def test_intake_exists_true_when_present():
    conn = FakeConn(intakes={"INT-1"})
    assert sa.intake_exists(conn, "INT-1") is True


def test_intake_exists_false_when_absent():
    conn = FakeConn(intakes={"INT-1"})
    assert sa.intake_exists(conn, "INT-NOPE") is False


# ---------------------------------------------------------------------------
# process_change_request
# ---------------------------------------------------------------------------

def test_cr_unknown_intake_airlocks_gracefully():
    conn = _cr_conn(intakes=set())
    out = sa.process_change_request(conn, _Graph(), _cr(IntakeID="INT-BOGUS"),
                                    dry=True, current=None)
    assert out.startswith("ERROR change_request")
    assert "Unknown IntakeID: INT-BOGUS" in out


def test_cr_blank_intake_unchanged_and_not_queried():
    conn = _cr_conn()
    out = sa.process_change_request(conn, _Graph(), _cr(IntakeID=None),
                                    dry=True, current=None)
    assert out == CR_DRY
    assert conn.intake_queries == []  # blank IntakeID -> no lookup at all


def test_cr_known_intake_unchanged_after_lookup():
    conn = _cr_conn(intakes={"INT-1"})
    out = sa.process_change_request(conn, _Graph(), _cr(IntakeID="INT-1"),
                                    dry=True, current=None)
    assert out == CR_DRY
    assert conn.intake_queries == ["INT-1"]  # validated, found, no error


# ---------------------------------------------------------------------------
# process_document
# ---------------------------------------------------------------------------

def test_document_unknown_intake_airlocks_gracefully():
    conn = _doc_conn(intakes=set())
    out = sa.process_document(conn, _Graph(), _document(IntakeID="INT-X"),
                              dry=True, current=None)
    assert out.startswith("ERROR document")
    assert "Unknown IntakeID: INT-X" in out


def test_document_blank_intake_unchanged_and_not_queried():
    conn = _doc_conn()
    out = sa.process_document(conn, _Graph(), _document(IntakeID=None),
                              dry=True, current=None)
    assert out == DOC_DRY
    assert conn.intake_queries == []


def test_document_known_intake_unchanged_after_lookup():
    conn = _doc_conn(intakes={"INT-1"})
    out = sa.process_document(conn, _Graph(), _document(IntakeID="INT-1"),
                              dry=True, current=None)
    assert out == DOC_DRY
    assert conn.intake_queries == ["INT-1"]
