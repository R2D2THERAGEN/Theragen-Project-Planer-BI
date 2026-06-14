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

    def test_month_boundary(self):
        # 2026-06-29 (Mon) through 2026-07-03 (Fri) = 5 working days (crosses month end)
        assert al.working_days("2026-06-29", "2026-07-03") == 5


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

    def test_non_contiguous_level1(self):
        # existing codes 1, 2, 4 (gap) -> next is 5 (max + 1, not fill-gap)
        assert al.next_wbs_code(["1", "2", "4"]) == "5"

    def test_non_contiguous_level2(self):
        # existing children 2.1 and 2.3 (gap) -> next is 2.4 (max + 1)
        assert al.next_wbs_code(["2.1", "2.3"], parent_code="2") == "2.4"


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

    def test_pct_complete_zero_is_valid(self):
        # PctComplete = 0 is a valid boundary value — no errors expected
        assert al.validate_activity(_activity(PctComplete=0)) == []

    def test_pct_complete_hundred_is_valid(self):
        # PctComplete = 100 is the upper boundary — no errors expected
        assert al.validate_activity(_activity(PctComplete=100)) == []


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


# ===========================================================================
# Change Request / Decision logic (Task 2b-T2)
# ===========================================================================

def _cr(**over):
    """Minimal valid normalized change-request item (Pending + no decider)."""
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


