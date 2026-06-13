# tools/sync_intake.py
"""Daily M365 -> PostgreSQL intake sync (spec: 2026-06-12-project-ingestion).

Reads Project Intake List items, creates intake + Proposed project + charter
rows for new submissions, applies triage status transitions for existing ones,
and writes results back onto the List. Idempotent via
intake_submission.external_ref = List item id. --dry-run prints intent only.
"""
import argparse
import datetime
import json
import os
import sys
import uuid

import psycopg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intake_lib as il
from graph_client import Graph, SitePeople, coerce_bool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PG = json.load(open(os.path.join(ROOT, "db", ".pg.local.json")))
M365 = json.load(open(os.path.join(ROOT, "db", ".m365.local.json")))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# ADAPTATION (discovered 2026-06-12): Graph returns person columns two ways
# depending on how they are selected:
#   - Without $select: person fields are absent from the response entirely.
#   - With $select=Sponsor:  returns "Sponsor": "Display Name" (plain string).
#   - With $select=SponsorLookupId: returns "SponsorLookupId": "485" (numeric string).
# We request both so we have the LookupId for email resolution via the
# User Information List, which requires an explicit $filter to discover.
FIELDS = ("Title,RequestType,Department,BusinessProblem,DesiredOutcome,"
          "Sponsor,SponsorLookupId,ProjectManager,ProjectManagerLookupId,"
          "PlannedStart,PlannedFinish,EstimatedBudget,"
          "EffortBucket,PHIFlag,CFR11Flag,ClinicalFlag,VendorFlag,"
          "DataSharingFlag,StrategicObjective,TriageStatus,IntakeID,"
          "ProjectCode,SyncStatus,SyncMessage")


def fetch_items(g):
    site, lst = M365["site_id"], M365["list_id"]
    url = f"/sites/{site}/lists/{lst}/items"
    out, params = [], {"$expand": f"fields($select={FIELDS})", "$top": "200"}
    while url:
        page = g.get(url, **params)
        out += page.get("value", [])
        url = page.get("@odata.nextLink", "")
        if url:
            url = url.replace("https://graph.microsoft.com/v1.0", "")
            params = {}
    return out


def normalize(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "RequestType": f.get("RequestType") or "",
        "Department": f.get("Department") or "",
        "BusinessProblem": f.get("BusinessProblem") or "",
        "DesiredOutcome": f.get("DesiredOutcome") or "",
        "SponsorEmail": people.email(f.get("SponsorLookupId")),
        "ProjectManagerEmail": people.email(f.get("ProjectManagerLookupId")),
        "PlannedStart": (f.get("PlannedStart") or "")[:10] or None,
        "PlannedFinish": (f.get("PlannedFinish") or "")[:10] or None,
        "EstimatedBudget": f.get("EstimatedBudget"),
        "EffortBucket": f.get("EffortBucket") or "Large (3-12 mo)",  # spec default when the choice is blank
        "Flags": {k: coerce_bool(f.get(k)) for k in
                  ("PHIFlag", "CFR11Flag", "ClinicalFlag", "VendorFlag",
                   "DataSharingFlag")},
        "StrategicObjective": f.get("StrategicObjective") or None,
        "TriageStatus": f.get("TriageStatus") or "Submitted",
        "SyncStatus": f.get("SyncStatus") or "Pending",
        "IntakeID": f.get("IntakeID") or "",
        "ProjectCode": f.get("ProjectCode") or "",
    }


def writeback(g, item_id, fields):
    g.patch(f"/sites/{M365['site_id']}/lists/{M365['list_id']}/items/{item_id}/fields",
            fields)


def person_id_by_email(conn, email):
    row = conn.execute("SELECT person_id FROM doc_mgmt.person WHERE lower(email)=%s",
                       (email,)).fetchone()
    return row[0] if row else None


