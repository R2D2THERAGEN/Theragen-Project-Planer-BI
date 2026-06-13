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


# ---------------------------------------------------------------------------
# Activity / WBS helpers (Task 2)
# ---------------------------------------------------------------------------

def _activity(**over):
    """Minimal valid activity fixture."""
    base = {
        "item_id": "42", "Title": "Implement feature X",
        "ProjectCode": "THG-IT-005", "Workstream": "Platform",
        "WorkPackage": "Email delivery",
        "StartPlanned": "2026-06-01", "FinishPlanned": "2026-06-05",
        "StartActual": None, "FinishActual": None,
        "OwnerEmail": "pm@theragen.com",
        "Department": "IT / Data / Security",
        "ActivityStatus": "Not started", "PctComplete": None,
        "ActivityCode": "", "SyncStatus": "Pending",
    }
    base.update(over)
    return base


# --- working_days -----------------------------------------------------------

class TestWorkingDays:
    def test_full_mon_fri_week(self):
        # 2026-06-01 (Mon) through 2026-06-05 (Fri) = 5 working days
        assert al.working_days("2026-06-01", "2026-06-05") == 5

    def test_sat_sun_span_is_zero(self):
        # 2026-06-06 (Sat) through 2026-06-07 (Sun) = 0 working days
        assert al.working_days("2026-06-06", "2026-06-07") == 0

    def test_single_weekday(self):
        # 2026-06-03 (Wed) = 1 working day
        assert al.working_days("2026-06-03", "2026-06-03") == 1

    def test_finish_before_start_returns_zero(self):
        assert al.working_days("2026-06-05", "2026-06-01") == 0

    def test_blank_start_returns_zero(self):
        assert al.working_days("", "2026-06-05") == 0
        assert al.working_days(None, "2026-06-05") == 0

    def test_blank_finish_returns_zero(self):
        assert al.working_days("2026-06-01", "") == 0
        assert al.working_days("2026-06-01", None) == 0

    def test_known_span_five_days(self):
        # 2026-06-01 Mon through 2026-06-05 Fri = 5
        assert al.working_days("2026-06-01", "2026-06-05") == 5

    def test_known_span_six_days(self):
        # 2026-06-01 Mon through 2026-06-08 Mon = 6 (skip Sat+Sun)
        assert al.working_days("2026-06-01", "2026-06-08") == 6


# --- next_wbs_code ----------------------------------------------------------

class TestNextWbsCode:
    def test_empty_list_returns_one(self):
        assert al.next_wbs_code([]) == "1"

    def test_two_existing_level1(self):
        assert al.next_wbs_code(["1", "2"]) == "3"

    def test_level2_with_parent(self):
        # parent "1", existing children "1.1" and "1.2" -> "1.3"
        assert al.next_wbs_code(["1.1", "1.2"], parent_code="1") == "1.3"

    def test_widens_beyond_nine(self):
        # codes 1 through 10 -> next is 11
        codes = [str(i) for i in range(1, 11)]
        assert al.next_wbs_code(codes) == "11"

    def test_parent_codes_ignored_for_level1(self):
        # level-1 call ignores "1.1", "1.2" (they are not pure digits)
        assert al.next_wbs_code(["1.1", "1.2"]) == "1"

    def test_level1_codes_ignored_for_level2(self):
        # sibling filter: "1" and "2" are not children of parent "1"
        assert al.next_wbs_code(["1", "2"], parent_code="1") == "1.1"


# --- next_activity_code -----------------------------------------------------

class TestNextActivityCode:
    def test_empty_codes_returns_a1(self):
        assert al.next_activity_code([], "1.1") == "1.1-A1"

    def test_sequences_within_wbs(self):
        assert al.next_activity_code(["1.1-A1", "1.1-A2"], "1.1") == "1.1-A3"

    def test_codes_for_different_wbs_ignored(self):
        # "1.2-A1" belongs to wbs 1.2, not 1.1
        assert al.next_activity_code(["1.2-A1", "1.2-A2"], "1.1") == "1.1-A1"

    def test_mixed_wbs_only_counts_matching(self):
        codes = ["1.1-A1", "1.1-A2", "1.2-A1"]
        assert al.next_activity_code(codes, "1.1") == "1.1-A3"
        assert al.next_activity_code(codes, "1.2") == "1.2-A2"


# --- validate_activity ------------------------------------------------------

