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
