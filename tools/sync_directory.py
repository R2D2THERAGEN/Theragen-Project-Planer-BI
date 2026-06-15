# tools/sync_directory.py
"""Org-directory sync (sub-stage D, D-T5).

Pulls the Entra enabled-member roster (graph_directory), filters it to the staff
domains, then:
  1. upserts doc_mgmt.person  -- new staff INSERTed (Unassigned dept), matched
     persons enriched with upn/entra_object_id/job_title/active/source='entra'
     (a curated department_id is never overwritten); entra-sourced rows that left
     the roster are deactivated (active=false, never deleted);
  2. seeds the "Staff Directory" List -- one item per staff person (create-if-
     absent; the PMO's Department choice is never overwritten);
  3. reads the curated Department back -> person.department_id.

The department is NOT taken from Entra (87% blank); it is curated in the List.

    python tools/sync_directory.py --dry-run   # report intent, no writes
    python tools/sync_directory.py             # live
"""
import argparse
import datetime
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_lib as al           # noqa: E402
# psycopg, graph_client, graph_directory are imported lazily inside main() so the
# pure helpers below (and their unit tests) don't pay the psycopg/msal import cost.

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = uuid.NAMESPACE_URL
STAFF_DOMAINS = ["theragen.com", "actastim.com"]


def _cfg(name):
    return json.load(open(os.path.join(ROOT, "db", name), encoding="utf-8"))


# --- pure decision logic (unit-tested) --------------------------------------
def domain_of(email):
    e = (email or "").lower()
    return e.rsplit("@", 1)[-1] if "@" in e else ""


def filter_staff(roster, domains):
    """Keep only roster users whose mail/UPN domain is in `domains`."""
    ds = {d.lower() for d in domains}
    return [u for u in roster
            if domain_of(u.get("mail") or u.get("userPrincipalName")) in ds]


def classify_persons(staff, existing_by_email):
    """staff: Entra user dicts; existing_by_email: {email_lower: {person_id, source}}.
    Returns (to_insert, to_enrich, to_deactivate):
      to_insert     = staff users whose email is new to person,
      to_enrich     = [(user, person_id)] for staff matching an existing person,
      to_deactivate = [person_id] that are source='entra' but no longer in staff."""
    staff_emails, to_insert, to_enrich = set(), [], []
    for u in staff:
        email = al.normalize_email(u.get("mail") or u.get("userPrincipalName"))
        if not email:
            continue
        staff_emails.add(email)
        ex = existing_by_email.get(email)
        (to_enrich.append((u, ex["person_id"])) if ex else to_insert.append(u))
    to_deactivate = [v["person_id"] for e, v in existing_by_email.items()
                     if v.get("source") == "entra" and e not in staff_emails]
    return to_insert, to_enrich, to_deactivate


def person_id_for(u):
    return str(uuid.uuid5(NS, "thg/person/" + (u.get("id") or
               al.normalize_email(u.get("mail") or u.get("userPrincipalName")))))


# --- Graph List helpers ------------------------------------------------------
def _list_items(g, site, list_id, select, base):
    """All items of a List, with fields($select=...); follows @odata.nextLink."""
    out = []
    path = f"/sites/{site}/lists/{list_id}/items"
    params = {"$expand": f"fields($select={select})", "$top": "500"}
    while path:
        page = g.get(path, **params)
        out.extend(page.get("value", []))
        nxt = page.get("@odata.nextLink", "")
        path = nxt.replace(base, "") if nxt else ""
        params = {}
    return out


# --- main --------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    dry = args.dry_run
    today = datetime.date.today().isoformat()
    PG, M365 = _cfg(".pg.local.json"), _cfg(".m365.local.json")
    import psycopg
    import graph_directory as gd
    from graph_client import Graph

    roster = gd.pull_roster()
    staff = filter_staff(roster, STAFF_DOMAINS)
    print(f"roster: {len(roster)} enabled members -> {len(staff)} staff "
          f"(domains: {', '.join(STAFF_DOMAINS)})")

    with psycopg.connect(host=PG["server"], dbname=PG["database"], user=PG["user"],
                         password=PG["password"], sslmode="require",
                         autocommit=True, connect_timeout=30) as conn:
        unas_id = conn.execute(
            "SELECT department_id FROM doc_mgmt.department WHERE code='UNAS'").fetchone()[0]
        existing = {}
        for r in conn.execute(
                "SELECT person_id, LOWER(email), source FROM doc_mgmt.person").fetchall():
            existing[r[1]] = {"person_id": r[0], "source": r[2]}
        to_insert, to_enrich, to_deactivate = classify_persons(staff, existing)
        print(f"person: {len(to_insert)} new, {len(to_enrich)} enrich, "
              f"{len(to_deactivate)} deactivate")

        if not dry:
            for u in to_insert:
                row = al.build_person_directory_row(u, unas_id, today)
                conn.execute(
                    "INSERT INTO doc_mgmt.person (person_id, email, display_name, upn,"
                    " entra_object_id, job_title, active, source, department_id,"
                    " employment_type, start_date) VALUES"
                    " (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (person_id_for(u), row["email"], row["display_name"], row["upn"],
                     row["entra_object_id"], row["job_title"], row["active"],
                     row["source"], row["department_id"], row["employment_type"],
                     row["start_date"]))
            for u, pid in to_enrich:
                row = al.build_person_directory_row(u, unas_id, today)
                conn.execute(
                    "UPDATE doc_mgmt.person SET upn=%s, entra_object_id=%s,"
                    " job_title=%s, active=%s, source='entra' WHERE person_id=%s",
                    (row["upn"], row["entra_object_id"], row["job_title"],
                     row["active"], pid))
            for pid in to_deactivate:
                conn.execute("UPDATE doc_mgmt.person SET active=FALSE WHERE person_id=%s", (pid,))

        # --- Staff Directory List: seed create-if-absent ---------------------
        g = Graph()
        site, lid = M365["site_id"], M365["staff_directory_list_id"]
        items = _list_items(g, site, lid, "UPN,Department", gd.BASE)
        have_upn = {al.normalize_upn((it.get("fields") or {}).get("UPN")) for it in items}
        to_seed = [u for u in staff
                   if al.normalize_upn(u.get("userPrincipalName")) not in have_upn]
        print(f"staff directory list: {len(items)} existing items, {len(to_seed)} to seed")
        if not dry:
            for u in to_seed:
                g.post(f"/sites/{site}/lists/{lid}/items", {"fields": {
                    "UPN": al.normalize_upn(u.get("userPrincipalName")),
                    "DisplayName": (u.get("displayName") or "").strip(),
                    "Active": "Yes" if u.get("accountEnabled") else "No",
                    "JobTitle": (u.get("jobTitle") or ""),
                    "SyncStatus": "Synced"}})

        # --- read curated Department back -> person.department_id -------------
        assigned = 0
        for it in items:
            f = it.get("fields") or {}
            dept = (f.get("Department") or "").strip()
            upn = al.normalize_upn(f.get("UPN"))
            if not dept or dept == al.UNASSIGNED_DEPARTMENT or not upn:
                continue
            did = conn.execute("SELECT department_id FROM doc_mgmt.department WHERE name=%s",
                               (dept,)).fetchone()
            if not did:
                continue
            assigned += 1
            if not dry:
                conn.execute("UPDATE doc_mgmt.person SET department_id=%s"
                             " WHERE LOWER(upn)=%s OR LOWER(email)=%s", (did[0], upn, upn))
        print(f"department read-back: {assigned} curated assignment(s)"
              f"{' (dry-run, not applied)' if dry else ''}")

    print("DRY-RUN - no writes." if dry else "done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
