# tools/sync_artifacts.py
"""Daily M365 -> PostgreSQL execution-artifact sync
(spec: 2026-06-12-execution-tracking).

Reads the Project Risks / Project Milestones / Project Status Reports Lists,
inserts new artifacts (status reports fan out to 9 knowledge-area rows),
re-applies PM edits via full-row compare, heals lost write-backs, and surfaces
errors on each List row. Idempotent via <table>.external_ref = List item id.
PostgreSQL is the system of record; the Lists are the authoring surface and
win on conflict. --dry-run prints intent only.
"""
import argparse
import json
import os
import sys
import uuid

import psycopg
from psycopg.types.json import Jsonb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_lib as al
import audit_lib
from graph_client import Graph, SitePeople, coerce_bool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PG = json.load(open(os.path.join(ROOT, "db", ".pg.local.json")))
M365 = json.load(open(os.path.join(ROOT, "db", ".m365.local.json")))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

HEALTH_FIELDS = ",".join(f"{ka}Health" for ka in al.KNOWLEDGE_AREAS)
RISK_FIELDS = ("Title,ProjectCode,Category,Description,Trigger,Likelihood,"
               "Impact,ResponseType,RiskOwner,RiskOwnerLookupId,DueDate,"
               "RiskStatus,ResidualScore,ComplianceFlag,RiskCode,"
               "SyncStatus,SyncMessage")
ACTIVITY_FIELDS = ("Title,ProjectCode,Workstream,WorkPackage,StartPlanned,"
                   "FinishPlanned,StartActual,FinishActual,Owner,OwnerLookupId,"
                   "Department,ActivityStatus,PctComplete,ActivityCode,"
                   "SyncStatus,SyncMessage")
MILESTONE_FIELDS = ("Title,ProjectCode,BaselineDate,ForecastDate,ActualDate,"
                    "MilestoneStatus,OwnerRole,SyncStatus,SyncMessage")
REPORT_FIELDS = ("Title,ProjectCode,PeriodStart,PeriodEnd,OverallStatus,Trend,"
                 "ExecutiveSummary,DecisionsNeeded,SubmittedBy,"
                 "SubmittedByLookupId,ApprovedBy,ApprovedByLookupId,ApprovedDate,"
                 + HEALTH_FIELDS + ",SyncStatus,SyncMessage")
CR_FIELDS = ("Title,ProjectCode,RequestedDate,RequestedBy,RequestedByLookupId,"
             "CRClass,ChangeType,AffectedArtifacts,Description,Reason,"
             "ImpactScope,ImpactQuality,ImpactScheduleDays,ImpactCost,"
             "IntakeID,Decision,DecidedBy,DecidedByLookupId,DecidedDate,"
             "ImplementationVerified,LinkedArtifactsUpdated,CRStatus,CRCode,"
             "SyncStatus,SyncMessage")
DECISION_FIELDS = ("Title,ProjectCode,Rationale,DecidedBy,DecidedByLookupId,"
                   "DecidedDate,DecisionCode,SyncStatus,SyncMessage")
BASELINE_FIELDS = ("Title,ProjectCode,BaselineType,ChangeSummary,LinkedCRCode,"
                   "BaselinedBy,BaselinedByLookupId,BaselineVersion,"
                   "SyncStatus,SyncMessage")
PHASE_GATE_FIELDS = ("Title,ProjectCode,TargetPhase,GateDecision,"
                     "ApprovedBy,ApprovedByLookupId,DecidedDate,"
                     "GateNotes,SyncStatus,SyncMessage")
IMPACT_FIELDS = ("Title,ProjectCode,ParentCRCode,Department,ScopeImpact,"
                 "ScheduleImpactDays,CostImpact,QualityImpact,"
                 "SubmittedBy,SubmittedByLookupId,SubmittedDate,"
                 "SyncStatus,SyncMessage")
DOC_FIELDS = ("Title,DocTypeCode,Subtitle,PrimaryDepartment,Owner,OwnerLookupId,"
              "Approver,ApproverLookupId,LifecyclePhase,Status,ReviewCycle,"
              "Classification,StorageSystem,StoragePath,NextReviewDue,IntakeID,"
              "DocID,SyncStatus,SyncMessage")
RACI_FIELDS = ("Title,ParentDocID,Department,Role,Touchpoint,ValidFrom,ValidTo,"
               "SyncStatus,SyncMessage")
VERSION_FIELDS = ("Title,ParentDocID,Version,Status,ChangeSummary,ChangeClass,"
                  "EffectiveDate,StoragePath,Author,AuthorLookupId,"
                  "SyncStatus,SyncMessage")
APPROVAL_FIELDS = ("Title,ParentDocID,ParentVersion,Approver,ApproverLookupId,"
                   "SignatureMeaning,Reason,SyncStatus,SyncMessage")


def _date(v):
    return (v or "")[:10] or None


def fetch_items(g, list_id, fields):
    site = M365["site_id"]
    url = f"/sites/{site}/lists/{list_id}/items"
    out, params = [], {"$expand": f"fields($select={fields})", "$top": "200"}
    while url:
        page = g.get(url, **params)
        out += page.get("value", [])
        url = page.get("@odata.nextLink", "")
        if url:
            url = url.replace("https://graph.microsoft.com/v1.0", "")
            params = {}
    return out


