"""Provision the THG-ENT-DBS-001 schemas and load SampleData into PostgreSQL.

Steps (idempotent - drops and recreates the three schemas):
  1. Execute db/01_dm.sql, db/02_pmbok.sql, db/03_bi_views.sql
  2. Load SampleData CSVs into the spec tables in FK order, synthesizing the
     DM spine rows the spec requires (role catalog, intake submissions,
     project charters carrying business_value as business_case)
  3. Verify: spec-table row counts vs CSVs, and one probe row per bi view

Connection comes from db/.pg.local.json (gitignored).
"""
import csv
import json
import os
import sys
import uuid
from datetime import date, timedelta

import psycopg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "db", ".pg.local.json")))
DATA = os.path.join(ROOT, "SampleData")
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def uid(kind, key):
    return str(uuid.uuid5(NS, f"thg/{kind}/{key}"))


def rows(name):
    with open(os.path.join(DATA, f"{name}.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            yield {k: (v if v != "" else None) for k, v in r.items()}


def to_bool(v):
    return None if v is None else v.upper() == "TRUE"


def insert(cur, table, cols, data):
    if not data:
        return 0
    ph = ", ".join(["%s"] * len(cols))
    collist = ", ".join(f'"{c}"' if c == "trigger" else c for c in cols)
    cur.executemany(f"INSERT INTO {table} ({collist}) VALUES ({ph})",
                    [[row.get(c2, None) for c2 in cols] for row in data])
    return len(data)


def main():
    # This loader DROPS and recreates all three schemas. Once real intakes
    # exist, an accidental run is data loss - require explicit intent.
    if "--reseed" not in sys.argv:
        sys.exit("Refusing to run: this is a destructive reseed. "
                 "Pass --reseed and confirm interactively.")
    try:
        typed = input(f"Type the database name ({CFG['database']}) to confirm wipe: ")
    except EOFError:
        sys.exit("Non-interactive stdin - refusing destructive reseed.")
    if typed.strip() != CFG["database"]:
        sys.exit("Confirmation mismatch - aborting.")

    conn = psycopg.connect(host=CFG["server"], dbname=CFG["database"],
                           user=CFG["user"], password=CFG["password"],
                           sslmode="require")
    cur = conn.cursor()

    # ---- DDL (fresh) ------------------------------------------------------
    cur.execute("DROP SCHEMA IF EXISTS bi CASCADE; "
                "DROP SCHEMA IF EXISTS pmbok CASCADE; "
                "DROP SCHEMA IF EXISTS doc_mgmt CASCADE;")
    for f in ("01_dm.sql", "02_pmbok.sql", "03_bi_views.sql", "04_foreign_keys.sql",
              "05_intake_external_ref.sql", "06_artifact_external_ref.sql",
              "07_activity_external_ref.sql", "08_change_request_external_ref.sql",
              "09_decision_external_ref.sql", "10_status_report_signoff.sql"):
        sql = open(os.path.join(ROOT, "db", f), encoding="utf-8").read()
        cur.execute(sql)
        print(f"executed {f}")
    conn.commit()

    counts = {}

    # ---- DM seeds ---------------------------------------------------------
    dept = list(rows("department"))
    for d in dept:
        d["active"] = to_bool(d["active"])
    counts["doc_mgmt.department"] = insert(
        cur, "doc_mgmt.department", ["department_id", "code", "name", "active"], dept)
    dept_id_by_name = {d["name"]: d["department_id"] for d in dept}

    people = list(rows("person"))
    roles = sorted({p["role_title"] for p in people if p["role_title"]})
    role_rows = [{"role_id": uid("role", r), "name": r} for r in roles]
    counts["doc_mgmt.role"] = insert(cur, "doc_mgmt.role", ["role_id", "name"], role_rows)
    role_id_by_name = {r["name"]: r["role_id"] for r in role_rows}

    for p in people:
        p["department_id"] = dept_id_by_name[p["department_name"]]
        p["role_id"] = role_id_by_name.get(p["role_title"])
        p["active"] = to_bool(p["active"])
    counts["doc_mgmt.person"] = insert(
        cur, "doc_mgmt.person",
        ["person_id", "employee_number", "email", "display_name", "department_id",
         "role_id", "employment_type", "active", "start_date"], people)

    projects = list(rows("project"))
    intakes = []
    for p in projects:
        start = date.fromisoformat(p["planned_start"]) if p["planned_start"] else date(2026, 1, 1)
        budget = float(p["budget_total"] or 0)
        intakes.append({
            "intake_submission_id": uid("intake", p["intake_id"]),
            "intake_id": p["intake_id"],
            "submitted_at": (start - timedelta(days=30)).isoformat(),
            "requester_person_id": p["sponsor_person_id"],
            "requesting_department_id": dept_id_by_name[p["primary_department"]],
            "request_title": p["name"][:200],
            "request_type": "Project / Initiative",
            "business_problem": p["description"] or p["name"],
            "desired_outcome": p["business_value"] or p["name"],
            "effort": "Large (3-12 mo)",
            "budget_envelope": "$250k-1M" if budget > 250000 else "$25-250k",
        })
    counts["doc_mgmt.intake_submission"] = insert(
        cur, "doc_mgmt.intake_submission",
        ["intake_submission_id", "intake_id", "submitted_at", "requester_person_id",
         "requesting_department_id", "request_title", "request_type",
         "business_problem", "desired_outcome", "effort", "budget_envelope"],
        intakes)

    # ---- PMBOK ------------------------------------------------------------
    counts["pmbok.project"] = insert(
        cur, "pmbok.project",
        ["project_id", "project_code", "intake_id", "name", "description",
         "sponsor_person_id", "project_manager_id", "primary_department",
         "approach", "lifecycle_phase", "status", "planned_start",
         "planned_finish", "actual_start", "actual_finish", "budget_total",
         "strategic_objective_ref"], projects)

    charters = [{
        "charter_id": uid("charter", p["project_code"]),
        "project_id": p["project_id"],
        "doc_id": "THG-CHR-" + p["project_code"][4:],
        "business_case": p["business_value"],
        "high_level_in_scope": "Per approved scope baseline.",
        "pm_authority_text": "Authority per the Theragen project charter standard.",
    } for p in projects]
    counts["pmbok.project_charter"] = insert(
        cur, "pmbok.project_charter",
        ["charter_id", "project_id", "doc_id", "business_case",
         "high_level_in_scope", "pm_authority_text"], charters)

    counts["pmbok.wbs_element"] = insert(
        cur, "pmbok.wbs_element",
        ["wbs_element_id", "project_id", "wbs_code", "parent_wbs_element_id",
         "level", "name", "owning_department", "owner_role",
         "estimated_effort_hrs", "estimated_cost"], list(rows("wbs_element")))

    counts["pmbok.schedule_activity"] = insert(
        cur, "pmbok.schedule_activity",
        ["activity_id", "wbs_element_id", "activity_code", "name",
         "start_planned", "finish_planned", "start_actual", "finish_actual",
         "duration_days", "owner_person_id", "department", "status",
         "pct_complete"], list(rows("schedule_activity")))

    counts["pmbok.milestone"] = insert(
        cur, "pmbok.milestone",
        ["milestone_id", "project_id", "name", "baseline_date", "forecast_date",
         "actual_date", "status", "owner_role"], list(rows("milestone")))

    counts["pmbok.budget_line_item"] = insert(
        cur, "pmbok.budget_line_item",
        ["budget_line_id", "wbs_element_id", "category", "labor_amount",
         "materials_amount", "vendor_amount", "other_amount", "subtotal",
         "contingency_pct", "total", "funding_source"],
        list(rows("budget_line_item")))

    counts["pmbok.risk"] = insert(
        cur, "pmbok.risk",
        ["risk_id", "project_id", "risk_code", "category", "description",
         "likelihood", "impact", "score", "response_type", "owner_person_id",
         "department", "due_date", "status", "residual_score",
         "compliance_flag"], list(rows("risk")))

    counts["pmbok.risk_response"] = insert(
        cur, "pmbok.risk_response",
        ["response_id", "risk_id", "action_type", "description",
         "owner_person_id", "due_date", "status"], list(rows("risk_response")))

    crs = list(rows("change_request"))
    for c in crs:
        c["affected_artifacts"] = "Project scope / schedule baseline"
    counts["pmbok.change_request"] = insert(
        cur, "pmbok.change_request",
        ["cr_id", "project_id", "cr_code", "intake_id", "requested_at",
         "requested_by_person_id", "cr_class", "change_types",
         "affected_artifacts", "description", "reason",
         "impact_schedule_days", "impact_cost", "decision",
         "decided_at", "status"], crs)

    counts["pmbok.status_report"] = insert(
        cur, "pmbok.status_report",
        ["report_id", "project_id", "period_start", "period_end",
         "overall_status", "trend", "executive_summary", "decisions_needed",
         "submitted_by_person_id", "submitted_at"], list(rows("status_report")))

    counts["pmbok.status_report_area"] = insert(
        cur, "pmbok.status_report_area",
        ["area_id", "report_id", "knowledge_area", "status", "commentary"],
        list(rows("status_report_area")))

    counts["pmbok.stakeholder"] = insert(
        cur, "pmbok.stakeholder",
        ["stakeholder_id", "project_id", "stk_code", "person_id", "role",
         "department", "engagement", "interest", "influence",
         "communication_preference"], list(rows("stakeholder")))

    counts["pmbok.project_team_member"] = insert(
        cur, "pmbok.project_team_member",
        ["team_member_id", "project_id", "person_id", "role", "department",
         "allocation_pct", "start_date", "end_date"],
        list(rows("project_team_member")))

    counts["pmbok.lesson_learned"] = insert(
        cur, "pmbok.lesson_learned",
        ["lesson_id", "project_id", "category", "lesson", "what_happened",
         "recommendation", "followup_owner_role", "status"],
        list(rows("lesson_learned")))

    closure = list(rows("closure_checklist_item"))
    for c in closure:
        c["done"] = to_bool(c["done"])
    counts["pmbok.closure_checklist_item"] = insert(
        cur, "pmbok.closure_checklist_item",
        ["closure_item_id", "project_id", "item", "owner_role", "done",
         "evidence"], closure)

    conn.commit()

    # ---- verify -----------------------------------------------------------
    print("\nrow counts (loaded -> db):")
    ok = True
    for table, n in counts.items():
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        db_n = cur.fetchone()[0]
        flag = "OK " if db_n == n else "MISMATCH"
        if db_n != n:
            ok = False
        print(f"  {flag} {table}: {n} -> {db_n}")

    print("\nbi view probes:")
    for v in ["project", "schedule_activity", "risk", "status_report",
              "change_request", "knowledge_area"]:
        cur.execute(f"SELECT COUNT(*) FROM bi.{v}")
        print(f"  bi.{v}: {cur.fetchone()[0]} rows")

    cur.close()
    conn.close()
    print("\nLOAD " + ("SUCCEEDED" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
