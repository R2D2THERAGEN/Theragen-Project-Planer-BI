# tools/create_artifact_lists.py
"""One-time: create the three execution-artifact Lists on the root site and
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
         for ka in al.KNOWLEDGE_AREAS] + BOOKKEEPING),
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
        cols = g.get(f"/sites/{site_id}/lists/{lst['id']}/columns")
        names = {c["name"] for c in cols["value"]}
        missing = [c["name"] for c in columns if c["name"] not in names]
        print(f"  columns: {'OK all present' if not missing else f'MISSING {missing}'}")
    json.dump(cfg, open(CFG_PATH, "w", encoding="utf-8"), indent=2)
    print(f"config merged: {CFG_PATH}")


if __name__ == "__main__":
    main()
