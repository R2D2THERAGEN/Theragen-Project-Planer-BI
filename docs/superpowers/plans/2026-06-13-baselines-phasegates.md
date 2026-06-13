# Baselines + Phase Gates — Implementation Plan (Phase 2c-1)

Spec: `docs/superpowers/specs/2026-06-13-baselines-phasegates-design.md`. Deep design: the approved
plan file (Stage 2c → 2c-1). Process: subagent-driven, fresh subagent per task, two-stage review.

Hard riders (every task): NEVER run `tools/load_postgres.py`/reseed (DDL via inline psycopg; data
writes only through `sync_artifacts.py` + listed probe cleanups); never commit `db/.pg.local.json`/
`db/.m365.local.json`/`db/.graph_token_cache.json`; `python -m pytest tests/ -q` green at every
commit; both syncs LIVE — keep existing artifact dry-run output byte-unchanged for the current Lists
when touching shared files (capture before/after); Graph identity richard.allen@theragen.com;
**mirror established patterns** — `process_risk` (per-item), `process_triage` in sync_intake.py
(List status → project state + current==target short-circuit; the phase-gate template), the
activity WBS reconcile / report `area_map` pre-pass in `main()`, `audit_lib.write_trail` (2b, inside
the txn), migration/List/test conventions. APNE = THG-IT-005 (live, the e2e target).

---

### Task 1: Migrations 12 + 13
Create `db/12_project_baseline.sql` and `db/13_phase_gate_log.sql` with the exact DDL from the
spec (comment headers like db/07–db/11; `CREATE TABLE IF NOT EXISTS`; both carry `external_ref
VARCHAR(64) UNIQUE`; project_baseline also `UNIQUE(project_id, baseline_type, version)`). Append
both filenames to the `load_postgres.py` DDL tuple after `11_bi_governance_views.sql`. Apply live
via inline psycopg; verify `information_schema` (both tables + columns + the UNIQUEs); seeded counts
unchanged. pytest green. Commit `"Add project_baseline + phase_gate_log migrations"`.

### Task 2: Pure baseline/phase-gate logic with tests (TDD)
Tests FIRST in `tests/test_artifact_lib.py`, then code in `tools/artifact_lib.py`.

```python
BASELINE_TYPES = ["Schedule", "Scope", "Budget"]
LIFECYCLE_PHASES = ["Initiating", "Planning", "Executing",
                    "Monitoring & Controlling", "Closing"]
PHASE_ORDER = {p: i for i, p in enumerate(LIFECYCLE_PHASES)}
GATE_DECISIONS = ["Approved", "Approved with conditions", "Held"]
_BASELINE_VER = re.compile(r"^(\d+)\.0$")


def next_baseline_version(existing):
    nums = [int(m.group(1)) for s in existing if s and (m := _BASELINE_VER.match(s))]
    return f"{(max(nums) + 1 if nums else 1)}.0"


def validate_baseline(it):
    errs = [f"Missing: {k}" for k in ("ProjectCode", "BaselineType")
            if _blank(it.get(k))]
    if _blank(it.get("BaselinedByEmail")):
        errs.append("Missing: BaselinedBy")
    if it.get("BaselineType") and it["BaselineType"] not in BASELINE_TYPES:
        errs.append(f"BaselineType not recognized: {it['BaselineType']}")
    return errs


def validate_phase_gate(it):
    errs = [f"Missing: {k}" for k in ("ProjectCode", "TargetPhase", "GateDecision")
            if _blank(it.get(k))]
    if _blank(it.get("ApprovedByEmail")):
        errs.append("Missing: ApprovedBy")
    if it.get("TargetPhase") and it["TargetPhase"] not in LIFECYCLE_PHASES:
        errs.append(f"TargetPhase not recognized: {it['TargetPhase']}")
    if it.get("GateDecision") and it["GateDecision"] not in GATE_DECISIONS:
        errs.append(f"GateDecision not recognized: {it['GateDecision']}")
    return errs


def _d(v):  # date -> 'YYYY-MM-DD' or None (rows come from psycopg as date/Decimal/str)
    if v is None:
        return None
    return v.isoformat()[:10] if hasattr(v, "isoformat") else str(v)[:10]


def assemble_schedule_snapshot(activities, milestones, headline):
    """activities/milestones: lists of dict rows (already SELECTed). Deterministic."""
    acts = sorted(({"code": a["activity_code"], "name": a["name"],
                    "start_planned": _d(a["start_planned"]),
                    "finish_planned": _d(a["finish_planned"]),
                    "duration_days": int(a["duration_days"])} for a in activities),
                  key=lambda x: x["code"])
    mils = sorted(({"name": m["name"], "baseline_date": _d(m["baseline_date"])}
                   for m in milestones),
                  key=lambda x: (x["baseline_date"] or "", x["name"]))
    return {"type": "Schedule", "activities": acts, "milestones": mils,
            "headline": {"planned_start": _d(headline.get("planned_start")),
                         "planned_finish": _d(headline.get("planned_finish"))}}


def assemble_budget_snapshot(budget_total, lines):
    ls = sorted(({"wbs_code": l["wbs_code"], "category": l["category"],
                  "total": float(l["total"]),
                  "funding_source": l["funding_source"]} for l in lines),
                key=lambda x: (x["wbs_code"], x["category"]))
    return {"type": "Budget",
            "budget_total": float(budget_total) if budget_total is not None else None,
            "lines": ls}


def assemble_scope_snapshot(charter, inclusions, exclusions, acceptance):
    c = charter or {}
    return {"type": "Scope",
            "charter": {"business_case": c.get("business_case"),
                        "high_level_in_scope": c.get("high_level_in_scope"),
                        "high_level_out_scope": c.get("high_level_out_scope")},
            "inclusions": [r["item"] for r in sorted(inclusions, key=lambda r: r.get("sequence", 0))],
            "exclusions": [r["item"] for r in sorted(exclusions, key=lambda r: r.get("sequence", 0))],
            "acceptance": [r["criterion"] for r in sorted(acceptance, key=lambda r: r.get("sequence", 0))]}


def build_phase_gate_row(it, project_id, from_phase, to_phase, approver_id):
    return {"project_id": project_id, "from_phase": from_phase, "to_phase": to_phase,
            "gate_decision": it["GateDecision"], "approved_by_person_id": approver_id,
            "decided_at": it.get("DecidedDate"), "gate_notes": it.get("GateNotes")}
```

