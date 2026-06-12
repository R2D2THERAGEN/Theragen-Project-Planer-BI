# tools/create_intake_list.py
"""One-time: create the 'Project Intake' SharePoint List on the root site with
typed columns, and persist site/list ids to db/.m365.local.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graph_client import Graph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "db", ".m365.local.json")
LIST_NAME = "Project Intake"

DEPARTMENTS = ["Clinical / Medical Affairs", "Regulatory / Quality",
               "R&D / Engineering", "Operations / PMO", "Finance / Procurement",
               "Commercial / Marketing", "IT / Data / Security", "HR / People"]
REQUEST_TYPES = ["Project / Initiative", "Clinical or study request",
                 "Cross-dept work request", "System change",
                 "Vendor / procurement", "Other"]
EFFORTS = ["Small (<4 wk)", "Medium (1-3 mo)", "Large (3-12 mo)", "Program (>12 mo)"]
TRIAGE = ["Submitted", "Approved", "Rejected", "On Hold"]
SYNC = ["Pending", "Synced", "Error"]


def choice(name, choices, default=None):
    col = {"name": name, "choice": {"allowTextEntry": False, "choices": choices,
                                    "displayAs": "dropDownMenu"}}
    if default:
        col["defaultValue"] = {"value": default}
    return col


COLUMNS = [
    choice("RequestType", REQUEST_TYPES),
    choice("Department", DEPARTMENTS),
    {"name": "BusinessProblem", "text": {"allowMultipleLines": True}},
    {"name": "DesiredOutcome", "text": {"allowMultipleLines": True}},
    {"name": "Sponsor", "personOrGroup": {"allowMultipleSelection": False}},
    {"name": "ProjectManager", "personOrGroup": {"allowMultipleSelection": False}},
    {"name": "PlannedStart", "dateTime": {"format": "dateOnly"}},
    {"name": "PlannedFinish", "dateTime": {"format": "dateOnly"}},
    {"name": "EstimatedBudget", "number": {"decimalPlaces": "two"}},
    choice("EffortBucket", EFFORTS),
    {"name": "PHIFlag", "boolean": {}},
    {"name": "CFR11Flag", "boolean": {}},
    {"name": "ClinicalFlag", "boolean": {}},
    {"name": "VendorFlag", "boolean": {}},
    {"name": "DataSharingFlag", "boolean": {}},
    {"name": "StrategicObjective", "text": {}},
    choice("TriageStatus", TRIAGE, default="Submitted"),
    {"name": "IntakeID", "text": {}},
    {"name": "ProjectCode", "text": {}},
    choice("SyncStatus", SYNC, default="Pending"),
    {"name": "SyncMessage", "text": {"allowMultipleLines": True}},
]


def main():
    g = Graph()
    site = g.get("/sites/root")
    site_id = site["id"]
    existing = g.get(f"/sites/{site_id}/lists", **{"$filter": f"displayName eq '{LIST_NAME}'"})
    if existing.get("value"):
        lst = existing["value"][0]
        print(f"List already exists: {lst['id']}")
    else:
        lst = g.post(f"/sites/{site_id}/lists", {
            "displayName": LIST_NAME,
            "description": "Theragen project intake (SOP-002). Synced to PostgreSQL daily.",
            "columns": COLUMNS,
            "list": {"template": "genericList"},
        })
        print(f"List created: {lst['id']}")
    json.dump({"site_id": site_id, "list_id": lst["id"], "list_name": LIST_NAME},
              open(CFG_PATH, "w", encoding="utf-8"), indent=2)
    print(f"config written: {CFG_PATH}")
    cols = g.get(f"/sites/{site_id}/lists/{lst['id']}/columns")
    names = {c["name"] for c in cols["value"]}
    missing = [c["name"] for c in COLUMNS if c["name"] not in names]
    print("column check:", "OK all present" if not missing else f"MISSING {missing}")


if __name__ == "__main__":
    main()
