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
