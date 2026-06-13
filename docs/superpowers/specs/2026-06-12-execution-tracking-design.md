# Project Execution Tracking — Design

Status: approved 2026-06-12 (plan-mode review). Expansion Phase 1 of the roadmap:
(1) execution tracking → (2) schedule & WBS → (3) people & notifications →
(4) platform hardening → (5) Phase-2 schema & EVM.

## Decisions (from planning)

- **Problem:** intake-born projects render an empty Project Status Report page —
  nothing feeds status reports, risks, milestones, or activities for live projects.
  Sample CSVs cover only the 6 demo projects.
- **Surface:** three new SharePoint Lists (Project Risks, Project Milestones,
  Project Status Reports) — the PMO already triages in SharePoint; the pattern
  (Graph list creation, person resolution, write-backs, airlock) is proven in
  production by the intake build. Power Apps deferred (additive veneer over the
  same Lists); Excel and a custom web app rejected for v1.
- **Scope:** `status_report` + `status_report_area`, `risk`, `milestone` now.
  `schedule_activity`/`wbs_element`/`risk_response` deferred to Phase 2 —
  activities carry six hard NOT NULL fields incl. an FK to WBS, and a bare
  auto-created WBS root feeds no visual. Consequence accepted: Accomplishments /
  Next Steps render from milestones only until Phase 2; Key Project Areas stays
  empty for new projects.
- **System of record:** PostgreSQL. Lists are the authoring surface; on any
  conflict the List wins (full-row compare re-applies List state).
- **Cadence:** daily 5:40 AM scheduled task (10 min after the intake sync,
  20 min before the 6:00 AM model refresh), same PC, same wrapper pattern.

## Architecture

```
PM edits List row (create/update)
        │ (SharePoint root site: Project Risks / Project Milestones / Project Status Reports)
        ▼
tools/sync_artifacts.py  (daily 5:40 AM via Theragen\SyncArtifacts → run_artifact_sync.cmd)
  fetch items (Graph, paged) → normalize → validate (artifact_lib)
  route by external_ref:
    new     → resolve project + people → mint codes → INSERT (1 row; reports: 1+9 atomic)
    existing→ full-row compare → UPDATE only when changed; heal lost write-backs
  write back SyncStatus / SyncMessage / RiskCode after commit
        ▼
PostgreSQL pmbok.risk / milestone / status_report / status_report_area
        ▼  (bi.* views — zero changes needed)
6:00 AM semantic-model refresh → status page traffic light, health check, RAID, gauge
```

## Components

### 1. Lists (created programmatically — `tools/create_artifact_lists.py`)

Common to all three: `SyncStatus` choice (Pending/Synced/Error, default Pending),
`SyncMessage` multiline — written only by the sync. `ProjectCode` text binds rows
to `pmbok.project.project_code`; unknown code → Error write-back.

**Project Risks → pmbok.risk**

| Column | Type | → target |
|---|---|---|
| Title | text (built-in) | label only |
| ProjectCode | text | → project_id (+ department derived from project.primary_department) |
| Category | choice: Technical, Schedule, Cost, Regulatory, Vendor, People, Safety, Reputational | category |
| Description | multiline, required | description |
| Trigger | multiline | "trigger" (reserved word — quoted in SQL) |
| Likelihood / Impact | choice "1".."5" | likelihood / impact; score = L×I computed |
| ResponseType | choice: Mitigate, Accept, Avoid, Transfer | response_type |
| RiskOwner | person | owner_person_id (LookupId → UIL → email → person; miss → Error) |
| DueDate | dateOnly | due_date |
| RiskStatus | choice: Open, Mitigating, Monitoring, Closed, Realized (default Open) | status |
| ResidualScore | number | residual_score (1–25 when present) |
| ComplianceFlag | choice: None, HIPAA, GxP, FDA 21 CFR Part 11 (default None) | compliance_flag |
| RiskCode | text (write-back) | risk_code — minted `R-NNN` per project |

**Project Milestones → pmbok.milestone** (no person column — cheapest List)

| Column | Type | → target |
|---|---|---|
| Title | text (built-in) | name |
| ProjectCode | text | → project_id |
| BaselineDate | dateOnly, required | baseline_date |
| ForecastDate / ActualDate | dateOnly | forecast_date / actual_date |
| MilestoneStatus | choice: On track, At risk, Achieved, Slipped (default On track) | status |
| OwnerRole | choice + allowTextEntry: Project Manager, Sponsor, Workstream Lead, Work Package Owner | owner_role |

Validation rule: **Achieved requires ActualDate** — the Recent Accomplishment
calculated table filters `[Milestone Status] = "Achieved" && NOT ISBLANK([Actual Date])`
(and a 35-day recency window); an Achieved milestone without a date silently
vanishes from the leadership page, so the sync makes it a visible Error instead.

**Project Status Reports → pmbok.status_report + 9 × status_report_area**

