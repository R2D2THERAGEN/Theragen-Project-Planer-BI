# Schedule Activities + Auto-WBS — Design (Phase 2a)

Status: approved 2026-06-13 (plan-mode review). Stage 2a of the staged Phase 2
roadmap (2a Schedule & WBS → 2b Change & Approval → 2c Versioning & Handoffs);
full arc in the approved plan. This spec covers **2a only**.

## Problem

Intake-born projects (e.g. APNE / THG-IT-005) have risks, milestones, and status
reports but **no schedule activities or WBS** — so the status page's **Key Project
Areas** panel is empty, activity-sourced Accomplishments/Next-Steps never appear, and
the **Schedule & Milestones** report page has nothing to show. There is no surface for
PMs to enter a schedule.

## Decisions

- **Surface:** one new SharePoint List, "Project Activities", synced by the existing
  registry-driven `tools/sync_artifacts.py`. PMs enter activities; the sync derives WBS.
- **WBS model: two-tier**, reproducing the seeded topology exactly (level-1 workstream
  → level-2 work package → activity linked to the work package). This is what makes the
  existing Workstream measures roll up under Key Project Areas — verified against the
  seeded demo projects, which light up this way.
- **Activity Department: explicit choice** per activity (the Schedule page groups
  "Activities by department and status"), not derived from the owner.
- **Derived, never typed:** `duration_days` (working days), `wbs_element_id` (reconciled),
  `activity_code` (minted). WBS is **entirely derived** from the activity set — PMs never
  touch WBS directly.
- **Zero view/model/report changes** — `bi.schedule_activity`, `bi.wbs_element`, and all
  Schedule/Workstream measures already exist; 2a only feeds rows.

## "Project Activities" List → `pmbok.schedule_activity` (+ derived `pmbok.wbs_element`)

PM-entered columns: `Title`→name, `ProjectCode`, `Workstream` (text), `WorkPackage`
(text), `StartPlanned`/`FinishPlanned` (dateOnly, required), `StartActual`/`FinishActual`
(dateOnly), `Owner` (person), `Department` (choice — the 8 Theragen departments),
`ActivityStatus` (choice: Not started/In progress/At risk/Done/Cancelled, default
Not started), `PctComplete` (number 0–100, default 0), `ActivityCode` (text, write-back),
plus `SyncStatus`/`SyncMessage`.

Derived: `duration_days` = working days (Mon–Fri inclusive) between planned start and
finish; `wbs_element_id` from the reconciled level-2 work package; `activity_code` minted
`{work_package_wbs_code}-A{n}` (matches seed `1.1-A1`), per work package, append-only.

Validation (pure, tested): required Workstream, WorkPackage, Title, ProjectCode,
StartPlanned, FinishPlanned, Owner, Department, ActivityStatus; FinishPlanned ≥
StartPlanned; PctComplete 0–100; ActivityStatus & Department in their domains; **Done
requires FinishActual** (mirrors the milestone Achieved-requires-ActualDate rule — the
Recent Accomplishment DAX filters `Activity Status = "Done"` AND non-blank Actual Finish);
owner resolves to a `doc_mgmt.person` (airlock); ProjectCode exists; ProjectCode-change
guard on update.

Activity status domain (exact, from SampleData + the Next-Step DAX which excludes
{Done, Cancelled}): **Not started, In progress, At risk, Done, Cancelled**.

## Auto-WBS (derived per project from the activity set — two-tier)

Per project, from its activity rows:
- distinct `Workstream` → **level-1** node (`level=1`, `owner_role="Workstream Lead"`);
- distinct `(Workstream, WorkPackage)` → **level-2** node (`level=2`, parent = its
  workstream, `owner_role="Work Package Owner"`);
- each activity links to its **level-2** node's `wbs_element_id`.

