# Document RACI — Design (Phase 2c-4)

Status: approved 2026-06-13 (plan-mode review). Fourth sub-stage of the decomposed Phase 2c
(2c-1 Baselines + Phase Gates → 2c-2 impact-assessment authoring → 2c-3 documents foundation →
**2c-4 RACI** → 2c-5 versions + e-sig → 2c-6 governance CRs). Full arc: the approved plan. This spec
covers **2c-4 only** — the **third parent-child surface**, attaching a per-department R/A/C/I
responsibility matrix to the controlled documents built in 2c-3.

## Problem

2c-3 made controlled documents authorable, but a document carries no record of **who is responsible
for it** — no Responsible / Accountable / Consulted / Informed assignment per department. The
`doc_mgmt.raci_assignment` table exists for exactly this but is empty, has no authoring surface, and
no `bi.raci_assignment` view.

## Decisions

- One new authoring surface synced by the registry-driven `tools/sync_artifacts.py`:
  **"Document RACI"** → `doc_mgmt.raci_assignment`.
- **Parent-child by `doc_id`** (the 2c-2 pattern, reused): each List row names its parent document by
  the human `doc_id` (e.g. `THG-OPS-CHR-001`). `doc_id` is **globally UNIQUE** (`db/01_dm.sql:76`), so
  the parent resolves with a single-key lookup `resolve_parent_document(conn, doc_id)` — simpler than
  the CR's per-project scope. Registry orders `document` before `raci`, so a same-run parent is
  committed when its child resolves (autocommit).
- **Assignee is a department**, not a person (`fk_raci_assignment_department_id`). RACI is recorded
  per (document, department): each row says "for this document, this department is R/A/C/I."
- **Single-char roles** `R` / `A` / `C` / `I` (`_source_extracts/DM_Enumerations.tsv`), VARCHAR with no
  DB CHECK → enforced in `validate_raci`.
- **Effective-dated**: `valid_from` (NOT NULL, defaults to the item created date) + `valid_to`
  (nullable, open-ended).
- **No audit trail** — RACI is descriptive assignment metadata, not a governance state transition;
  consistent with how impact assessments (2c-2) sync without an audit row.
- **Editable** (`row_changed`); re-parent guard fixes the parent document after first sync.
- New `bi.raci_assignment` view + one new TMDL model table. **No "exactly one Accountable per
  document" / temporal-overlap validation in v1** (deferred; the matrix is recorded as authored).

## "Document RACI" List → `doc_mgmt.raci_assignment`

Confirmed DDL (`db/01_dm.sql:199-207`): `raci_id UUID PK, document_id UUID NOT NULL, department_id
UUID NOT NULL, role VARCHAR NOT NULL, touchpoint VARCHAR(300), valid_from DATE NOT NULL, valid_to
DATE`. **NOT NULL to satisfy:** `document_id`, `department_id`, `role`, `valid_from`. **Nullable:**
`touchpoint`, `valid_to`. Both FKs (`document_id`→document, `department_id`→department) are **real DB
constraints** (`db/04`) → resolve both up front, airlock misses. No `external_ref` yet.

List columns:
- **Required:** `ParentDocID` (text) → parent `doc_id`; `Department` (choice = 8 `DEPARTMENTS`) →
  `department_id`; `Role` (choice = `R`/`A`/`C`/`I`) → `role`.
- **Optional:** `Touchpoint` (ml) → `touchpoint`; `ValidFrom` (date) → `valid_from`, **defaults to the
  item `createdDateTime` date** when blank; `ValidTo` (date) → `valid_to` (open-ended when blank).
- `SyncStatus`/`SyncMessage`. **No write-back code** (`raci_id` is uuid5). `raci_list_id` merged into
  `db/.m365.local.json`.

## Migration

