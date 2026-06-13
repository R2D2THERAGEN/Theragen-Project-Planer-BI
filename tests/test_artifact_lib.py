# tests/test_artifact_lib.py
import datetime
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))
import artifact_lib as al


def _risk(**over):
    base = {"item_id": "7", "Title": "Vendor slip", "ProjectCode": "THG-IT-001",
            "Category": "Vendor", "Description": "Vendor may slip the date.",
            "Trigger": None, "Likelihood": "4", "Impact": "3",
            "ResponseType": "Mitigate", "RiskOwnerEmail": "a@theragen.com",
            "DueDate": "2026-07-01", "RiskStatus": "Open",
            "ResidualScore": None, "ComplianceFlag": "None",
            "RiskCode": "", "SyncStatus": "Pending"}
    base.update(over)
    return base


def _milestone(**over):
    base = {"item_id": "3", "Title": "Go-live", "ProjectCode": "THG-IT-001",
            "BaselineDate": "2026-08-01", "ForecastDate": None,
            "ActualDate": None, "MilestoneStatus": "On track",
            "OwnerRole": "Project Manager", "SyncStatus": "Pending"}
    base.update(over)
    return base


def _report(**over):
    base = {"item_id": "9", "Title": "wk24", "ProjectCode": "THG-IT-001",
            "PeriodStart": "2026-06-08", "PeriodEnd": "2026-06-12",
            "OverallStatus": "Green", "Trend": "Steady",
            "ExecutiveSummary": "On plan.", "DecisionsNeeded": None,
            "SubmittedByEmail": "a@theragen.com", "CreatedByEmail": "",
            "CreatedAt": "2026-06-12T22:00:00Z",
            "Health": {ka: "Green" for ka in al.KNOWLEDGE_AREAS},
            "SyncStatus": "Pending"}
    base.update(over)
    return base


def test_next_risk_code_sequences_and_widens():
    assert al.next_risk_code([]) == "R-001"
    assert al.next_risk_code(["R-001", "R-007", None, "x"]) == "R-008"
    assert al.next_risk_code(["R-999"]) == "R-1000"  # widens, never truncates


def test_risk_score_bounds():
    assert al.risk_score("4", "3") == 12
    assert al.risk_score(5, 5) == 25
    assert al.risk_score(0, 3) is None
    assert al.risk_score("6", 3) is None
    assert al.risk_score(None, 3) is None
    assert al.risk_score("x", 3) is None


def test_validate_risk_happy_and_missing():
    assert al.validate_risk(_risk()) == []
    errs = al.validate_risk(_risk(ProjectCode="", Description="  ",
                                  Likelihood=None, RiskOwnerEmail=""))
    assert any("ProjectCode" in e for e in errs)
    assert any("Description" in e for e in errs)
    assert any("Likelihood" in e for e in errs)
    assert any("RiskOwner" in e for e in errs)


def test_validate_risk_residual_and_membership():
    assert any("Residual" in e for e in al.validate_risk(_risk(ResidualScore=26)))
    assert al.validate_risk(_risk(ResidualScore=25)) == []
    assert any("Category" in e for e in al.validate_risk(_risk(Category="Weather")))


def test_validate_milestone_achieved_needs_actual_date():
    assert al.validate_milestone(_milestone()) == []
    errs = al.validate_milestone(_milestone(MilestoneStatus="Achieved"))
    assert any("ActualDate" in e for e in errs)
    assert al.validate_milestone(_milestone(MilestoneStatus="Achieved",
                                            ActualDate="2026-06-10")) == []


def test_validate_milestone_required():
    errs = al.validate_milestone(_milestone(Title="", BaselineDate=None))
    assert any("Title" in e for e in errs)
    assert any("BaselineDate" in e for e in errs)


def test_validate_status_report_periods_and_membership():
    assert al.validate_status_report(_report()) == []
    errs = al.validate_status_report(_report(PeriodEnd="2026-06-01"))
    assert any("PeriodEnd" in e for e in errs)
    errs = al.validate_status_report(_report(Trend="Sideways"))
    assert any("Trend" in e for e in errs)
    bad_health = {ka: "Green" for ka in al.KNOWLEDGE_AREAS}
    bad_health["Cost"] = "Purple"
    errs = al.validate_status_report(_report(Health=bad_health))
    assert any("Cost" in e for e in errs)


def test_validate_status_report_submitter_fallback():
    # empty picker but createdBy known -> no error
    assert al.validate_status_report(
        _report(SubmittedByEmail="", CreatedByEmail="pm@theragen.com")) == []
    errs = al.validate_status_report(_report(SubmittedByEmail="", CreatedByEmail=""))
    assert any("SubmittedBy" in e for e in errs)


def test_build_area_rows_complete_and_ordered():
    health = {ka: "Green" for ka in al.KNOWLEDGE_AREAS}
    health["Schedule"] = "Red"
    rows = al.build_area_rows(_report(Health=health))
    assert [r["knowledge_area"] for r in rows] == al.KNOWLEDGE_AREAS  # 9, in order
    assert {r["knowledge_area"]: r["status"] for r in rows}["Schedule"] == "Red"


def test_row_changed_normalizes_types():
    cur = {"due_date": datetime.date(2026, 7, 1), "residual_score": Decimal("12"),
           "description": "x", "trigger": None}
    assert not al.row_changed(cur, {"due_date": "2026-07-01",
                                    "residual_score": 12,
                                    "description": "x", "trigger": ""})
    assert al.row_changed(cur, {"due_date": "2026-07-02"})