def process_new(conn, g, it, dry):
    errs = il.validate_item(it)
    sponsor = person_id_by_email(conn, it["SponsorEmail"]) if it["SponsorEmail"] else None
    pm = person_id_by_email(conn, it["ProjectManagerEmail"]) if it["ProjectManagerEmail"] else None
    if it["SponsorEmail"] and not sponsor:
        errs.append(f"Sponsor {it['SponsorEmail']} not in person directory")
    if it["ProjectManagerEmail"] and not pm:
        errs.append(f"PM {it['ProjectManagerEmail']} not in person directory")
    if errs:
        msg = "; ".join(errs)
        if not dry:
            writeback(g, it["item_id"], {"SyncStatus": "Error", "SyncMessage": msg})
        return f"ERROR item {it['item_id']}: {msg}"

    year = datetime.date.today().year
    existing_intakes = [r[0] for r in conn.execute(
        "SELECT intake_id FROM doc_mgmt.intake_submission").fetchall()]
    intake_id = il.next_intake_id(existing_intakes, year)
    dept = conn.execute("SELECT department_id, code FROM doc_mgmt.department "
                        "WHERE name=%s", (it["Department"],)).fetchone()
    if not dept:
        msg = f"Unknown department: {it['Department']}"
        if not dry:
            writeback(g, it["item_id"], {"SyncStatus": "Error", "SyncMessage": msg})
        return f"ERROR item {it['item_id']}: {msg}"
    dept_id, dept_code = dept
    existing_codes = [r[0] for r in conn.execute(
        "SELECT project_code FROM pmbok.project").fetchall()]
    project_code = il.next_project_code(dept_code, existing_codes)
    project_id = str(uuid.uuid5(NS, f"thg/project/{project_code}"))

    if dry:
        return (f"DRY item {it['item_id']}: would create {intake_id} / "
                f"{project_code} ({it['Title']})")

    # sponsor/pm are guaranteed non-None here: validate_item rejects blank
    # emails and the directory-miss guards above return before this point.
    with conn.transaction():
        conn.execute(
            "INSERT INTO doc_mgmt.intake_submission (intake_submission_id, intake_id,"
            " submitted_at, requester_person_id, requesting_department_id,"
            " request_title, request_type, business_problem, desired_outcome,"
            " effort, budget_envelope, phi_flag, cfr11_flag, clinical_flag,"
            " vendor_flag, data_sharing_flag, external_ref)"
            " VALUES (%s,%s,now(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(uuid.uuid5(NS, f"thg/intake/{intake_id}")), intake_id, sponsor,
             dept_id, it["Title"][:200], it["RequestType"], it["BusinessProblem"],
             it["DesiredOutcome"], it["EffortBucket"],
             il.derive_envelope(it["EstimatedBudget"]),
             it["Flags"]["PHIFlag"], it["Flags"]["CFR11Flag"],
             it["Flags"]["ClinicalFlag"], it["Flags"]["VendorFlag"],
             it["Flags"]["DataSharingFlag"], it["item_id"]))
        conn.execute(
            "INSERT INTO pmbok.project (project_id, project_code, intake_id, name,"
            " description, sponsor_person_id, project_manager_id,"
            " primary_department, approach, lifecycle_phase, status,"
            " planned_start, planned_finish, budget_total, strategic_objective_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'predictive','Initiating','Proposed',"
            " %s,%s,%s,%s)",
            (project_id, project_code, intake_id, it["Title"][:200],
             it["BusinessProblem"], sponsor, pm, it["Department"],
             it["PlannedStart"], it["PlannedFinish"], it["EstimatedBudget"],
             it["StrategicObjective"]))
        conn.execute(
            "INSERT INTO pmbok.project_charter (charter_id, project_id, doc_id,"
            " business_case, high_level_in_scope, pm_authority_text)"
            " VALUES (%s,%s,%s,%s,'Per approved scope baseline.',"
            " 'Authority per the Theragen project charter standard.')",
            (str(uuid.uuid5(NS, f"thg/charter/{project_code}")), project_id,
             "THG-CHR-" + project_code[4:], it["DesiredOutcome"]))
    writeback(g, it["item_id"], {"SyncStatus": "Synced", "SyncMessage": "",
                                 "IntakeID": intake_id, "ProjectCode": project_code})
    return f"OK new {intake_id} / {project_code} ({it['Title']})"


def process_triage(conn, g, it, dry):
    target = il.triage_to_status(it["TriageStatus"])
    if target is None:
        msg = f"Unknown TriageStatus: {it['TriageStatus']}"
        if not dry:
            writeback(g, it["item_id"], {"SyncStatus": "Error", "SyncMessage": msg})
        return f"ERROR item {it['item_id']}: {msg}"
    row = conn.execute(
        "SELECT p.project_id, p.status, p.project_code, i.intake_id"
        " FROM pmbok.project p"
        " JOIN doc_mgmt.intake_submission i ON i.intake_id = p.intake_id"
        " WHERE i.external_ref = %s", (it["item_id"],)).fetchone()
    if not row:
        msg = "synced intake has no project row"
        if not dry:
            writeback(g, it["item_id"], {"SyncStatus": "Error", "SyncMessage": msg})
        return f"ERROR item {it['item_id']}: {msg}"
    project_id, current, project_code, intake_id = row
    ids = {"IntakeID": intake_id, "ProjectCode": project_code}
    if current == target:
        # Heal a lost write-back (DB committed but the PATCH failed last run).
        if it["SyncStatus"] != "Synced" or it["IntakeID"] != intake_id \
                or it["ProjectCode"] != project_code:
            if not dry:
                writeback(g, it["item_id"], {"SyncStatus": "Synced",
                                             "SyncMessage": "", **ids})
            return f"OK item {it['item_id']}: healed write-back (status already {current})"
        return f"OK item {it['item_id']}: status already {current}"
    if dry:
        return f"DRY item {it['item_id']}: would move {current} -> {target}"
    with conn.transaction():
        conn.execute(
            "UPDATE pmbok.project SET status=%s,"
            " actual_start = CASE WHEN %s='Active' AND actual_start IS NULL"
            " THEN CURRENT_DATE ELSE actual_start END WHERE project_id=%s",
            (target, target, project_id))
    writeback(g, it["item_id"], {"SyncStatus": "Synced",
                                 "SyncMessage": f"Status -> {target}", **ids})
    return f"OK triage item {it['item_id']}: {current} -> {target}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = Graph()
    people = SitePeople(g, M365["site_id"])
    # autocommit: bare SELECTs run autonomously, so a transient DB error on one
    # item cannot leave the connection INERROR and poison the rest of the batch;
    # each conn.transaction() block below is a real per-item COMMIT.
    with psycopg.connect(host=PG["server"], dbname=PG["database"],
                         user=PG["user"], password=PG["password"],
                         sslmode="require", autocommit=True) as conn:
        raw_items = fetch_items(g)
        print(f"{len(raw_items)} list item(s) fetched")

        items = [normalize(i, people) for i in raw_items]

        synced = dict(conn.execute(
            "SELECT external_ref, intake_id FROM doc_mgmt.intake_submission "
            "WHERE external_ref IS NOT NULL").fetchall())

        results = []
        for it in items:
            try:
                if it["item_id"] not in synced:
                    results.append(process_new(conn, g, it, args.dry_run))
                else:
                    results.append(process_triage(conn, g, it, args.dry_run))
            except Exception as e:  # one item's Graph/DB hiccup must not kill the batch
                results.append(f"ERROR item {it['item_id']}: {type(e).__name__}: {e}")
    for r in results:
        print(" ", r)
    bad = [r for r in results if r.startswith("ERROR")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
