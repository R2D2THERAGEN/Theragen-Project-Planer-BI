# Change Impact Assessment Authoring — Design (Phase 2c-2)

Status: approved 2026-06-13 (plan-mode review). Second sub-stage of the decomposed Phase 2c
(2c-1 Baselines + Phase Gates → **2c-2 impact-assessment authoring** → 2c-3 documents foundation →
2c-4 RACI → 2c-5 versions + e-sig → 2c-6 governance CRs). Full arc: the approved plan
(`~/.claude/plans/lets-plan-phase-two-foamy-turing.md`). This spec covers **2c-2 only** — chosen
second because it introduces the one genuinely new sync shape (**parent-child authoring**) in the
cheapest possible setting: the parent change requests are already live from 2b, it touches a single
table, and it needs no lookup seeding. The pattern proven here is reused unchanged in 2c-4/2c-5/2c-6.

## Problem

2b made change requests authorable and approvable, but a CR's **per-department impact** can't be
recorded. `pmbok.change_impact_assessment` exists and `bi.change_impact_assessment` already ships
(2b, `db/11`), yet there is no authoring surface — so the Change Control page can't show "which
departments assessed this CR, and what schedule/cost hit each one reported."

## Decisions

- One new authoring surface synced by the existing registry-driven `tools/sync_artifacts.py`:
  **"Change Impact Assessments"** → `pmbok.change_impact_assessment`.
- **Parent-child by human code (the new shape):** each List row names its parent CR by
  `ParentCRCode` (+ `ProjectCode` to scope it); the sync resolves the parent `cr_id` per item.
  `cr_code` is UNIQUE per `(project_id, cr_code)` — **not** global — so the resolution keys on
  `(project_id, ParentCRCode)`. **No pre-pass map** is needed: the sync runs under
  `autocommit=True` and the registry processes `change_request` **before** `change_impact_assessment`,
  so a parent (even one filed the same morning) is already committed when its child resolves. Reuses
  the exact `LinkedCRCode` lookup already in `process_baseline`.
- **Editable, not append-once:** an impact statement is authored content (like a decision), so the
  `process_decision` create/update/heal skeleton applies — `row_changed` drives a targeted UPDATE.
- **No audit trail:** an impact statement is descriptive content attached to a CR, not a governance
  state transition; consistent with how `process_decision` syncs without an `audit_trail_entry` row.
- **No code minting:** the table has no human code; identity is `impact_id = uuid5` + `external_ref`.
- No new pmbok entity, **no new/changed bi view** (the `db/11` view already exposes everything);
  one new model table in TMDL.

## "Change Impact Assessments" List → `pmbok.change_impact_assessment`

Confirmed DDL (`db/02_pmbok.sql:293`): `impact_id UUID PK, cr_id UUID NOT NULL, department VARCHAR
NOT NULL, scope_impact TEXT, schedule_impact_days INTEGER, cost_impact NUMERIC(12,2), quality_impact
TEXT, submitted_by_person_id UUID NOT NULL, submitted_at DATE NOT NULL`. **NOT NULL to satisfy:**
`cr_id`, `department`, `submitted_by_person_id`, `submitted_at`. No DB FKs (resolved in app — the
db/10 convention). No `UNIQUE(cr_id, department)` → a department may file more than one assessment
per CR; each List row is its own assessment keyed by `external_ref`, edits update in place.

Migration (`db/15_impact_assessment_external_ref.sql`, additive, inline psycopg — never the loader;
appended to the loader DDL tuple): `ALTER TABLE pmbok.change_impact_assessment ADD COLUMN IF NOT
EXISTS external_ref VARCHAR(64) UNIQUE;`. **No bi-view file** (the view shipped in `db/11`).

List columns (creator helpers `text/choice/date_only` + `BOOKKEEPING`; person column
`{"name":..,"personOrGroup":{"allowMultipleSelection":False}}`):
- `ProjectCode` (text) → resolve project (scopes the parent lookup)
- `ParentCRCode` (text) → parent CR's `cr_code`
- `Department` (choice = the 8 `artifact_lib.DEPARTMENTS`) → `department`
- `ScopeImpact` (ml) → `scope_impact`; `QualityImpact` (ml) → `quality_impact`
- `ScheduleImpactDays` (number, none-dp) → `schedule_impact_days`
- `CostImpact` (number, two-dp) → `cost_impact`
- `SubmittedBy` (person, + `SubmittedByLookupId`) → `submitted_by_person_id`, with **author-fallback**
  to `createdBy.user.email` (the `normalize_change_request` pattern) to satisfy NOT NULL
- `SubmittedDate` (date) → `submitted_at`, **defaulting to the item `createdDateTime` date** when
  blank, to satisfy NOT NULL
- `SyncStatus` / `SyncMessage` (bookkeeping). **No write-back code column** (no minted human code).

`impact_assessment_list_id` is merged into `db/.m365.local.json`. No schedule change (the 5:40 AM
`Theragen\SyncArtifacts` job already runs `sync_artifacts.py`).

## Pure logic (`tools/artifact_lib.py`, unit-tested)

