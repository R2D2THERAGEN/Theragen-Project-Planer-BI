# tools/create_artifact_lists.py
"""One-time: create the four execution-artifact Lists on the root site and
merge their ids into db/.m365.local.json (preserving the intake keys)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_lib as al
from graph_client import Graph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "db", ".m365.local.json")


def choice(name, choices, default=None, allow_text=False):
    col = {"name": name, "choice": {"allowTextEntry": allow_text,
                                    "choices": choices,
                                    "displayAs": "dropDownMenu"}}
    if default:
        col["defaultValue"] = {"value": default}
    return col


def text(name, multiline=False):
    return {"name": name, "text": ({"allowMultipleLines": True} if multiline else {})}


def date_only(name):
    return {"name": name, "dateTime": {"format": "dateOnly"}}


BOOKKEEPING = [
    choice("SyncStatus", ["Pending", "Synced", "Error"], default="Pending"),
    text("SyncMessage", multiline=True),
]

LISTS = {
    "risk_list_id": ("Project Risks", [
        text("ProjectCode"),
        choice("Category", al.RISK_CATEGORIES),
        text("Description", multiline=True),
        text("Trigger", multiline=True),
        choice("Likelihood", ["1", "2", "3", "4", "5"]),
        choice("Impact", ["1", "2", "3", "4", "5"]),
        choice("ResponseType", al.RESPONSE_TYPES),
        {"name": "RiskOwner", "personOrGroup": {"allowMultipleSelection": False}},
        date_only("DueDate"),
        choice("RiskStatus", al.RISK_STATUSES, default="Open"),
        {"name": "ResidualScore", "number": {"decimalPlaces": "none"}},
        choice("ComplianceFlag", al.COMPLIANCE_FLAGS, default="None"),
        text("RiskCode"),
    ] + BOOKKEEPING),
    "milestone_list_id": ("Project Milestones", [
        text("ProjectCode"),
        date_only("BaselineDate"),
        date_only("ForecastDate"),
        date_only("ActualDate"),
        choice("MilestoneStatus", al.MILESTONE_STATUSES, default="On track"),
        choice("OwnerRole", ["Project Manager", "Sponsor", "Workstream Lead",
                             "Work Package Owner"],
               default="Project Manager", allow_text=True),
    ] + BOOKKEEPING),
    "status_report_list_id": ("Project Status Reports", [
        text("ProjectCode"),
        date_only("PeriodStart"),
        date_only("PeriodEnd"),
        choice("OverallStatus", al.RAG, default="Green"),
        choice("Trend", al.TRENDS, default="Steady"),
        text("ExecutiveSummary", multiline=True),
        text("DecisionsNeeded", multiline=True),
        {"name": "SubmittedBy", "personOrGroup": {"allowMultipleSelection": False}},
    ] + [choice(f"{ka}Health", al.RAG, default="Green")
         for ka in al.KNOWLEDGE_AREAS] + [
        {"name": "ApprovedBy", "personOrGroup": {"allowMultipleSelection": False}},
        date_only("ApprovedDate"),
    ] + BOOKKEEPING),
    "activity_list_id": ("Project Activities", [
        text("ProjectCode"),
        text("Workstream"),
        text("WorkPackage"),
        date_only("StartPlanned"),
        date_only("FinishPlanned"),
        date_only("StartActual"),
        date_only("FinishActual"),
        {"name": "Owner", "personOrGroup": {"allowMultipleSelection": False}},
        choice("Department", al.DEPARTMENTS),
        choice("ActivityStatus", al.ACTIVITY_STATUSES, default="Not started"),
        {"name": "PctComplete", "number": {"decimalPlaces": "none"}},
        text("ActivityCode"),
    ] + BOOKKEEPING),
    "change_request_list_id": ("Project Change Requests", [
        text("ProjectCode"),
        date_only("RequestedDate"),
        {"name": "RequestedBy", "personOrGroup": {"allowMultipleSelection": False}},
        choice("CRClass", al.CR_CLASSES),
        choice("ChangeType", al.CHANGE_TYPES),
        text("AffectedArtifacts", multiline=True),
        text("Description", multiline=True),
        text("Reason", multiline=True),
        text("ImpactScope", multiline=True),
        text("ImpactQuality", multiline=True),
        {"name": "ImpactScheduleDays", "number": {"decimalPlaces": "none"}},
        {"name": "ImpactCost", "number": {"decimalPlaces": "two"}},
        text("IntakeID"),
        choice("Decision", al.CR_DECISIONS, default="Pending"),
        {"name": "DecidedBy", "personOrGroup": {"allowMultipleSelection": False}},
        date_only("DecidedDate"),
        choice("ImplementationVerified", ["Yes", "No"], default="No"),
        choice("LinkedArtifactsUpdated", ["Yes", "No"], default="No"),
        choice("CRStatus", al.CR_STATUSES, default="Open"),
        text("CRCode"),
    ] + BOOKKEEPING),
    "decision_list_id": ("Project Decisions", [
        text("ProjectCode"),
        text("Rationale", multiline=True),
        {"name": "DecidedBy", "personOrGroup": {"allowMultipleSelection": False}},
        date_only("DecidedDate"),
        text("DecisionCode"),
    ] + BOOKKEEPING),
    "baseline_list_id": ("Project Baselines", [
        text("ProjectCode"),
        choice("BaselineType", al.BASELINE_TYPES),
        text("ChangeSummary", multiline=True),
        text("LinkedCRCode"),
        {"name": "BaselinedBy", "personOrGroup": {"allowMultipleSelection": False}},
        text("BaselineVersion"),
    ] + BOOKKEEPING),
    "phase_gate_list_id": ("Project Phase Gates", [
        text("ProjectCode"),
        choice("TargetPhase", al.LIFECYCLE_PHASES),
        choice("GateDecision", al.GATE_DECISIONS, default="Approved"),
        {"name": "ApprovedBy", "personOrGroup": {"allowMultipleSelection": False}},
        date_only("DecidedDate"),
        text("GateNotes", multiline=True),
    ] + BOOKKEEPING),
    "impact_assessment_list_id": ("Change Impact Assessments", [
        text("ProjectCode"),
        text("ParentCRCode"),
        choice("Department", al.DEPARTMENTS),
        text("ScopeImpact", multiline=True),
        {"name": "ScheduleImpactDays", "number": {"decimalPlaces": "none"}},
        {"name": "CostImpact", "number": {"decimalPlaces": "two"}},
        text("QualityImpact", multiline=True),
        {"name": "SubmittedBy", "personOrGroup": {"allowMultipleSelection": False}},
        date_only("SubmittedDate"),
    ] + BOOKKEEPING),
    "document_list_id": ("Controlled Documents", [
        choice("DocTypeCode", al.DOC_TYPE_CODES),
        text("Title"),
        text("Subtitle"),
        choice("PrimaryDepartment", al.DEPARTMENTS),
        {"name": "Owner", "personOrGroup": {"allowMultipleSelection": False}},
        {"name": "Approver", "personOrGroup": {"allowMultipleSelection": False}},
        choice("LifecyclePhase", al.DOC_LIFECYCLE_PHASES),
        choice("Status", al.DOC_STATUSES, default="DRAFT"),
        choice("ReviewCycle", al.REVIEW_CYCLES),
        choice("Classification", al.DOC_CLASSIFICATIONS),
        choice("StorageSystem", al.STORAGE_SYSTEMS),
        text("StoragePath"),
        date_only("NextReviewDue"),
        text("IntakeID"),
        text("DocID"),
    ] + BOOKKEEPING),
    "govcr_list_id": ("Governance Change Requests", [
        text("ParentDocID"),  # the target controlled document (no ProjectCode)
        date_only("RequestedDate"),
        {"name": "RequestedBy", "personOrGroup": {"allowMultipleSelection": False}},
        choice("CRClass", al.CR_CLASSES),
        text("Description", multiline=True),
        text("Reason", multiline=True),
        text("IntakeID"),
        choice("Decision", al.CR_DECISIONS, default="Pending"),
        {"name": "DecidedBy", "personOrGroup": {"allowMultipleSelection": False}},
        date_only("DecidedDate"),
        choice("ImplementationVerified", ["Yes", "No"], default="No"),
        choice("CRStatus", al.CR_STATUSES, default="Open"),
        text("CRCode"),
    ] + BOOKKEEPING),
    "govassessment_list_id": ("Governance Change Assessments", [
        text("ParentCRCode"),  # the governance CR (CHG-NNN), globally unique
        choice("Department", al.DEPARTMENTS),
        text("ImpactSummary", multiline=True),
        text("ComplianceImpact", multiline=True),
        date_only("SubmittedDate"),
    ] + BOOKKEEPING),
    "raci_list_id": ("Document RACI", [
        text("ParentDocID"),
        choice("Department", al.DEPARTMENTS),
        choice("Role", al.RACI_ROLES),
        text("Touchpoint", multiline=True),
        date_only("ValidFrom"),
        date_only("ValidTo"),
    ] + BOOKKEEPING),
    "version_list_id": ("Document Versions", [
        text("ParentDocID"),
        text("Version"),
        choice("Status", al.DOC_STATUSES, default="DRAFT"),
        text("ChangeSummary", multiline=True),
        choice("ChangeClass", al.CR_CLASSES),
        date_only("EffectiveDate"),
        text("StoragePath"),
        {"name": "Author", "personOrGroup": {"allowMultipleSelection": False}},
        text("LinkedCRCode"),  # 2c-6 loop closure: cite the governance CR (CHG-NNN)
    ] + BOOKKEEPING),
    "approval_list_id": ("Document Approvals (e-sig)", [
        text("ParentDocID"),
        text("ParentVersion"),
        {"name": "Approver", "personOrGroup": {"allowMultipleSelection": False}},
        choice("SignatureMeaning", al.SIGNATURE_MEANINGS, default="Approval"),
        text("Reason", multiline=True),
    ] + BOOKKEEPING),
}


def main():
    g = Graph()
    cfg = json.load(open(CFG_PATH, encoding="utf-8"))
    site_id = cfg["site_id"]
    for key, (name, columns) in LISTS.items():
        existing = g.get(f"/sites/{site_id}/lists",
                         **{"$filter": f"displayName eq '{name}'"})
        if existing.get("value"):
            lst = existing["value"][0]
            print(f"{name}: already exists ({lst['id']})")
        else:
            lst = g.post(f"/sites/{site_id}/lists", {
                "displayName": name,
                "description": f"Theragen {name.lower()} - synced to PostgreSQL daily.",
                "columns": columns,
                "list": {"template": "genericList"},
            })
            print(f"{name}: created ({lst['id']})")
        cfg[key] = lst["id"]
        # Ensure every declared column exists on the live list (idempotent).
        # Built-in SharePoint columns (id, Title, Modified, Created, Author, Editor,
        # _UIVersionString, Attachments, Edit, LinkTitleNoMenu, LinkTitle,
        # DocIcon, ItemChildCount, FolderChildCount, _ComplianceFlags,
        # _ComplianceTag, _ComplianceTagWrittenTime, _ComplianceTagUserId,
        # AppAuthor, AppEditor) are never in our column dicts so they are never
        # re-posted.  The GET returns all columns; we only POST ones whose name
        # is absent from the live list.
        live_cols = g.get(f"/sites/{site_id}/lists/{lst['id']}/columns")
        live_names = {c["name"] for c in live_cols["value"]}
        added = []
        for col in columns:
            if col["name"] not in live_names:
                g.post(f"/sites/{site_id}/lists/{lst['id']}/columns", col)
                added.append(col["name"])
        if added:
            print(f"  columns added: {added}")
        else:
            print(f"  columns: OK all present")
    json.dump(cfg, open(CFG_PATH, "w", encoding="utf-8"), indent=2)
    print(f"config merged: {CFG_PATH}")


if __name__ == "__main__":
    main()