Tests: `next_baseline_version` ([]→"1.0"; ["1.0","2.0",None,"x"]→"3.0"; ["9.0"]→"10.0");
`validate_baseline`/`validate_phase_gate` (each missing required; bad domains); **snapshot
byte-determinism** — call each assembler twice with shuffled input row order and assert
`json.dumps(a, sort_keys=False) == json.dumps(b, …)` IS EQUAL (the sort makes order-independent);
assert the exact key set + sorted order; `assemble_scope_snapshot` with empty inclusion/exclusion/
acceptance → `[]`; numeric coercions (`total` float, `duration_days` int). Green. Commit
`"Add pure baseline + phase-gate logic: version minting, validators, snapshot assemblers"`.

### Task 3: Lists in the creator
Add to `create_artifact_lists.py` `LISTS`: **"Project Baselines"** (ProjectCode, BaselineType
choice al.BASELINE_TYPES, ChangeSummary ml, LinkedCRCode text, BaselinedBy person, BaselineVersion
text + BOOKKEEPING; key `baseline_list_id`) and **"Project Phase Gates"** (ProjectCode, TargetPhase
choice al.LIFECYCLE_PHASES, GateDecision choice al.GATE_DECISIONS default "Approved", ApprovedBy
person, DecidedDate date_only, GateNotes ml + BOOKKEEPING; key `phase_gate_list_id`). Run live
(idempotent; keys merged into `db/.m365.local.json` → now 11 keys; column-ensure loop covers them).
Spot-verify facets. pytest green. Commit (script only) `"Add Project Baselines + Phase Gates Lists"`.

### Task 4: Sync read/normalize/dry-run + snapshot I/O wiring
`BASELINE_FIELDS`/`PHASE_GATE_FIELDS` (incl. BaselinedByLookupId/ApprovedByLookupId);
`normalize_baseline`/`normalize_phase_gate` (mirror normalize_risk; resolve emails via SitePeople;
`_date` for dates); `BASELINE_SELECT` (external_ref + project_id, baseline_type, version, status —
the comparable/immutability columns) / `PHASE_GATE_SELECT` (external_ref + project_id, to_phase,
gate_decision); `build_baseline_snapshot(conn, project_id, baseline_type)` I/O helper (runs the
type's SELECTs — Schedule/Budget JOIN wbs_element; Scope reads charter + the scope_* child tables if
present — and calls the pure assembler); STUB `process_baseline`/`process_phase_gate` (validate →
resolve project + person → for phase-gate compute from_phase + legality → report DRY/ERROR intent;
NO writes). Registry entries. Dry-run live: 1 baseline probe (ProjectCode THG-IT-005, BaselineType
Schedule) → "DRY baseline item N: would create Schedule v1.0 (THG-IT-005)"; 1 phase-gate probe
(THG-IT-005, TargetPhase Planning — APNE is Initiating, so forward-legal) → "DRY phase_gate item N:
would move Initiating -> Planning"; a backward probe (TargetPhase Initiating with project already
Initiating → "would no-op", or a truly-backward case once advanced) errors appropriately. Confirm
existing Lists' dry-run unchanged. Commit `"Baseline + phase-gate sync: fields, normalize, snapshot, dry-run"`.

