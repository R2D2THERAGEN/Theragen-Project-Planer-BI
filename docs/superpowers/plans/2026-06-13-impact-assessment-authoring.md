# Change Impact Assessment Authoring — Implementation Plan (Phase 2c-2)

Design: [`2026-06-13-impact-assessment-authoring-design.md`](../specs/2026-06-13-impact-assessment-authoring-design.md).
Build order is the proven machinery: subagent per task, two-stage review (spec compliance → quality),
a final whole-stage review, live verification on APNE (THG-IT-005). `python -m pytest tests/ -q` green
at every commit. The parent CRs `C-001`/`C-002` already exist on APNE from the 2b e2e.

Patterns to mirror (read, do not reinvent):
- `process_decision` (`tools/sync_artifacts.py`) — create/update/heal skeleton + write-back.
- `process_baseline` (`tools/sync_artifacts.py`) — the `(project_id, cr_code) → cr_id` parent lookup.
- `normalize_change_request` (`tools/sync_artifacts.py`) — author-fallback + date-default.
- `validate_decision` / `build_decision_row` (`tools/artifact_lib.py`).
- The `"decision_list_id"` entry (`tools/create_artifact_lists.py`) and the registry
  (`tools/sync_artifacts.py` `ARTIFACTS`).
- `Decision.tmdl` — the model-table + relationship template.

## T1 — Migration `db/15`
`db/15_impact_assessment_external_ref.sql`: `ALTER TABLE pmbok.change_impact_assessment ADD COLUMN
IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;`. Append the file to the loader DDL tuple in
`tools/load_postgres.py` (the existing `db/12`–`db/14` entries are the precedent). Apply live via
inline psycopg (the standard one-off connect; **never** run `load_postgres.py`). Verify via
`information_schema.columns` that the column exists. **Commit.**

## T2 — `artifact_lib` + tests (tests first)
Add `validate_impact_assessment(it)` and `build_impact_assessment_row(it, cr_id, submitted_by_person_id,
submitted_at)` per the spec (reuse the existing `DEPARTMENTS`, `_blank`). Write tests in
`tests/test_artifact_lib.py` first:
- validator: all-valid → `[]`; each missing required (`ProjectCode`/`ParentCRCode`/`Department`/
  `SubmittedBy`) flagged; `Department` not in domain flagged; non-integer `ScheduleImpactDays` and
  non-numeric `CostImpact` flagged; blank numerics accepted; submitter present via fallback accepted.
- builder: full row shape; blank nullable fields → `None`; `int()`/`float()` coercion.
Green. **Commit.**

## T3 — "Change Impact Assessments" List in the creator
Add the `"impact_assessment_list_id": ("Change Impact Assessments", [...])` entry to
`tools/create_artifact_lists.py` `LISTS` (columns per the spec; `ParentCRCode` as `text`, `Department`
as `choice(al.DEPARTMENTS)`, the two numerics, the two ml impact fields, `SubmittedBy` person,
`SubmittedDate` date_only, + `BOOKKEEPING`). Run live (idempotent create-if-absent); confirm
`impact_assessment_list_id` is merged into `db/.m365.local.json`. **Commit.**

## T4 — sync read / validate / dry-run + parent-resolution stub
In `tools/sync_artifacts.py`: `IMPACT_FIELDS`, `normalize_impact_assessment` (author-fallback +
date-default, mirroring `normalize_change_request`), `IMPACT_SELECT`, and `process_impact_assessment`
as a **stub** (validate → resolve project → resolve parent `cr_id` → resolve submitter → return a
`DRY ...` intent string; **no writes**). Add the registry entry after `change_request`. Dry-run live
against one probe row (a CIA pointing at APNE `C-001`). Confirm the parent resolves and the unknown-CR
path errors cleanly. **Verify the dry-run output for the other artifacts is byte-identical** to before
(shared-file discipline; both syncs live). **Commit.**

## T5 — write path (insert + update/heal + re-parent guard)
Flesh out `process_impact_assessment`: real `INSERT` + write-back on new; `row_changed` → `UPDATE` the
mutable cols + write-back on change; heal a lost write-back; no-op when unchanged; the **re-parent
guard** (resolved `cr_id` ≠ stored `cr_id` → Error); orphan-keep on delete. Live on APNE:
1. file a CIA on `C-001` (Department `Finance / Procurement`, `ScheduleImpactDays=5`, `CostImpact=2500`)
   → `pmbok.change_impact_assessment` row + `Synced` write-back;
2. immediate re-run → no-op;
3. edit `ScheduleImpactDays` → targeted UPDATE;
4. flip `ParentCRCode` → `C-002` → Error (re-parent guard), DB row unchanged;
5. delete the List row → orphan-keep INFO, DB row retained.
Clean up the probe row(s). **Commit.**

## T6 — TMDL model table + relationship + measures
New `Theragen Project Planner.SemanticModel/definition/tables/Change Impact Assessment.tmdl` (mirror
`Decision.tmdl`: hidden `Impact ID` key, hidden `CR ID`, the visible columns, the `bi.* → SelectColumns
→ RenameColumns` M partition over `bi.change_impact_assessment`). Add the single-direction relationship
`Change Impact Assessment[CR ID]` → `Change Request[CR ID]` to `relationships.tmdl` (match how
`Decision`'s relationship is stored). Add the 5 measures to `_Measures.tmdl` (folder **Change**, fresh
uuid5 lineageTags). Verify: `"C:\Program Files (x86)\Tabular Editor\TabularEditor.exe"
"<...SemanticModel\definition>" -A` → **zero BPA violations**; `python tools/validate_pbir.py` → pass.
Note the required Allen republish. **Commit.**

## T7 — docs + e2e + final review
- `docs/artifact-entry-setup.md`: new **§P Change Impact Assessments** (columns, the `ParentCRCode`
  parent-link rule, the 8 Department choices, author-/date-fallback, the no-reparent rule); update the
  title's List inventory line. `README.md`: extend the change-control paragraph with the
  impact-assessment surface.
- **e2e on APNE/THG-IT-005:** file 2 impact assessments across 2 departments against a real CR
  (`C-001` and/or `C-002`) → `python tools/sync_artifacts.py` → `SELECT … FROM bi.change_impact_assessment`
  probe (rows + `submitted_by_name` + `cr_code`) → `python tools/service_refresh.py`. The bi data is
  verifiable immediately; the new **model table** appears only after the Allen republish — note this in
  the e2e write-up.
- **Final** whole-stage review (most capable model) over the full 2c-2 diff; fix loop. pytest green.
  **Commit.**

## Verification summary
- Unit: `validate_impact_assessment` + `build_impact_assessment_row` (T2).
- Live I/O: parent resolution + unknown-CR error (T4); insert/update/heal/re-parent-guard/orphan (T5).
- Model: BPA zero + `validate_pbir` pass (T6).
- e2e: `bi.change_impact_assessment` populated on APNE; idempotent re-run = no-ops (T7).
