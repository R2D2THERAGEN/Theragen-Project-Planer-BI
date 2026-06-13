# Baselines + Phase Gates — Design (Phase 2c-1)

Status: approved 2026-06-13 (plan-mode review). First sub-stage of the decomposed Phase 2c
(2c-1 Baselines + Phase Gates → 2c-2 impact-assessment authoring → 2c-3 documents foundation →
2c-4 RACI → 2c-5 versions + e-sig → 2c-6 governance CRs). Full arc: the approved plan. This
spec covers **2c-1 only** — chosen first because it depends on nothing new (reads the already-live
`pmbok.*` execution artifacts) and is the highest-value self-contained versioning/handoff payload.

## Problem

The system can change and approve projects (2b), but it can't **freeze a baseline** (so "what
changed since the approved plan?" is unanswerable) and the project `lifecycle_phase`
(Initiating→Planning→Executing→Monitoring→Closing) advances with no documented
**gate** — no record of who signed off the handoff between phases, when, or why.

## Decisions

- Two new authoring surfaces synced by the existing registry-driven `tools/sync_artifacts.py`:
  **"Project Baselines"** → `pmbok.project_baseline`, **"Project Phase Gates"** → `pmbok.phase_gate_log`.
- **Baselines freeze a real JSONB snapshot** of the project's live schedule / budget / scope
  (locked decision), built **server-side** at creation — the PM never types snapshot content.
- Baselines are **append-once (immutable)**: a new baseline of the same type mints the next
  version and supersedes the prior `BASELINED` row; editing a synced baseline is rejected.
- **Phase gates are forward+Hold** (locked decision): a gate advances the project one step
  forward on sign-off, or records a `Held` decision (stays put); backward moves are rejected;
  every gate is logged with approver/date/notes + audit.
- Every transition writes an append-only `doc_mgmt.audit_trail_entry` row (the 2b `audit_lib`).
- No new pmbok core entity beyond the two log tables; two new model tables in TMDL.

## "Project Baselines" List → `pmbok.project_baseline`

New table (`db/12`): `baseline_id PK, project_id, baseline_type [Schedule|Scope|Budget], version
[1.0,2.0,…], status [BASELINED|SUPERSEDED def BASELINED], change_summary, change_class,
linked_cr_id, snapshot JSONB NOT NULL, baselined_by_person_id, baselined_at def now(),
superseded_by_baseline_id, external_ref VARCHAR(64) UNIQUE, UNIQUE(project_id, baseline_type,
version)`. No DB FKs (resolved in app, the db/10 convention).

List columns: ProjectCode, BaselineType (choice Schedule/Scope/Budget), ChangeSummary (ml),
LinkedCRCode (text, optional), BaselinedBy (person), BaselineVersion (write-back) + bookkeeping.
**No snapshot input** — built from live tables.

**Snapshot builder** (pure/I-O split): `build_baseline_snapshot(conn, project_id, type)` (I/O in
sync) runs the type's SELECTs; `assemble_{schedule,budget,scope}_snapshot(rows)` (pure, tested)
returns deterministic JSON (stable `ORDER BY` in SQL **and** re-sort in the assembler; fixed key
order; dates `YYYY-MM-DD`; `float()` numerics). Shapes:
- **Schedule**: `{type:"Schedule", activities:[{code,name,start_planned,finish_planned,duration_days}]
  (sorted by code), milestones:[{name,baseline_date}] (sorted by baseline_date,name),
  headline:{planned_start,planned_finish}}`. Activities join project **through wbs_element**
  (`JOIN pmbok.wbs_element w USING(wbs_element_id) WHERE w.project_id=%s`).
- **Budget**: `{type:"Budget", budget_total, lines:[{wbs_code,category,total,funding_source}]
  (sorted by wbs_code,category)}` (budget_line_item joins project through wbs_element).
- **Scope**: `{type:"Scope", charter:{business_case,high_level_in_scope,high_level_out_scope},
  inclusions:[…], exclusions:[…], acceptance:[…] (each `[]` when unseeded)}`.

**Versioning + supersede**: `next_baseline_version(existing)` (`^(\d+)\.0$`, widen) → 1.0/2.0/…
per (project, type). On version N>1, the same transaction `UPDATE pmbok.project_baseline SET
status='SUPERSEDED', superseded_by_baseline_id=<new> WHERE project_id=%s AND baseline_type=%s AND
status='BASELINED'`. Prior versions retained. `baseline_id = uuid5(NS, "thg/artifact/baseline/{item_id}")`.