class TestValidateActivity:
    def test_happy_path(self):
        assert al.validate_activity(_activity()) == []

    def test_missing_project_code(self):
        errs = al.validate_activity(_activity(ProjectCode=""))
        assert any("ProjectCode" in e for e in errs)

    def test_missing_title(self):
        errs = al.validate_activity(_activity(Title=""))
        assert any("Title" in e for e in errs)

    def test_missing_workstream(self):
        errs = al.validate_activity(_activity(Workstream=None))
        assert any("Workstream" in e for e in errs)

    def test_missing_workpackage(self):
        errs = al.validate_activity(_activity(WorkPackage="  "))
        assert any("WorkPackage" in e for e in errs)

    def test_missing_start_planned(self):
        errs = al.validate_activity(_activity(StartPlanned=""))
        assert any("StartPlanned" in e for e in errs)

    def test_missing_finish_planned(self):
        errs = al.validate_activity(_activity(FinishPlanned=None))
        assert any("FinishPlanned" in e for e in errs)

    def test_missing_department(self):
        errs = al.validate_activity(_activity(Department=""))
        assert any("Department" in e for e in errs)

    def test_missing_owner_email(self):
        errs = al.validate_activity(_activity(OwnerEmail=""))
        assert any("Owner" in e for e in errs)

    def test_bad_activity_status(self):
        errs = al.validate_activity(_activity(ActivityStatus="Unknown"))
        assert any("ActivityStatus" in e for e in errs)

    def test_bad_department(self):
        errs = al.validate_activity(_activity(Department="Magic"))
        assert any("Department" in e for e in errs)

    def test_finish_before_start(self):
        errs = al.validate_activity(
            _activity(StartPlanned="2026-06-10", FinishPlanned="2026-06-05"))
        assert any("FinishPlanned" in e for e in errs)

    def test_pct_complete_over_100(self):
        errs = al.validate_activity(_activity(PctComplete=101))
        assert any("PctComplete" in e for e in errs)

    def test_done_without_finish_actual_is_error(self):
        errs = al.validate_activity(
            _activity(ActivityStatus="Done", FinishActual=None))
        assert any("FinishActual" in e for e in errs)

    def test_done_with_finish_actual_is_ok(self):
        assert al.validate_activity(
            _activity(ActivityStatus="Done", FinishActual="2026-06-05")) == []

    def test_all_valid_statuses_accepted(self):
        for status in al.ACTIVITY_STATUSES:
            act = _activity(ActivityStatus=status)
            if status == "Done":
                act["FinishActual"] = "2026-06-05"
            errs = al.validate_activity(act)
            assert not any("ActivityStatus" in e for e in errs), \
                f"Status '{status}' should be valid but got: {errs}"

    def test_all_valid_departments_accepted(self):
        for dept in al.DEPARTMENTS:
            errs = al.validate_activity(_activity(Department=dept))
            assert not any("Department" in e for e in errs), \
                f"Department '{dept}' should be valid but got: {errs}"


# --- build_activity_row -----------------------------------------------------

class TestBuildActivityRow:
    def test_duration_days_computed(self):
        row = al.build_activity_row(
            _activity(StartPlanned="2026-06-01", FinishPlanned="2026-06-05"),
            wbs_element_id=99, owner_person_id=7, activity_code="1.1-A1")
        assert row["duration_days"] == 5

    def test_pct_complete_defaults_zero_when_none(self):
        row = al.build_activity_row(
            _activity(PctComplete=None),
            wbs_element_id=99, owner_person_id=7, activity_code="1.1-A1")
        assert row["pct_complete"] == 0.0

    def test_pct_complete_preserved_when_given(self):
        row = al.build_activity_row(
            _activity(PctComplete=75),
            wbs_element_id=99, owner_person_id=7, activity_code="1.1-A1")
        assert row["pct_complete"] == 75.0

    def test_name_truncated_to_200(self):
        long_title = "X" * 250
        row = al.build_activity_row(
            _activity(Title=long_title),
            wbs_element_id=99, owner_person_id=7, activity_code="1.1-A1")
        assert len(row["name"]) == 200

    def test_wbs_element_id_and_activity_code_stored(self):
        row = al.build_activity_row(
            _activity(), wbs_element_id=55, owner_person_id=3,
            activity_code="2.1-A4")
        assert row["wbs_element_id"] == 55
        assert row["activity_code"] == "2.1-A4"
        assert row["owner_person_id"] == 3
