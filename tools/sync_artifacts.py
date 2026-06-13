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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_lib as al
from graph_client import Graph, SitePeople

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PG = json.load(open(os.path.join(ROOT, "db", ".pg.local.json")))
M365 = json.load(open(os.path.join(ROOT, "db", ".m365.local.json")))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

HEALTH_FIELDS = ",".join(f"{ka}Health" for ka in al.KNOWLEDGE_AREAS)
RISK_FIELDS = ("Title,ProjectCode,Category,Description,Trigger,Likelihood,"
               "Impact,ResponseType,RiskOwner,RiskOwnerLookupId,DueDate,"
               "RiskStatus,ResidualScore,ComplianceFlag,RiskCode,"
               "SyncStatus,SyncMessage")
MILESTONE_FIELDS = ("Title,ProjectCode,BaselineDate,ForecastDate,ActualDate,"
                    "MilestoneStatus,OwnerRole,SyncStatus,SyncMessage")
REPORT_FIELDS = ("Title,ProjectCode,PeriodStart,PeriodEnd,OverallStatus,Trend,"
                 "ExecutiveSummary,DecisionsNeeded,SubmittedBy,"
                 "SubmittedByLookupId," + HEALTH_FIELDS + ",SyncStatus,SyncMessage")


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
                 ' decisions_needed, submitted_by_person_id'
                 ' FROM pmbok.status_report WHERE external_ref IS NOT NULL')


# ---- processors (T5: stubs - validate/resolve and report intent only) -------

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
    if current:
        return f"DRY risk item {it['item_id']}: existing (update path lands in T6/T7)"
    return f"DRY risk item {it['item_id']}: would create (project {it['ProjectCode']})"
    # TODO(T6): insert + write-back; TODO(T7): compare/update/heal


def process_milestone(conn, g, it, dry, current):
    errs = al.validate_milestone(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    if errs:
        return _error(g, M365["milestone_list_id"], it, errs, dry, "milestone")
    if current:
        return f"DRY milestone item {it['item_id']}: existing (update path lands in T6/T7)"
    return f"DRY milestone item {it['item_id']}: would create ({it['Title']})"
    # TODO(T6)/TODO(T7) as above


def process_report(conn, g, it, dry, current):
    errs = al.validate_status_report(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    submitter = (person_id_by_email(conn, it["SubmittedByEmail"])
                 or person_id_by_email(conn, it["CreatedByEmail"]))
    if not errs and not submitter:
        errs.append("SubmittedBy not in person directory")
    if errs:
        return _error(g, M365["status_report_list_id"], it, errs, dry, "report")
    if current:
        return f"DRY report item {it['item_id']}: existing (update path lands in T6/T7)"
    return (f"DRY report item {it['item_id']}: would create report + "
            f"{len(al.KNOWLEDGE_AREAS)} areas ({it['ProjectCode']} "
            f"{it['PeriodStart']}..{it['PeriodEnd']})")
    # TODO(T6)/TODO(T7) as above


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
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = Graph()
    people = SitePeople(g, M365["site_id"])
    results, orphans = [], []
    with psycopg.connect(host=PG["server"], dbname=PG["database"],
                         user=PG["user"], password=PG["password"],
                         sslmode="require") as conn:
        for art in ARTIFACTS:
            raw = fetch_items(g, M365[art["list_key"]], art["fields"])
            print(f"{art['kind']}: {len(raw)} list item(s) fetched")
            items = [art["normalize"](i, people) for i in raw]
            synced = synced_map(conn, art["kind"], art["select"])
            seen = set()
            for it in items:
                seen.add(it["item_id"])
                try:
                    results.append(art["process"](conn, g, it, args.dry_run,
                                                  synced.get(it["item_id"])))
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
