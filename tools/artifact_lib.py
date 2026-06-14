# tools/artifact_lib.py
"""Pure logic for the execution-artifact sync (no I/O - unit-testable).

Companion to intake_lib.py: domain constants, code minting, validators and
row/fan-out builders for the three artifact Lists. Choice strings are the
de-facto contract shared by the Lists, the DB rows, and the report DAX
(e.g. Health Score SWITCHes on Green/Yellow/Red; Recent Accomplishment
filters Milestone Status = "Achieved").
"""
import datetime
import hashlib
import numbers
import re

RISK_CATEGORIES = ["Technical", "Schedule", "Cost", "Regulatory", "Vendor",
                   "People", "Safety", "Reputational"]
RESPONSE_TYPES = ["Mitigate", "Accept", "Avoid", "Transfer"]
RISK_STATUSES = ["Open", "Mitigating", "Monitoring", "Closed", "Realized"]
COMPLIANCE_FLAGS = ["None", "HIPAA", "GxP", "FDA 21 CFR Part 11"]
MILESTONE_STATUSES = ["On track", "At risk", "Achieved", "Slipped"]
RAG = ["Green", "Yellow", "Red"]
TRENDS = ["Improving", "Steady", "Worsening"]
# Exact strings and order of bi.knowledge_area (db/03_bi_views.sql).
KNOWLEDGE_AREAS = ["Scope", "Schedule", "Cost", "Quality", "Risk",
                   "Stakeholders", "Compliance", "Procurement", "Communications"]

_RISK_CODE = re.compile(r"^R-(\d{3,})$")


def next_risk_code(existing):
    """Next R-NNN within one project. Overflow widens rather than truncates."""
    nums = [int(m.group(1)) for s in existing
            if s and (m := _RISK_CODE.match(s))]
    return f"R-{(max(nums) + 1 if nums else 1):03d}"


def risk_score(likelihood, impact):
    """likelihood x impact, both 1-5. None when either is missing/invalid."""
    try:
        lk, im = int(likelihood), int(impact)
    except (TypeError, ValueError):
        return None
    if not (1 <= lk <= 5 and 1 <= im <= 5):
        return None
    return lk * im


def _blank(v):
    return not str(v or "").strip()


def validate_risk(it):
    errs = [f"Missing: {k}" for k in
            ("ProjectCode", "Category", "Description", "ResponseType")
            if _blank(it.get(k))]
    if _blank(it.get("RiskOwnerEmail")):
        errs.append("Missing: RiskOwner")
    if it.get("Likelihood") is None:
        errs.append("Missing: Likelihood")
    if it.get("Impact") is None:
        errs.append("Missing: Impact")
    if (it.get("Likelihood") is not None and it.get("Impact") is not None
            and risk_score(it["Likelihood"], it["Impact"]) is None):
        errs.append("Likelihood/Impact must be 1-5")
    if not _blank(it.get("Category")) and it["Category"] not in RISK_CATEGORIES:
        errs.append(f"Category not recognized: {it['Category']}")
    if not _blank(it.get("ResponseType")) and it["ResponseType"] not in RESPONSE_TYPES:
        errs.append(f"ResponseType not recognized: {it['ResponseType']}")
    if it.get("RiskStatus") and it["RiskStatus"] not in RISK_STATUSES:
        errs.append(f"RiskStatus not recognized: {it['RiskStatus']}")
    rs = it.get("ResidualScore")
    if rs is not None and not (1 <= int(rs) <= 25):
        errs.append("ResidualScore must be 1-25")
    return errs


def validate_milestone(it):
    errs = [f"Missing: {k}" for k in ("Title", "ProjectCode", "BaselineDate",
                                      "OwnerRole") if _blank(it.get(k))]
    if it.get("MilestoneStatus") not in MILESTONE_STATUSES:
        errs.append(f"MilestoneStatus not recognized: {it.get('MilestoneStatus')}")
    # The report's Recent Accomplishment DAX filters Achieved AND non-blank
    # Actual Date - an Achieved milestone without a date silently disappears.
    if it.get("MilestoneStatus") == "Achieved" and _blank(it.get("ActualDate")):
        errs.append("Achieved requires ActualDate (report hides it otherwise)")
    return errs


def validate_status_report(it):
    errs = [f"Missing: {k}" for k in ("ProjectCode", "PeriodStart", "PeriodEnd",
                                      "ExecutiveSummary") if _blank(it.get(k))]
    if (not _blank(it.get("PeriodStart")) and not _blank(it.get("PeriodEnd"))
            and it["PeriodEnd"] < it["PeriodStart"]):
        errs.append("PeriodEnd must be on/after PeriodStart")
    if it.get("OverallStatus") not in RAG:
        errs.append(f"OverallStatus not recognized: {it.get('OverallStatus')}")
    if it.get("Trend") not in TRENDS:
        errs.append(f"Trend not recognized: {it.get('Trend')}")
    for ka in KNOWLEDGE_AREAS:
        if it["Health"].get(ka) not in RAG:
            errs.append(f"{ka} health not recognized: {it['Health'].get(ka)}")
    if _blank(it.get("SubmittedByEmail")) and _blank(it.get("CreatedByEmail")):
        errs.append("Missing: SubmittedBy (picker empty and item author unknown)")
    return errs