Node identity is **keyed on names** for stability:
`uuid5(NS, "thg/wbs/{project_code}/ws/{workstream}")` for L1,
`uuid5(NS, "thg/wbs/{project_code}/wp/{workstream}/{workpackage}")` for L2. `wbs_code` is
minted **append-only** — L1 gets the next integer not already used in the project, L2 gets
`{parent_code}.{next child int}`; existing codes never renumber (codes are display labels;
Key Project Areas groups by Deliverable=name). `owning_department` = the node's
first-seen activity's Department; `estimated_effort_hrs`/`estimated_cost`/`accepted_by`
null. WBS rows carry **no external_ref** (name-keyed, like `status_report_area`).

WBS nodes are **kept** when their activities are later removed (delete-keep policy); an
emptied workstream simply renders "NOT STARTED" in Key Project Areas.

## Sync architecture (extends `tools/sync_artifacts.py` + `tools/artifact_lib.py`)

A new `activity` registry entry. In `main()`, the activity List gets a **per-project WBS
reconciliation pre-pass** — analogous to the report `area_map`: group fetched activities
by ProjectCode, and for each project upsert the L1/L2 WBS nodes (insert new by name-keyed
uuid5, mint codes append-only continuing from existing, update `owning_department` if
changed), returning a `wbs_map[(project_code, workstream, workpackage)] = wbs_element_id`.
The pre-pass writes WBS in its own per-project transaction(s); in `--dry-run` it computes
the would-be ids/codes from existing rows without writing.

Then each activity is processed per-item (the `process_risk` skeleton): resolve project +
owner + its work-package `wbs_element_id` from `wbs_map`, compute duration, mint
`activity_code` (per work package), INSERT/UPDATE `schedule_activity` with `external_ref` =
List item id. Reuses wholesale the existing full-row-compare update (`row_changed`),
write-back healing, orphan-keep, ProjectCode-change guard, per-item transaction, and
autocommit machinery.

Pure additions to `artifact_lib.py` (tested): `ACTIVITY_STATUSES`, `working_days`,
`next_activity_code`, `next_wbs_code`, `validate_activity`, `build_activity_row`,
`build_wbs_row`.

## Migration & wiring

- `db/07_activity_external_ref.sql`: `ALTER TABLE pmbok.schedule_activity ADD COLUMN IF
  NOT EXISTS external_ref VARCHAR(64) UNIQUE;` — applied live via inline psycopg (never the
  destructive loader), appended to the loader DDL tuple. WBS needs no external_ref.
- Add "Project Activities" to `tools/create_artifact_lists.py` (+ `activity_list_id` in
  `db/.m365.local.json`). **No schedule change** — the 5:40 AM `Theragen\SyncArtifacts`
  task already runs `sync_artifacts.py`.

## What lights up (verified, zero report/view/model edits)

- **Key Project Areas** — `WBS Element[Deliverable]` rows with Workstream Start/Target,
  duration-weighted % complete, COMPLETED/AT RISK/NOT STARTED/ON TRACK rollup.
- **Recent Accomplishments** — Done activities with Actual Finish in the last 35 days.
- **Upcoming Next Steps** — non-Done/Cancelled activities with Planned Finish in
  TODAY−7 … TODAY+45.
- **Schedule & Milestones page** — activities by department & status, % complete, overdue,
  on-time completion.

`bi.schedule_activity` (JOINs WBS→project→person) and `bi.wbs_element` already exist, so a
resolvable owner and a valid WBS link are mandatory — both guaranteed by the airlock +
reconciliation.

## Error handling, testing, out of scope

Same airlock as the rest: every failed activity gets `SyncStatus=Error` + message on its
List row; lost write-backs heal; one bad item never blocks the batch; exit 1 on any error.
Pure logic only is unit-tested (working-day counting incl. weekends/single-day/inverted,
code minting incl. widen + per-WBS scoping, validators incl. Done-needs-FinishActual,
builders); I/O verified live in T4–T6 and the T8 e2e. Out of scope for 2a: schedule
dependencies / network analysis, risk responses, the governance stages (2b/2c), and any
WBS authoring surface (WBS stays fully derived).