`db/17_raci_external_ref_and_bi.sql`: `ALTER TABLE doc_mgmt.raci_assignment ADD COLUMN IF NOT EXISTS
external_ref VARCHAR(64) UNIQUE;` + `CREATE OR REPLACE VIEW bi.raci_assignment` (`raci_id,
document_id, doc_id, doc_title, department_id, department, role, role_name [CASE R/A/C/I →
Responsible/Accountable/Consulted/Informed], touchpoint, valid_from, valid_to`; JOIN document +
department). Additive; inline psycopg; appended to the loader DDL tuple.

## Pure logic (`tools/artifact_lib.py`, unit-tested)

- `RACI_ROLES = ["R", "A", "C", "I"]`.
- `validate_raci(it)` — required non-blank `ParentDocID`, `Department`, `Role`; `Department ∈
  DEPARTMENTS`; `Role ∈ RACI_ROLES`; `ValidTo ≥ ValidFrom` when both present (`ValidFrom` is defaulted
  in the normalizer, so never flagged here).
- `build_raci_row(it, document_id, department_id)` → `{document_id, department_id, role, touchpoint,
  valid_from, valid_to}` (blank `touchpoint`/`valid_to` → None).

## `process_raci_assignment` (`tools/sync_artifacts.py`)

Mirrors `process_impact_assessment` (no audit). `RACI_FIELDS` / `normalize_raci` (ValidFrom
createdDate default) / `RACI_SELECT` (`external_ref, raci_id, document_id, department_id, role,
touchpoint, valid_from, valid_to`); new `resolve_parent_document(conn, doc_id)` →
`SELECT document_id FROM doc_mgmt.document WHERE doc_id=%s`. Registry entry at the **end of
`ARTIFACTS`** (after `document`). Per item:
1. `validate_raci`; resolve document (Unknown ParentDocID → Error) + department (`department_by_name`,
   reused from 2c-3; unknown → Error).
2. **New** → `INSERT` (`raci_id = uuid5(NS,"thg/artifact/raci/{item_id}")`, `external_ref = item_id`)
   → write-back `Synced`.
3. **Existing** → `row_changed` over `MUTABLE` (`department_id, role, touchpoint, valid_from,
   valid_to`) → `UPDATE` + heal; no-op when unchanged.
4. **Re-parent guard** → resolved `document_id` ≠ stored → Error `"ParentDocID changed after sync -
   create a new RACI assignment instead"`. Orphan-keep. (Department/Role edit in place — only the
   parent document is fixed, the 2c-2 precedent.)

## BI + model (`db/17` view; TMDL)
- `bi.raci_assignment` (above).
- New `Document RACI.tmdl` (mirror `Decision.tmdl`: hidden `RACI ID` + hidden `Document ID` keys +
  `bi.raci_assignment` M-partition; columns RACI ID, Document ID, Doc ID, Document Title, Department,
  Role, Role Name, Touchpoint, Valid From [date], Valid To [date]).
- **One relationship** `Document RACI[Document ID]` → `Controlled Document[Document ID]`
  (single-direction). **No Department-dim relationship** — Controlled Document already relates to
  Department, so a second path would be ambiguous; Department slicing comes from the local column.
- Measures (folder **Documents**): RACI Assignments, Documents with RACI, Accountable Assignments
  (`Role="A"`), Responsible Assignments (`Role="R"`), Current RACI Assignments (`valid_to` blank or ≥
  TODAY()).
- **Schema additions require an Allen republish** (folds into the standing Decision / Project Baseline
  / Phase Gate Log / Change Impact Assessment / Controlled Document republish).

## Error handling, testing, out of scope
Same airlock: failed items → `SyncStatus=Error` + message; lost write-backs heal; one bad item never
blocks the batch; exit 1 on any error. Pure logic unit-tested (validator rules; builder shape). I/O
verified live in T4–T5 + the T7 e2e. Out of scope for 2c-4: "exactly one Accountable per document" /
temporal-overlap validation; per-person RACI (the table is per-department); compliance-frame mapping;
the version/e-sig (2c-5) and governance-CR (2c-6) surfaces.