def build_risk_row(it, project_id, department, owner_person_id, risk_code):
    return {
        "project_id": project_id,
        "risk_code": risk_code,
        "category": it["Category"],
        "description": it["Description"],
        "trigger": it["Trigger"],
        "likelihood": int(it["Likelihood"]),
        "impact": int(it["Impact"]),
        "score": risk_score(it["Likelihood"], it["Impact"]),
        "response_type": it["ResponseType"],
        "owner_person_id": owner_person_id,
        "department": department,
        "due_date": it["DueDate"],
        "status": it["RiskStatus"],
        "residual_score": int(it["ResidualScore"]) if it["ResidualScore"] is not None else None,
        "compliance_flag": it["ComplianceFlag"],
    }


def build_milestone_row(it, project_id):
    return {
        "project_id": project_id,
        "name": it["Title"][:200],
        "baseline_date": it["BaselineDate"],
        "forecast_date": it["ForecastDate"],
        "actual_date": it["ActualDate"],
        "status": it["MilestoneStatus"],
        "owner_role": it["OwnerRole"][:100],
    }


def build_report_row(it, project_id, submitted_by_person_id,
                     approved_by_person_id=None):
    return {
        "project_id": project_id,
        "period_start": it["PeriodStart"],
        "period_end": it["PeriodEnd"],
        "overall_status": it["OverallStatus"],
        "trend": it["Trend"],
        "executive_summary": it["ExecutiveSummary"],
        "decisions_needed": it["DecisionsNeeded"],
        "submitted_by_person_id": submitted_by_person_id,
        "approved_by_person_id": approved_by_person_id,
        "approved_at": it.get("ApprovedDate"),
    }


def build_area_rows(it):
    """One row per knowledge area, in bi.knowledge_area order."""
    return [{"knowledge_area": ka, "status": it["Health"][ka]}
            for ka in KNOWLEDGE_AREAS]


