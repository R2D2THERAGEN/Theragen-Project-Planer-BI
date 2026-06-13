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
ACTIVITY_FIELDS = ("Title,ProjectCode,Workstream,WorkPackage,StartPlanned,"
                   "FinishPlanned,StartActual,FinishActual,Owner,OwnerLookupId,"
                   "Department,ActivityStatus,PctComplete,ActivityCode,"
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
AREA_SELECT = ('SELECT r.external_ref, a.knowledge_area, a.status'
               ' FROM pmbok.status_report_area a'
               ' JOIN pmbok.status_report r ON r.report_id = a.report_id'
               ' WHERE r.external_ref IS NOT NULL')
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
    if errs:
        return _error(g, M365["status_report_list_id"], it, errs, dry, "report")
    project_id, _dept = proj
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
                                      current["submitted_by_person_id"])
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
                        " executive_summary=%s, decisions_needed=%s"
                        " WHERE external_ref=%s",
                        (desired["period_start"], desired["period_end"],
                         desired["overall_status"], desired["trend"],
                         desired["executive_summary"],
                         desired["decisions_needed"], it["item_id"]))
                for ka in areas_changed:
                    conn.execute(
                        "UPDATE pmbok.status_report_area SET status=%s"
                        " WHERE report_id=%s AND knowledge_area=%s",
                        (it["Health"][ka], report_id, ka))
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
    row = al.build_report_row(it, project_id, submitter)
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
                        ws = it["Workstream"]
                        wp = it["WorkPackage"]
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
