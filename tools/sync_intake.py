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
from graph_client import Graph

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

# --- Person-field resolution --------------------------------------------------
# LookupId (numeric string) -> lower-case email, populated once per run.
_user_cache: dict[str, str] = {}


def _load_user_cache(g):
    """Populate _user_cache from the site's User Information List (once per run).

    The UIL is a hidden list not returned by the default /lists endpoint;
    it requires an explicit $filter on displayName to be found.
    Items carry Id (numeric string), EMail, and UserName fields.
    """
    if _user_cache:
        return
    site = M365["site_id"]
    # Locate the hidden User Information List via explicit filter.
    lists = g.get(f"/sites/{site}/lists",
                  **{"$filter": "displayName eq 'User Information List'",
                     "$select": "id,displayName"})
    uil_id = next((l["id"] for l in lists.get("value", [])), None)
    if not uil_id:
        print("WARNING: User Information List not found - person fields will be empty",
              file=sys.stderr)
        return
    # Fetch all user entries; Id is the SharePoint LookupId.
    url = f"/sites/{site}/lists/{uil_id}/items"
    params = {"$expand": "fields($select=Id,EMail,UserName)", "$top": "500"}
    while url:
        page = g.get(url, **params)
        for item in page.get("value", []):
            f = item.get("fields", {})
            lid = str(f.get("Id") or item.get("id") or "").strip()
            email = (f.get("EMail") or f.get("UserName") or "").lower().strip()
            if lid and email:
                _user_cache[lid] = email
        url = page.get("@odata.nextLink", "")
        if url:
            url = url.replace("https://graph.microsoft.com/v1.0", "")
            params = {}


def _coerce_bool(v):
    """Graph booleans are JSON true/false; non-UI writers may send strings."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() not in ("", "0", "false", "no")
    return bool(v)


def person_email(lookup_id_str, g):
    """Resolve a SharePoint LookupId string to an e-mail address.

    Graph person fields arrive as plain display-name strings when requested
    by column name (e.g. 'Sponsor': 'Richard Allen'), but the companion
    LookupId field (e.g. 'SponsorLookupId': '485') gives the numeric site
    user id needed to look up the actual e-mail in the User Information List.
    """
    lid = str(lookup_id_str or "").strip()
    if not lid:
        return ""
    _load_user_cache(g)
    return _user_cache.get(lid, "")


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


def normalize(item, g):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "RequestType": f.get("RequestType") or "",
        "Department": f.get("Department") or "",
        "BusinessProblem": f.get("BusinessProblem") or "",
        "DesiredOutcome": f.get("DesiredOutcome") or "",
        "SponsorEmail": person_email(f.get("SponsorLookupId"), g),
        "ProjectManagerEmail": person_email(f.get("ProjectManagerLookupId"), g),
        "PlannedStart": (f.get("PlannedStart") or "")[:10] or None,
        "PlannedFinish": (f.get("PlannedFinish") or "")[:10] or None,
        "EstimatedBudget": f.get("EstimatedBudget"),
        "EffortBucket": f.get("EffortBucket") or "Large (3-12 mo)",
        "Flags": {k: _coerce_bool(f.get(k)) for k in
                  ("PHIFlag", "CFR11Flag", "ClinicalFlag", "VendorFlag",
                   "DataSharingFlag")},
        "StrategicObjective": f.get("StrategicObjective") or None,
        "TriageStatus": f.get("TriageStatus") or "Submitted",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


# TODO(Task 6): branch on `dry` - real writes land here; DRY prefix only when dry.
def process_new(conn, g, it, dry):
    errs = il.validate_item(it)
    if errs:
        return f"ERROR item {it['item_id']}: " + "; ".join(errs)
    return f"DRY new item {it['item_id']}: would create intake+project ({it['Title']})"


def process_triage(conn, g, it, dry):
    return f"DRY triage item {it['item_id']}: status {it['TriageStatus']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = Graph()
    with psycopg.connect(host=PG["server"], dbname=PG["database"],
                         user=PG["user"], password=PG["password"],
                         sslmode="require") as conn:
        raw_items = fetch_items(g)
        print(f"{len(raw_items)} list item(s) fetched")

        items = [normalize(i, g) for i in raw_items]

        synced = dict(conn.execute(
            "SELECT external_ref, intake_id FROM doc_mgmt.intake_submission "
            "WHERE external_ref IS NOT NULL").fetchall())

        results = []
        for it in items:
            if it["item_id"] not in synced:
                results.append(process_new(conn, g, it, args.dry_run))
            else:
                results.append(process_triage(conn, g, it, args.dry_run))
    for r in results:
        print(" ", r)
    bad = [r for r in results if r.startswith("ERROR")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