def normalize_risk(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "Category": f.get("Category") or "",
        "Description": f.get("Description") or "",
        "Trigger": f.get("Trigger") or None,
        "Likelihood": f.get("Likelihood"),
        "Impact": f.get("Impact"),
        "ResponseType": f.get("ResponseType") or "",
        "RiskOwnerEmail": people.email(f.get("RiskOwnerLookupId")),
        "DueDate": _date(f.get("DueDate")),
        "RiskStatus": f.get("RiskStatus") or "Open",
        "ResidualScore": f.get("ResidualScore"),
        "ComplianceFlag": f.get("ComplianceFlag") or "None",
        "RiskCode": f.get("RiskCode") or "",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_milestone(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "BaselineDate": _date(f.get("BaselineDate")),
        "ForecastDate": _date(f.get("ForecastDate")),
        "ActualDate": _date(f.get("ActualDate")),
        "MilestoneStatus": f.get("MilestoneStatus") or "On track",
        "OwnerRole": f.get("OwnerRole") or "Project Manager",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_report(item, people):
    f = item.get("fields", {})
    created_by = (((item.get("createdBy") or {}).get("user") or {})
                  .get("email") or "").lower()
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "PeriodStart": _date(f.get("PeriodStart")),
        "PeriodEnd": _date(f.get("PeriodEnd")),
        "OverallStatus": f.get("OverallStatus") or "Green",
        "Trend": f.get("Trend") or "Steady",
        "ExecutiveSummary": f.get("ExecutiveSummary") or "",
        "DecisionsNeeded": f.get("DecisionsNeeded") or None,
        "SubmittedByEmail": people.email(f.get("SubmittedByLookupId")),
        "CreatedByEmail": created_by,
        "CreatedAt": item.get("createdDateTime"),
        "Health": {ka: f.get(f"{ka}Health") or "Green"
                   for ka in al.KNOWLEDGE_AREAS},
        "ApprovedByEmail": people.email(f.get("ApprovedByLookupId")),
        "ApprovedDate": _date(f.get("ApprovedDate")),
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_activity(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "Workstream": f.get("Workstream") or "",
        "WorkPackage": f.get("WorkPackage") or "",
        "StartPlanned": _date(f.get("StartPlanned")),
        "FinishPlanned": _date(f.get("FinishPlanned")),
        "StartActual": _date(f.get("StartActual")),
        "FinishActual": _date(f.get("FinishActual")),
        "OwnerEmail": people.email(f.get("OwnerLookupId")),
        "Department": f.get("Department") or "",
        "ActivityStatus": f.get("ActivityStatus") or "Not started",
        "PctComplete": f.get("PctComplete"),
        "ActivityCode": f.get("ActivityCode") or "",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_change_request(item, people):
    f = item.get("fields", {})
    created_by = (((item.get("createdBy") or {}).get("user") or {})
                  .get("email") or "").lower()
    # RequestedDate defaults to createdDateTime date when blank (like author fallback)
    created_date = (item.get("createdDateTime") or "")[:10] or None
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "RequestedDate": _date(f.get("RequestedDate")) or created_date,
        "RequestedByEmail": people.email(f.get("RequestedByLookupId")) or created_by,
        "CreatedAt": item.get("createdDateTime"),
        "CRClass": f.get("CRClass") or "",
        "ChangeType": f.get("ChangeType") or "",
        "AffectedArtifacts": f.get("AffectedArtifacts") or None,
        "Description": f.get("Description") or "",
        "Reason": f.get("Reason") or "",
        "ImpactScope": f.get("ImpactScope") or None,
        "ImpactQuality": f.get("ImpactQuality") or None,
        "ImpactScheduleDays": f.get("ImpactScheduleDays"),
        "ImpactCost": f.get("ImpactCost"),
        "IntakeID": f.get("IntakeID") or None,
        "Decision": f.get("Decision") or "Pending",
        "DecidedByEmail": people.email(f.get("DecidedByLookupId")),
        "DecidedDate": _date(f.get("DecidedDate")),
        "ImplementationVerified": coerce_bool(f.get("ImplementationVerified")),
        "LinkedArtifactsUpdated": coerce_bool(f.get("LinkedArtifactsUpdated")),
        "CRStatus": f.get("CRStatus") or "Open",
        "CRCode": f.get("CRCode") or "",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_decision(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "Rationale": f.get("Rationale") or "",
        "DecidedByEmail": people.email(f.get("DecidedByLookupId")),
        "DecidedDate": _date(f.get("DecidedDate")),
        "DecisionCode": f.get("DecisionCode") or "",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_baseline(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "BaselineType": f.get("BaselineType") or "",
        "ChangeSummary": f.get("ChangeSummary") or None,
        "LinkedCRCode": f.get("LinkedCRCode") or None,
        "BaselinedByEmail": people.email(f.get("BaselinedByLookupId")),
        "BaselineVersion": f.get("BaselineVersion") or "",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_phase_gate(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "TargetPhase": f.get("TargetPhase") or "",
        "GateDecision": f.get("GateDecision") or "Approved",
        "ApprovedByEmail": people.email(f.get("ApprovedByLookupId")),
        "DecidedDate": _date(f.get("DecidedDate")),
        "GateNotes": f.get("GateNotes") or None,
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_impact_assessment(item, people):
    f = item.get("fields", {})
    created_by = (((item.get("createdBy") or {}).get("user") or {})
                  .get("email") or "").lower()
    # SubmittedDate defaults to createdDateTime date when blank (NOT NULL column).
    created_date = (item.get("createdDateTime") or "")[:10] or None
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "ParentCRCode": (f.get("ParentCRCode") or "").strip(),
        "Department": f.get("Department") or "",
        "ScopeImpact": f.get("ScopeImpact") or None,
        "ScheduleImpactDays": f.get("ScheduleImpactDays"),
        "CostImpact": f.get("CostImpact"),
        "QualityImpact": f.get("QualityImpact") or None,
        # Author-fallback covers the NOT NULL submitted_by_person_id.
        "SubmittedByEmail": people.email(f.get("SubmittedByLookupId")) or created_by,
        "SubmittedDate": _date(f.get("SubmittedDate")) or created_date,
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_document(item, people):
    f = item.get("fields", {})
    created_by = (((item.get("createdBy") or {}).get("user") or {})
                  .get("email") or "").lower()
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "DocTypeCode": (f.get("DocTypeCode") or "").strip(),
        "Subtitle": f.get("Subtitle") or None,
        "PrimaryDepartment": f.get("PrimaryDepartment") or "",
        # Author-fallback covers the NOT NULL owner_person_id.
        "OwnerEmail": people.email(f.get("OwnerLookupId")) or created_by,
        "ApproverEmail": people.email(f.get("ApproverLookupId")),
        "LifecyclePhase": f.get("LifecyclePhase") or "",
        "Status": f.get("Status") or "DRAFT",
        "ReviewCycle": f.get("ReviewCycle") or "",
        "Classification": f.get("Classification") or "",
        "StorageSystem": f.get("StorageSystem") or "",
        "StoragePath": f.get("StoragePath") or "",
        "NextReviewDue": _date(f.get("NextReviewDue")),
        "IntakeID": f.get("IntakeID") or None,
        "DocID": f.get("DocID") or "",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_raci(item, people):
    f = item.get("fields", {})
    # ValidFrom defaults to createdDateTime date when blank (NOT NULL column).
    created_date = (item.get("createdDateTime") or "")[:10] or None
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ParentDocID": (f.get("ParentDocID") or "").strip(),
        "Department": f.get("Department") or "",
        "Role": (f.get("Role") or "").strip(),
        "Touchpoint": f.get("Touchpoint") or None,
        "ValidFrom": _date(f.get("ValidFrom")) or created_date,
        "ValidTo": _date(f.get("ValidTo")),
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_version(item, people):
    f = item.get("fields", {})
    created_by = (((item.get("createdBy") or {}).get("user") or {})
                  .get("email") or "").lower()
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ParentDocID": (f.get("ParentDocID") or "").strip(),
        "Version": (f.get("Version") or "").strip(),
        "Status": f.get("Status") or "DRAFT",
        "ChangeSummary": f.get("ChangeSummary") or "",
        "ChangeClass": f.get("ChangeClass") or "",
        "EffectiveDate": _date(f.get("EffectiveDate")),
        "StoragePath": f.get("StoragePath") or "",
        "AuthorEmail": people.email(f.get("AuthorLookupId")) or created_by,
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_approval(item, people):
    f = item.get("fields", {})
    created_by = (((item.get("createdBy") or {}).get("user") or {})
                  .get("email") or "").lower()
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ParentDocID": (f.get("ParentDocID") or "").strip(),
        "ParentVersion": (f.get("ParentVersion") or "").strip(),
        "ApproverEmail": people.email(f.get("ApproverLookupId")) or created_by,
        "SignatureMeaning": f.get("SignatureMeaning") or "Approval",
        "Reason": f.get("Reason") or None,
        # signed_at (and thus the esig_hash) bind to the moment of attestation.
        "CreatedAt": item.get("createdDateTime"),
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def writeback(g, list_id, item_id, fields):
    g.patch(f"/sites/{M365['site_id']}/lists/{list_id}/items/{item_id}/fields",
            fields)


def person_id_by_email(conn, email):
    row = conn.execute("SELECT person_id FROM doc_mgmt.person WHERE lower(email)=%s",
                       (email,)).fetchone()
    return row[0] if row else None


def project_by_code(conn, code):
    return conn.execute(
        "SELECT project_id, primary_department FROM pmbok.project "
        "WHERE project_code=%s", (code,)).fetchone()


def department_by_name(conn, name):
    """Resolve a doc_mgmt.department NAME to (department_id, code) or None."""
    return conn.execute(
        "SELECT department_id, code FROM doc_mgmt.department WHERE name=%s",
        (name,)).fetchone()


def document_type_by_code(conn, code):
    """Resolve a document_type code to (id, lifecycle_phase, default_review_cycle)."""
    return conn.execute(
        "SELECT document_type_id, lifecycle_phase, default_review_cycle"
        " FROM doc_mgmt.document_type WHERE code=%s", (code,)).fetchone()


def intake_exists(conn, intake_id):
    """True if intake_id is present in doc_mgmt.intake_submission.

    Airlocks the FK columns doc_mgmt.document.intake_id and
    pmbok.change_request.intake_id: a typo'd/unknown IntakeID becomes a clean
    validation error (like the project/person/type/dept resolvers) instead of a
    raw psycopg ForeignKeyViolation surfaced at INSERT/UPDATE time.
    """
    return conn.execute(
        "SELECT 1 FROM doc_mgmt.intake_submission WHERE intake_id=%s",
        (intake_id,)).fetchone() is not None


def resolve_parent_document(conn, doc_id):
    """Resolve a document by its globally-unique doc_id -> document_id or None."""
    row = conn.execute(
        "SELECT document_id FROM doc_mgmt.document WHERE doc_id=%s",
        (doc_id,)).fetchone()
    return row[0] if row else None


def resolve_parent_version(conn, document_id, version):
    """Resolve a (document_id, version) pair -> version_id or None."""
    row = conn.execute(
        "SELECT version_id FROM doc_mgmt.document_version"
        " WHERE document_id=%s AND version=%s",
        (document_id, version)).fetchone()
    return row[0] if row else None


def project_leads(conn, project_id):
    """Return (sponsor_person_id, project_manager_id) for authority checks."""
    row = conn.execute(
        "SELECT sponsor_person_id, project_manager_id FROM pmbok.project"
        " WHERE project_id=%s", (project_id,)).fetchone()
    return (row[0], row[1]) if row else (None, None)


def _error(g, list_id, it, errs, dry, kind):
    msg = "; ".join(errs)
    if not dry:
        writeback(g, list_id, it["item_id"],
                  {"SyncStatus": "Error", "SyncMessage": msg})
    return f"ERROR {kind} item {it['item_id']}: {msg}"


def synced_map(conn, table, select_sql):
    """external_ref -> current-row dict for one artifact table."""
    out = {}
    cur = conn.execute(select_sql)
    cols = [d.name for d in cur.description]
    for row in cur.fetchall():
        rec = dict(zip(cols, row))
        out[rec.pop("external_ref")] = rec
    return out


RISK_SELECT = ('SELECT external_ref, risk_id, project_id, risk_code, category,'
               ' description, "trigger", likelihood, impact, score,'
               ' response_type, owner_person_id, department, due_date, status,'
               ' residual_score, compliance_flag'
               ' FROM pmbok.risk WHERE external_ref IS NOT NULL')
MILESTONE_SELECT = ('SELECT external_ref, milestone_id, project_id, name,'
                    ' baseline_date, forecast_date, actual_date, status,'
                    ' owner_role'
                    ' FROM pmbok.milestone WHERE external_ref IS NOT NULL')
REPORT_SELECT = ('SELECT external_ref, report_id, project_id, period_start,'
                 ' period_end, overall_status, trend, executive_summary,'
                 ' decisions_needed, submitted_by_person_id,'
                 ' approved_by_person_id, approved_at'
                 ' FROM pmbok.status_report WHERE external_ref IS NOT NULL')
CR_SELECT = ('SELECT external_ref, cr_id, project_id, cr_code, intake_id,'
             ' requested_at, requested_by_person_id, cr_class, change_types,'
             ' affected_artifacts, description, reason, impact_scope,'
             ' impact_schedule_days, impact_cost, impact_quality, decision,'
             ' decided_by_person_id, decided_at, implementation_verified,'
             ' linked_artifacts_updated, status'
             ' FROM pmbok.change_request WHERE external_ref IS NOT NULL')
DECISION_SELECT = ('SELECT external_ref, decision_id, project_id, code,'
                   ' decision, rationale, decided_by_person_id, decided_at'
                   ' FROM pmbok.decision WHERE external_ref IS NOT NULL')
AREA_SELECT = ('SELECT r.external_ref, a.knowledge_area, a.status'
               ' FROM pmbok.status_report_area a'
               ' JOIN pmbok.status_report r ON r.report_id = a.report_id'
               ' WHERE r.external_ref IS NOT NULL')
BASELINE_SELECT = ('SELECT external_ref, baseline_id, project_id,'
                   ' baseline_type, version, status'
                   ' FROM pmbok.project_baseline WHERE external_ref IS NOT NULL')
PHASE_GATE_SELECT = ('SELECT external_ref, phase_gate_id, project_id,'
                     ' from_phase, to_phase, gate_decision'
                     ' FROM pmbok.phase_gate_log WHERE external_ref IS NOT NULL')
IMPACT_SELECT = ('SELECT external_ref, impact_id, cr_id, department,'
                 ' scope_impact, schedule_impact_days, cost_impact,'
                 ' quality_impact, submitted_by_person_id, submitted_at'
                 ' FROM pmbok.change_impact_assessment'
                 ' WHERE external_ref IS NOT NULL')
DOC_SELECT = ('SELECT external_ref, document_id, doc_id, document_type_id,'
              ' primary_department_id, title, subtitle, lifecycle_phase, status,'
              ' current_version, owner_person_id, approver_person_id,'
              ' review_cycle, next_review_due, intake_id, classification,'
              ' storage_system, storage_path'
              ' FROM doc_mgmt.document WHERE external_ref IS NOT NULL')
RACI_SELECT = ('SELECT external_ref, raci_id, document_id, department_id, role,'
               ' touchpoint, valid_from, valid_to'
               ' FROM doc_mgmt.raci_assignment WHERE external_ref IS NOT NULL')
VERSION_SELECT = ('SELECT external_ref, version_id, document_id, version, status,'
                  ' change_summary, change_class, linked_cr_id, author_person_id,'
                  ' effective_date, storage_path'
                  ' FROM doc_mgmt.document_version WHERE external_ref IS NOT NULL')
APPROVAL_SELECT = ('SELECT external_ref, approval_id, version_id,'
                   ' approver_person_id, signature_meaning, signed_at, esig_hash,'
                   ' reason'
                   ' FROM doc_mgmt.document_approval WHERE external_ref IS NOT NULL')
ACTIVITY_SELECT = ('SELECT a.external_ref, a.activity_id, a.wbs_element_id,'
                   ' w.project_id, a.activity_code, a.name, a.start_planned,'
                   ' a.finish_planned, a.start_actual, a.finish_actual,'
                   ' a.duration_days, a.owner_person_id, a.department,'
                   ' a.status, a.pct_complete'
                   ' FROM pmbok.schedule_activity a'
                   ' JOIN pmbok.wbs_element w USING (wbs_element_id)'
                   ' WHERE a.external_ref IS NOT NULL')
WBS_SELECT = ('SELECT wbs_code, parent_wbs_element_id, level, name,'
              ' owning_department FROM pmbok.wbs_element WHERE project_id=%s')


# ---- processors -------

def process_risk(conn, g, it, dry, current):
    errs = al.validate_risk(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    owner = (person_id_by_email(conn, it["RiskOwnerEmail"])
             if it["RiskOwnerEmail"] else None)
    if it["RiskOwnerEmail"] and not owner:
        errs.append(f"RiskOwner {it['RiskOwnerEmail']} not in person directory")
    if errs:
        return _error(g, M365["risk_list_id"], it, errs, dry, "risk")
    project_id, department = proj
    if current:
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["risk_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "risk")
        desired = al.build_risk_row(it, current["project_id"], department,
                                    owner, current["risk_code"])
        if al.row_changed(current, desired):
            if dry:
                return f"DRY risk item {it['item_id']}: would update {current['risk_code']}"
            with conn.transaction():
                conn.execute(
                    'UPDATE pmbok.risk SET category=%s, description=%s,'
                    ' "trigger"=%s, likelihood=%s, impact=%s, score=%s,'
                    ' response_type=%s, owner_person_id=%s, department=%s,'
                    ' due_date=%s, status=%s, residual_score=%s,'
                    ' compliance_flag=%s WHERE external_ref=%s',
                    (desired["category"], desired["description"],
                     desired["trigger"], desired["likelihood"],
                     desired["impact"], desired["score"],
                     desired["response_type"], desired["owner_person_id"],
                     desired["department"], desired["due_date"],
                     desired["status"], desired["residual_score"],
                     desired["compliance_flag"], it["item_id"]))
            writeback(g, M365["risk_list_id"], it["item_id"],
                      {"SyncStatus": "Synced", "SyncMessage": "",
                       "RiskCode": current["risk_code"]})
            return f"OK risk item {it['item_id']}: updated {current['risk_code']}"
        if it["SyncStatus"] != "Synced" or it["RiskCode"] != current["risk_code"]:
            if not dry:
                writeback(g, M365["risk_list_id"], it["item_id"],
                          {"SyncStatus": "Synced", "SyncMessage": "",
                           "RiskCode": current["risk_code"]})
            return f"OK risk item {it['item_id']}: healed write-back"
        return f"OK risk item {it['item_id']}: no change"
    existing_codes = [r[0] for r in conn.execute(
        "SELECT risk_code FROM pmbok.risk WHERE project_id=%s",
        (project_id,)).fetchall()]
    risk_code = al.next_risk_code(existing_codes)
    if dry:
        return f"DRY risk item {it['item_id']}: would create {risk_code} ({it['ProjectCode']})"
    row = al.build_risk_row(it, project_id, department, owner, risk_code)
    with conn.transaction():
        conn.execute(
            'INSERT INTO pmbok.risk (risk_id, project_id, risk_code, category,'
            ' description, "trigger", likelihood, impact, score, response_type,'
            ' owner_person_id, department, due_date, status, residual_score,'
            ' compliance_flag, external_ref)'
            ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (str(uuid.uuid5(NS, f"thg/artifact/risk/{it['item_id']}")),
             row["project_id"], row["risk_code"], row["category"],
             row["description"], row["trigger"], row["likelihood"],
             row["impact"], row["score"], row["response_type"],
             row["owner_person_id"], row["department"], row["due_date"],
             row["status"], row["residual_score"], row["compliance_flag"],
             it["item_id"]))
    writeback(g, M365["risk_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": "", "RiskCode": risk_code})
    return f"OK new risk {risk_code} ({it['ProjectCode']}, item {it['item_id']})"


def process_milestone(conn, g, it, dry, current):
    errs = al.validate_milestone(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    if errs:
        return _error(g, M365["milestone_list_id"], it, errs, dry, "milestone")
    project_id, _dept = proj
    if current:
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["milestone_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "milestone")
        desired = al.build_milestone_row(it, current["project_id"])
        if al.row_changed(current, desired):
            if dry:
                return f"DRY milestone item {it['item_id']}: would update {it['Title']}"
            with conn.transaction():
                conn.execute(
                    "UPDATE pmbok.milestone SET name=%s, baseline_date=%s,"
                    " forecast_date=%s, actual_date=%s, status=%s,"
                    " owner_role=%s WHERE external_ref=%s",
                    (desired["name"], desired["baseline_date"],
                     desired["forecast_date"], desired["actual_date"],
                     desired["status"], desired["owner_role"],
                     it["item_id"]))
            writeback(g, M365["milestone_list_id"], it["item_id"],
                      {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK milestone item {it['item_id']}: updated {it['Title']}"
        if it["SyncStatus"] != "Synced":
            if not dry:
                writeback(g, M365["milestone_list_id"], it["item_id"],
                          {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK milestone item {it['item_id']}: healed write-back"
        return f"OK milestone item {it['item_id']}: no change"
    if dry:
        return f"DRY milestone item {it['item_id']}: would create ({it['Title']})"
    row = al.build_milestone_row(it, project_id)
    with conn.transaction():
        conn.execute(
            "INSERT INTO pmbok.milestone (milestone_id, project_id, name,"
            " baseline_date, forecast_date, actual_date, status, owner_role,"
            " external_ref) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(uuid.uuid5(NS, f"thg/artifact/milestone/{it['item_id']}")),
             row["project_id"], row["name"], row["baseline_date"],
             row["forecast_date"], row["actual_date"], row["status"],
             row["owner_role"], it["item_id"]))
    writeback(g, M365["milestone_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": ""})
    return f"OK new milestone ({it['Title']}, item {it['item_id']})"


def process_report(conn, g, it, dry, current, area_map=None):
    errs = al.validate_status_report(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    submitter = (person_id_by_email(conn, it["SubmittedByEmail"])
                 or person_id_by_email(conn, it["CreatedByEmail"]))
    if not errs and not submitter:
        errs.append("SubmittedBy not in person directory")
    # Sign-off validation: ApprovedBy and ApprovedDate must be set together
    has_approver = bool(it.get("ApprovedByEmail"))
    has_approved_date = bool(it.get("ApprovedDate"))
    if has_approver != has_approved_date:
        errs.append("ApprovedBy and ApprovedDate must be set together")
    if has_approver:
        if not person_id_by_email(conn, it["ApprovedByEmail"]):
            errs.append(f"ApprovedBy {it['ApprovedByEmail']} not in person directory")
    if errs:
        return _error(g, M365["status_report_list_id"], it, errs, dry, "report")
    project_id, _dept = proj
    # Resolve approver person_id (None when no sign-off set)
    approver = (person_id_by_email(conn, it["ApprovedByEmail"])
                if it.get("ApprovedByEmail") else None)
    # Duplicate-period guard applies on both create AND update (PeriodStart may
    # have been edited into a collision). Exclude self via external_ref<>%s.
    dup = conn.execute(
        "SELECT 1 FROM pmbok.status_report WHERE project_id=%s AND"
        " period_start=%s AND (external_ref IS NULL OR external_ref<>%s)",
        (project_id, it["PeriodStart"], it["item_id"])).fetchone()
    if dup:
        return _error(g, M365["status_report_list_id"], it,
                      [f"Duplicate report period for {it['ProjectCode']}: "
                       f"{it['PeriodStart']}"], dry, "report")
    if current:
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["status_report_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "report")
        # submitter and submitted_at are immutable — use current's person id
        desired = al.build_report_row(it, current["project_id"],
                                      current["submitted_by_person_id"],
                                      approver)
        # Check parent row + area statuses for any change
        current_areas = (area_map or {}).get(it["item_id"], {})
        areas_changed = [ka for ka in al.KNOWLEDGE_AREAS
                         if it["Health"].get(ka) != current_areas.get(ka)]
        changed = al.row_changed(current, desired) or bool(areas_changed)
        if changed:
            if dry:
                return f"DRY report item {it['item_id']}: would update {it['ProjectCode']} {it['PeriodStart']}"
            report_id = current["report_id"]
            with conn.transaction():
                if al.row_changed(current, desired):
                    conn.execute(
                        "UPDATE pmbok.status_report SET period_start=%s,"
                        " period_end=%s, overall_status=%s, trend=%s,"
                        " executive_summary=%s, decisions_needed=%s,"
                        " approved_by_person_id=%s, approved_at=%s"
                        " WHERE external_ref=%s",
                        (desired["period_start"], desired["period_end"],
                         desired["overall_status"], desired["trend"],
                         desired["executive_summary"],
                         desired["decisions_needed"],
                         desired["approved_by_person_id"],
                         desired["approved_at"], it["item_id"]))
                for ka in areas_changed:
                    conn.execute(
                        "UPDATE pmbok.status_report_area SET status=%s"
                        " WHERE report_id=%s AND knowledge_area=%s",
                        (it["Health"][ka], report_id, ka))
                # Write STATUS_SIGNOFF audit entry when approved_at transitions
                # from NULL to set (first sign-off). INSIDE the transaction.
                if current.get("approved_at") is None and desired["approved_at"] is not None:
                    audit_lib.write_trail(
                        conn, approver, "STATUS_SIGNOFF", "status_report",
                        current["report_id"], None,
                        {"approved_at": str(desired["approved_at"])}, None)
            writeback(g, M365["status_report_list_id"], it["item_id"],
                      {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK report item {it['item_id']}: updated {it['ProjectCode']} {it['PeriodStart']}"
        if it["SyncStatus"] != "Synced":
            if not dry:
                writeback(g, M365["status_report_list_id"], it["item_id"],
                          {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK report item {it['item_id']}: healed write-back"
        return f"OK report item {it['item_id']}: no change"
    if dry:
        return (f"DRY report item {it['item_id']}: would create report + 9 areas"
                f" ({it['ProjectCode']} {it['PeriodStart']}..{it['PeriodEnd']})")
    report_id = str(uuid.uuid5(NS, f"thg/artifact/report/{it['item_id']}"))
    row = al.build_report_row(it, project_id, submitter, None)
    with conn.transaction():
        conn.execute(
            "INSERT INTO pmbok.status_report (report_id, project_id,"
            " period_start, period_end, overall_status, trend,"
            " executive_summary, decisions_needed, submitted_by_person_id,"
            " submitted_at, external_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (report_id, row["project_id"], row["period_start"],
             row["period_end"], row["overall_status"], row["trend"],
             row["executive_summary"], row["decisions_needed"],
             row["submitted_by_person_id"], it["CreatedAt"], it["item_id"]))
        for area in al.build_area_rows(it):
            conn.execute(
                "INSERT INTO pmbok.status_report_area (area_id, report_id,"
                " knowledge_area, status) VALUES (%s,%s,%s,%s)",
                (str(uuid.uuid5(NS, f"thg/sra/{it['item_id']}/{area['knowledge_area']}")),
                 report_id, area["knowledge_area"], area["status"]))
    writeback(g, M365["status_report_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": ""})
    return f"OK new report + 9 areas ({it['ProjectCode']} {it['PeriodStart']}, item {it['item_id']})"


def reconcile_wbs(conn, project_id, project_code, project_activities, dry):
    """Ensure L1 workstream + L2 work-package WBS nodes exist for every
    (workstream, workpackage) referenced by this project's activities.
    Returns (wbs_map, wbs_code_map):
      wbs_map       : {(workstream, workpackage): wbs_element_id (uuid)}
      wbs_code_map  : {(workstream, workpackage): wbs_code string}
    Hardening A: per-node owning_department/owner_role are computed here and
      threaded into inserts (via nodes_to_insert list).
    Hardening B: existing rows are processed L1-first (sorted by level asc)
      so L2 parent lookups never miss.
    In dry mode: NO writes; maps still returned (existing + would-be ids/codes).
    """
    # Load existing WBS rows for this project.
    existing_rows = conn.execute(WBS_SELECT, (project_id,)).fetchall()

    # Hardening B: sort existing rows level-ascending so L1s populate
    # l1_name_to_code before any L2 tries to look up its parent.
    existing_rows_sorted = sorted(existing_rows, key=lambda r: r[2])  # level is index 2

    l1_name_to_code = {}   # ws_name  -> wbs_code  (for existing L1 rows)
    l2_name_to_code = {}   # (ws_name, wp_name) -> wbs_code  (for existing L2 rows)
    existing_codes = set()

    for row in existing_rows_sorted:
        wbs_code, _parent, level, name, _dept = row
        existing_codes.add(wbs_code)
        if level == 1:
            l1_name_to_code[name] = wbs_code
        elif level == 2:
            # Reconstruct workstream by prefix-matching against known L1 codes.
            for ws_name, l1_code in l1_name_to_code.items():
                if wbs_code.startswith(l1_code + "."):
                    l2_name_to_code[(ws_name, name)] = wbs_code
                    break

    # Working set of all codes (existing + newly minted this run) so two new
    # workstreams in one run get distinct integers.
    working_codes = set(existing_codes)

    # Sort activities by int(item_id) for deterministic owning_department.
    sorted_acts = sorted(project_activities, key=lambda a: int(a["item_id"]))

    # Hardening A: track per-node owning_department (first activity under the node).
    seen_ws = {}    # ws_name -> (wbs_code, wbs_element_id, owning_department)
    seen_wp = {}    # (ws_name, wp_name) -> (wbs_code, wbs_element_id, owning_department)
    # Ordered list of nodes to INSERT (L1 before L2 to satisfy FK).
    nodes_to_insert = []  # list of dicts with all INSERT fields

    for act in sorted_acts:
        ws = act["Workstream"]
        wp = act["WorkPackage"]
        dept = act["Department"] or ""
        if not ws or not wp:
            continue

        # --- L1: workstream ---
        if ws not in seen_ws:
            is_new_l1 = ws not in l1_name_to_code
            if is_new_l1:
                l1_code = al.next_wbs_code(working_codes)
                working_codes.add(l1_code)
                l1_name_to_code[ws] = l1_code
            else:
                l1_code = l1_name_to_code[ws]
            l1_id = uuid.uuid5(NS, f"thg/wbs/{project_code}/ws/{ws}")
            seen_ws[ws] = (l1_code, l1_id, dept)
            if is_new_l1:
                nodes_to_insert.append({
                    "wbs_element_id": str(l1_id),
                    "project_id": str(project_id),
                    "wbs_code": l1_code,
                    "parent_wbs_element_id": None,
                    "level": 1,
                    "name": ws,
                    "owning_department": dept,
                    "owner_role": "Workstream Lead",
                })
        else:
            l1_code, l1_id, _l1_dept = seen_ws[ws]

        # --- L2: work package ---
        if (ws, wp) not in seen_wp:
            is_new_l2 = (ws, wp) not in l2_name_to_code
            if is_new_l2:
                l2_code = al.next_wbs_code(working_codes, l1_code)
                working_codes.add(l2_code)
                l2_name_to_code[(ws, wp)] = l2_code
            else:
                l2_code = l2_name_to_code[(ws, wp)]
            l2_id = uuid.uuid5(NS, f"thg/wbs/{project_code}/wp/{ws}/{wp}")
            seen_wp[(ws, wp)] = (l2_code, l2_id, dept)
            if is_new_l2:
                nodes_to_insert.append({
                    "wbs_element_id": str(l2_id),
                    "project_id": str(project_id),
                    "wbs_code": l2_code,
                    "parent_wbs_element_id": str(l1_id),
                    "level": 2,
                    "name": wp,
                    "owning_department": dept,
                    "owner_role": "Work Package Owner",
                })

    # Real write: INSERT missing nodes inside one transaction (L1 before L2 in
    # nodes_to_insert order — guaranteed by the loop above: L1 is appended before
    # any of its L2 children).  Deterministic ids make ON CONFLICT idempotent.
    if not dry and nodes_to_insert:
        with conn.transaction():
            for node in nodes_to_insert:
                conn.execute(
                    "INSERT INTO pmbok.wbs_element"
                    " (wbs_element_id, project_id, wbs_code,"
                    "  parent_wbs_element_id, level, name,"
                    "  owning_department, owner_role)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
                    " ON CONFLICT (wbs_element_id) DO NOTHING",
                    (node["wbs_element_id"], node["project_id"],
                     node["wbs_code"], node["parent_wbs_element_id"],
                     node["level"], node["name"],
                     node["owning_department"], node["owner_role"]))

    # Build output maps: (ws, wp) -> l2_element_id and (ws, wp) -> l2_code.
    wbs_map = {key: val[1] for key, val in seen_wp.items()}
    wbs_code_map = {key: val[0] for key, val in seen_wp.items()}
    return wbs_map, wbs_code_map


def process_activity(conn, g, it, dry, current, wbs_map=None, wbs_code_map=None):
    wbs_map = wbs_map or {}
    wbs_code_map = wbs_code_map or {}
    errs = al.validate_activity(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    owner = (person_id_by_email(conn, it["OwnerEmail"])
             if it["OwnerEmail"] else None)
    if it["OwnerEmail"] and not owner:
        errs.append(f"Owner {it['OwnerEmail']} not in person directory")
    if errs:
        return _error(g, M365["activity_list_id"], it, errs, dry, "activity")
    ws = it["Workstream"]
    wp = it["WorkPackage"]
    wbs_id = wbs_map.get((ws, wp))
    wbs_code = wbs_code_map.get((ws, wp))
    if wbs_id is None or wbs_code is None:
        # ProjectCode resolved but (ws, wp) not in map — reconcile_wbs skips
        # rows with blank ws/wp; those already fail validate_activity above.
        return _error(g, M365["activity_list_id"], it,
                      [f"WBS node not found for ({ws!r} / {wp!r})"], dry, "activity")
    # Fetch existing activity codes for this WBS element (for code minting).
    existing_codes = [r[0] for r in conn.execute(
        "SELECT activity_code FROM pmbok.schedule_activity WHERE wbs_element_id=%s",
        (str(wbs_id),)).fetchall()]
    if current:
        project_id, _dept = proj
        # Re-parent guard: project changed.
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["activity_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "activity")
        # Re-parent guard: WBS parent (workstream / workpackage) changed.
        if str(current["wbs_element_id"]) != str(wbs_id):
            return _error(g, M365["activity_list_id"], it,
                          ["Workstream/WorkPackage changed after sync - create a"
                           " new row instead"], dry, "activity")
        desired = al.build_activity_row(it, current["wbs_element_id"],
                                        owner, current["activity_code"])
        if al.row_changed(current, desired):
            if dry:
                return (f"DRY activity item {it['item_id']}: would update"
                        f" {current['activity_code']}")
            with conn.transaction():
                conn.execute(
                    "UPDATE pmbok.schedule_activity SET name=%s,"
                    " start_planned=%s, finish_planned=%s,"
                    " start_actual=%s, finish_actual=%s,"
                    " duration_days=%s, owner_person_id=%s,"
                    " department=%s, status=%s, pct_complete=%s"
                    " WHERE external_ref=%s",
                    (desired["name"], desired["start_planned"],
                     desired["finish_planned"], desired["start_actual"],
                     desired["finish_actual"], desired["duration_days"],
                     desired["owner_person_id"], desired["department"],
                     desired["status"], desired["pct_complete"],
                     it["item_id"]))
            writeback(g, M365["activity_list_id"], it["item_id"],
                      {"SyncStatus": "Synced", "SyncMessage": "",
                       "ActivityCode": current["activity_code"]})
            return (f"OK activity item {it['item_id']}:"
                    f" updated {current['activity_code']}")
        if (it["SyncStatus"] != "Synced"
                or it.get("ActivityCode") != current["activity_code"]):
            if not dry:
                writeback(g, M365["activity_list_id"], it["item_id"],
                          {"SyncStatus": "Synced", "SyncMessage": "",
                           "ActivityCode": current["activity_code"]})
            return f"OK activity item {it['item_id']}: healed write-back"
        return f"OK activity item {it['item_id']}: no change"
    # New item — mint code.
    activity_code = al.next_activity_code(existing_codes, wbs_code)
    if dry:
        return (f"DRY activity item {it['item_id']}: would create {activity_code}"
                f" ({ws} / {wp})")
    # Real insert (mirror process_risk transaction + write-back structure).
    activity_id = str(uuid.uuid5(NS, f"thg/artifact/activity/{it['item_id']}"))
    row = al.build_activity_row(it, str(wbs_id), owner, activity_code)
    with conn.transaction():
        conn.execute(
            "INSERT INTO pmbok.schedule_activity"
            " (activity_id, wbs_element_id, activity_code, name,"
            "  start_planned, finish_planned, start_actual, finish_actual,"
            "  duration_days, owner_person_id, department, status,"
            "  pct_complete, external_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (activity_id, row["wbs_element_id"], row["activity_code"],
             row["name"], row["start_planned"], row["finish_planned"],
             row["start_actual"], row["finish_actual"], row["duration_days"],
             row["owner_person_id"], row["department"], row["status"],
             row["pct_complete"], it["item_id"]))
    writeback(g, M365["activity_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": "",
               "ActivityCode": activity_code})
    return f"OK new activity {activity_code} ({ws} / {wp}, item {it['item_id']})"


def process_change_request(conn, g, it, dry, current):
    errs = al.validate_change_request(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    requester = (person_id_by_email(conn, it["RequestedByEmail"])
                 if it["RequestedByEmail"] else None)
    if it["RequestedByEmail"] and not requester:
        errs.append(f"RequestedBy {it['RequestedByEmail']} not in person directory")
    decider = (person_id_by_email(conn, it["DecidedByEmail"])
               if it["DecidedByEmail"] else None)
    if it["DecidedByEmail"] and not decider:
        errs.append(f"DecidedBy {it['DecidedByEmail']} not in person directory")
    if it.get("IntakeID") and not intake_exists(conn, it["IntakeID"]):
        errs.append(f"Unknown IntakeID: {it['IntakeID']}")
    if errs:
        return _error(g, M365["change_request_list_id"], it, errs, dry,
                      "change_request")
    project_id, _dept = proj
    # Soft-authority note: if Decision != Pending and decider is not project lead
    warn = ""
    if it["Decision"] != "Pending" and decider:
        sponsor_id, pm_id = project_leads(conn, project_id)
        if decider not in (sponsor_id, pm_id):
            warn = (f"DecidedBy {it['DecidedByEmail']} is not the project"
                    " sponsor or PM — authority advisory only")
    if current:
        # ProjectCode-change guard
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["change_request_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "change_request")
        desired = al.build_cr_row(it, current["project_id"], requester,
                                  decider, current["cr_code"])
        if al.row_changed(current, desired):
            if dry:
                return (f"DRY change_request item {it['item_id']}: would update"
                        f" {current['cr_code']}")
            with conn.transaction():
                conn.execute(
                    "UPDATE pmbok.change_request SET intake_id=%s,"
                    " requested_at=%s, requested_by_person_id=%s,"
                    " cr_class=%s, change_types=%s, affected_artifacts=%s,"
                    " description=%s, reason=%s, impact_scope=%s,"
                    " impact_schedule_days=%s, impact_cost=%s,"
                    " impact_quality=%s, decision=%s,"
                    " decided_by_person_id=%s, decided_at=%s,"
                    " implementation_verified=%s,"
                    " linked_artifacts_updated=%s, status=%s"
                    " WHERE external_ref=%s",
                    (desired["intake_id"], desired["requested_at"],
                     desired["requested_by_person_id"], desired["cr_class"],
                     desired["change_types"], desired["affected_artifacts"],
                     desired["description"], desired["reason"],
                     desired["impact_scope"], desired["impact_schedule_days"],
                     desired["impact_cost"], desired["impact_quality"],
                     desired["decision"], desired["decided_by_person_id"],
                     desired["decided_at"],
                     desired["implementation_verified"],
                     desired["linked_artifacts_updated"],
                     desired["status"], it["item_id"]))
                # Audit decision change (if any), INSIDE the transaction
                if str(current.get("decision") or "") != str(desired["decision"]):
                    before_d, after_d = al._trail_states(
                        current, desired, ["decision"])
                    audit_lib.write_trail(
                        conn, decider or requester, "CR_DECISION",
                        "change_request", current["cr_id"],
                        before_d, after_d, None)
                # Audit status change (if any), INSIDE the transaction
                if str(current.get("status") or "") != str(desired["status"]):
                    before_s, after_s = al._trail_states(
                        current, desired, ["status"])
                    audit_lib.write_trail(
                        conn, decider or requester, "CR_STATUS",
                        "change_request", current["cr_id"],
                        before_s, after_s, None)
            writeback(g, M365["change_request_list_id"], it["item_id"],
                      {"SyncStatus": "Synced", "SyncMessage": warn,
                       "CRCode": current["cr_code"]})
            return (f"OK change_request item {it['item_id']}:"
                    f" updated {current['cr_code']}")
        if (it["SyncStatus"] != "Synced"
                or it.get("CRCode") != current["cr_code"]):
            if not dry:
                writeback(g, M365["change_request_list_id"], it["item_id"],
                          {"SyncStatus": "Synced", "SyncMessage": warn,
                           "CRCode": current["cr_code"]})
            return f"OK change_request item {it['item_id']}: healed write-back"
        return f"OK change_request item {it['item_id']}: no change"
    # New item — mint code
    existing_codes = [r[0] for r in conn.execute(
        "SELECT cr_code FROM pmbok.change_request WHERE project_id=%s",
        (project_id,)).fetchall()]
    cr_code = al.next_cr_code(existing_codes)
    suffix = f" - {warn}" if warn else ""
    if dry:
        return (f"DRY change_request item {it['item_id']}: would create"
                f" {cr_code} ({it['ProjectCode']}){suffix}")
    cr_id = str(uuid.uuid5(NS, f"thg/artifact/cr/{it['item_id']}"))
    row = al.build_cr_row(it, project_id, requester, decider, cr_code)
    with conn.transaction():
        conn.execute(
            "INSERT INTO pmbok.change_request"
            " (cr_id, project_id, cr_code, intake_id, requested_at,"
            " requested_by_person_id, cr_class, change_types,"
            " affected_artifacts, description, reason, impact_scope,"
            " impact_schedule_days, impact_cost, impact_quality, decision,"
            " decided_by_person_id, decided_at, implementation_verified,"
            " linked_artifacts_updated, status, external_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,%s)",
            (cr_id, row["project_id"], row["cr_code"], row["intake_id"],
             row["requested_at"], row["requested_by_person_id"],
             row["cr_class"], row["change_types"], row["affected_artifacts"],
             row["description"], row["reason"], row["impact_scope"],
             row["impact_schedule_days"], row["impact_cost"],
             row["impact_quality"], row["decision"],
             row["decided_by_person_id"], row["decided_at"],
             row["implementation_verified"], row["linked_artifacts_updated"],
             row["status"], it["item_id"]))
        audit_lib.write_trail(
            conn, decider or requester, "CR_CREATE", "change_request", cr_id,
            None, {"decision": row["decision"], "status": row["status"]},
            None)
    writeback(g, M365["change_request_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": warn, "CRCode": cr_code})
    return (f"OK new change_request {cr_code}"
            f" ({it['ProjectCode']}, item {it['item_id']})")


def process_decision(conn, g, it, dry, current):
    errs = al.validate_decision(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    decider = (person_id_by_email(conn, it["DecidedByEmail"])
               if it["DecidedByEmail"] else None)
    if it["DecidedByEmail"] and not decider:
        errs.append(f"DecidedBy {it['DecidedByEmail']} not in person directory")
    if errs:
        return _error(g, M365["decision_list_id"], it, errs, dry, "decision")
    project_id, _dept = proj
    if current:
        # ProjectCode-change guard
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["decision_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "decision")
        desired = al.build_decision_row(it, current["project_id"], decider,
                                        current["code"])
        if al.row_changed(current, desired):
            if dry:
                return (f"DRY decision item {it['item_id']}: would update"
                        f" {current['code']}")
            with conn.transaction():
                conn.execute(
                    "UPDATE pmbok.decision SET decision=%s, rationale=%s,"
                    " decided_by_person_id=%s, decided_at=%s"
                    " WHERE external_ref=%s",
                    (desired["decision"], desired["rationale"],
                     desired["decided_by_person_id"], desired["decided_at"],
                     it["item_id"]))
            writeback(g, M365["decision_list_id"], it["item_id"],
                      {"SyncStatus": "Synced", "SyncMessage": "",
                       "DecisionCode": current["code"]})
            return f"OK decision item {it['item_id']}: updated {current['code']}"
        if (it["SyncStatus"] != "Synced"
                or it.get("DecisionCode") != current["code"]):
            if not dry:
                writeback(g, M365["decision_list_id"], it["item_id"],
                          {"SyncStatus": "Synced", "SyncMessage": "",
                           "DecisionCode": current["code"]})
            return f"OK decision item {it['item_id']}: healed write-back"
        return f"OK decision item {it['item_id']}: no change"
    # New item — mint code
    existing_codes = [r[0] for r in conn.execute(
        "SELECT code FROM pmbok.decision WHERE project_id=%s",
        (project_id,)).fetchall()]
    decision_code = al.next_decision_code(existing_codes)
    if dry:
        return (f"DRY decision item {it['item_id']}: would create"
                f" {decision_code} ({it['ProjectCode']})")
    decision_id = str(uuid.uuid5(NS, f"thg/artifact/decision/{it['item_id']}"))
    row = al.build_decision_row(it, project_id, decider, decision_code)
    with conn.transaction():
        conn.execute(
            "INSERT INTO pmbok.decision"
            " (decision_id, project_id, code, decision, rationale,"
            " decided_by_person_id, decided_at, external_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (decision_id, row["project_id"], row["code"], row["decision"],
             row["rationale"], row["decided_by_person_id"], row["decided_at"],
             it["item_id"]))
    writeback(g, M365["decision_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": "",
               "DecisionCode": decision_code})
    return (f"OK new decision {decision_code}"
            f" ({it['ProjectCode']}, item {it['item_id']})")


def resolve_parent_cr(conn, project_id, cr_code):
    """Resolve a parent change request by (project_id, cr_code) -> cr_id or None.

    cr_code is UNIQUE per (project_id, cr_code), not global, so the project
    scopes the lookup. The registry processes change_request before
    change_impact_assessment and the sync runs autocommit, so a parent filed
    the same morning is already committed when its child resolves here.
    """
    row = conn.execute(
        "SELECT cr_id FROM pmbok.change_request"
        " WHERE project_id=%s AND cr_code=%s",
        (project_id, cr_code)).fetchone()
    return row[0] if row else None


def process_impact_assessment(conn, g, it, dry, current):
    errs = al.validate_impact_assessment(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    submitter = (person_id_by_email(conn, it["SubmittedByEmail"])
                 if it["SubmittedByEmail"] else None)
    if it["SubmittedByEmail"] and not submitter:
        errs.append(f"SubmittedBy {it['SubmittedByEmail']} not in person directory")
    cr_id = None
    if it.get("ParentCRCode") and proj and not errs:
        cr_id = resolve_parent_cr(conn, proj[0], it["ParentCRCode"])
        if cr_id is None:
            errs.append(f"Unknown ParentCRCode {it['ParentCRCode']} for project"
                        f" {it['ProjectCode']}")
    if errs:
        return _error(g, M365["impact_assessment_list_id"], it, errs, dry,
                      "impact")
    item_id = it["item_id"]
    desired = al.build_impact_assessment_row(it, cr_id, submitter,
                                             it["SubmittedDate"])
    list_id = M365["impact_assessment_list_id"]

    if current:
        # Re-parent guard: the parent CR is fixed for a given row. Editing
        # ProjectCode/ParentCRCode to point elsewhere is rejected.
        if str(current["cr_id"]) != str(cr_id):
            return _error(g, list_id, it,
                          ["Reparenting not allowed; create a new impact"
                           " assessment"], dry, "impact")
        if al.row_changed(current, desired):
            if dry:
                return f"DRY impact item {item_id}: would update"
            with conn.transaction():
                conn.execute(
                    "UPDATE pmbok.change_impact_assessment SET department=%s,"
                    " scope_impact=%s, schedule_impact_days=%s, cost_impact=%s,"
                    " quality_impact=%s, submitted_by_person_id=%s,"
                    " submitted_at=%s WHERE external_ref=%s",
                    (desired["department"], desired["scope_impact"],
                     desired["schedule_impact_days"], desired["cost_impact"],
                     desired["quality_impact"], desired["submitted_by_person_id"],
                     desired["submitted_at"], item_id))
            writeback(g, list_id, item_id,
                      {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK impact item {item_id}: updated"
        if it["SyncStatus"] != "Synced":
            if not dry:
                writeback(g, list_id, item_id,
                          {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK impact item {item_id}: healed write-back"
        return f"OK impact item {item_id}: no change"
    # New item
    if dry:
        return (f"DRY impact item {item_id}: would create for CR"
                f" {it['ParentCRCode']} ({it['ProjectCode']}/{it['Department']})")
    impact_id = str(uuid.uuid5(NS, f"thg/artifact/impact/{item_id}"))
    with conn.transaction():
        conn.execute(
            "INSERT INTO pmbok.change_impact_assessment"
            " (impact_id, cr_id, department, scope_impact, schedule_impact_days,"
            " cost_impact, quality_impact, submitted_by_person_id, submitted_at,"
            " external_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (impact_id, desired["cr_id"], desired["department"],
             desired["scope_impact"], desired["schedule_impact_days"],
             desired["cost_impact"], desired["quality_impact"],
             desired["submitted_by_person_id"], desired["submitted_at"], item_id))
    writeback(g, list_id, item_id, {"SyncStatus": "Synced", "SyncMessage": ""})
    return (f"OK new impact for CR {it['ParentCRCode']}"
            f" ({it['ProjectCode']}/{it['Department']}, item {item_id})")


def process_document(conn, g, it, dry, current):
    errs = al.validate_document(it)
    dtype = (document_type_by_code(conn, it["DocTypeCode"])
             if it["DocTypeCode"] else None)
    if it["DocTypeCode"] and not dtype:
        errs.append(f"Unknown DocTypeCode: {it['DocTypeCode']}")
    dept = (department_by_name(conn, it["PrimaryDepartment"])
            if it["PrimaryDepartment"] else None)
    if it["PrimaryDepartment"] and not dept:
        errs.append(f"Unknown PrimaryDepartment: {it['PrimaryDepartment']}")
    owner = (person_id_by_email(conn, it["OwnerEmail"])
             if it["OwnerEmail"] else None)
    if it["OwnerEmail"] and not owner:
        errs.append(f"Owner {it['OwnerEmail']} not in person directory")
    approver = (person_id_by_email(conn, it["ApproverEmail"])
                if it["ApproverEmail"] else None)
    if it["ApproverEmail"] and not approver:
        errs.append(f"Approver {it['ApproverEmail']} not in person directory")
    if it.get("IntakeID") and not intake_exists(conn, it["IntakeID"]):
        errs.append(f"Unknown IntakeID: {it['IntakeID']}")
    if errs:
        return _error(g, M365["document_list_id"], it, errs, dry, "document")
    type_id, type_phase, type_cycle = dtype
    dept_id, dept_code = dept
    lifecycle_phase = it["LifecyclePhase"] or type_phase
    review_cycle = it["ReviewCycle"] or type_cycle
    item_id = it["item_id"]
    list_id = M365["document_list_id"]

    if current:
        # Immutable-identity guard: DocTypeCode + PrimaryDepartment define the
        # doc_id, so they cannot change after sync.
        if (str(current["document_type_id"]) != str(type_id)
                or str(current["primary_department_id"]) != str(dept_id)):
            return _error(g, list_id, it,
                          ["DocTypeCode/PrimaryDepartment changed after sync -"
                           " create a new document instead"], dry, "document")
        full = al.build_document_row(it, type_id, dept_id, owner, approver,
                                     lifecycle_phase, review_cycle,
                                     current["doc_id"])
        desired = {k: full[k] for k in al.MUTABLE_DOC_COLS}
        if al.row_changed(current, desired):
            if dry:
                return (f"DRY document item {item_id}: would update"
                        f" {current['doc_id']}")
            sets = ", ".join(f"{k}=%s" for k in al.MUTABLE_DOC_COLS)
            with conn.transaction():
                conn.execute(
                    f"UPDATE doc_mgmt.document SET {sets}, updated_at=now()"
                    " WHERE external_ref=%s",
                    [desired[k] for k in al.MUTABLE_DOC_COLS] + [item_id])
                if str(current.get("status") or "") != str(desired["status"]):
                    before, after = al._trail_states(current, desired, ["status"])
                    audit_lib.write_trail(conn, owner, "DOCUMENT_STATUS",
                                          "document", current["document_id"],
                                          before, after, None)
            writeback(g, list_id, item_id,
                      {"SyncStatus": "Synced", "SyncMessage": "",
                       "DocID": current["doc_id"]})
            return f"OK document item {item_id}: updated {current['doc_id']}"
        if it["SyncStatus"] != "Synced" or it.get("DocID") != current["doc_id"]:
            if not dry:
                writeback(g, list_id, item_id,
                          {"SyncStatus": "Synced", "SyncMessage": "",
                           "DocID": current["doc_id"]})
            return f"OK document item {item_id}: healed write-back"
        return f"OK document item {item_id}: no change"
    # New item — mint doc_id per (department, type)
    existing = [r[0] for r in conn.execute(
        "SELECT doc_id FROM doc_mgmt.document"
        " WHERE primary_department_id=%s AND document_type_id=%s",
        (dept_id, type_id)).fetchall()]
    doc_id = al.next_doc_id(existing, dept_code, it["DocTypeCode"])
    if dry:
        return (f"DRY document item {item_id}: would create {doc_id}"
                f" '{it['Title']}'")
    document_id = str(uuid.uuid5(NS, f"thg/artifact/document/{item_id}"))
    row = al.build_document_row(it, type_id, dept_id, owner, approver,
                                lifecycle_phase, review_cycle, doc_id)
    cols = ["document_id"] + list(row.keys()) + ["external_ref"]
    vals = [document_id] + list(row.values()) + [item_id]
    with conn.transaction():
        conn.execute(
            f"INSERT INTO doc_mgmt.document ({', '.join(cols)})"
            f" VALUES ({', '.join(['%s'] * len(cols))})", vals)
        audit_lib.write_trail(conn, owner, "DOCUMENT_CREATE", "document",
                              document_id, None, {"status": row["status"]}, None)
    writeback(g, list_id, item_id,
              {"SyncStatus": "Synced", "SyncMessage": "", "DocID": doc_id})
    return (f"OK new document {doc_id} '{it['Title']}'"
            f" ({dept_code}/{it['DocTypeCode']}, item {item_id})")


def process_raci_assignment(conn, g, it, dry, current):
    errs = al.validate_raci(it)
    document_id = (resolve_parent_document(conn, it["ParentDocID"])
                   if it["ParentDocID"] else None)
    if it["ParentDocID"] and document_id is None:
        errs.append(f"Unknown ParentDocID: {it['ParentDocID']}")
    dept = (department_by_name(conn, it["Department"])
            if it["Department"] else None)
    if it["Department"] and not dept:
        errs.append(f"Unknown Department: {it['Department']}")
    if errs:
        return _error(g, M365["raci_list_id"], it, errs, dry, "raci")
    dept_id = dept[0]
    item_id = it["item_id"]
    list_id = M365["raci_list_id"]
    desired = al.build_raci_row(it, document_id, dept_id)

    if current:
        # Re-parent guard: the parent document is fixed for a given row.
        if str(current["document_id"]) != str(document_id):
            return _error(g, list_id, it,
                          ["ParentDocID changed after sync - create a new RACI"
                           " assignment instead"], dry, "raci")
        if al.row_changed(current, desired):
            if dry:
                return f"DRY raci item {item_id}: would update"
            with conn.transaction():
                conn.execute(
                    "UPDATE doc_mgmt.raci_assignment SET department_id=%s,"
                    " role=%s, touchpoint=%s, valid_from=%s, valid_to=%s"
                    " WHERE external_ref=%s",
                    (desired["department_id"], desired["role"],
                     desired["touchpoint"], desired["valid_from"],
                     desired["valid_to"], item_id))
            writeback(g, list_id, item_id,
                      {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK raci item {item_id}: updated"
        if it["SyncStatus"] != "Synced":
            if not dry:
                writeback(g, list_id, item_id,
                          {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK raci item {item_id}: healed write-back"
        return f"OK raci item {item_id}: no change"
    # New item
    if dry:
        return (f"DRY raci item {item_id}: would create {it['Role']} for"
                f" {it['Department']} on {it['ParentDocID']}")
    raci_id = str(uuid.uuid5(NS, f"thg/artifact/raci/{item_id}"))
    with conn.transaction():
        conn.execute(
            "INSERT INTO doc_mgmt.raci_assignment"
            " (raci_id, document_id, department_id, role, touchpoint,"
            " valid_from, valid_to, external_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (raci_id, desired["document_id"], desired["department_id"],
             desired["role"], desired["touchpoint"], desired["valid_from"],
             desired["valid_to"], item_id))
    writeback(g, list_id, item_id, {"SyncStatus": "Synced", "SyncMessage": ""})
    return (f"OK new raci {it['Role']} for {it['Department']} on"
            f" {it['ParentDocID']} (item {item_id})")


def process_document_version(conn, g, it, dry, current):
    # T4: validate + resolve (document, author); no writes yet (T5 write path).
    errs = al.validate_version(it)
    document_id = (resolve_parent_document(conn, it["ParentDocID"])
                   if it["ParentDocID"] else None)
    if it["ParentDocID"] and document_id is None:
        errs.append(f"Unknown ParentDocID: {it['ParentDocID']}")
    author = (person_id_by_email(conn, it["AuthorEmail"])
              if it["AuthorEmail"] else None)
    if it["AuthorEmail"] and not author:
        errs.append(f"Author {it['AuthorEmail']} not in person directory")
    if errs:
        return _error(g, M365["version_list_id"], it, errs, dry, "version")
    return (f"DRY version item {it['item_id']}: {it['ParentDocID']} v{it['Version']}"
            f" ({it['Status']}); no writes (stub)")


def process_document_approval(conn, g, it, dry, current):
    # T4: validate + resolve (document, version, approver); no writes yet (T6).
    errs = al.validate_approval(it)
    document_id = (resolve_parent_document(conn, it["ParentDocID"])
                   if it["ParentDocID"] else None)
    if it["ParentDocID"] and document_id is None:
        errs.append(f"Unknown ParentDocID: {it['ParentDocID']}")
    version_id = None
    if document_id and it["ParentVersion"] and not errs:
        version_id = resolve_parent_version(conn, document_id, it["ParentVersion"])
        if version_id is None:
            errs.append(f"Unknown ParentVersion {it['ParentVersion']} for"
                        f" {it['ParentDocID']}")
    approver = (person_id_by_email(conn, it["ApproverEmail"])
                if it["ApproverEmail"] else None)
    if it["ApproverEmail"] and not approver:
        errs.append(f"Approver {it['ApproverEmail']} not in person directory")
    if errs:
        return _error(g, M365["approval_list_id"], it, errs, dry, "approval")
    return (f"DRY approval item {it['item_id']}: {it['SignatureMeaning']} on"
            f" {it['ParentDocID']} v{it['ParentVersion']}; no writes (stub)")


def _rows_as_dicts(conn, sql, params=()):
    """Execute sql, return list of dicts keyed by column name.

    This helper avoids repeating the cur.description zip pattern for the
    build_baseline_snapshot SELECTs. The same pattern is already used in
    synced_map(); we factor it here for reuse across snapshot types.
    """
    cur = conn.execute(sql, params)
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def project_phase(conn, project_id):
    """Return the current lifecycle_phase string for a project, or None."""
    row = conn.execute(
        "SELECT lifecycle_phase FROM pmbok.project WHERE project_id=%s",
        (project_id,)).fetchone()
    return row[0] if row else None


def build_baseline_snapshot(conn, project_id, baseline_type):
    """Read live tables and call the pure assembler for the given baseline type.

    Returns the assembled snapshot dict (no writes). Raises ValueError for an
    unrecognised baseline_type so callers get a clear error, not a silent None.

    Schedule: joins schedule_activity -> wbs_element for activities; reads
      milestone for milestones; reads planned_start/planned_finish from project.
    Budget: reads budget_total from project; joins budget_line_item -> wbs_element
      for lines.
    Scope: reads project_charter for the charter row (one or None).
      scope_inclusion, scope_exclusion, acceptance_criterion each link via
      scope_statement (scope_id). We join scope_statement -> scope_* child tables
      via scope_statement.project_id = %s. If a project has no scope_statement
      row, the join yields [] for each child, which the assembler accepts fine.
      (scope_statement.project_id exists in db/02_pmbok.sql; the child tables
      scope_inclusion, scope_exclusion, acceptance_criterion link via scope_id
      which is scope_statement.scope_id — a standard 1:N pattern.)
    """
    if baseline_type not in al.BASELINE_TYPES:
        raise ValueError(f"Unknown baseline_type: {baseline_type!r}")

    if baseline_type == "Schedule":
        activities = _rows_as_dicts(
            conn,
            "SELECT a.activity_code, a.name, a.start_planned, a.finish_planned,"
            "       a.duration_days"
            " FROM pmbok.schedule_activity a"
            " JOIN pmbok.wbs_element w USING (wbs_element_id)"
            " WHERE w.project_id=%s",
            (project_id,))
        milestones = _rows_as_dicts(
            conn,
            "SELECT name, baseline_date"
            " FROM pmbok.milestone WHERE project_id=%s",
            (project_id,))
        headline_rows = _rows_as_dicts(
            conn,
            "SELECT planned_start, planned_finish"
            " FROM pmbok.project WHERE project_id=%s",
            (project_id,))
        headline = headline_rows[0] if headline_rows else {}
        return al.assemble_schedule_snapshot(activities, milestones, headline)

    if baseline_type == "Budget":
        budget_rows = _rows_as_dicts(
            conn,
            "SELECT budget_total FROM pmbok.project WHERE project_id=%s",
            (project_id,))
        budget_total = budget_rows[0]["budget_total"] if budget_rows else None
        lines = _rows_as_dicts(
            conn,
            "SELECT w.wbs_code, b.category, b.total, b.funding_source"
            " FROM pmbok.budget_line_item b"
            " JOIN pmbok.wbs_element w USING (wbs_element_id)"
            " WHERE w.project_id=%s",
            (project_id,))
        return al.assemble_budget_snapshot(budget_total, lines)

    # baseline_type == "Scope"
    charter_rows = _rows_as_dicts(
        conn,
        "SELECT business_case, high_level_in_scope, high_level_out_scope"
        " FROM pmbok.project_charter WHERE project_id=%s",
        (project_id,))
    charter = charter_rows[0] if charter_rows else None
    # scope_inclusion / scope_exclusion / acceptance_criterion link via
    # scope_statement (scope_id FK). We join through scope_statement on
    # project_id. If no scope_statement exists, each child query returns [].
    inclusions = _rows_as_dicts(
        conn,
        "SELECT si.sequence, si.item"
        " FROM pmbok.scope_inclusion si"
        " JOIN pmbok.scope_statement ss USING (scope_id)"
        " WHERE ss.project_id=%s",
        (project_id,))
    exclusions = _rows_as_dicts(
        conn,
        "SELECT se.sequence, se.item"
        " FROM pmbok.scope_exclusion se"
        " JOIN pmbok.scope_statement ss USING (scope_id)"
        " WHERE ss.project_id=%s",
        (project_id,))
    acceptance = _rows_as_dicts(
        conn,
        "SELECT ac.sequence, ac.criterion"
        " FROM pmbok.acceptance_criterion ac"
        " JOIN pmbok.scope_statement ss USING (scope_id)"
        " WHERE ss.project_id=%s",
        (project_id,))
    return al.assemble_scope_snapshot(charter, inclusions, exclusions, acceptance)


def process_baseline(conn, g, it, dry, current):
    errs = al.validate_baseline(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    baselined_by = (person_id_by_email(conn, it["BaselinedByEmail"])
                    if it["BaselinedByEmail"] else None)
    if it["BaselinedByEmail"] and not baselined_by:
        errs.append(f"BaselinedBy {it['BaselinedByEmail']} not in person directory")
    # Resolve linked CR if provided
    linked_cr_id = None
    if it.get("LinkedCRCode"):
        if proj and not errs:
            cr_row = conn.execute(
                "SELECT cr_id FROM pmbok.change_request"
                " WHERE project_id=%s AND cr_code=%s",
                (proj[0], it["LinkedCRCode"])).fetchone()
            if cr_row:
                linked_cr_id = cr_row[0]
            else:
                errs.append(f"Unknown LinkedCRCode: {it['LinkedCRCode']}")
    if errs:
        return _error(g, M365["baseline_list_id"], it, errs, dry, "baseline")
    project_id, _dept = proj
    item_id = it["item_id"]

    # ---- current (already synced) branch: append-once, immutable ----
    if current:
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["baseline_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "baseline")
        # Heal write-back if SyncStatus or BaselineVersion is out of sync.
        if (it["SyncStatus"] != "Synced"
                or it.get("BaselineVersion") != current["version"]):
            if not dry:
                writeback(g, M365["baseline_list_id"], item_id,
                          {"SyncStatus": "Synced", "SyncMessage": "",
                           "BaselineVersion": current["version"]})
            return f"OK baseline item {item_id}: healed write-back"
        return (f"OK baseline item {item_id}: no change"
                " (baselines are immutable; create a new baseline to re-baseline)")

    # ---- new (current is None) branch: create ----
    existing_versions = [r[0] for r in conn.execute(
        "SELECT version FROM pmbok.project_baseline"
        " WHERE project_id=%s AND baseline_type=%s",
        (project_id, it["BaselineType"])).fetchall()]
    version = al.next_baseline_version(existing_versions)
    if dry:
        return (f"DRY baseline item {item_id}: would create"
                f" {it['BaselineType']} v{version} ({it['ProjectCode']})")

    snapshot = build_baseline_snapshot(conn, project_id, it["BaselineType"])
    baseline_id = str(uuid.uuid5(NS, f"thg/artifact/baseline/{item_id}"))

    with conn.transaction():
        if version != "1.0":
            # Supersede the prior BASELINED row
            prior_row = conn.execute(
                "SELECT baseline_id FROM pmbok.project_baseline"
                " WHERE project_id=%s AND baseline_type=%s AND status='BASELINED'",
                (project_id, it["BaselineType"])).fetchone()
            if prior_row:
                prior_id = prior_row[0]
                conn.execute(
                    "UPDATE pmbok.project_baseline"
                    " SET status='SUPERSEDED', superseded_by_baseline_id=%s"
                    " WHERE baseline_id=%s",
                    (baseline_id, prior_id))
                audit_lib.write_trail(
                    conn, baselined_by, "BASELINE_SUPERSEDE",
                    "project_baseline", prior_id,
                    {"status": "BASELINED"}, {"status": "SUPERSEDED"}, None)

        conn.execute(
            "INSERT INTO pmbok.project_baseline"
            " (baseline_id, project_id, baseline_type, version, status,"
            "  change_summary, change_class, linked_cr_id, snapshot,"
            "  baselined_by_person_id, external_ref)"
            " VALUES (%s,%s,%s,%s,'BASELINED',%s,%s,%s,%s,%s,%s)",
            (baseline_id, project_id, it["BaselineType"], version,
             it.get("ChangeSummary"), None, linked_cr_id,
             Jsonb(snapshot), baselined_by, item_id))
        audit_lib.write_trail(
            conn, baselined_by, "BASELINE_CREATE", "project_baseline",
            baseline_id, None,
            {"baseline_type": it["BaselineType"], "version": version}, None)

    writeback(g, M365["baseline_list_id"], item_id,
              {"SyncStatus": "Synced", "SyncMessage": "",
               "BaselineVersion": version})
    return (f"OK new baseline {it['BaselineType']} v{version}"
            f" ({it['ProjectCode']}, item {item_id})")


def process_phase_gate(conn, g, it, dry, current):
    """Apply a phase-gate decision (the process_triage analog).

    Append-once like a baseline: the phase_gate_log row (external_ref = List
    item id) is the idempotency anchor. A Synced gate is never re-applied — the
    project was already advanced when it first synced. A Held (or same-phase
    Approved) records a log row with from==to and does NOT touch the project. A
    forward Approved advances pmbok.project.lifecycle_phase, inserts the log
    row, and writes a PHASE_GATE audit entry — all in one transaction.
    """
    errs = al.validate_phase_gate(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    approver = (person_id_by_email(conn, it["ApprovedByEmail"])
                if it["ApprovedByEmail"] else None)
    if it["ApprovedByEmail"] and not approver:
        errs.append(f"ApprovedBy {it['ApprovedByEmail']} not in person directory")
    if errs:
        return _error(g, M365["phase_gate_list_id"], it, errs, dry, "phase_gate")
    project_id, _dept = proj
    item_id = it["item_id"]

    # from_phase = the project's CURRENT lifecycle_phase (the gate's origin).
    from_phase = project_phase(conn, project_id)

    # ---- current (already synced) branch: append-once anchor ----
    # The log row is the idempotency anchor; a synced gate already advanced the
    # project when it first applied, so it is never re-applied here.
    if current:
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["phase_gate_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "phase_gate")
        if it["SyncStatus"] != "Synced":
            if not dry:
                writeback(g, M365["phase_gate_list_id"], item_id,
                          {"SyncStatus": "Synced", "SyncMessage": ""})
            return f"OK phase_gate item {item_id}: healed write-back"
        return f"OK phase_gate item {item_id}: no change"

    # ---- new (current is None) branch: compute legality + apply ----
    to_phase = it["TargetPhase"]
    dec = it["GateDecision"]

    # Defensive: from_phase comes from the DB; the domain is aligned now, so a
    # miss here should not happen — surface it rather than mis-rank.
    if from_phase not in al.PHASE_ORDER:
        return _error(g, M365["phase_gate_list_id"], it,
                      [f"Project lifecycle_phase {from_phase!r} not a known phase"],
                      dry, "phase_gate")

    if dec == "Held":
        # A hold stays put — record from==to. Always legal.
        to_phase = from_phase
    else:
        # Approved / Approved with conditions: forward-only.
        if al.PHASE_ORDER[to_phase] < al.PHASE_ORDER[from_phase]:
            return _error(g, M365["phase_gate_list_id"], it,
                          [f"Backward phase transition rejected:"
                           f" {from_phase} -> {to_phase}"], dry, "phase_gate")
        # PHASE_ORDER[to_phase] == PHASE_ORDER[from_phase] falls through as a
        # no-op (already there); '>' is a real forward advance.

    record_only = to_phase == from_phase  # Held OR same-phase Approved

    if dry:
        if record_only:
            return (f"DRY phase_gate item {item_id}: would record {dec}"
                    f" at {from_phase}")
        return (f"DRY phase_gate item {item_id}: would move"
                f" {from_phase} -> {to_phase} ({it['ProjectCode']})")

    phase_gate_id = str(uuid.uuid5(NS, f"thg/artifact/phasegate/{item_id}"))
    row = al.build_phase_gate_row(it, project_id, from_phase, to_phase, approver)

    if record_only:
        # No project change — just log the gate (Held or same-phase Approved).
        with conn.transaction():
            conn.execute(
                "INSERT INTO pmbok.phase_gate_log"
                " (phase_gate_id, project_id, from_phase, to_phase,"
                "  gate_decision, approved_by_person_id, decided_at,"
                "  gate_notes, external_ref)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (phase_gate_id, row["project_id"], row["from_phase"],
                 row["to_phase"], row["gate_decision"],
                 row["approved_by_person_id"], row["decided_at"],
                 row["gate_notes"], item_id))
            audit_lib.write_trail(
                conn, approver, "PHASE_GATE_HOLD", "phase_gate_log",
                phase_gate_id, {"lifecycle_phase": from_phase},
                {"lifecycle_phase": from_phase}, None)
        writeback(g, M365["phase_gate_list_id"], item_id,
                  {"SyncStatus": "Synced", "SyncMessage": ""})
        return f"OK phase_gate item {item_id}: recorded {dec} at {from_phase}"

    # Forward advance: UPDATE project + INSERT log + audit in one transaction.
    with conn.transaction():
        conn.execute(
            "UPDATE pmbok.project SET lifecycle_phase=%s, updated_at=now()"
            " WHERE project_id=%s", (to_phase, project_id))
        conn.execute(
            "INSERT INTO pmbok.phase_gate_log"
            " (phase_gate_id, project_id, from_phase, to_phase,"
            "  gate_decision, approved_by_person_id, decided_at,"
            "  gate_notes, external_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (phase_gate_id, row["project_id"], row["from_phase"],
             row["to_phase"], row["gate_decision"],
             row["approved_by_person_id"], row["decided_at"],
             row["gate_notes"], item_id))
        audit_lib.write_trail(
            conn, approver, "PHASE_GATE", "phase_gate_log", phase_gate_id,
            {"lifecycle_phase": from_phase}, {"lifecycle_phase": to_phase},
            None)
    writeback(g, M365["phase_gate_list_id"], item_id,
              {"SyncStatus": "Synced", "SyncMessage": ""})
    return f"OK phase_gate item {item_id}: moved {from_phase} -> {to_phase}"


ARTIFACTS = [
    {"kind": "risk", "list_key": "risk_list_id", "fields": RISK_FIELDS,
     "normalize": normalize_risk, "process": process_risk,
     "select": RISK_SELECT},
    {"kind": "milestone", "list_key": "milestone_list_id",
     "fields": MILESTONE_FIELDS, "normalize": normalize_milestone,
     "process": process_milestone, "select": MILESTONE_SELECT},
    {"kind": "report", "list_key": "status_report_list_id",
     "fields": REPORT_FIELDS, "normalize": normalize_report,
     "process": process_report, "select": REPORT_SELECT},
    {"kind": "activity", "list_key": "activity_list_id",
     "fields": ACTIVITY_FIELDS, "normalize": normalize_activity,
     "process": process_activity, "select": ACTIVITY_SELECT},
    {"kind": "change_request", "list_key": "change_request_list_id",
     "fields": CR_FIELDS, "normalize": normalize_change_request,
     "process": process_change_request, "select": CR_SELECT},
    {"kind": "impact_assessment", "list_key": "impact_assessment_list_id",
     "fields": IMPACT_FIELDS, "normalize": normalize_impact_assessment,
     "process": process_impact_assessment, "select": IMPACT_SELECT},
    {"kind": "decision", "list_key": "decision_list_id",
     "fields": DECISION_FIELDS, "normalize": normalize_decision,
     "process": process_decision, "select": DECISION_SELECT},
    {"kind": "baseline", "list_key": "baseline_list_id",
     "fields": BASELINE_FIELDS, "normalize": normalize_baseline,
     "process": process_baseline, "select": BASELINE_SELECT},
    {"kind": "phase_gate", "list_key": "phase_gate_list_id",
     "fields": PHASE_GATE_FIELDS, "normalize": normalize_phase_gate,
     "process": process_phase_gate, "select": PHASE_GATE_SELECT},
    {"kind": "document", "list_key": "document_list_id",
     "fields": DOC_FIELDS, "normalize": normalize_document,
     "process": process_document, "select": DOC_SELECT},
    {"kind": "raci", "list_key": "raci_list_id",
     "fields": RACI_FIELDS, "normalize": normalize_raci,
     "process": process_raci_assignment, "select": RACI_SELECT},
    {"kind": "version", "list_key": "version_list_id",
     "fields": VERSION_FIELDS, "normalize": normalize_version,
     "process": process_document_version, "select": VERSION_SELECT},
    {"kind": "approval", "list_key": "approval_list_id",
     "fields": APPROVAL_FIELDS, "normalize": normalize_approval,
     "process": process_document_approval, "select": APPROVAL_SELECT},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = Graph()
    people = SitePeople(g, M365["site_id"])
    results, orphans = [], []
    # autocommit: bare SELECTs run autonomously, so a transient DB error on one
    # item cannot leave the connection INERROR and poison the rest of the batch;
    # each conn.transaction() block is a real per-item COMMIT (report rows stay
    # atomic with their 9 areas inside one block).
    with psycopg.connect(host=PG["server"], dbname=PG["database"],
                         user=PG["user"], password=PG["password"],
                         sslmode="require", autocommit=True) as conn:
        # Build area_map once: external_ref -> {knowledge_area: status}.
        # Used by process_report to detect per-area changes without re-querying.
        area_map = {}
        for ref, ka, status in conn.execute(AREA_SELECT).fetchall():
            area_map.setdefault(ref, {})[ka] = status

        for art in ARTIFACTS:
            raw = fetch_items(g, M365[art["list_key"]], art["fields"])
            print(f"{art['kind']}: {len(raw)} list item(s) fetched")
            items = [art["normalize"](i, people) for i in raw]
            synced = synced_map(conn, art["kind"], art["select"])

            # Activity: build wbs_map/wbs_code_map per project (read-only in T4).
            activity_wbs_map = {}
            activity_wbs_code_map = {}
            if art["kind"] == "activity":
                by_project = {}
                for it in items:
                    pc = it["ProjectCode"]
                    if pc:
                        by_project.setdefault(pc, []).append(it)
                for pc, acts in by_project.items():
                    proj = project_by_code(conn, pc)
                    if not proj:
                        continue  # unknown ProjectCode: processor will surface the error
                    project_id, _dept = proj
                    wm, wcm = reconcile_wbs(conn, project_id, pc, acts, args.dry_run)
                    for key, val in wm.items():
                        activity_wbs_map[(pc, key[0], key[1])] = val
                    for key, val in wcm.items():
                        activity_wbs_code_map[(pc, key[0], key[1])] = val

            seen = set()
            for it in items:
                seen.add(it["item_id"])
                try:
                    kwargs = {}
                    if art["kind"] == "report":
                        kwargs["area_map"] = area_map
                    if art["kind"] == "activity":
                        pc = it["ProjectCode"]
                        kwargs["wbs_map"] = {
                            (k[1], k[2]): v
                            for k, v in activity_wbs_map.items()
                            if k[0] == pc
                        }
                        kwargs["wbs_code_map"] = {
                            (k[1], k[2]): v
                            for k, v in activity_wbs_code_map.items()
                            if k[0] == pc
                        }
                    results.append(art["process"](conn, g, it, args.dry_run,
                                                  synced.get(it["item_id"]),
                                                  **kwargs))
                except Exception as e:  # one item must not kill the batch
                    results.append(f"ERROR {art['kind']} item {it['item_id']}: "
                                   f"{type(e).__name__}: {e}")
            for ref in sorted(set(synced) - seen, key=str):
                orphans.append(f"INFO orphaned external_ref {art['kind']}/{ref}: "
                               "List row deleted; DB row kept (system of record)")
    for r in results:
        print(" ", r)
    for o in orphans:
        print(" ", o)
    bad = [r for r in results if r.startswith("ERROR")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
