# tools/artifact_lib.py
"""Pure logic for the execution-artifact sync (no I/O - unit-testable).

Companion to intake_lib.py: domain constants, code minting, validators and
row/fan-out builders for the three artifact Lists. Choice strings are the
de-facto contract shared by the Lists, the DB rows, and the report DAX
(e.g. Health Score SWITCHes on Green/Yellow/Red; Recent Accomplishment
filters Milestone Status = "Achieved").
"""
import datetime
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


def build_report_row(it, project_id, submitted_by_person_id):
    return {
        "project_id": project_id,
        "period_start": it["PeriodStart"],
        "period_end": it["PeriodEnd"],
        "overall_status": it["OverallStatus"],
        "trend": it["Trend"],
        "executive_summary": it["ExecutiveSummary"],
        "decisions_needed": it["DecisionsNeeded"],
        "submitted_by_person_id": submitted_by_person_id,
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