def _norm(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return v
    if isinstance(v, numbers.Number):
        return float(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()[:10]
    return str(v).strip()


def row_changed(current, desired):
    """True if any desired column differs from current, normalizing types
    (date vs ISO string, Decimal vs int, None vs '')."""
    return any(_norm(current.get(k)) != _norm(desired[k]) for k in desired)


# ---------------------------------------------------------------------------
# Activity / WBS constants and helpers
# ---------------------------------------------------------------------------

ACTIVITY_STATUSES = ["Not started", "In progress", "At risk", "Done", "Cancelled"]
# The 8 Theragen departments (exact strings; also doc_mgmt.department.name).
DEPARTMENTS = ["Clinical / Medical Affairs", "Regulatory / Quality",
               "R&D / Engineering", "Operations / PMO", "Finance / Procurement",
               "Commercial / Marketing", "IT / Data / Security", "HR / People"]

_ACTIVITY_CODE = re.compile(r"-A(\d+)$")


def working_days(start, finish):
    """Inclusive Mon-Fri count between two ISO date strings (yyyy-mm-dd).
    Returns 0 if either is blank or finish < start."""
    if _blank(start) or _blank(finish):
        return 0
    s = datetime.date.fromisoformat(str(start)[:10])
    f = datetime.date.fromisoformat(str(finish)[:10])
    if f < s:
        return 0
    days, d = 0, s
    while d <= f:
        if d.weekday() < 5:
            days += 1
        d += datetime.timedelta(days=1)
    return days


def next_wbs_code(existing_codes, parent_code=None):
    """Append-only WBS code. Level-1 (parent_code None): next unused integer.
    Level-2: '{parent}.{next unused child int}'. Never renumbers existing codes."""
    if parent_code is None:
        nums = [int(c) for c in existing_codes if c and c.isdigit()]
        return str(max(nums) + 1 if nums else 1)
    prefix = f"{parent_code}."
    nums = [int(c[len(prefix):]) for c in existing_codes
            if c and c.startswith(prefix) and c[len(prefix):].isdigit()]
    return f"{prefix}{max(nums) + 1 if nums else 1}"


def next_activity_code(existing_codes, wbs_code):
    """Next '{wbs_code}-A{n}' for one work package. Widens, never truncates."""
    nums = [int(m.group(1)) for c in existing_codes
            if c and (m := _ACTIVITY_CODE.search(c)) and c.startswith(f"{wbs_code}-A")]
    return f"{wbs_code}-A{max(nums) + 1 if nums else 1}"


def validate_activity(it):
    errs = [f"Missing: {k}" for k in
            ("ProjectCode", "Title", "Workstream", "WorkPackage",
             "StartPlanned", "FinishPlanned", "Department") if _blank(it.get(k))]
    if _blank(it.get("OwnerEmail")):
        errs.append("Missing: Owner")
    if it.get("ActivityStatus") not in ACTIVITY_STATUSES:
        errs.append(f"ActivityStatus not recognized: {it.get('ActivityStatus')}")
    if not _blank(it.get("Department")) and it["Department"] not in DEPARTMENTS:
        errs.append(f"Department not recognized: {it['Department']}")
    if (not _blank(it.get("StartPlanned")) and not _blank(it.get("FinishPlanned"))
            and it["FinishPlanned"] < it["StartPlanned"]):
        errs.append("FinishPlanned must be on/after StartPlanned")
    pct = it.get("PctComplete")
    if pct is not None and not (0 <= float(pct) <= 100):
        errs.append("PctComplete must be 0-100")
    # Recent Accomplishment DAX filters Done AND non-blank Actual Finish.
    if it.get("ActivityStatus") == "Done" and _blank(it.get("FinishActual")):
        errs.append("Done requires FinishActual (report hides it otherwise)")
    return errs


def build_wbs_row(project_id, wbs_code, parent_id, level, name, owning_department, owner_role):
    return {"project_id": project_id, "wbs_code": wbs_code,
            "parent_wbs_element_id": parent_id, "level": level, "name": name[:200],
            "owning_department": owning_department, "owner_role": owner_role}


def build_activity_row(it, wbs_element_id, owner_person_id, activity_code):
    return {
        "wbs_element_id": wbs_element_id,
        "activity_code": activity_code,
        "name": it["Title"][:200],
        "start_planned": it["StartPlanned"],
        "finish_planned": it["FinishPlanned"],
        "start_actual": it["StartActual"],
        "finish_actual": it["FinishActual"],
        "duration_days": working_days(it["StartPlanned"], it["FinishPlanned"]),
        "owner_person_id": owner_person_id,
        "department": it["Department"],
        "status": it["ActivityStatus"],
        "pct_complete": float(it["PctComplete"]) if it["PctComplete"] is not None else 0,
    }


# ---------------------------------------------------------------------------
# Change Request / Decision constants, minting, validators, and builders
# ---------------------------------------------------------------------------

CR_CLASSES = ["A - Minor", "B - Substantive", "C - Controlling", "Emergency / Safety"]
CHANGE_TYPES = ["Scope", "Schedule", "Cost", "Quality", "Compliance"]
CR_DECISIONS = ["Pending", "Approved", "Deferred", "Rejected"]
CR_STATUSES = ["Open", "In Assessment", "Implementing", "Verified", "Closed", "Rejected"]

_CR_CODE = re.compile(r"^C-(\d{3,})$")
_DECISION_CODE = re.compile(r"^D-(\d{3,})$")


def next_cr_code(existing):
    """Next C-NNN within one project. Overflow widens rather than truncates."""
    nums = [int(m.group(1)) for s in existing if s and (m := _CR_CODE.match(s))]
    return f"C-{(max(nums) + 1 if nums else 1):03d}"


def next_decision_code(existing):
    """Next D-NNN within one project. Overflow widens rather than truncates."""
    nums = [int(m.group(1)) for s in existing if s and (m := _DECISION_CODE.match(s))]
    return f"D-{(max(nums) + 1 if nums else 1):03d}"


def validate_change_request(it):
    """Return a list of error strings; empty list means valid."""
    errs = [f"Missing: {k}" for k in
            ("ProjectCode", "Description", "Reason", "CRClass", "ChangeType")
            if _blank(it.get(k))]
    if _blank(it.get("RequestedByEmail")):
        errs.append("Missing: RequestedBy (picker empty and item author unknown)")
    if it.get("CRClass") and it["CRClass"] not in CR_CLASSES:
        errs.append(f"CRClass not recognized: {it['CRClass']}")
    if it.get("ChangeType") and it["ChangeType"] not in CHANGE_TYPES:
        errs.append(f"ChangeType not recognized: {it['ChangeType']}")
    dec, st = it.get("Decision") or "Pending", it.get("CRStatus") or "Open"
    if dec not in CR_DECISIONS:
        errs.append(f"Decision not recognized: {dec}")
    if st not in CR_STATUSES:
        errs.append(f"CRStatus not recognized: {st}")
    if dec != "Pending":
        if _blank(it.get("DecidedByEmail")):
            errs.append("Decision set but DecidedBy is empty")
        if _blank(it.get("DecidedDate")):
            errs.append("Decision set but DecidedDate is empty")
    elif not _blank(it.get("DecidedDate")):
        errs.append("DecidedDate must be blank while Decision is Pending")
    if dec == "Rejected" and st != "Rejected":
        errs.append("Rejected decision requires CRStatus = Rejected")
    if st in ("Verified", "Closed") and dec != "Approved":
        errs.append(f"CRStatus {st} requires Decision = Approved")
    if (not _blank(it.get("DecidedDate")) and not _blank(it.get("RequestedDate"))
            and it["DecidedDate"] < it["RequestedDate"]):
        errs.append("DecidedDate must be on/after RequestedDate")
    return errs


def validate_decision(it):
    """Return a list of error strings; empty list means valid."""
    errs = [f"Missing: {k}" for k in
            ("Title", "ProjectCode", "Rationale", "DecidedDate")
            if _blank(it.get(k))]
    if _blank(it.get("DecidedByEmail")):
        errs.append("Missing: DecidedBy")
    return errs


def build_cr_row(it, project_id, requester_id, decider_id, cr_code):
    """Build the change_request DB column dict.

    implementation_verified and linked_artifacts_updated are received as
    already-coerced Python bools (the normalizer in T4 does Yes/No→bool).
    build_cr_row is pure and passes them through unchanged.
    """
    raw_days = it.get("ImpactScheduleDays")
    raw_cost = it.get("ImpactCost")
    return {
        "project_id": project_id,
        "cr_code": cr_code,
        "intake_id": it.get("IntakeID"),
        "requested_at": it["RequestedDate"],
        "requested_by_person_id": requester_id,
        "cr_class": it["CRClass"],
        "change_types": it["ChangeType"],
        "affected_artifacts": it.get("AffectedArtifacts") or "n/a",
        "description": it["Description"],
        "reason": it["Reason"],
        "impact_scope": it.get("ImpactScope"),
        "impact_schedule_days": int(raw_days) if raw_days not in (None, "") else 0,
        "impact_cost": float(raw_cost) if raw_cost not in (None, "") else 0.0,
        "impact_quality": it.get("ImpactQuality"),
        "decision": it.get("Decision") or "Pending",
        "decided_by_person_id": decider_id,
        "decided_at": it.get("DecidedDate"),
        "implementation_verified": it.get("ImplementationVerified"),
        "linked_artifacts_updated": it.get("LinkedArtifactsUpdated"),
        "status": it.get("CRStatus") or "Open",
    }


def build_decision_row(it, project_id, decider_id, code):
    """Build the decision DB column dict."""
    return {
        "project_id": project_id,
        "code": code,
        "decision": it["Title"],
        "rationale": it["Rationale"],
        "decided_by_person_id": decider_id,
        "decided_at": it["DecidedDate"],
    }


def _trail_states(current, desired, keys):
    """Return (before, after) dicts restricted to the given keys.

    before reads from current (None for missing keys); after reads from desired.
    Pure utility for audit before/after snapshots.
    """
    before = {k: current.get(k) for k in keys}
    after = {k: desired[k] for k in keys}
    return before, after


# ---------------------------------------------------------------------------
# Change Impact Assessment (2c-2) - per-department impact statement on a CR
# ---------------------------------------------------------------------------

def validate_impact_assessment(it):
    """Return a list of error strings; empty list means valid.

    The parent CR (ParentCRCode) and submitter (SubmittedByEmail) are resolved
    in the sync; here we only require the human inputs be present/coherent.
    schedule_impact_days / cost_impact are nullable - blank is fine, but a
    non-coercible value gets a clean error instead of a raw int()/float() crash.
    """
    errs = [f"Missing: {k}" for k in ("ProjectCode", "ParentCRCode", "Department")
            if _blank(it.get(k))]
    if _blank(it.get("SubmittedByEmail")):
        errs.append("Missing: SubmittedBy (picker empty and item author unknown)")
    if it.get("Department") and it["Department"] not in DEPARTMENTS:
        errs.append(f"Department not recognized: {it['Department']}")
    raw_days = it.get("ScheduleImpactDays")
    if raw_days not in (None, ""):
        try:
            int(raw_days)
        except (TypeError, ValueError):
            errs.append(f"ScheduleImpactDays must be a whole number: {raw_days}")
    raw_cost = it.get("CostImpact")
    if raw_cost not in (None, ""):
        try:
            float(raw_cost)
        except (TypeError, ValueError):
            errs.append(f"CostImpact must be numeric: {raw_cost}")
    return errs


def build_impact_assessment_row(it, cr_id, submitted_by_person_id, submitted_at):
    """Build the change_impact_assessment DB column dict.

    cr_id (parent CR), submitted_by_person_id and submitted_at are already
    resolved by the caller (parent lookup, person directory, createdDate
    fallback). Unlike build_cr_row, schedule_impact_days / cost_impact are
    NULLABLE: blank -> None (the column has no default).
    """
    raw_days = it.get("ScheduleImpactDays")
    raw_cost = it.get("CostImpact")
    return {
        "cr_id": cr_id,
        "department": it["Department"],
        "scope_impact": it.get("ScopeImpact") or None,
        "schedule_impact_days": int(raw_days) if raw_days not in (None, "") else None,
        "cost_impact": float(raw_cost) if raw_cost not in (None, "") else None,
        "quality_impact": it.get("QualityImpact") or None,
        "submitted_by_person_id": submitted_by_person_id,
        "submitted_at": submitted_at,
    }


# ---------------------------------------------------------------------------
# Baseline + Phase-Gate constants, minting, validators, snapshot assemblers
# ---------------------------------------------------------------------------

BASELINE_TYPES = ["Schedule", "Scope", "Budget"]
LIFECYCLE_PHASES = ["Initiating", "Planning", "Executing",
                    "Monitoring", "Closing"]
PHASE_ORDER = {p: i for i, p in enumerate(LIFECYCLE_PHASES)}
GATE_DECISIONS = ["Approved", "Approved with conditions", "Held"]
_BASELINE_VER = re.compile(r"^(\d+)\.0$")


def next_baseline_version(existing):
    """Next N.0 version string. [] -> '1.0'; non-matching entries ignored."""
    nums = [int(m.group(1)) for s in existing if s and (m := _BASELINE_VER.match(s))]
    return f"{(max(nums) + 1 if nums else 1)}.0"


def validate_baseline(it):
    """Return list of error strings; empty means valid."""
    errs = [f"Missing: {k}" for k in ("ProjectCode", "BaselineType")
            if _blank(it.get(k))]
    if _blank(it.get("BaselinedByEmail")):
        errs.append("Missing: BaselinedBy")
    if it.get("BaselineType") and it["BaselineType"] not in BASELINE_TYPES:
        errs.append(f"BaselineType not recognized: {it['BaselineType']}")
    return errs


def validate_phase_gate(it):
    """Return list of error strings; empty means valid."""
    errs = [f"Missing: {k}" for k in ("ProjectCode", "TargetPhase", "GateDecision")
            if _blank(it.get(k))]
    if _blank(it.get("ApprovedByEmail")):
        errs.append("Missing: ApprovedBy")
    if it.get("TargetPhase") and it["TargetPhase"] not in LIFECYCLE_PHASES:
        errs.append(f"TargetPhase not recognized: {it['TargetPhase']}")
    if it.get("GateDecision") and it["GateDecision"] not in GATE_DECISIONS:
        errs.append(f"GateDecision not recognized: {it['GateDecision']}")
    return errs


def _d(v):
    """Coerce a psycopg date/Decimal/str/None to 'YYYY-MM-DD' string or None."""
    if v is None:
        return None
    return v.isoformat()[:10] if hasattr(v, "isoformat") else str(v)[:10]


def assemble_schedule_snapshot(activities, milestones, headline):
    """Build deterministic schedule snapshot dict from raw DB rows.

    activities/milestones are lists of plain dicts (already SELECTed).
    Dates may be datetime.date objects or ISO strings; Decimal durations are
    coerced to int.  Output is fully sorted so json.dumps is byte-stable.
    """
    acts = sorted(
        ({"code": a["activity_code"],
          "name": a["name"],
          "start_planned": _d(a["start_planned"]),
          "finish_planned": _d(a["finish_planned"]),
          "duration_days": int(a["duration_days"])} for a in activities),
        key=lambda x: (x["code"], x["name"]))
    mils = sorted(
        ({"name": m["name"], "baseline_date": _d(m["baseline_date"])}
         for m in milestones),
        key=lambda x: (x["baseline_date"] or "", x["name"]))
    return {"type": "Schedule", "activities": acts, "milestones": mils,
            "headline": {"planned_start": _d(headline.get("planned_start")),
                         "planned_finish": _d(headline.get("planned_finish"))}}


def assemble_budget_snapshot(budget_total, lines):
    """Build deterministic budget snapshot dict from raw DB rows.

    Decimal totals are coerced to float; lines sorted by (wbs_code, category).
    """
    ls = sorted(
        ({"wbs_code": l["wbs_code"], "category": l["category"],
          "total": float(l["total"]),
          "funding_source": l["funding_source"]} for l in lines),
        key=lambda x: (x["wbs_code"], x["category"], x["funding_source"], x["total"]))
    return {"type": "Budget",
            "budget_total": float(budget_total) if budget_total is not None else None,
            "lines": ls}


def assemble_scope_snapshot(charter, inclusions, exclusions, acceptance):
    """Build deterministic scope snapshot dict.

    charter is a dict or None; inclusions/exclusions/acceptance are lists of
    dicts with 'item'/'criterion' and optional 'sequence' (defaults to 0).
    """
    c = charter or {}
    return {"type": "Scope",
            "charter": {"business_case": c.get("business_case"),
                        "high_level_in_scope": c.get("high_level_in_scope"),
                        "high_level_out_scope": c.get("high_level_out_scope")},
            "inclusions": [r["item"] for r in sorted(inclusions,
                           key=lambda r: (r.get("sequence", 0), r["item"]))],
            "exclusions": [r["item"] for r in sorted(exclusions,
                           key=lambda r: (r.get("sequence", 0), r["item"]))],
            "acceptance": [r["criterion"] for r in sorted(acceptance,
                           key=lambda r: (r.get("sequence", 0), r["criterion"]))]}


def build_phase_gate_row(it, project_id, from_phase, to_phase, approver_id):
    """Build the phase_gate_log DB column dict from a normalized List item."""
    return {"project_id": project_id,
            "from_phase": from_phase,
            "to_phase": to_phase,
            "gate_decision": it["GateDecision"],
            "approved_by_person_id": approver_id,
            "decided_at": it.get("DecidedDate"),
            "gate_notes": it.get("GateNotes")}


# ---------------------------------------------------------------------------
# Controlled Document (2c-3) - org-wide controlled-document register
# ---------------------------------------------------------------------------

DOC_TYPE_CODES = ["CHR", "SOP", "PLN", "SCP", "RPT", "POL", "WI", "FRM"]
DOC_STATUSES = ["DRAFT", "REVIEW", "BASELINE", "AMENDED", "RETIRED"]
DOC_LIFECYCLE_PHASES = ["Initiating", "Planning", "Executing", "Monitoring",
                        "Closing", "Cross-Lifecycle", "Intake", "Governance",
                        "Reference"]
REVIEW_CYCLES = ["Annual", "Semi-Annual", "Quarterly", "Monthly",
                 "On Major Revision", "On Phase Gate"]
DOC_CLASSIFICATIONS = ["Public", "Confidential – Internal",
                       "Confidential – Restricted", "PHI – HIPAA"]
STORAGE_SYSTEMS = ["PMO SharePoint", "eQMS", "eTMF", "HIPAA-controlled store",
                   "ERP", "HRIS", "Other"]
# Columns process_document re-applies on edit (row_changed + UPDATE). Excludes
# the immutable identity (doc_id / document_type_id / primary_department_id) and
# current_version (the document's own version pointer, left at its initial
# value - this authoring surface does not maintain it).
MUTABLE_DOC_COLS = ["title", "subtitle", "lifecycle_phase", "status",
                    "owner_person_id", "approver_person_id", "review_cycle",
                    "next_review_due", "intake_id", "classification",
                    "storage_system", "storage_path"]

_DOC_ID = re.compile(r"^THG-[A-Z]+-[A-Z]+-(\d{3,})$")


def next_doc_id(existing, dept_code, type_code):
    """Next THG-{dept}-{type}-NNN within one (department, type) family.

    Overflow widens rather than truncates. `existing` is the doc_ids already
    minted for that family (the caller scopes the SELECT by dept + type).
    """
    nums = [int(m.group(1)) for s in existing if s and (m := _DOC_ID.match(s))]
    n = max(nums) + 1 if nums else 1
    return f"THG-{dept_code}-{type_code}-{n:03d}"


def validate_document(it):
    """Return a list of error strings; empty list means valid.

    DocTypeCode / PrimaryDepartment / Owner are resolved to ids in the sync;
    here we require the human inputs present + in domain. LifecyclePhase /
    ReviewCycle are derived from the type when blank, so they are optional.
    """
    errs = [f"Missing: {k}" for k in ("DocTypeCode", "Title", "PrimaryDepartment")
            if _blank(it.get(k))]
    if _blank(it.get("OwnerEmail")):
        errs.append("Missing: Owner (picker empty and item author unknown)")
    if it.get("DocTypeCode") and it["DocTypeCode"] not in DOC_TYPE_CODES:
        errs.append(f"DocTypeCode not recognized: {it['DocTypeCode']}")
    if it.get("PrimaryDepartment") and it["PrimaryDepartment"] not in DEPARTMENTS:
        errs.append(f"PrimaryDepartment not recognized: {it['PrimaryDepartment']}")
    for field, domain, label in (
            ("Status", DOC_STATUSES, "Status"),
            ("LifecyclePhase", DOC_LIFECYCLE_PHASES, "LifecyclePhase"),
            ("ReviewCycle", REVIEW_CYCLES, "ReviewCycle"),
            ("Classification", DOC_CLASSIFICATIONS, "Classification"),
            ("StorageSystem", STORAGE_SYSTEMS, "StorageSystem")):
        if it.get(field) and it[field] not in domain:
            errs.append(f"{label} not recognized: {it[field]}")
    return errs


def build_document_row(it, type_id, dept_id, owner_id, approver_id,
                       lifecycle_phase, review_cycle, doc_id):
    """Build the full doc_mgmt.document column dict (used for INSERT).

    type_id / dept_id / owner_id / approver_id are resolved by the caller;
    lifecycle_phase / review_cycle are the type-derived (or List-overridden)
    values; doc_id is the minted code. current_version is "0.1" at creation
    (versioning is owned by 2c-5). storage_path defaults to
    "{storage_system}/{doc_id}" when blank (the column is NOT NULL).
    """
    storage_system = it.get("StorageSystem") or "PMO SharePoint"
    return {
        "doc_id": doc_id,
        "document_type_id": type_id,
        "primary_department_id": dept_id,
        "title": it["Title"],
        "subtitle": it.get("Subtitle") or None,
        "lifecycle_phase": lifecycle_phase,
        "status": it.get("Status") or "DRAFT",
        "current_version": "0.1",
        "owner_person_id": owner_id,
        "approver_person_id": approver_id,
        "review_cycle": review_cycle,
        "next_review_due": it.get("NextReviewDue") or None,
        "intake_id": it.get("IntakeID") or None,
        "classification": it.get("Classification") or "Confidential – Internal",
        "storage_system": storage_system,
        "storage_path": it.get("StoragePath") or f"{storage_system}/{doc_id}",
    }


# ---------------------------------------------------------------------------
# Document RACI (2c-4) - per-document, per-department R/A/C/I assignment
# ---------------------------------------------------------------------------

RACI_ROLES = ["R", "A", "C", "I"]


def validate_raci(it):
    """Return a list of error strings; empty list means valid.

    ParentDocID resolves to a document and Department to a department_id in the
    sync; here we require the human inputs present + in domain. ValidFrom is
    defaulted to the item created date in the normalizer, so it is not required.
    """
    errs = [f"Missing: {k}" for k in ("ParentDocID", "Department", "Role")
            if _blank(it.get(k))]
    if it.get("Department") and it["Department"] not in DEPARTMENTS:
        errs.append(f"Department not recognized: {it['Department']}")
    if it.get("Role") and it["Role"] not in RACI_ROLES:
        errs.append(f"Role not recognized: {it['Role']} (use R/A/C/I)")
    vf, vt = it.get("ValidFrom"), it.get("ValidTo")
    if not _blank(vf) and not _blank(vt) and vt < vf:
        errs.append("ValidTo must be on/after ValidFrom")
    return errs


def build_raci_row(it, document_id, department_id):
    """Build the raci_assignment DB column dict.

    document_id / department_id are resolved by the caller. touchpoint and
    valid_to are nullable (blank -> None); valid_from is the normalizer's
    createdDate-defaulted value.
    """
    return {
        "document_id": document_id,
        "department_id": department_id,
        "role": it["Role"],
        "touchpoint": it.get("Touchpoint") or None,
        "valid_from": it["ValidFrom"],
        "valid_to": it.get("ValidTo") or None,
    }


# ---------------------------------------------------------------------------
# Document Versions + e-signature Attestations (2c-5)
# ---------------------------------------------------------------------------

# Document-approval signature meanings (the doc-approval subset of the enum).
SIGNATURE_MEANINGS = ["Approval", "Review", "Authorship"]


def esig_hash(doc_id, version, approver_email, meaning, signed_at):
    """Server-computed ATTESTATION hash - NOT a 21 CFR Part 11 signature.

    Deterministic SHA-256 hex over a canonical pipe-joined string. The same five
    inputs always yield the same 64-char hex, so a stored attestation is
    verifiable by recomputing it from its row. This is a traceability hash, not a
    signer-controlled cryptographic signature; true Part 11 signing is deferred.
    """
    payload = "|".join([str(doc_id), str(version), str(approver_email),
                        str(meaning), str(signed_at)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_version(it):
    """Return a list of error strings; empty list means valid.

    ParentDocID resolves to a document and Author to a person in the sync; here
    we require the human inputs present + in domain.
    """
    errs = [f"Missing: {k}" for k in ("ParentDocID", "Version", "ChangeSummary")
            if _blank(it.get(k))]
    if _blank(it.get("AuthorEmail")):
        errs.append("Missing: Author (picker empty and item author unknown)")
    if it.get("Status") and it["Status"] not in DOC_STATUSES:
        errs.append(f"Status not recognized: {it['Status']}")
    if it.get("ChangeClass") and it["ChangeClass"] not in CR_CLASSES:
        errs.append(f"ChangeClass not recognized: {it['ChangeClass']}")
    return errs


def build_version_row(it, document_id, author_id, linked_cr_id=None):
    """Build the document_version DB column dict. linked_cr_id is resolved from
    the optional LinkedCRCode (a governance CR, 2c-6) in the sync - None when the
    version cites no CR; storage_path defaults to {DocID}/v{Version}."""
    return {
        "document_id": document_id,
        "version": it["Version"],
        "status": it.get("Status") or "DRAFT",
        "change_summary": it["ChangeSummary"],
        "change_class": it.get("ChangeClass") or None,
        "linked_cr_id": linked_cr_id,
        "author_person_id": author_id,
        "effective_date": it.get("EffectiveDate") or None,
        "storage_path": it.get("StoragePath") or f"{it['ParentDocID']}/v{it['Version']}",
    }


def validate_approval(it):
    """Return a list of error strings; empty list means valid.

    ParentDocID + ParentVersion resolve to a version_id, and Approver to a
    person, in the sync. signed_at + esig_hash are server-derived (never typed).
    """
    errs = [f"Missing: {k}" for k in ("ParentDocID", "ParentVersion")
            if _blank(it.get(k))]
    if _blank(it.get("ApproverEmail")):
        errs.append("Missing: Approver (picker empty and item author unknown)")
    if it.get("SignatureMeaning") and it["SignatureMeaning"] not in SIGNATURE_MEANINGS:
        errs.append(f"SignatureMeaning not recognized: {it['SignatureMeaning']}")
    return errs


def build_approval_row(it, version_id, approver_id, signed_at, esig):
    """Build the document_approval DB column dict. ip_address is None (no signer
    IP is captured - part of the honest non-Part-11 scoping)."""
    return {
        "version_id": version_id,
        "approver_person_id": approver_id,
        "signature_meaning": it.get("SignatureMeaning") or "Approval",
        "signed_at": signed_at,
        "esig_hash": esig,
        "ip_address": None,
        "reason": it.get("Reason") or None,
    }


# ---------------------------------------------------------------------------
# Governance Change Requests (2c-6) - document-scoped CRs + per-dept assessments
# ---------------------------------------------------------------------------
# Governance CRs reuse the 2b two-axis enums verbatim (CR_CLASSES / CR_DECISIONS
# / CR_STATUSES) - the doc_mgmt enums are byte-identical to the pmbok ones. The
# only differences from a project CR: the gov CR is keyed to a DOCUMENT (not a
# project), has no change_type column, and mints a GLOBAL CHG-NNN code.

_GOVCR_CODE = re.compile(r"^CHG-(\d{3,})$")


def next_govcr_code(existing):
    """Next CHG-NNN GLOBALLY (cr_code is UNIQUE across all governance CRs, not
    scoped per project/document). Overflow widens rather than truncates."""
    nums = [int(m.group(1)) for s in existing if s and (m := _GOVCR_CODE.match(s))]
    return f"CHG-{(max(nums) + 1 if nums else 1):03d}"


def validate_govcr(it):
    """Return a list of error strings; empty list means valid.

    The 2b two-axis coherence rules carried over verbatim, minus ProjectCode
    (gov CRs are project-less) and ChangeType (no change_type column). The target
    document (ParentDocID) and the requester/decider persons are resolved in the
    sync; here we only require the human inputs be present + coherent.
    """
    errs = [f"Missing: {k}" for k in
            ("ParentDocID", "Description", "Reason", "CRClass")
            if _blank(it.get(k))]
    if _blank(it.get("RequestedByEmail")):
        errs.append("Missing: RequestedBy (picker empty and item author unknown)")
    if it.get("CRClass") and it["CRClass"] not in CR_CLASSES:
        errs.append(f"CRClass not recognized: {it['CRClass']}")
    dec, st = it.get("Decision") or "Pending", it.get("CRStatus") or "Open"
    if dec not in CR_DECISIONS:
        errs.append(f"Decision not recognized: {dec}")
    if st not in CR_STATUSES:
        errs.append(f"CRStatus not recognized: {st}")
    if dec != "Pending":
        if _blank(it.get("DecidedByEmail")):
            errs.append("Decision set but DecidedBy is empty")
        if _blank(it.get("DecidedDate")):
            errs.append("Decision set but DecidedDate is empty")
    elif not _blank(it.get("DecidedDate")):
        errs.append("DecidedDate must be blank while Decision is Pending")
    if dec == "Rejected" and st != "Rejected":
        errs.append("Rejected decision requires CRStatus = Rejected")
    if st in ("Verified", "Closed") and dec != "Approved":
        errs.append(f"CRStatus {st} requires Decision = Approved")
    if (not _blank(it.get("DecidedDate")) and not _blank(it.get("RequestedDate"))
            and it["DecidedDate"] < it["RequestedDate"]):
        errs.append("DecidedDate must be on/after RequestedDate")
    return errs


def build_govcr_row(it, document_id, requester_id, decider_id, cr_code):
    """Build the change_request_gov DB column dict.

    implementation_verified arrives as an already-coerced Python bool (the
    normalizer does Yes/No->bool); build_govcr_row passes it through unchanged.
    """
    return {
        "cr_code": cr_code,
        "document_id": document_id,
        "intake_id": it.get("IntakeID") or None,
        "requested_at": it["RequestedDate"],
        "requested_by_person_id": requester_id,
        "cr_class": it["CRClass"],
        "description": it["Description"],
        "reason": it["Reason"],
        "decision": it.get("Decision") or "Pending",
        "decided_by_person_id": decider_id,
        "decided_at": it.get("DecidedDate") or None,
        "implementation_verified": it.get("ImplementationVerified") or False,
        "status": it.get("CRStatus") or "Open",
    }


def validate_govassessment(it):
    """Return a list of error strings; empty list means valid.

    The parent gov CR (ParentCRCode) and assessing department are resolved in the
    sync; here we only require the human inputs be present + in domain. The
    assessment is department-scoped (no person column); compliance_impact is
    optional free text.
    """
    errs = [f"Missing: {k}" for k in ("ParentCRCode", "Department", "ImpactSummary")
            if _blank(it.get(k))]
    if it.get("Department") and it["Department"] not in DEPARTMENTS:
        errs.append(f"Department not recognized: {it['Department']}")
    return errs


def build_govassessment_row(it, cr_gov_id, department_id, submitted_at):
    """Build the change_assessment_gov DB column dict (blank compliance -> None)."""
    return {
        "cr_gov_id": cr_gov_id,
        "department_id": department_id,
        "impact_summary": it["ImpactSummary"],
        "compliance_impact": it.get("ComplianceImpact") or None,
        "submitted_at": submitted_at,
    }