| Column | Type | → target |
|---|---|---|
| Title | text (built-in) | label only (suggest "CODE — period end") |
| ProjectCode | text | → project_id |
| PeriodStart / PeriodEnd | dateOnly, required | period_start / period_end (end ≥ start; (project, period_start) unique — drives bi report_number) |
| OverallStatus | choice: Green, Yellow, Red (default Green) | overall_status (the traffic light) |
| Trend | choice: Improving, Steady, Worsening (default Steady) | trend |
| ExecutiveSummary | multiline, required | executive_summary |
| DecisionsNeeded | multiline | decisions_needed |
| SubmittedBy | person | submitted_by_person_id (fallback: item createdBy email) |
| ScopeHealth … CommunicationsHealth (9 columns) | choice: Green, Yellow, Red (default Green) | one status_report_area row each |

One List row = one weekly report; the sync fans it into 1 + 9 DB rows with
deterministic child keys `uuid5(NS, "thg/sra/{item_id}/{ka}")` so re-syncs update
in place. Knowledge areas (exact, from bi.knowledge_area): Scope, Schedule, Cost,
Quality, Risk, Stakeholders, Compliance, Procurement, Communications.
`status_report_area.commentary` stays NULL in v1. `submitted_at` ← item
createdDateTime (stable across edits).

### 2. `tools/artifact_lib.py` (pure, tested)

Domain constants; `next_risk_code(existing)` (`R-(\d{3})$`, max+1, width-widens);
`risk_score(l, i)` (validates 1–5); `validate_risk` / `validate_milestone` /
`validate_status_report` (error lists, incl. Achieved-needs-date, period order,
residual bounds); `build_risk_row` / `build_milestone_row` / `build_report_row` /
`build_area_rows` (item → column dicts; 9-row fan-out); `row_changed(current,
desired, cols)` — type-normalizing diff (date vs ISO string, Decimal vs float/int,
None vs "").

### 3. `tools/sync_artifacts.py` (engine — new script, not an intake extension)

- `ARTIFACTS` registry: {list_key, fields, normalize_fn, process_fn} per List —
  Phase-2 lists are a registry entry + handler.
- Fetch paged with `$expand=fields($select=…)` incl. person `…LookupId` companions.
- New items: validate → resolve project/persons → mint → one transaction
  (reports: parent + 9 areas atomic) → write back Synced (+ RiskCode).
- Existing items: build desired row, compare to current (one
  `SELECT … WHERE external_ref IS NOT NULL` per table per run, dict by ref);
  UPDATE only on change; heal write-backs when List bookkeeping disagrees
  (SyncStatus ≠ Synced or RiskCode blank); quiet no-op otherwise.
- ProjectCode changed after sync → Error "create a new row instead".
- Deletes: List row gone → keep DB row, log `orphaned external_ref` INFO, exit 0.
- Per-item try/except; ERROR results → exit 1. Same isatty fail-fast via
  graph_client.
- PKs: `uuid5(NS, "thg/artifact/{risk|milestone|report}/{item_id}")`.

### 4. Shared person resolution (`SitePeople` in graph_client.py)

Extract `_load_user_cache` / `person_email` / `_coerce_bool` from sync_intake.py
into a `SitePeople(g, site_id)` class (`.email(lookup_id)`, `.coerce_bool`
stays module-level or moves too); sync_intake.py refactored to consume it.
Behavior-identical — gated by before/after `--dry-run` output diff.

### 5. Migration — `db/06_artifact_external_ref.sql`

```sql
ALTER TABLE pmbok.risk          ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
ALTER TABLE pmbok.milestone     ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
ALTER TABLE pmbok.status_report ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
```

Applied live via inline psycopg (never the loader); file also appended to the
loader DDL tuple for future from-scratch builds. `status_report_area` needs no
external_ref (children keyed deterministically through their report). Hard rule
documented: **no `load_postgres.py --reseed` after go-live** — it destroys live
intakes and artifacts.

### 6. Scheduling

`tools/run_artifact_sync.cmd` (clone of run_intake_sync.cmd → logs\artifact_sync.log)
+ scheduled task `Theragen\SyncArtifacts` daily 5:40 AM, StartWhenAvailable,
battery-tolerant. Pipeline: 5:30 intake → 5:40 artifacts → 6:00 refresh.

## Error handling

Same airlock contract as intake: every failed item gets SyncStatus=Error +
SyncMessage on its List row (validation, unknown ProjectCode, person miss,
duplicate period); PM fixes the row; next run converges. Lost write-backs heal
via the compare path. One bad item never blocks the batch. Exit 1 on any ERROR;
wrapper logs exit codes per run.

## Testing

Pure logic only (team rule): `tests/test_artifact_lib.py` covers minting overflow
and None-tolerance, score bounds, all three validators (incl. Achieved-without-date,
period inversion, RAG membership), 9-area fan-out completeness/order, and
`row_changed` normalization (date vs string, Decimal vs int, None vs ""). I/O
verified live in T5–T7 and the T9 e2e smoke.

## Out of scope (v1)

Activities/WBS/risk responses (Phase 2), sync-maintained ProjectCode dropdown
choices (Phase 2), area commentary columns, `--prune` deletes, Power Apps veneer,
notifications, cloud-hosted sync.

## Build order

T1 migration → T2 artifact_lib+tests → T3 SitePeople extraction → T4 Lists →
T5 engine dry-run → T6 write path → T7 update path → T8 schedule+docs → T9 e2e.