### Task 5: Baseline write path
Real `process_baseline` (create-or-noop per spec): existing_versions = SELECT version FROM
pmbok.project_baseline WHERE project_id=%s AND baseline_type=%s; version = next_baseline_version;
snapshot = build_baseline_snapshot(...); in conn.transaction(): if version != "1.0" UPDATE prior
BASELINED→SUPERSEDED (+ optional BASELINE_SUPERSEDE audit); INSERT project_baseline (baseline_id
uuid5, all columns incl. snapshot via Jsonb, external_ref); write_trail BASELINE_CREATE; then
write-back {SyncStatus:Synced, BaselineVersion:version}. Existing-item branch: immutability reject
(SyncMessage) + heal + ProjectCode-guard (no snapshot rebuild/UPDATE). Live on APNE: create a
Schedule baseline (v1.0) and a Budget baseline (v1.0); SELECT pmbok.project_baseline + inspect the
frozen snapshot JSONB (activities/milestones for schedule; lines+budget_total for budget); create a
SECOND Schedule baseline (ChangeSummary "re-baseline") → v2.0 mints, v1.0 → SUPERSEDED with
superseded_by chain; bi.project_baseline shows baseline_budget_total/activity_count; audit
BASELINE_CREATE rows present; idempotent re-run = no-ops (no new versions). Leave probes for T6
cleanup or keep as real APNE data (decide in T8). Commit `"Baseline sync: snapshot freeze, version supersede, audit"`.

### Task 6: Phase-gate write path + guards + baseline immutability
Real `process_phase_gate` (the process_triage analog from the spec): from_phase = project
lifecycle_phase; legality (Held ok; forward `>` ok; `==` no-op/heal; `<` Error); apply
(UPDATE project + INSERT log + PHASE_GATE audit, or Held INSERT + PHASE_GATE_HOLD); idempotency via
the log row external_ref; heal/orphan/ProjectCode-guard. Live on APNE (currently Initiating):
advance Initiating→Planning (Approved) → project lifecycle_phase=Planning, log row + audit; re-run
twice → no double-advance ("no change"); a backward gate (TargetPhase Initiating) → Error "Backward
phase transition rejected"; a Held gate (TargetPhase Executing, GateDecision Held) → log row
from==to==Planning, no project change; verify pmbok.phase_gate_log + bi.phase_gate_log + audit rows.
Confirm baseline immutability: PATCH a synced baseline's ChangeSummary → run → reject message, no DB
change. Cleanup any throwaway phase-gate probes (keep one real forward advance as APNE data if
sensible). Commit `"Phase-gate sync: forward+Hold transitions, log anchor, baseline immutability"`.

### Task 7: bi views + TMDL tables/measures
`db/14_bi_baseline_phasegate_views.sql` (bi.project_baseline + bi.phase_gate_log per spec; append to
loader tuple). New `Project Baseline.tmdl` + `Phase Gate Log.tmdl` model tables (mirror Decision.tmdl
exactly: hidden Project ID, M-partition SelectColumns/RenameColumns from the bi views) + two
single-direction relationships to `Project.'Project ID'` (mirror the Decision→Project block; date
facts → Date.Date if a date relationship is conventional). Measures in `_Measures.tmdl` (fresh uuid5
lineageTags, folders Baselines/Governance): Baselines (COUNTROWS), Current Baselines
(status=BASELINED), Current Schedule/Budget/Scope Baseline Version (MAX version per type among
BASELINED), Budget Variance vs Baseline, Phase Gates Passed (Approved/conditions), Gates Held, Days
in Current Phase. Validate: `python tools/validate_pbir.py` (0 problems) + Tabular Editor BPA (0
violations, if available) + manual review. Republish note (Allen). pytest green. Commit `"Model:
baseline + phase-gate views, model tables, measures"`.

### Task 8: Docs + e2e + final review
`docs/artifact-entry-setup.md`: new Baselines + Phase Gates sections (columns, choices, the
**immutability rule** for baselines, the **forward-only + Hold** rule for gates, that snapshots are
auto-built, the audit trail) + README pointer (mind the §-cross-references — re-grep "see §" after
any renumber). E2e on APNE: ensure a Schedule + Budget baseline exist (v1.0) and the project has
advanced Initiating→Planning via a gate (real data, left in place); `python tools/service_refresh.py`
(note the new tables/measures need a republish to appear). Whole-sub-stage review (most capable
model); fix loop; final commit.

---

## Self-review
- **Spec coverage:** migrations (T1), pure logic+tests incl. snapshot determinism (T2), Lists (T3),
  dry-run + snapshot I/O (T4), baseline write path + supersede + audit (T5), phase-gate write path +
  guards + immutability (T6), bi+TMDL (T7), docs+e2e (T8). 2c-2…2c-6 out of scope. ✓
- **Type consistency:** `next_baseline_version`/`validate_baseline`/`validate_phase_gate`/
  `assemble_*_snapshot`/`build_phase_gate_row` match tests (T2) and call sites (T4–T6);
  `build_baseline_snapshot` (I/O) feeds the pure assemblers; `baseline_list_id`/`phase_gate_list_id`
  written by T3, read by T4. ✓
- **Reuse:** process_risk + process_triage skeletons, `audit_lib.write_trail`, `_error`/`writeback`/
  `person_id_by_email`/`project_by_code`/`synced_map`/`row_changed`, the migration/List/test
  conventions — reused, not reinvented. The append-once processor (create-or-noop) is the one new
  per-processor shape. ✓
