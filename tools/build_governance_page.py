"""Emit the interactive Governance report page (PBIR) + the status-page
sign-off card.

Writes only NEW files (a new page folder + visual.json files); pages.json is
patched separately with the Edit tool. Mirrors the existing report's visual
schemas exactly: card / slicer use visualContainer/2.10.0, tableEx uses 1.0.0.
Run: python tools/build_governance_page.py  (then validate with tools/validate_pbir.py)
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RPT = os.path.join(ROOT, "Theragen Project Planner.Report", "definition", "pages")

SCHEMA_VC = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json"
SCHEMA_TBL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.0.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.0.0/schema.json"


def _col(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                       "Property": prop}}


def _measure(prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}},
                        "Property": prop}}


def _title(text):
    return {"title": [{"properties": {
        "show": {"expr": {"Literal": {"Value": "true"}}},
        "text": {"expr": {"Literal": {"Value": f"'{text}'"}}}}}]}


def card(name, measure, title, x, y, w, h):
    return name, {
        "$schema": SCHEMA_VC, "name": name,
        "position": {"x": x, "y": y, "z": 1000, "width": w, "height": h},
        "visual": {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": [
                {"field": _measure(measure), "queryRef": f"_Measures.{measure}"}]}}},
            "objects": {
                "labels": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "13D"}}}}}],
                "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}],
            },
            "visualContainerObjects": _title(title),
            "drillFilterOtherVisuals": True,
        },
    }


def table(name, entity, columns, title, x, y, w, h, sort_prop, desc=False):
    projections = [{"field": _col(entity, p), "queryRef": f"{entity}.{p}"} for p in columns]
    return name, {
        "$schema": SCHEMA_TBL, "name": name,
        "position": {"x": x, "y": y, "z": 1000, "width": w, "height": h},
        "visual": {
            "visualType": "tableEx",
            "query": {
                "queryState": {"Values": {"projections": projections}},
                "sortDefinition": {"sort": [{
                    "field": _col(entity, sort_prop),
                    "direction": "Descending" if desc else "Ascending"}],
                    "isDefaultSort": True},
            },
            "drillFilterOtherVisuals": True,
            "visualContainerObjects": _title(title),
        },
    }


def slicer(name, entity, prop, title, x, y, w, h):
    return name, {
        "$schema": SCHEMA_VC, "name": name,
        "position": {"x": x, "y": y, "z": 1000, "width": w, "height": h},
        "visual": {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [
                {"field": _col(entity, prop), "queryRef": f"{entity}.{prop}", "active": True}]}}},
            "objects": {
                "header": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
                "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}],
            },
            "visualContainerObjects": _title(title),
            "drillFilterOtherVisuals": True,
        },
        "filterConfig": {"filters": [{
            "name": f"{name}flt", "field": _col(entity, prop), "type": "Categorical"}]},
    }


def write_visual(page, name, payload):
    d = os.path.join(RPT, page, "visuals", name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "visual.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main():
    # ---- page def ----
    os.makedirs(os.path.join(RPT, "governance"), exist_ok=True)
    with open(os.path.join(RPT, "governance", "page.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema": SCHEMA_PAGE, "name": "governance",
                   "displayName": "Governance & Documents",
                   "displayOption": "FitToPage", "height": 720, "width": 1280}, f, indent=2)

    visuals = [
        slicer("govDocSlicer", "Controlled Document", "Doc ID", "Select document", 8, 8, 240, 72),
        card("govKpiCRs", "Governance CRs", "Governance CRs", 256, 8, 196, 72),
        card("govKpiApproved", "Approved Governance CRs", "Approved", 456, 8, 196, 72),
        card("govKpiDocs", "Controlled Documents", "Documents", 656, 8, 196, 72),
        card("govKpiVersions", "Document Versions", "Versions", 856, 8, 196, 72),
        card("govKpiApprovals", "Document Approvals", "Attestations", 1056, 8, 208, 72),
        table("govTblCRs", "Governance Change Request",
              ["CR Code", "Doc ID", "Doc Title", "CR Class", "Requested By",
               "Decision", "Decided By", "Status"],
              "Governance change requests", 8, 88, 1264, 300, "CR Code"),
        table("govTblDocs", "Controlled Document",
              ["Doc ID", "Title", "Document Type", "Status", "Current Version",
               "Owner", "Next Review Due"],
              "Controlled documents", 8, 396, 628, 316, "Doc ID"),
        table("govTblVersions", "Document Version",
              ["Doc ID", "Version", "Status", "Author", "Linked CR", "Effective Date"],
              "Document versions (with linked CR)", 644, 396, 628, 316, "Doc ID"),
    ]
    for name, payload in visuals:
        write_visual("governance", name, payload)
    print(f"  governance page + {len(visuals)} visuals")

    # ---- status-page sign-off card (closes the pre-existing 2b gap) ----
    _, signoff = card("statusSignoffRate", "Sign-off Rate", "Report Sign-off Rate",
                      1007, 84, 119, 72)
    write_visual("status", "statusSignoffRate", signoff)
    print("  status sign-off card")


if __name__ == "__main__":
    main()