- `validate_impact_assessment(it)` — required non-blank `ProjectCode`, `ParentCRCode`, `Department`;
  `Department ∈ DEPARTMENTS`; submitter resolvable (`SubmittedByEmail`, which the normalizer fills
  from the picker **or** the author fallback) — else `Missing: SubmittedBy` (can't satisfy NOT NULL);
  `ScheduleImpactDays` integer-coercible when present, `CostImpact` numeric-coercible when present
  (blank ok → NULL); `ScopeImpact`/`QualityImpact` free text optional. (`SubmittedDate` is optional
  here — defaulted in the normalizer — so it never appears as a validation error.)
- `build_impact_assessment_row(it, cr_id, submitted_by_person_id, submitted_at)` — returns the column
  dict `{cr_id, department, scope_impact, schedule_impact_days, cost_impact, quality_impact,
  submitted_by_person_id, submitted_at}`; `None` for blank nullable fields; `int()` / `float()`
  coercion for the two numerics. Pure; mirrors `build_decision_row`.

## `process_impact_assessment` (`tools/sync_artifacts.py`)

Mirrors `process_decision`, with the parent-CR resolution from `process_baseline`.
`IMPACT_FIELDS` / `normalize_impact_assessment` / `IMPACT_SELECT` (`external_ref, impact_id, cr_id,
department, scope_impact, schedule_impact_days, cost_impact, quality_impact, submitted_by_person_id,
submitted_at`); registry entry **after `change_request`** in `ARTIFACTS`.

Per item:
1. `validate_impact_assessment`; resolve project (`project_by_code`; unknown → Error).
2. Resolve parent `cr_id`: `SELECT cr_id FROM pmbok.change_request WHERE project_id=%s AND cr_code=%s`
   → miss → Error `"Unknown ParentCRCode <X> for project <ProjectCode>"`.
3. Resolve submitter (`person_id_by_email(SubmittedByEmail)`; the normalizer already applied the
   author fallback) → miss → Error.
4. **New item** → `INSERT` (per-item `conn.transaction()`, `impact_id = uuid5(NS,
   "thg/artifact/impact/{item_id}")`, `external_ref = item_id`) → write-back `Synced`.
5. **Existing item** → `row_changed(current, build_impact_assessment_row(...))` → `UPDATE` the mutable
   cols (`department, scope_impact, schedule_impact_days, cost_impact, quality_impact,
   submitted_by_person_id, submitted_at`); else heal a lost write-back; else no-op.
6. **Re-parent guard** (the new-shape safety rule): if the freshly resolved `cr_id` ≠ the stored
   `current["cr_id"]` (i.e. `ProjectCode` or `ParentCRCode` was edited to point at a different CR) →
   Error `"Reparenting not allowed; create a new impact assessment"` (subsumes the ProjectCode-change
   guard). Orphan-keep on List-row delete (INFO, DB row retained).

## BI + model (no `db` view file; TMDL only)

- `bi.change_impact_assessment` **already exists** (`db/11:65`) — `impact_id, cr_id, cr_code,
  project_code, department, scope_impact, schedule_impact_days, cost_impact, quality_impact,
  submitted_by_person_id, submitted_by_name, submitted_at`.
- **NEW `Change Impact Assessment.tmdl`** consuming that view — mirror `Decision.tmdl` (hidden uuid
  key + `bi.* → Table.SelectColumns → Table.RenameColumns` M partition). Columns: `Impact ID`
  (hidden), `CR ID` (hidden — relationship key), `CR Code`, `Project Code`, `Department`,
  `Scope Impact`, `Schedule Impact Days` (int64, `#,0`), `Cost Impact` (double,
  `\$#,##0;(\$#,##0);\$0`), `Quality Impact`, `Submitted By`, `Submitted Date` (dateTime, `yyyy-mm-dd`,
  `UnderlyingDateTimeDataType = Date`).
- **One new relationship** (lowest BPA footprint, the Decision precedent): `Change Impact
  Assessment[CR ID]` → `Change Request[CR ID]` (the hidden `CR ID` key already on `Change
  Request.tmdl`), single-direction. Per-dept slicing comes from the local `Department` column in a
  matrix visual — **no Department-dim relationship** (avoids an ambiguous path to `Project`).
- `_Measures.tmdl`, folder **Change** (exact block format; fresh uuid5 lineageTags; no trailing
  semicolon): `Impact Assessments = COUNTROWS('Change Impact Assessment')`; `Assessed CRs =
  DISTINCTCOUNT('Change Impact Assessment'[CR ID])`; `Departments Assessed = DISTINCTCOUNT('Change
  Impact Assessment'[Department])`; `Assessed Schedule Impact Days = SUM('Change Impact
  Assessment'[Schedule Impact Days])`; `Assessed Cost Impact = SUM('Change Impact Assessment'[Cost
  Impact])`.
- **Schema additions require an Allen republish** from Power BI Desktop — a data-only service refresh
  won't surface the new table/relationship/measures (the 2b/2c-1 precedent). This republish folds in
  with the still-pending Decision + Project Baseline + Phase Gate Log republish.

## Migrations

`db/15_impact_assessment_external_ref.sql` — additive, `IF NOT EXISTS`, applied live via inline
psycopg (never the loader), appended to the loader DDL tuple. The only migration in 2c-2.

## Error handling, testing, out of scope

Same airlock: failed items → `SyncStatus=Error` + message; lost write-backs heal; one bad item never
blocks the batch; exit 1 on any error. Pure logic unit-tested (validator: every required-field and
domain rule, submitter present/absent via fallback, int/numeric coercion + blank→NULL; builder shape;
`impact_id` uuid5 determinism). I/O verified live in T4–T5 + the T7 e2e. **Shared-file discipline:**
both syncs are live (5:30/5:40 AM) — keep dry-run output byte-identical for the other artifacts when
touching `sync_artifacts.py`. Out of scope for 2c-2: no `(cr_id, department)` uniqueness (a dept may
re-assess); CR-status auto-derivation from assessments; a Department-dim relationship; and everything
in 2c-3…2c-6 (documents, RACI, versions, e-sig, governance CRs).
