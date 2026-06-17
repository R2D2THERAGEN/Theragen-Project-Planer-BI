"""Generate docs/admin-map.md — the platform operations / admin map.

Read-only. For every SharePoint authoring List it maps the full lineage:

    List (live link) -> sync process -> DB table -> bi view -> model table -> measures -> audit

The architecture relationships are a curated registry (SURFACES) — the one place a
human asserts "this List feeds that table/view/model". Live SharePoint display
names + clickable links are resolved via Graph at generation time (graceful
offline fallback to a constructed link). A coverage gate (--audit) fails if any
List in db/.m365.local.json is missing from the map, so the doc can't silently
drift as the platform grows.

Usage:
    python tools/build_admin_map.py            # regenerate docs/admin-map.md
    python tools/build_admin_map.py --audit    # coverage gate; exit 1 if a List is unmapped
    python tools/build_admin_map.py --stdout    # print to stdout instead of writing

See docs/change-control-process.md (this generator is a Documentation-category
change) and docs/artifact-entry-setup.md (the per-List authoring detail).
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
OUT_FILE = REPO_ROOT / "docs" / "admin-map.md"
CONFIG = REPO_ROOT / "db" / ".m365.local.json"
SITE_BASE = "https://neurotechus.sharepoint.com"  # fallback if Graph is unavailable

# --- curated architecture registry ------------------------------------------
# One row per authoring surface. `list_key` MUST match a key in db/.m365.local.json
# (the coverage gate enforces this). `label` is the offline-fallback display name;
# the live name/link come from Graph when available.
SURFACES = [
    {"list_key": "list_id", "label": "Project Intake", "phase": "1",
     "columns": "Title, Project Code, Sponsor, Primary Department, Business Case, Requested Budget",
     "process": "sync_intake.py", "db_table": "doc_mgmt.intake_submission",
     "bi_view": "—", "model_table": "— (approved intake seeds pmbok.project)",
     "measures": "Projects, Active Projects, Portfolio Charter Budget", "audit": "intake decision log"},
    {"list_key": "risk_list_id", "label": "Project Risks", "phase": "1",
     "columns": "Title, Project Code, Category, Likelihood, Impact, Risk Status, Owner, Due Date, Mitigation, Residual Score",
     "process": "process_risk", "db_table": "pmbok.risk", "bi_view": "bi.risk", "model_table": "Risk",
     "measures": "Risks, Open Risks, High/Critical Risks, Total Risk Exposure, Avg Risk Score", "audit": "—"},
    {"list_key": "risk_response_list_id", "label": "Risk Responses", "phase": "post-2c",
     "columns": "Title, Parent Risk Code, Response Strategy, Action Status, Owner, Due Date",
     "process": "process_risk_response", "db_table": "pmbok.risk_response", "bi_view": "bi.risk_response",
     "model_table": "Risk Response", "measures": "Response Actions, Open Response Actions, Mitigation Coverage %",
     "audit": "—"},
    {"list_key": "milestone_list_id", "label": "Project Milestones", "phase": "1",
     "columns": "Title, Project Code, Baseline Date, Actual Date, Milestone Status, Owner",
     "process": "process_milestone", "db_table": "pmbok.milestone", "bi_view": "bi.milestone",
     "model_table": "Milestone", "measures": "Milestones, Milestones Achieved, Milestone Hit Rate, Avg Slip Days",
     "audit": "—"},
    {"list_key": "status_report_list_id", "label": "Project Status Reports", "phase": "1 / 2b",
     "columns": "Title, Project Code, Period End, Overall Status, Trend, area statuses, Submitted By, Approved By/Date",
     "process": "process_report", "db_table": "pmbok.status_report (+ status_report_area)",
     "bi_view": "bi.status_report (+ bi.status_report_area)", "model_table": "Status Report (+ Status Report Area)",
     "measures": "Status Reports, Latest Overall Status, Health Score, Signed-off Reports, Sign-off Rate",
     "audit": "STATUS_SIGNOFF"},
    {"list_key": "activity_list_id", "label": "Project Activities", "phase": "2a",
     "columns": "Title, Project Code, Workstream, Work Package, Start/Finish Planned, Activity Status, Pct Complete, Owner, Department",
     "process": "process_activity", "db_table": "pmbok.schedule_activity (+ derived pmbok.wbs_element)",
     "bi_view": "bi.schedule_activity (+ bi.wbs_element)", "model_table": "Schedule Activity (+ WBS Element)",
     "measures": "Activities, Pct Complete (Duration Wtd), On-Time Completion %, Earned Value, SPI/SV", "audit": "—"},
    {"list_key": "cost_actual_list_id", "label": "Cost Actuals", "phase": "post-2c (EVM)",
     "columns": "Title, Project Code, WBS Code, Amount, Cost Category, Incurred Date, Entered By",
     "process": "process_cost_actual", "db_table": "pmbok.cost_actual", "bi_view": "bi.cost_actual",
     "model_table": "Cost Actual", "measures": "Actual Cost (AC), CPI, EAC, VAC, TCPI", "audit": "—"},
    {"list_key": "change_request_list_id", "label": "Project Change Requests", "phase": "2b",
     "columns": "Project Code, Description, Reason, CR Class, Change Type, Decision, CR Status, Decided By, Impact Days/Cost, Implementation Verified",
     "process": "process_change_request", "db_table": "pmbok.change_request", "bi_view": "bi.change_request",
     "model_table": "Change Request",
     "measures": "Change Requests, Open/Approved/Rejected CRs, CR Approval Rate, Verified CRs, Net Schedule Impact Days",
     "audit": "CR_CREATE, CR_DECISION, CR_STATUS"},
    {"list_key": "impact_assessment_list_id", "label": "Change Impact Assessments", "phase": "2c-2",
     "columns": "Project Code, Parent CR Code, Department, Scope Impact, Schedule Impact Days, Cost Impact, Quality Impact, Submitted By",
     "process": "process_impact_assessment", "db_table": "pmbok.change_impact_assessment",
     "bi_view": "bi.change_impact_assessment", "model_table": "Change Impact Assessment",
     "measures": "Impact Assessments, Assessed CRs, Departments Assessed, Assessed Schedule/Cost Impact", "audit": "—"},
    {"list_key": "decision_list_id", "label": "Project Decisions", "phase": "2b",
     "columns": "Title, Project Code, Rationale, Decided By, Decided Date",
     "process": "process_decision", "db_table": "pmbok.decision", "bi_view": "bi.decision",
     "model_table": "Decision", "measures": "Decisions Logged", "audit": "—"},
    {"list_key": "baseline_list_id", "label": "Project Baselines", "phase": "2c-1",
     "columns": "Project Code, Baseline Type, Change Summary, Linked CR Code, Baselined By (snapshot built server-side)",
     "process": "process_baseline", "db_table": "pmbok.project_baseline", "bi_view": "bi.project_baseline",
     "model_table": "Project Baseline",
     "measures": "Baselines, Current Baselines, Current X Baseline Version, Budget Variance vs Baseline",
     "audit": "BASELINE_CREATE, BASELINE_SUPERSEDE"},
    {"list_key": "phase_gate_list_id", "label": "Project Phase Gates", "phase": "2c-1",
     "columns": "Project Code, Target Phase, Gate Decision, Approved By, Gate Notes",
     "process": "process_phase_gate", "db_table": "pmbok.phase_gate_log (+ updates pmbok.project.lifecycle_phase)",
     "bi_view": "bi.phase_gate_log", "model_table": "Phase Gate Log", "measures": "Phase Gates Passed, Gates Held",
     "audit": "PHASE_GATE, PHASE_GATE_HOLD"},
    {"list_key": "document_list_id", "label": "Controlled Documents", "phase": "2c-3",
     "columns": "Doc Type Code, Title, Primary Department, Owner, Approver, Lifecycle Phase, Status, Review Cycle",
     "process": "process_document", "db_table": "doc_mgmt.document", "bi_view": "bi.document",
     "model_table": "Controlled Document",
     "measures": "Controlled Documents, Draft/Baseline/Retired Documents, Documents Due for Review",
     "audit": "DOCUMENT_CREATE, DOCUMENT_STATUS"},
    {"list_key": "raci_list_id", "label": "Document RACI", "phase": "2c-4",
     "columns": "Parent Doc ID, Department, Role (R/A/C/I), Touchpoint, Valid From/To",
     "process": "process_raci_assignment", "db_table": "doc_mgmt.raci_assignment", "bi_view": "bi.raci_assignment",
     "model_table": "Document RACI", "measures": "RACI Assignments, Documents with RACI, Accountable/Responsible Assignments",
     "audit": "—"},
    {"list_key": "version_list_id", "label": "Document Versions", "phase": "2c-5",
     "columns": "Parent Doc ID, Version, Change Summary, Author, Status, Change Class, Effective Date, Linked CR Code",
     "process": "process_document_version", "db_table": "doc_mgmt.document_version", "bi_view": "bi.document_version",
     "model_table": "Document Version", "measures": "Document Versions, Baseline Versions, Attested Versions",
     "audit": "VERSION_CREATE, VERSION_STATUS"},
    {"list_key": "approval_list_id", "label": "Document Approvals (e-sig)", "phase": "2c-5",
     "columns": "Parent Doc ID, Parent Version, Approver, Signature Meaning, Reason (esig hash + signed_at server-derived)",
     "process": "process_document_approval", "db_table": "doc_mgmt.document_approval", "bi_view": "bi.document_approval",
     "model_table": "Document Approval", "measures": "Document Approvals, Approvals (non-§11 attestation)",
     "audit": "APPROVAL_SIGN"},
    {"list_key": "govcr_list_id", "label": "Governance Change Requests", "phase": "2c-6",
     "columns": "Parent Doc ID, Description, Reason, CR Class, Decision, CR Status, Decided By, Implementation Verified",
     "process": "process_change_request_gov", "db_table": "doc_mgmt.change_request_gov",
     "bi_view": "bi.change_request_gov", "model_table": "Governance Change Request",
     "measures": "Governance CRs, Open/Approved/Verified Governance CRs", "audit": "GOVCR_CREATE, GOVCR_DECISION, GOVCR_STATUS"},
    {"list_key": "govassessment_list_id", "label": "Governance Change Assessments", "phase": "2c-6",
     "columns": "Parent CR Code, Department, Impact Summary, Compliance Impact, Submitted Date",
     "process": "process_change_assessment_gov", "db_table": "doc_mgmt.change_assessment_gov",
     "bi_view": "bi.change_assessment_gov", "model_table": "Governance Change Assessment",
     "measures": "Governance Assessments, Assessed Governance CRs", "audit": "—"},
    {"list_key": "report_access_list_id", "label": "Report Access", "phase": "Compliance (RLS)",
     "columns": "User Email, Scope Type (Project/Department/All), Scope Value, Active, Granted By",
     "process": "process_report_access", "db_table": "pmbok.report_access", "bi_view": "bi.report_access",
     "model_table": "Report Access (disconnected — drives RLS)", "measures": "— (RLS plumbing)",
     "audit": "ACCESS_GRANT, ACCESS_REVOKE, ACCESS_CHANGE"},
    {"list_key": "platform_change_list_id", "label": "Platform Changes", "phase": "Round 2",
     "columns": "Category, Summary, Version, Status, Requested By, Approved By, Git SHA",
     "process": "process_platform_change", "db_table": "pmbok.platform_change", "bi_view": "bi.platform_change",
     "model_table": "Platform Change (disconnected)",
     "measures": "Platform Changes, Approved/Deployed Platform Changes", "audit": "PLATFORM_CHANGE_CREATE, _APPROVE, _DEPLOY"},
    {"list_key": "staff_directory_list_id", "label": "Staff Directory", "phase": "Sub-stage D / E",
     "columns": "UPN, DisplayName, Department + ManagerUPN + Location (PMO-assigned), Active, JobTitle",
     "process": "sync_directory.py (Entra roster via graph_directory)", "db_table": "doc_mgmt.person",
     "bi_view": "bi.org_directory", "model_table": "Directory",
     "measures": "Headcount, Active Staff, Unassigned Staff, Staff with Report Access, Departments Assigned",
     "audit": "—"},
]

SCHEDULED_JOBS = [
    ("`\\Theragen\\SyncIntake`", "05:30 daily", "`tools\\run_intake_sync.cmd` → `sync_intake.py`",
     "Phase-1 intake submissions → `doc_mgmt.intake_submission`"),
    ("`\\Theragen\\SyncArtifacts`", "05:40 daily", "`tools\\run_artifact_sync.cmd` → `sync_artifacts.py`",
     "All Phase-2 authoring Lists → `pmbok.*` / `doc_mgmt.*` (the registry below)"),
    ("Power BI dataset refresh", "~hourly / morning", "Service scheduled refresh / `tools/service_refresh.py`",
     "**Data-only** refresh of the published model (cannot surface schema/model changes)"),
    ("Republish (manual)", "as needed", "Power BI Desktop → Publish",
     "Surfaces **new** tables / columns / measures / descriptions / roles"),
]


# --- pure helpers ------------------------------------------------------------
def list_keys(cfg):
    """The List-reference keys in the M365 config (intake `list_id` + every `*_list_id`)."""
    return [k for k in cfg if k == "list_id" or k.endswith("_list_id")]


def coverage(surfaces, cfg):
    """(unmapped, extra): config List keys with no SURFACES row, and SURFACES rows with no config key."""
    cfg_keys = set(list_keys(cfg))
    surf_keys = {s["list_key"] for s in surfaces}
    return sorted(cfg_keys - surf_keys), sorted(surf_keys - cfg_keys)


def _md(s):
    """Escape a value for a Markdown table cell."""
    if s is None:
        return ""
    return str(s).replace("|", "\\|").replace("\n", " ")


def surface_link(s, resolved):
    """Clickable [name](url): live Graph values when present, else a constructed fallback."""
    name, url = resolved.get(s["list_key"], (None, None))
    name = name or s["label"]
    if not url:
        url = f"{SITE_BASE}/Lists/" + name.replace(" ", "%20")
    return f"[{name}]({url})"


def provenance_header(sha, date, version, n):
    return (f"> Generated by `tools/build_admin_map.py` at `{sha}` ({date}) · platform **v{version}** · "
            f"{n} authoring surfaces  \n"
            f"> **Do not edit by hand** — regenerate after adding a List / table / view "
            f"(see [change-control process](change-control-process.md)).")


def render(surfaces, resolved, header):
    out = ["# Theragen Project Planner — Admin & Operations Map", "", header, ""]
    out.append("The platform is **data-driven**: every authoring surface is a SharePoint List that the "
               "morning sync validates, airlocks, audits, and lands in Azure PostgreSQL, exposed through "
               "`bi.*` views to the Power BI model. This map links each List to its full lineage.")
    out.append("")
    out.append("```")
    out.append("SharePoint List  ──►  sync (Graph read → validate → airlock → audit)  ──►  Azure PostgreSQL")
    out.append("   (the form)            sync_intake.py / sync_artifacts.py              (pmbok.* / doc_mgmt.*)")
    out.append("                                                                                │")
    out.append("   Power BI report  ◄──  semantic model (TMDL)  ◄──  bi.* views  ◄─────────────┘")
    out.append("   + RLS (Report Access → Scoped Viewer role)")
    out.append("```")
    out.append("")

    # scheduled jobs
    out.append("## Automation — scheduled jobs")
    out.append("")
    out.append("| Job | Schedule | Runs | Purpose |")
    out.append("|---|---|---|---|")
    for name, sched, runs, purpose in SCHEDULED_JOBS:
        out.append(f"| {name} | {sched} | {runs} | {purpose} |")
    out.append("")

    # RLS + health
    out.append("## Security & operations")
    out.append("")
    out.append("- **Row-level security:** the **Report Access** List → `bi.report_access` drives the "
               "**`Scoped Viewer`** role (default-deny; a user sees the union of their active "
               "Project / Department / All grants, matched on `LOWER(USERPRINCIPALNAME())`). **`All Access`** "
               "is the admin bypass. RLS only takes effect under per-user identities in the Service.")
    out.append("- **Audit trail:** governance state changes write an append-only `doc_mgmt.audit_trail_entry` "
               "row in the same transaction (the **Audit** column below lists each surface's actions).")
    out.append("- **Health check:** `tools/governance_health.py` produces an exceptions digest "
               "(see [operations docs](../README.md)).")
    out.append("- **Change control:** every change to this platform follows "
               "[the SOP](change-control-process.md); the data dictionary "
               "([data-dictionary.md](data-dictionary.md)) and glossary ([glossary.md](glossary.md)) document the model.")
    out.append("")

    # master lineage table
    out.append("## Authoring surfaces — full lineage")
    out.append("")
    out.append("| # | SharePoint List | Phase | Key form fields | Sync process | DB table | bi view | Model table | Domain measures | Audit actions |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, s in enumerate(surfaces, 1):
        out.append("| " + " | ".join([
            str(i),
            surface_link(s, resolved),
            _md(s["phase"]),
            _md(s["columns"]),
            f"`{_md(s['process'])}`",
            f"`{_md(s['db_table'])}`",
            f"`{_md(s['bi_view'])}`" if s["bi_view"] not in ("—", "") else "—",
            _md(s["model_table"]),
            _md(s["measures"]),
            _md(s["audit"]),
        ]) + " |")
    out.append("")
    out.append(f"_{len(surfaces)} authoring Lists. Links resolve live via Microsoft Graph; if Graph was "
               f"unavailable at generation time, a constructed `{SITE_BASE}/Lists/...` link is used._")
    out.append("")
    return "\n".join(out)


# --- I/O ---------------------------------------------------------------------
def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def resolve_links(cfg):
    """{list_key: (display_name, web_url)} via Graph; {} on any failure (caller falls back)."""
    out = {}
    try:
        from graph_client import Graph
        g = Graph()
        sid = cfg["site_id"]
        for k in list_keys(cfg):
            try:
                lst = g.get(f"/sites/{sid}/lists/{cfg[k]}")
                out[k] = (lst.get("displayName") or lst.get("name"), lst.get("webUrl"))
            except Exception:
                pass
    except Exception:
        pass
    return out


def git_stamp():
    """(short_sha, date) of repo HEAD; ('unknown','unknown') on failure."""
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "log", "-1", "--format=%h\t%cs"],
                             capture_output=True, text=True, timeout=10)
        line = out.stdout.strip()
        if "\t" in line:
            sha, date = line.split("\t", 1)
            return sha.strip(), date.strip()
    except Exception:
        pass
    return "unknown", "unknown"


def read_version():
    try:
        return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def main(argv):
    cfg = load_config()
    if "--audit" in argv:
        unmapped, extra = coverage(SURFACES, cfg)
        for k in unmapped:
            print(f"UNMAPPED: config List '{k}' has no SURFACES row in build_admin_map.py")
        for k in extra:
            print(f"EXTRA: SURFACES row '{k}' has no matching List in db/.m365.local.json")
        bad = len(unmapped) + len(extra)
        print(f"\n{bad} coverage problem(s); {len(SURFACES)} surfaces mapped.")
        return 1 if bad else 0
    resolved = resolve_links(cfg)
    sha, date = git_stamp()
    header = provenance_header(sha, date, read_version(), len(SURFACES))
    md = render(SURFACES, resolved, header)
    if "--stdout" in argv:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        sys.stdout.write(md + "\n")
        return 0
    OUT_FILE.write_text(md + "\n", encoding="utf-8")
    live = sum(1 for s in SURFACES if s["list_key"] in resolved)
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)} — {len(SURFACES)} surfaces ({live} live links via Graph)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