**process_baseline = create-or-noop**: new item → snapshot → mint → supersede-prior → INSERT →
`write_trail("BASELINE_CREATE", …)` → write-back BaselineVersion. Existing item → snapshot is
frozen (no rebuild, no UPDATE of snapshot); heal a lost write-back; **reject** substantive edits
("Baselines are immutable; create a new baseline to re-baseline"); ProjectCode-change guard;
orphan-keep. (Approved-CR auto-trigger = future; v1 = explicit List authoring.)

## "Project Phase Gates" List → `pmbok.phase_gate_log`

New table (`db/13`): `phase_gate_id PK, project_id, from_phase, to_phase, gate_decision
[Approved|Approved with conditions|Held], approved_by_person_id, decided_at DATE, gate_notes,
external_ref VARCHAR(64) UNIQUE`.

List columns: ProjectCode, TargetPhase (choice of the 5 lifecycle phases), GateDecision (choice,
default Approved), ApprovedBy (person), DecidedDate (date), GateNotes (ml) + bookkeeping.

`process_phase_gate` = a `process_triage` analog with `PHASE_ORDER = {Initiating:0, Planning:1,
Executing:2, Monitoring:3, Closing:4}`:
- `from_phase` = the project's current `lifecycle_phase` (read at sync time).
- **Forward-only legality**: `Held` always legal (to=from); `Approved`/`Approved with conditions`
  require `PHASE_ORDER[Target] > PHASE_ORDER[from]`; `==` is the no-op/heal short-circuit; `<`
  rejected ("Backward phase transition rejected").
- Apply: Approved/conditions AND from≠to → one txn `UPDATE pmbok.project SET lifecycle_phase=to`
  + INSERT log + `write_trail("PHASE_GATE", before={lifecycle_phase:from}, after={…:to})`. Held →
  INSERT log (from==to) + `write_trail("PHASE_GATE_HOLD", …)`, no project update.
- **Idempotency anchor = the log row** (`external_ref`): an already-synced gate is a no-op/heal, so
  a project never double-advances. `phase_gate_id = uuid5(NS, "thg/artifact/phasegate/{item_id}")`.

Validation: required ProjectCode/TargetPhase/GateDecision/ApprovedBy; domain membership;
DecidedDate when decided.

## Audit trail
Reuse `tools/audit_lib.write_trail` (2b), inside the per-item transaction: `BASELINE_CREATE`
(+ optional `BASELINE_SUPERSEDE` on the superseded row), `PHASE_GATE`, `PHASE_GATE_HOLD`.

## BI + model (`db/14`, TMDL)
- `bi.project_baseline`: metadata + headline delta — `baseline_type, version, status,
  change_summary, baselined_at, baselined_by_name, (snapshot->>'budget_total')::numeric AS
  baseline_budget_total, jsonb_array_length(COALESCE(snapshot->'activities','[]')) AS
  baseline_activity_count` (+ project_code via JOIN). The blob interior stays in PG.
- `bi.phase_gate_log`: project_code, from_phase, to_phase, gate_decision, decided_at, gate_notes,
  approved_by_name.
- Two new model tables (`Project Baseline.tmdl`, `Phase Gate Log.tmdl`, mirroring `Decision.tmdl`)
  + single-direction relationships to `Project.'Project ID'`. Measures (folders Baselines/
  Governance): Baselines, Current Baselines, Current {Schedule|Budget|Scope} Baseline Version,
  Budget Variance vs Baseline, Phase Gates Passed, Gates Held, Days in Current Phase.
- **Schema additions require an Allen republish** (data refresh won't surface them — the 2b precedent).

## Migrations
`db/12_project_baseline.sql`, `db/13_phase_gate_log.sql`, `db/14_bi_baseline_phasegate_views.sql`
— additive, IF NOT EXISTS / CREATE OR REPLACE, applied live via inline psycopg (never the loader),
appended to the loader DDL tuple.

## Error handling, testing, out of scope
Same airlock: failed items → SyncStatus=Error + message; lost write-backs heal; one bad item
never blocks the batch; exit 1 on any error. Pure logic unit-tested (version minting widen;
validators; the three snapshot assemblers incl. **byte-determinism** — same input → identical
JSON bytes; the phase legality incl. forward/backward/Held/equal). I/O verified live in T4–T6 +
the T8 e2e. Out of scope for 2c-1: minor (1.x) versions, Approved-CR auto-baseline, line-level
baseline-vs-current diff view, and everything in 2c-2…2c-6 (impact authoring, documents, RACI,
versions, e-sig, governance CRs).