def _decision(**over):
    """Minimal valid normalized decision item."""
    base = {
        "item_id": "2",
        "ProjectCode": "THG-IT-001",
        "Title": "Proceed with vendor A for hosting.",
        "Rationale": "Best value for cost and SLA.",
        "DecidedByEmail": "sponsor@theragen.com",
        "DecidedDate": "2026-06-05",
        "DecisionCode": "",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


# --- next_cr_code / next_decision_code --------------------------------------

class TestNextCrCode:
    def test_empty_list(self):
        assert al.next_cr_code([]) == "C-001"

    def test_sequences_and_widens(self):
        assert al.next_cr_code(["C-001", "C-007", None, "x"]) == "C-008"

    def test_widens_beyond_999(self):
        assert al.next_cr_code(["C-999"]) == "C-1000"

    def test_non_matching_strings_ignored(self):
        # "D-001" and "R-001" should not count
        assert al.next_cr_code(["D-001", "R-001"]) == "C-001"


class TestNextDecisionCode:
    def test_empty_list(self):
        assert al.next_decision_code([]) == "D-001"

    def test_sequences_and_widens(self):
        assert al.next_decision_code(["D-001", "D-007", None, "x"]) == "D-008"

    def test_widens_beyond_999(self):
        assert al.next_decision_code(["D-999"]) == "D-1000"

    def test_non_matching_strings_ignored(self):
        assert al.next_decision_code(["C-001", "R-001"]) == "D-001"


# --- validate_change_request ------------------------------------------------

class TestValidateChangeRequest:
    def test_happy_pending_cr(self):
        assert al.validate_change_request(_cr()) == []

    def test_missing_project_code(self):
        errs = al.validate_change_request(_cr(ProjectCode=""))
        assert any("ProjectCode" in e for e in errs)

    def test_missing_description(self):
        errs = al.validate_change_request(_cr(Description="  "))
        assert any("Description" in e for e in errs)

    def test_missing_reason(self):
        errs = al.validate_change_request(_cr(Reason=None))
        assert any("Reason" in e for e in errs)

    def test_missing_cr_class(self):
        errs = al.validate_change_request(_cr(CRClass=""))
        assert any("CRClass" in e for e in errs)

    def test_missing_change_type(self):
        errs = al.validate_change_request(_cr(ChangeType=""))
        assert any("ChangeType" in e for e in errs)

    def test_requester_empty_flagged(self):
        errs = al.validate_change_request(_cr(RequestedByEmail=""))
        assert any("RequestedBy" in e for e in errs)

    def test_bad_cr_class(self):
        errs = al.validate_change_request(_cr(CRClass="X - Unknown"))
        assert any("CRClass" in e for e in errs)

    def test_bad_change_type(self):
        errs = al.validate_change_request(_cr(ChangeType="People"))
        assert any("ChangeType" in e for e in errs)

    def test_bad_decision(self):
        errs = al.validate_change_request(_cr(Decision="Maybe"))
        assert any("Decision" in e for e in errs)

    def test_bad_cr_status(self):
        errs = al.validate_change_request(_cr(CRStatus="Unknown"))
        assert any("CRStatus" in e for e in errs)

    def test_approved_without_decided_by_flagged(self):
        errs = al.validate_change_request(_cr(
            Decision="Approved", DecidedByEmail="", DecidedDate="2026-06-10"))
        assert any("DecidedBy" in e for e in errs)

    def test_approved_without_decided_date_flagged(self):
        errs = al.validate_change_request(_cr(
            Decision="Approved", DecidedByEmail="approver@theragen.com",
            DecidedDate=None))
        assert any("DecidedDate" in e for e in errs)

    def test_pending_with_decided_date_flagged(self):
        errs = al.validate_change_request(_cr(
            Decision="Pending", DecidedDate="2026-06-10"))
        assert any("DecidedDate" in e for e in errs)

    def test_rejected_decision_requires_rejected_status(self):
        errs = al.validate_change_request(_cr(
            Decision="Rejected", DecidedByEmail="a@theragen.com",
            DecidedDate="2026-06-10", CRStatus="Open"))
        assert any("Rejected" in e for e in errs)

    def test_verified_status_requires_approved_decision(self):
        errs = al.validate_change_request(_cr(
            CRStatus="Verified", Decision="Pending"))
        assert any("Verified" in e or "Approved" in e for e in errs)

    def test_closed_status_with_approved_is_ok(self):
        assert al.validate_change_request(_cr(
            CRStatus="Closed", Decision="Approved",
            DecidedByEmail="a@theragen.com",
            DecidedDate="2026-06-10")) == []

    def test_decided_date_before_requested_date_flagged(self):
        errs = al.validate_change_request(_cr(
            Decision="Approved",
            DecidedByEmail="a@theragen.com",
            RequestedDate="2026-06-10",
            DecidedDate="2026-06-05"))
        assert any("DecidedDate" in e for e in errs)

    def test_fully_valid_approved_implementing_cr(self):
        assert al.validate_change_request(_cr(
            Decision="Approved",
            DecidedByEmail="sponsor@theragen.com",
            DecidedDate="2026-06-10",
            CRStatus="Implementing")) == []


# --- validate_decision -------------------------------------------------------

class TestValidateDecision:
    def test_happy_path(self):
        assert al.validate_decision(_decision()) == []

    def test_missing_title(self):
        errs = al.validate_decision(_decision(Title=""))
        assert any("Title" in e for e in errs)

    def test_missing_project_code(self):
        errs = al.validate_decision(_decision(ProjectCode=""))
        assert any("ProjectCode" in e for e in errs)

    def test_missing_rationale(self):
        errs = al.validate_decision(_decision(Rationale=None))
        assert any("Rationale" in e for e in errs)

    def test_missing_decided_date(self):
        errs = al.validate_decision(_decision(DecidedDate=""))
        assert any("DecidedDate" in e for e in errs)

    def test_missing_decided_by_email(self):
        errs = al.validate_decision(_decision(DecidedByEmail=""))
        assert any("DecidedBy" in e for e in errs)


# --- build_cr_row -----------------------------------------------------------

class TestBuildCrRow:
    def _row(self, **over):
        it = _cr(**over)
        return al.build_cr_row(it, project_id=10, requester_id=1,
                               decider_id=None, cr_code="C-001")

    def test_basic_columns_present(self):
        row = self._row()
        assert row["project_id"] == 10
        assert row["cr_code"] == "C-001"
        assert row["requested_by_person_id"] == 1
        assert row["decided_by_person_id"] is None

    def test_change_types_equals_change_type(self):
        row = self._row(ChangeType="Cost")
        assert row["change_types"] == "Cost"

    def test_affected_artifacts_defaults_na_when_blank(self):
        row = self._row(AffectedArtifacts="")
        assert row["affected_artifacts"] == "n/a"
        row2 = self._row(AffectedArtifacts=None)
        assert row2["affected_artifacts"] == "n/a"

    def test_affected_artifacts_preserved_when_set(self):
        row = self._row(AffectedArtifacts="WBS 1.2")
        assert row["affected_artifacts"] == "WBS 1.2"

    def test_impact_schedule_days_defaults_zero(self):
        row = self._row(ImpactScheduleDays=None)
        assert row["impact_schedule_days"] == 0
        row2 = self._row(ImpactScheduleDays="")
        assert row2["impact_schedule_days"] == 0

    def test_impact_schedule_days_coerced_to_int(self):
        row = self._row(ImpactScheduleDays="14")
        assert row["impact_schedule_days"] == 14

    def test_impact_cost_defaults_zero(self):
        row = self._row(ImpactCost=None)
        assert row["impact_cost"] == 0.0
        row2 = self._row(ImpactCost="")
        assert row2["impact_cost"] == 0.0

    def test_impact_cost_coerced_to_float(self):
        row = self._row(ImpactCost="5000.50")
        assert row["impact_cost"] == 5000.50

    def test_implementation_verified_passthrough_bool(self):
        row = self._row(ImplementationVerified=True)
        assert row["implementation_verified"] is True
        row2 = self._row(ImplementationVerified=False)
        assert row2["implementation_verified"] is False

    def test_linked_artifacts_updated_passthrough_bool(self):
        row = self._row(LinkedArtifactsUpdated=True)
        assert row["linked_artifacts_updated"] is True

    def test_status_defaults_open(self):
        row = self._row(CRStatus=None)
        assert row["status"] == "Open"

    def test_decision_defaults_pending(self):
        row = self._row(Decision=None)
        assert row["decision"] == "Pending"

    def test_requested_at_equals_requested_date(self):
        row = self._row(RequestedDate="2026-05-15")
        assert row["requested_at"] == "2026-05-15"

    def test_decided_at_set_when_provided(self):
        it = _cr(Decision="Approved", DecidedByEmail="a@theragen.com",
                 DecidedDate="2026-06-10")
        row = al.build_cr_row(it, project_id=10, requester_id=1,
                              decider_id=5, cr_code="C-002")
        assert row["decided_at"] == "2026-06-10"
        assert row["decided_by_person_id"] == 5


# --- build_decision_row -----------------------------------------------------

class TestBuildDecisionRow:
    def test_columns_present(self):
        row = al.build_decision_row(_decision(), project_id=10,
                                    decider_id=5, code="D-001")
        assert row["project_id"] == 10
        assert row["code"] == "D-001"
        assert row["decision"] == _decision()["Title"]
        assert row["rationale"] == _decision()["Rationale"]
        assert row["decided_by_person_id"] == 5
        assert row["decided_at"] == _decision()["DecidedDate"]


# --- build_report_row extension ---------------------------------------------

class TestBuildReportRowExtension:
    def test_approved_by_defaults_none(self):
        row = al.build_report_row(_report(), project_id=10,
                                  submitted_by_person_id=1)
        assert row["approved_by_person_id"] is None
        assert row["approved_at"] is None

    def test_approved_by_person_id_set(self):
        rpt = _report()
        rpt["ApprovedDate"] = "2026-06-15"
        row = al.build_report_row(rpt, project_id=10,
                                  submitted_by_person_id=1,
                                  approved_by_person_id=7)
        assert row["approved_by_person_id"] == 7
        assert row["approved_at"] == "2026-06-15"

    def test_existing_3arg_callers_unaffected(self):
        # Simulates existing callers: build_report_row(it, project_id, submitter)
        row = al.build_report_row(_report(), 10, 1)
        assert row["project_id"] == 10
        assert row["submitted_by_person_id"] == 1
        assert row["approved_by_person_id"] is None


# --- _trail_states ----------------------------------------------------------

class TestTrailStates:
    def test_returns_before_and_after(self):
        current = {"decision": "Pending", "status": "Open", "other": "x"}
        desired = {"decision": "Approved", "status": "Implementing", "other": "y"}
        before, after = al._trail_states(current, desired,
                                         ["decision", "status"])
        assert before == {"decision": "Pending", "status": "Open"}
        assert after == {"decision": "Approved", "status": "Implementing"}

    def test_only_requested_keys_included(self):
        current = {"decision": "Pending", "status": "Open", "other": "x"}
        desired = {"decision": "Approved", "status": "Implementing", "other": "y"}
        before, after = al._trail_states(current, desired, ["decision"])
        assert "other" not in before
        assert "other" not in after

    def test_missing_current_key_gives_none(self):
        current = {}
        desired = {"decision": "Approved", "status": "Open"}
        before, after = al._trail_states(current, desired,
                                         ["decision", "status"])
        assert before["decision"] is None
        assert after["decision"] == "Approved"


# ===========================================================================
# Baseline + Phase-Gate logic (Task 2c-1 T2)
# ===========================================================================
import json
import random
from decimal import Decimal


# ---------------------------------------------------------------------------
# next_baseline_version
# ---------------------------------------------------------------------------

class TestNextBaselineVersion:
    def test_empty_list_returns_1_0(self):
        assert al.next_baseline_version([]) == "1.0"

    def test_sequences_past_existing(self):
        # ["1.0","2.0",None,"x"] -> matches 1 and 2; max+1 = 3 -> "3.0"
        assert al.next_baseline_version(["1.0", "2.0", None, "x"]) == "3.0"

    def test_nine_becomes_ten(self):
        assert al.next_baseline_version(["9.0"]) == "10.0"

    def test_non_matching_strings_ignored(self):
        # "1.1" does not match ^(\d+)\.0$ so treated as no valid versions -> "1.0"
        assert al.next_baseline_version(["1.1"]) == "1.0"

    def test_none_entries_ignored(self):
        assert al.next_baseline_version([None, None]) == "1.0"

    def test_single_valid_entry(self):
        assert al.next_baseline_version(["1.0"]) == "2.0"


# ---------------------------------------------------------------------------
# validate_baseline
# ---------------------------------------------------------------------------

def _baseline(**over):
    """Minimal valid baseline item fixture."""
    base = {
        "ProjectCode": "THG-IT-005",
        "BaselineType": "Schedule",
        "BaselinedByEmail": "pm@theragen.com",
        "ChangeSummary": "Initial baseline",
        "BaselineVersion": "",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


class TestValidateBaseline:
    def test_happy_path(self):
        assert al.validate_baseline(_baseline()) == []

    def test_missing_project_code(self):
        errs = al.validate_baseline(_baseline(ProjectCode=""))
        assert any("ProjectCode" in e for e in errs)

    def test_missing_baseline_type(self):
        errs = al.validate_baseline(_baseline(BaselineType=""))
        assert any("BaselineType" in e for e in errs)

    def test_missing_baselined_by_email(self):
        errs = al.validate_baseline(_baseline(BaselinedByEmail=""))
        assert any("BaselinedBy" in e for e in errs)

    def test_missing_baselined_by_none(self):
        errs = al.validate_baseline(_baseline(BaselinedByEmail=None))
        assert any("BaselinedBy" in e for e in errs)

    def test_bad_baseline_type(self):
        errs = al.validate_baseline(_baseline(BaselineType="Resources"))
        assert any("BaselineType" in e for e in errs)

    def test_all_valid_baseline_types_accepted(self):
        for bt in al.BASELINE_TYPES:
            assert al.validate_baseline(_baseline(BaselineType=bt)) == [], \
                f"BaselineType '{bt}' should be valid"

    def test_multiple_missing_fields(self):
        errs = al.validate_baseline(_baseline(ProjectCode="", BaselineType="",
                                              BaselinedByEmail=""))
        assert any("ProjectCode" in e for e in errs)
        assert any("BaselineType" in e for e in errs)
        assert any("BaselinedBy" in e for e in errs)


# ---------------------------------------------------------------------------
# validate_phase_gate
# ---------------------------------------------------------------------------

def _phase_gate(**over):
    """Minimal valid phase-gate item fixture."""
    base = {
        "ProjectCode": "THG-IT-005",
        "TargetPhase": "Planning",
        "GateDecision": "Approved",
        "ApprovedByEmail": "sponsor@theragen.com",
        "DecidedDate": "2026-06-13",
        "GateNotes": "",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


class TestValidatePhaseGate:
    def test_happy_path(self):
        assert al.validate_phase_gate(_phase_gate()) == []

    def test_missing_project_code(self):
        errs = al.validate_phase_gate(_phase_gate(ProjectCode=""))
        assert any("ProjectCode" in e for e in errs)

    def test_missing_target_phase(self):
        errs = al.validate_phase_gate(_phase_gate(TargetPhase=""))
        assert any("TargetPhase" in e for e in errs)

    def test_missing_gate_decision(self):
        errs = al.validate_phase_gate(_phase_gate(GateDecision=""))
        assert any("GateDecision" in e for e in errs)

    def test_missing_approved_by_email(self):
        errs = al.validate_phase_gate(_phase_gate(ApprovedByEmail=""))
        assert any("ApprovedBy" in e for e in errs)

    def test_missing_approved_by_none(self):
        errs = al.validate_phase_gate(_phase_gate(ApprovedByEmail=None))
        assert any("ApprovedBy" in e for e in errs)

    def test_bad_target_phase(self):
        errs = al.validate_phase_gate(_phase_gate(TargetPhase="Discovery"))
        assert any("TargetPhase" in e for e in errs)

    def test_bad_gate_decision(self):
        errs = al.validate_phase_gate(_phase_gate(GateDecision="Rejected"))
        assert any("GateDecision" in e for e in errs)

    def test_all_valid_phases_accepted(self):
        for phase in al.LIFECYCLE_PHASES:
            assert al.validate_phase_gate(_phase_gate(TargetPhase=phase)) == [], \
                f"TargetPhase '{phase}' should be valid"

    def test_all_valid_gate_decisions_accepted(self):
        for dec in al.GATE_DECISIONS:
            assert al.validate_phase_gate(_phase_gate(GateDecision=dec)) == [], \
                f"GateDecision '{dec}' should be valid"

    def test_multiple_missing_fields(self):
        errs = al.validate_phase_gate(_phase_gate(
            ProjectCode="", TargetPhase="", GateDecision="", ApprovedByEmail=""))
        assert any("ProjectCode" in e for e in errs)
        assert any("TargetPhase" in e for e in errs)
        assert any("GateDecision" in e for e in errs)
        assert any("ApprovedBy" in e for e in errs)


# ---------------------------------------------------------------------------
# assemble_schedule_snapshot
# ---------------------------------------------------------------------------

def _act(code, name, start, finish, dur):
    """Helper: create an activity row (dates as datetime.date to prove _d coercion)."""
    return {
        "activity_code": code,
        "name": name,
        "start_planned": datetime.date.fromisoformat(start),
        "finish_planned": datetime.date.fromisoformat(finish),
        "duration_days": dur,
    }


def _mil(name, baseline_date):
    """Helper: milestone row (date as datetime.date or None)."""
    return {
        "name": name,
        "baseline_date": datetime.date.fromisoformat(baseline_date) if baseline_date else None,
    }


_HEADLINE = {"planned_start": datetime.date(2026, 6, 1),
             "planned_finish": datetime.date(2026, 9, 30)}

# A set of activity rows in a canonical order
_ACTIVITIES = [
    _act("1.1-A1", "Design",   "2026-06-01", "2026-06-10", 8),
    _act("1.1-A2", "Build",    "2026-06-11", "2026-06-25", 11),
    _act("1.2-A1", "Test",     "2026-06-26", "2026-07-05", 8),
    _act("2.1-A1", "Deploy",   "2026-07-06", "2026-07-10", 5),
]

# A set of milestone rows with varying dates (incl. one None-date) to test sort stability
_MILESTONES = [
    _mil("Go-live",    "2026-09-01"),
    _mil("UAT sign-off", "2026-08-01"),
    _mil("Kickoff",    "2026-06-01"),
    _mil("Orphan",     None),          # None baseline_date -> sorts to front (or "")
]


class TestAssembleScheduleSnapshot:
    def _snap(self, acts, mils):
        return al.assemble_schedule_snapshot(acts, mils, _HEADLINE)

    def test_type_field(self):
        snap = self._snap(_ACTIVITIES, _MILESTONES)
        assert snap["type"] == "Schedule"

    def test_activities_sorted_by_code(self):
        shuffled = list(_ACTIVITIES)
        random.shuffle(shuffled)
        snap = self._snap(shuffled, _MILESTONES)
        codes = [a["code"] for a in snap["activities"]]
        assert codes == sorted(codes)

    def test_activities_exact_keys(self):
        snap = self._snap(_ACTIVITIES, _MILESTONES)
        expected_keys = {"code", "name", "start_planned", "finish_planned", "duration_days"}
        for act in snap["activities"]:
            assert set(act.keys()) == expected_keys

    def test_dates_are_strings(self):
        snap = self._snap(_ACTIVITIES, _MILESTONES)
        for act in snap["activities"]:
            assert isinstance(act["start_planned"], str)
            assert isinstance(act["finish_planned"], str)
            # must be YYYY-MM-DD
            assert len(act["start_planned"]) == 10
            assert len(act["finish_planned"]) == 10

    def test_duration_days_is_int(self):
        snap = self._snap(_ACTIVITIES, _MILESTONES)
        for act in snap["activities"]:
            assert isinstance(act["duration_days"], int)

    def test_milestones_sorted_by_date_then_name(self):
        # After sort: None ("") comes first, then ascending date
        snap = self._snap(_ACTIVITIES, _MILESTONES)
        dates = [m["baseline_date"] for m in snap["milestones"]]
        # None maps to "" in the sort key, so None-date rows come first
        assert dates[0] is None
        # remaining dates should be in ascending order
        non_none = [d for d in dates if d is not None]
        assert non_none == sorted(non_none)

    def test_milestone_exact_keys(self):
        snap = self._snap(_ACTIVITIES, _MILESTONES)
        for m in snap["milestones"]:
            assert set(m.keys()) == {"name", "baseline_date"}

    def test_milestone_dates_are_strings_or_none(self):
        snap = self._snap(_ACTIVITIES, _MILESTONES)
        for m in snap["milestones"]:
            assert m["baseline_date"] is None or isinstance(m["baseline_date"], str)

    def test_headline_dates_are_strings(self):
        snap = self._snap(_ACTIVITIES, _MILESTONES)
        assert snap["headline"]["planned_start"] == "2026-06-01"
        assert snap["headline"]["planned_finish"] == "2026-09-30"

    def test_byte_determinism(self):
        """Two calls with differently-shuffled inputs must produce identical JSON."""
        order1 = list(_ACTIVITIES)
        order2 = list(reversed(_ACTIVITIES))
        mils1 = list(_MILESTONES)
        mils2 = list(reversed(_MILESTONES))
        a = al.assemble_schedule_snapshot(order1, mils1, _HEADLINE)
        b = al.assemble_schedule_snapshot(order2, mils2, _HEADLINE)
        assert json.dumps(a, sort_keys=False) == json.dumps(b, sort_keys=False)

    def test_decimal_duration_coerced_to_int(self):
        """psycopg may return Decimal for numeric columns; _d/int() must handle it."""
        acts = [{"activity_code": "1.1-A1", "name": "X",
                 "start_planned": datetime.date(2026, 6, 1),
                 "finish_planned": datetime.date(2026, 6, 5),
                 "duration_days": Decimal("5")}]
        snap = al.assemble_schedule_snapshot(acts, [], _HEADLINE)
        assert snap["activities"][0]["duration_days"] == 5
        assert isinstance(snap["activities"][0]["duration_days"], int)


# ---------------------------------------------------------------------------
# assemble_budget_snapshot
# ---------------------------------------------------------------------------

_BUDGET_LINES = [
    {"wbs_code": "1.2", "category": "Labour",    "total": Decimal("50000.00"), "funding_source": "Internal"},
    {"wbs_code": "1.1", "category": "Equipment", "total": Decimal("12000.50"), "funding_source": "Grant"},
    {"wbs_code": "1.1", "category": "Labour",    "total": Decimal("30000.00"), "funding_source": "Internal"},
    {"wbs_code": "2.1", "category": "Travel",    "total": Decimal("3500.00"),  "funding_source": "Internal"},
]


class TestAssembleBudgetSnapshot:
    def _snap(self, lines, total=Decimal("95500.50")):
        return al.assemble_budget_snapshot(total, lines)

    def test_type_field(self):
        assert self._snap(_BUDGET_LINES)["type"] == "Budget"

    def test_lines_sorted_by_wbs_then_category(self):
        shuffled = list(_BUDGET_LINES)
        random.shuffle(shuffled)
        snap = al.assemble_budget_snapshot(Decimal("95500.50"), shuffled)
        keys = [(l["wbs_code"], l["category"]) for l in snap["lines"]]
        assert keys == sorted(keys)

    def test_total_coerced_to_float(self):
        snap = self._snap(_BUDGET_LINES, Decimal("95500.50"))
        assert isinstance(snap["budget_total"], float)
        assert snap["budget_total"] == 95500.50

    def test_line_total_coerced_to_float(self):
        snap = self._snap(_BUDGET_LINES)
        for line in snap["lines"]:
            assert isinstance(line["total"], float)

    def test_budget_total_none_preserved(self):
        snap = al.assemble_budget_snapshot(None, [])
        assert snap["budget_total"] is None

    def test_byte_determinism(self):
        order1 = list(_BUDGET_LINES)
        order2 = list(reversed(_BUDGET_LINES))
        a = al.assemble_budget_snapshot(Decimal("95500.50"), order1)
        b = al.assemble_budget_snapshot(Decimal("95500.50"), order2)
        assert json.dumps(a, sort_keys=False) == json.dumps(b, sort_keys=False)

    def test_line_keys_present(self):
        snap = self._snap(_BUDGET_LINES)
        for line in snap["lines"]:
            assert "wbs_code" in line
            assert "category" in line
            assert "total" in line
            assert "funding_source" in line


# ---------------------------------------------------------------------------
# assemble_scope_snapshot
# ---------------------------------------------------------------------------

_CHARTER = {
    "business_case": "Reduce manual processing time by 80%.",
    "high_level_in_scope": "Modules A, B, C.",
    "high_level_out_scope": "Module D (Phase 2).",
}

_INCLUSIONS = [
    {"item": "User authentication", "sequence": 2},
    {"item": "Data import",         "sequence": 1},
    {"item": "Reporting dashboard", "sequence": 3},
]

_EXCLUSIONS = [
    {"item": "Mobile app",          "sequence": 1},
    {"item": "Legacy migration",    "sequence": 2},
]

_ACCEPTANCE = [
    {"criterion": "All unit tests pass", "sequence": 2},
    {"criterion": "UAT sign-off",        "sequence": 1},
]


class TestAssembleScopeSnapshot:
    def test_type_field(self):
        snap = al.assemble_scope_snapshot(_CHARTER, _INCLUSIONS, _EXCLUSIONS, _ACCEPTANCE)
        assert snap["type"] == "Scope"

    def test_charter_fields_mapped(self):
        snap = al.assemble_scope_snapshot(_CHARTER, [], [], [])
        assert snap["charter"]["business_case"] == _CHARTER["business_case"]
        assert snap["charter"]["high_level_in_scope"] == _CHARTER["high_level_in_scope"]
        assert snap["charter"]["high_level_out_scope"] == _CHARTER["high_level_out_scope"]

    def test_inclusions_sorted_by_sequence(self):
        shuffled = list(_INCLUSIONS)
        random.shuffle(shuffled)
        snap = al.assemble_scope_snapshot(_CHARTER, shuffled, [], [])
        assert snap["inclusions"] == ["Data import", "User authentication", "Reporting dashboard"]

    def test_exclusions_sorted_by_sequence(self):
        snap = al.assemble_scope_snapshot(_CHARTER, [], list(reversed(_EXCLUSIONS)), [])
        assert snap["exclusions"] == ["Mobile app", "Legacy migration"]

    def test_acceptance_sorted_by_sequence(self):
        snap = al.assemble_scope_snapshot(_CHARTER, [], [], list(reversed(_ACCEPTANCE)))
        assert snap["acceptance"] == ["UAT sign-off", "All unit tests pass"]

    def test_empty_lists_produce_empty_lists(self):
        snap = al.assemble_scope_snapshot(_CHARTER, [], [], [])
        assert snap["inclusions"] == []
        assert snap["exclusions"] == []
        assert snap["acceptance"] == []

    def test_none_charter_produces_dict_of_nones(self):
        snap = al.assemble_scope_snapshot(None, [], [], [])
        assert snap["charter"] == {
            "business_case": None,
            "high_level_in_scope": None,
            "high_level_out_scope": None,
        }

    def test_missing_sequence_key_treated_as_zero(self):
        """Rows without 'sequence' key must not crash (r.get('sequence', 0))."""
        rows = [{"item": "Alpha"}, {"item": "Beta"}]
        snap = al.assemble_scope_snapshot(_CHARTER, rows, [], [])
        # Both have sequence 0 -> stable sort by insertion; items are present
        assert set(snap["inclusions"]) == {"Alpha", "Beta"}

    def test_byte_determinism(self):
        inc1 = list(_INCLUSIONS)
        inc2 = list(reversed(_INCLUSIONS))
        exc1 = list(_EXCLUSIONS)
        exc2 = list(reversed(_EXCLUSIONS))
        acc1 = list(_ACCEPTANCE)
        acc2 = list(reversed(_ACCEPTANCE))
        a = al.assemble_scope_snapshot(_CHARTER, inc1, exc1, acc1)
        b = al.assemble_scope_snapshot(_CHARTER, inc2, exc2, acc2)
        assert json.dumps(a, sort_keys=False) == json.dumps(b, sort_keys=False)


# ---------------------------------------------------------------------------
# Determinism / total-order regression tests (sort-key hardening)
# ---------------------------------------------------------------------------

class TestBudgetSnapshotTotalOrder:
    """Two lines sharing (wbs_code, category) but differing in funding_source/total
    must produce byte-identical JSON regardless of input order.
    Before the fix (key only on wbs_code+category) the order of these two rows
    was input-order-dependent and json.dumps would have differed."""

    def test_duplicate_wbs_category_different_funding_and_total(self):
        line_a = {"wbs_code": "1.1", "category": "Labour",
                  "total": Decimal("30000.00"), "funding_source": "Grant"}
        line_b = {"wbs_code": "1.1", "category": "Labour",
                  "total": Decimal("50000.00"), "funding_source": "Internal"}
        snap1 = al.assemble_budget_snapshot(Decimal("80000.00"), [line_a, line_b])
        snap2 = al.assemble_budget_snapshot(Decimal("80000.00"), [line_b, line_a])
        # Must be equal — would have been UNEQUAL before the 4-key sort fix
        assert json.dumps(snap1, sort_keys=False) == json.dumps(snap2, sort_keys=False)

    def test_ordering_is_by_funding_source_then_total(self):
        """Grant < Internal alphabetically -> Grant line must appear first."""
        line_grant    = {"wbs_code": "1.1", "category": "Labour",
                         "total": Decimal("30000.00"), "funding_source": "Grant"}
        line_internal = {"wbs_code": "1.1", "category": "Labour",
                         "total": Decimal("50000.00"), "funding_source": "Internal"}
        snap = al.assemble_budget_snapshot(Decimal("80000.00"),
                                           [line_internal, line_grant])
        assert snap["lines"][0]["funding_source"] == "Grant"
        assert snap["lines"][1]["funding_source"] == "Internal"


class TestScopeSnapshotTotalOrder:
    """Two inclusions sharing the same sequence value must sort deterministically
    by item text regardless of input order."""

    def test_tied_sequence_inclusions_byte_stable(self):
        inc_alpha = {"item": "Alpha feature", "sequence": 1}
        inc_zebra = {"item": "Zebra feature", "sequence": 1}
        snap1 = al.assemble_scope_snapshot(None, [inc_alpha, inc_zebra], [], [])
        snap2 = al.assemble_scope_snapshot(None, [inc_zebra, inc_alpha], [], [])
        assert json.dumps(snap1, sort_keys=False) == json.dumps(snap2, sort_keys=False)

    def test_tied_sequence_inclusions_alphabetical_order(self):
        """Alpha < Zebra -> Alpha must come first after tiebreak."""
        inc_alpha = {"item": "Alpha feature", "sequence": 1}
        inc_zebra = {"item": "Zebra feature", "sequence": 1}
        snap = al.assemble_scope_snapshot(None, [inc_zebra, inc_alpha], [], [])
        assert snap["inclusions"] == ["Alpha feature", "Zebra feature"]

    def test_tied_sequence_exclusions_byte_stable(self):
        exc_a = {"item": "Audit trail",  "sequence": 2}
        exc_b = {"item": "Batch export", "sequence": 2}
        snap1 = al.assemble_scope_snapshot(None, [], [exc_a, exc_b], [])
        snap2 = al.assemble_scope_snapshot(None, [], [exc_b, exc_a], [])
        assert json.dumps(snap1, sort_keys=False) == json.dumps(snap2, sort_keys=False)

    def test_tied_sequence_acceptance_byte_stable(self):
        acc_a = {"criterion": "Load test passes",  "sequence": 0}
        acc_b = {"criterion": "Security scan clean", "sequence": 0}
        snap1 = al.assemble_scope_snapshot(None, [], [], [acc_a, acc_b])
        snap2 = al.assemble_scope_snapshot(None, [], [], [acc_b, acc_a])
        assert json.dumps(snap1, sort_keys=False) == json.dumps(snap2, sort_keys=False)


class TestScheduleSnapshotTotalOrder:
    """Defensive: two activities sharing a code (hypothetical) but differing in
    name must sort deterministically.  In practice activity_code is unique per
    project, so this is a belt-and-suspenders guard only.  We test it anyway to
    document the invariant and confirm the (code, name) key is in effect."""

    def test_tied_code_different_name_byte_stable(self):
        act_a = {"activity_code": "1.1-A1", "name": "Alpha task",
                 "start_planned": datetime.date(2026, 6, 1),
                 "finish_planned": datetime.date(2026, 6, 5),
                 "duration_days": 5}
        act_b = {"activity_code": "1.1-A1", "name": "Zebra task",
                 "start_planned": datetime.date(2026, 6, 1),
                 "finish_planned": datetime.date(2026, 6, 5),
                 "duration_days": 5}
        snap1 = al.assemble_schedule_snapshot([act_a, act_b], [], _HEADLINE)
        snap2 = al.assemble_schedule_snapshot([act_b, act_a], [], _HEADLINE)
        assert json.dumps(snap1, sort_keys=False) == json.dumps(snap2, sort_keys=False)

    def test_tied_code_name_is_alphabetical_tiebreak(self):
        act_a = {"activity_code": "1.1-A1", "name": "Alpha task",
                 "start_planned": datetime.date(2026, 6, 1),
                 "finish_planned": datetime.date(2026, 6, 5),
                 "duration_days": 5}
        act_b = {"activity_code": "1.1-A1", "name": "Zebra task",
                 "start_planned": datetime.date(2026, 6, 1),
                 "finish_planned": datetime.date(2026, 6, 5),
                 "duration_days": 5}
        snap = al.assemble_schedule_snapshot([act_b, act_a], [], _HEADLINE)
        assert snap["activities"][0]["name"] == "Alpha task"


# ---------------------------------------------------------------------------
# build_phase_gate_row
# ---------------------------------------------------------------------------

class TestBuildPhaseGateRow:
    def _row(self, **over):
        it = _phase_gate(**over)
        return al.build_phase_gate_row(it, project_id=42,
                                       from_phase="Initiating",
                                       to_phase="Planning",
                                       approver_id=7)

    def test_required_keys_present(self):
        row = self._row()
        expected = {"project_id", "from_phase", "to_phase", "gate_decision",
                    "approved_by_person_id", "decided_at", "gate_notes"}
        assert set(row.keys()) == expected

    def test_project_id_passed_through(self):
        assert self._row()["project_id"] == 42

    def test_from_phase(self):
        assert self._row()["from_phase"] == "Initiating"

    def test_to_phase(self):
        assert self._row()["to_phase"] == "Planning"

    def test_gate_decision_from_item(self):
        assert self._row()["gate_decision"] == "Approved"

    def test_approved_by_person_id(self):
        assert self._row()["approved_by_person_id"] == 7

    def test_decided_at_from_item(self):
        assert self._row()["decided_at"] == "2026-06-13"

    def test_gate_notes_from_item(self):
        row = self._row(GateNotes="Reviewed in board meeting")
        assert row["gate_notes"] == "Reviewed in board meeting"

    def test_gate_notes_defaults_empty_string(self):
        row = self._row()
        # GateNotes="" in fixture -> gate_notes=""
        assert row["gate_notes"] == ""

    def test_decided_at_none_when_absent(self):
        it = _phase_gate()
        del it["DecidedDate"]
        row = al.build_phase_gate_row(it, project_id=1, from_phase="Initiating",
                                      to_phase="Planning", approver_id=3)
        assert row["decided_at"] is None

    def test_held_gate_decision(self):
        row = self._row(GateDecision="Held")
        assert row["gate_decision"] == "Held"


# --- Change Impact Assessment (2c-2) ----------------------------------------

def _impact(**over):
    """Minimal valid normalized change-impact-assessment item.

    Keys are the normalizer's output (SubmittedByEmail already resolved from
    the picker or the item-author fallback; SubmittedDate already defaulted).
    """
    base = {
        "item_id": "3",
        "Title": "Finance impact on C-001",
        "ProjectCode": "THG-IT-001",
        "ParentCRCode": "C-001",
        "Department": "Finance / Procurement",
        "ScopeImpact": "Two extra reconciliation cycles.",
        "ScheduleImpactDays": "5",
        "CostImpact": "2500.00",
        "QualityImpact": "",
        "SubmittedByEmail": "sponsor@theragen.com",
        "SubmittedDate": "2026-06-10",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


class TestValidateImpactAssessment:
    def test_happy_path(self):
        assert al.validate_impact_assessment(_impact()) == []

    def test_missing_project_code(self):
        errs = al.validate_impact_assessment(_impact(ProjectCode=""))
        assert any("ProjectCode" in e for e in errs)

    def test_missing_parent_cr_code(self):
        errs = al.validate_impact_assessment(_impact(ParentCRCode=""))
        assert any("ParentCRCode" in e for e in errs)

    def test_missing_department(self):
        errs = al.validate_impact_assessment(_impact(Department=""))
        assert any("Department" in e for e in errs)

    def test_missing_submitter(self):
        errs = al.validate_impact_assessment(_impact(SubmittedByEmail=""))
        assert any("SubmittedBy" in e for e in errs)

    def test_missing_submitter_none(self):
        errs = al.validate_impact_assessment(_impact(SubmittedByEmail=None))
        assert any("SubmittedBy" in e for e in errs)

    def test_bad_department(self):
        errs = al.validate_impact_assessment(_impact(Department="Legal / IP"))
        assert any("Department not recognized" in e for e in errs)

    def test_all_valid_departments_accepted(self):
        for d in al.DEPARTMENTS:
            assert al.validate_impact_assessment(_impact(Department=d)) == [], \
                f"department {d} should be valid"

    def test_blank_numerics_ok(self):
        assert al.validate_impact_assessment(
            _impact(ScheduleImpactDays="", CostImpact="")) == []
        assert al.validate_impact_assessment(
            _impact(ScheduleImpactDays=None, CostImpact=None)) == []

    def test_non_integer_schedule_flagged(self):
        errs = al.validate_impact_assessment(_impact(ScheduleImpactDays="abc"))
        assert any("ScheduleImpactDays" in e for e in errs)

    def test_non_numeric_cost_flagged(self):
        errs = al.validate_impact_assessment(_impact(CostImpact="lots"))
        assert any("CostImpact" in e for e in errs)

    def test_submitted_date_optional(self):
        # SubmittedDate is defaulted in the normalizer -> never a validation error
        assert al.validate_impact_assessment(_impact(SubmittedDate="")) == []

    def test_aggregate_missing(self):
        errs = al.validate_impact_assessment(_impact(
            ProjectCode="", ParentCRCode="", Department="", SubmittedByEmail=""))
        assert len(errs) >= 4


class TestBuildImpactAssessmentRow:
    def _row(self, **over):
        it = _impact(**over)
        return al.build_impact_assessment_row(
            it, cr_id="cr-uuid", submitted_by_person_id=7,
            submitted_at="2026-06-10")

    def test_columns_present(self):
        row = self._row()
        assert row["cr_id"] == "cr-uuid"
        assert row["department"] == "Finance / Procurement"
        assert row["submitted_by_person_id"] == 7
        assert row["submitted_at"] == "2026-06-10"

    def test_schedule_days_coerced_int(self):
        row = self._row(ScheduleImpactDays="5")
        assert row["schedule_impact_days"] == 5
        assert isinstance(row["schedule_impact_days"], int)

    def test_schedule_days_blank_none(self):
        assert self._row(ScheduleImpactDays="")["schedule_impact_days"] is None
        assert self._row(ScheduleImpactDays=None)["schedule_impact_days"] is None

    def test_cost_coerced_float(self):
        row = self._row(CostImpact="2500.00")
        assert row["cost_impact"] == 2500.0

    def test_cost_blank_none(self):
        assert self._row(CostImpact="")["cost_impact"] is None
        assert self._row(CostImpact=None)["cost_impact"] is None

    def test_scope_and_quality_blank_none(self):
        row = self._row(ScopeImpact="", QualityImpact="")
        assert row["scope_impact"] is None
        assert row["quality_impact"] is None

    def test_scope_preserved_when_set(self):
        row = self._row(ScopeImpact="Adds two cycles")
        assert row["scope_impact"] == "Adds two cycles"


# --- Controlled Document (2c-3) ----------------------------------------------

def _document(**over):
    """Minimal valid normalized controlled-document item (normalizer output:
    OwnerEmail already resolved from the picker or item-author fallback)."""
    base = {
        "item_id": "5",
        "DocTypeCode": "CHR",
        "Title": "APNE Project Charter",
        "Subtitle": "",
        "PrimaryDepartment": "Operations / PMO",
        "OwnerEmail": "sponsor@theragen.com",
        "ApproverEmail": "",
        "LifecyclePhase": "",
        "Status": "DRAFT",
        "ReviewCycle": "",
        "Classification": "",
        "StorageSystem": "",
        "StoragePath": "",
        "NextReviewDue": None,
        "IntakeID": "",
        "DocID": "",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


class TestNextDocId:
    def test_empty_starts_001(self):
        assert al.next_doc_id([], "OPS", "CHR") == "THG-OPS-CHR-001"

    def test_increments_within_family(self):
        assert al.next_doc_id(["THG-OPS-CHR-001", "THG-OPS-CHR-002"],
                              "OPS", "CHR") == "THG-OPS-CHR-003"

    def test_per_family_scoping(self):
        assert al.next_doc_id([], "IT", "SOP") == "THG-IT-SOP-001"

    def test_widens_past_999(self):
        assert al.next_doc_id(["THG-OPS-CHR-999"], "OPS", "CHR") == "THG-OPS-CHR-1000"

    def test_ignores_non_matching(self):
        assert al.next_doc_id(["garbage", "C-001", None, "THG-OPS-CHR-004"],
                              "OPS", "CHR") == "THG-OPS-CHR-005"


class TestValidateDocument:
    def test_happy_path(self):
        assert al.validate_document(_document()) == []

    def test_missing_doc_type(self):
        assert any("DocTypeCode" in e
                   for e in al.validate_document(_document(DocTypeCode="")))

    def test_missing_title(self):
        assert any("Title" in e for e in al.validate_document(_document(Title="")))

    def test_missing_department(self):
        assert any("PrimaryDepartment" in e
                   for e in al.validate_document(_document(PrimaryDepartment="")))

    def test_missing_owner(self):
        assert any("Owner" in e for e in al.validate_document(_document(OwnerEmail="")))

    def test_bad_doc_type(self):
        assert any("DocTypeCode not recognized" in e
                   for e in al.validate_document(_document(DocTypeCode="XXX")))

    def test_bad_department(self):
        assert any("PrimaryDepartment not recognized" in e
                   for e in al.validate_document(_document(PrimaryDepartment="Legal")))

    def test_bad_status(self):
        assert any("Status not recognized" in e
                   for e in al.validate_document(_document(Status="PUBLISHED")))

    def test_bad_lifecycle(self):
        assert any("LifecyclePhase not recognized" in e
                   for e in al.validate_document(_document(LifecyclePhase="Wrapping")))

    def test_bad_review_cycle(self):
        assert any("ReviewCycle not recognized" in e
                   for e in al.validate_document(_document(ReviewCycle="Hourly")))

    def test_blank_optional_domains_ok(self):
        assert al.validate_document(_document(
            LifecyclePhase="", ReviewCycle="", Classification="",
            StorageSystem="")) == []

    def test_all_doc_types_accepted(self):
        for c in al.DOC_TYPE_CODES:
            assert al.validate_document(_document(DocTypeCode=c)) == [], \
                f"type {c} should be valid"


class TestBuildDocumentRow:
    def _row(self, **over):
        it = _document(**over)
        return al.build_document_row(
            it, type_id="t", dept_id="d", owner_id="o", approver_id=None,
            lifecycle_phase="Initiating", review_cycle="On Major Revision",
            doc_id="THG-OPS-CHR-001")

    def test_identity_and_fks(self):
        r = self._row()
        assert r["doc_id"] == "THG-OPS-CHR-001"
        assert r["document_type_id"] == "t"
        assert r["primary_department_id"] == "d"
        assert r["owner_person_id"] == "o"
        assert r["approver_person_id"] is None

    def test_current_version_default(self):
        assert self._row()["current_version"] == "0.1"

    def test_status_default_draft(self):
        assert self._row(Status="")["status"] == "DRAFT"
        assert self._row(Status="BASELINE")["status"] == "BASELINE"

    def test_storage_path_default(self):
        r = self._row(StoragePath="", StorageSystem="")
        assert r["storage_path"] == "PMO SharePoint/THG-OPS-CHR-001"
        assert r["storage_system"] == "PMO SharePoint"

    def test_storage_path_preserved(self):
        assert self._row(StoragePath="https://x/y")["storage_path"] == "https://x/y"

    def test_classification_default(self):
        assert self._row()["classification"] == "Confidential – Internal"

    def test_lifecycle_and_cycle_from_args(self):
        r = self._row()
        assert r["lifecycle_phase"] == "Initiating"
        assert r["review_cycle"] == "On Major Revision"

    def test_subtitle_blank_none(self):
        assert self._row(Subtitle="")["subtitle"] is None

    def test_mutable_cols_exclude_identity_and_version(self):
        for c in ("doc_id", "document_type_id", "primary_department_id",
                  "current_version"):
            assert c not in al.MUTABLE_DOC_COLS


# --- Document RACI (2c-4) -----------------------------------------------------

def _raci(**over):
    """Minimal valid normalized Document RACI item (ValidFrom already
    createdDate-defaulted by the normalizer)."""
    base = {
        "item_id": "9",
        "ParentDocID": "THG-OPS-CHR-001",
        "Department": "Operations / PMO",
        "Role": "A",
        "Touchpoint": "Owns and approves the charter.",
        "ValidFrom": "2026-06-13",
        "ValidTo": None,
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


class TestValidateRaci:
    def test_happy_path(self):
        assert al.validate_raci(_raci()) == []

    def test_missing_parent_doc(self):
        assert any("ParentDocID" in e for e in al.validate_raci(_raci(ParentDocID="")))

    def test_missing_department(self):
        assert any("Department" in e for e in al.validate_raci(_raci(Department="")))

    def test_missing_role(self):
        assert any("Role" in e for e in al.validate_raci(_raci(Role="")))

    def test_bad_department(self):
        assert any("Department not recognized" in e
                   for e in al.validate_raci(_raci(Department="Legal")))

    def test_bad_role(self):
        assert any("Role not recognized" in e
                   for e in al.validate_raci(_raci(Role="X")))

    def test_all_roles_accepted(self):
        for r in al.RACI_ROLES:
            assert al.validate_raci(_raci(Role=r)) == [], f"role {r} should be valid"

    def test_valid_to_before_from_flagged(self):
        errs = al.validate_raci(_raci(ValidFrom="2026-06-13", ValidTo="2026-06-10"))
        assert any("ValidTo" in e for e in errs)

    def test_valid_to_equal_ok(self):
        assert al.validate_raci(_raci(ValidFrom="2026-06-13", ValidTo="2026-06-13")) == []

    def test_valid_to_after_ok(self):
        assert al.validate_raci(_raci(ValidFrom="2026-06-13", ValidTo="2026-12-31")) == []

    def test_blank_valid_to_ok(self):
        assert al.validate_raci(_raci(ValidTo=None)) == []
        assert al.validate_raci(_raci(ValidTo="")) == []


class TestBuildRaciRow:
    def _row(self, **over):
        return al.build_raci_row(_raci(**over), document_id="doc", department_id="dep")

    def test_columns_present(self):
        r = self._row()
        assert r["document_id"] == "doc"
        assert r["department_id"] == "dep"
        assert r["role"] == "A"
        assert r["valid_from"] == "2026-06-13"

    def test_touchpoint_blank_none(self):
        assert self._row(Touchpoint="")["touchpoint"] is None

    def test_touchpoint_preserved(self):
        assert self._row(Touchpoint="Reviews")["touchpoint"] == "Reviews"

    def test_valid_to_blank_none(self):
        assert self._row(ValidTo=None)["valid_to"] is None
        assert self._row(ValidTo="")["valid_to"] is None

    def test_valid_to_preserved(self):
        assert self._row(ValidTo="2026-12-31")["valid_to"] == "2026-12-31"


# --- Document Versions + e-sig attestations (2c-5) ---------------------------

def _version(**over):
    base = {
        "item_id": "10",
        "ParentDocID": "THG-OPS-CHR-001",
        "Version": "1.0",
        "Status": "DRAFT",
        "ChangeSummary": "Initial baseline of the charter.",
        "ChangeClass": "A - Minor",
        "EffectiveDate": None,
        "StoragePath": "",
        "AuthorEmail": "sponsor@theragen.com",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


def _approval(**over):
    base = {
        "item_id": "11",
        "ParentDocID": "THG-OPS-CHR-001",
        "ParentVersion": "1.0",
        "SignatureMeaning": "Approval",
        "Reason": "Charter approved by sponsor.",
        "ApproverEmail": "sponsor@theragen.com",
        "SyncStatus": "Pending",
    }
    base.update(over)
    return base


class TestEsigHash:
    _ARGS = ("THG-OPS-CHR-001", "1.0", "sponsor@theragen.com", "Approval",
             "2026-06-14T00:00:00+00:00")

    def test_known_vector(self):
        assert al.esig_hash(*self._ARGS) == \
            "4426e95dfd496fa16861c8a762cdcc628bcf4eb5826f2c0faf380d7a4a0c3d6d"

    def test_deterministic(self):
        assert al.esig_hash(*self._ARGS) == al.esig_hash(*self._ARGS)

    def test_64_hex_chars(self):
        h = al.esig_hash(*self._ARGS)
        assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)

    def test_sensitive_to_each_field(self):
        base = al.esig_hash(*self._ARGS)
        for i in range(5):
            args = list(self._ARGS)
            args[i] = "CHANGED"
            assert al.esig_hash(*args) != base, f"field {i} did not affect the hash"

    def test_production_canonical_form(self):
        # process_document_approval canonicalizes signed_at as "...Z" (UTC,
        # whole seconds). Lock that exact production form so the canonicalization
        # recipe can't drift undetected.
        assert al.esig_hash("THG-OPS-CHR-001", "1.0", "sponsor@theragen.com",
                            "Approval", "2026-06-14T00:00:00Z") == \
            "55181c0ade7d32c0297405c8fab0956f17aef6ebeed6dbc27c9184bf83b0020d"


class TestValidateVersion:
    def test_happy_path(self):
        assert al.validate_version(_version()) == []

    def test_missing_parent_doc(self):
        assert any("ParentDocID" in e for e in al.validate_version(_version(ParentDocID="")))

    def test_missing_version(self):
        assert any("Version" in e for e in al.validate_version(_version(Version="")))

    def test_missing_change_summary(self):
        assert any("ChangeSummary" in e
                   for e in al.validate_version(_version(ChangeSummary="")))

    def test_missing_author(self):
        assert any("Author" in e for e in al.validate_version(_version(AuthorEmail="")))

    def test_bad_status(self):
        assert any("Status not recognized" in e
                   for e in al.validate_version(_version(Status="PUBLISHED")))

    def test_bad_change_class(self):
        assert any("ChangeClass not recognized" in e
                   for e in al.validate_version(_version(ChangeClass="Z - Huge")))

    def test_blank_change_class_ok(self):
        assert al.validate_version(_version(ChangeClass="")) == []


class TestBuildVersionRow:
    def _row(self, **over):
        return al.build_version_row(_version(**over), document_id="doc", author_id="au")

    def test_columns_present(self):
        r = self._row()
        assert r["document_id"] == "doc"
        assert r["version"] == "1.0"
        assert r["change_summary"] == "Initial baseline of the charter."
        assert r["author_person_id"] == "au"

    def test_status_default_draft(self):
        assert self._row(Status="")["status"] == "DRAFT"

    def test_storage_path_default(self):
        assert self._row(StoragePath="")["storage_path"] == "THG-OPS-CHR-001/v1.0"

    def test_storage_path_preserved(self):
        assert self._row(StoragePath="x/y")["storage_path"] == "x/y"

    def test_linked_cr_id_none(self):
        assert self._row()["linked_cr_id"] is None

    def test_change_class_blank_none(self):
        assert self._row(ChangeClass="")["change_class"] is None

    def test_effective_date_none(self):
        assert self._row(EffectiveDate=None)["effective_date"] is None


class TestValidateApproval:
    def test_happy_path(self):
        assert al.validate_approval(_approval()) == []

    def test_missing_parent_doc(self):
        assert any("ParentDocID" in e for e in al.validate_approval(_approval(ParentDocID="")))

    def test_missing_parent_version(self):
        assert any("ParentVersion" in e
                   for e in al.validate_approval(_approval(ParentVersion="")))

    def test_missing_approver(self):
        assert any("Approver" in e for e in al.validate_approval(_approval(ApproverEmail="")))

    def test_bad_meaning(self):
        assert any("SignatureMeaning not recognized" in e
                   for e in al.validate_approval(_approval(SignatureMeaning="Witness")))

    def test_all_meanings_accepted(self):
        for mng in al.SIGNATURE_MEANINGS:
            assert al.validate_approval(_approval(SignatureMeaning=mng)) == []


class TestBuildApprovalRow:
    def _row(self, **over):
        return al.build_approval_row(_approval(**over), version_id="v",
                                     approver_id="p", signed_at="2026-06-14T00:00:00+00:00",
                                     esig="deadbeef")

    def test_columns_present(self):
        r = self._row()
        assert r["version_id"] == "v"
        assert r["approver_person_id"] == "p"
        assert r["signed_at"] == "2026-06-14T00:00:00+00:00"
        assert r["esig_hash"] == "deadbeef"

    def test_ip_address_none(self):
        assert self._row()["ip_address"] is None

    def test_meaning_default_approval(self):
        assert self._row(SignatureMeaning="")["signature_meaning"] == "Approval"

    def test_reason_blank_none(self):
        assert self._row(Reason="")["reason"] is None
