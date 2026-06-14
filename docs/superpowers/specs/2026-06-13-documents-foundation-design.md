# Documents Foundation — Design (Phase 2c-3)

Status: approved 2026-06-13 (plan-mode review). Third sub-stage of the decomposed Phase 2c
(2c-1 Baselines + Phase Gates → 2c-2 impact-assessment authoring → **2c-3 documents foundation** →
2c-4 RACI → 2c-5 versions + e-sig → 2c-6 governance CRs). Full arc: the approved plan
(`~/.claude/plans/lets-plan-phase-two-foamy-turing.md`). This spec covers **2c-3 only** — the
**keystone**: it seeds the empty document lookups and makes controlled documents authorable, which is
what 2c-4/2c-5/2c-6 attach to (they key children to a `document` by its `document_id`).

## Problem

`doc_mgmt.document` (the "spine of the DM schema") exists but is **unreachable**: the
`document_type` and `compliance_frame` lookup catalogs are **empty**, there is no authoring surface,
and no `bi.document` view. Nothing downstream (RACI, versions, e-signature attestations, governance
change requests) can be built until documents can be created and referenced.

## Decisions

- **One-time idempotent lookup seeder** (the new shape): `tools/seed_doc_lookups.py` populates the 8
  `document_type` codes + 7 `compliance_frame` rows via `INSERT … ON CONFLICT (code) DO NOTHING`.
  It **never drops anything** (it is NOT `load_postgres.py`); a parity block in `load_postgres.py`
  ensures from-scratch rebuilds also seed them. Frames are foundation for later sub-stages; 2c-3
  authors no document↔frame links (the `document` table has no frame column).
- **One new authoring surface** synced by the registry-driven `tools/sync_artifacts.py`:
  **"Controlled Documents"** → `doc_mgmt.document`. This is the first **org-wide (project-less)**
  surface and the first with **composite code-minting** (`doc_id = THG-{DEPT}-{TYPE}-{NNN}`,
  per-(department, type) sequence).
- **Real FK constraints** (`db/04`): `document_type_id`, `primary_department_id`, `owner_person_id`,
  `approver_person_id` are enforced by the DB (unlike the pmbok `db/10` app-resolved convention). The
  processor resolves all four up front and airlocks any miss — a blank/unknown input never reaches a
  raw DB FK error.
- **Permissive, audited status** (`DRAFT/REVIEW/BASELINE/AMENDED/RETIRED`): any transition the PM sets
  is applied and written to `doc_mgmt.audit_trail_entry` (`DOCUMENT_CREATE` on insert,
  `DOCUMENT_STATUS` on change). No legality gate in v1 (the trust-based-v1 principle).
- **Smart defaults** so a sparse List never hits a NOT NULL: `lifecycle_phase`/`review_cycle` default
  from the chosen `document_type`; `current_version` defaults to `"0.1"`; `storage_path` defaults to
  `{storage_system}/{doc_id}`; `status`/`classification`/`storage_system` use the DB defaults.
- New `bi.document` view + one new TMDL model table; **no sample-document seeding** (consistent with
  2b/2c-1/2c-2 — the e2e files real rows, not fixtures).

## "Controlled Documents" List → `doc_mgmt.document`

Confirmed DDL (`db/01_dm.sql:74-96`). **NOT NULL, no default (must supply):** `doc_id VARCHAR(30)
UNIQUE`, `document_type_id`, `primary_department_id`, `title`, `lifecycle_phase`, `current_version`,
`owner_person_id`, `storage_path`. **NOT NULL, has default:** `status` (`DRAFT`), `review_cycle`
(`Annual`), `classification` (`Confidential – Internal`), `storage_system` (`PMO SharePoint`),
`created_at`/`updated_at` (`now()`). **Nullable:** `subtitle`, `approver_person_id`,
`next_review_due`, `intake_id`, `retired_at`, `superseded_by_document_id`. **No `project_id`** —
org-wide; `intake_id` is the only (optional) project link.

List columns (creator helpers; person columns for Owner/Approver):
- **Required:** `DocTypeCode` (choice = 8 type codes) → `document_type_id`; `Title` (text);
  `PrimaryDepartment` (choice = 8 `DEPARTMENTS`) → `(department_id, code)`; `Owner` (person,
  +LookupId, **author-fallback**) → `owner_person_id`.
- **Optional (smart defaults):** `Subtitle`; `Approver` (person, nullable); `LifecyclePhase`
  (choice = 9 doc phases, defaults from the type); `Status` (choice, default `DRAFT`); `ReviewCycle`
  (choice = 6, defaults from the type); `Classification` (choice = 4); `StorageSystem` (choice = 7);
  `StoragePath` (text, defaults to `{storage_system}/{doc_id}`); `NextReviewDue` (date); `IntakeID`.
- **Write-back:** `DocID` (the minted `doc_id`) + `SyncStatus`/`SyncMessage`. `document_list_id`
  merged into `db/.m365.local.json`.

## Migrations

- `db/16_document_external_ref_and_bi.sql`: `ALTER TABLE doc_mgmt.document ADD COLUMN IF NOT EXISTS
  external_ref VARCHAR(64) UNIQUE;` + `CREATE OR REPLACE VIEW bi.document` (joins document_type +
  department + owner person, **LEFT JOIN** approver person — nullable; exposes `doc_id, doc_type_code,
  doc_type_name, primary_department, title, subtitle, lifecycle_phase, status, current_version,
  owner_name, approver_name, review_cycle, next_review_due, classification, storage_system,
  storage_path, intake_id, created_at`). Additive; inline psycopg; appended to the loader DDL tuple.

## Pure logic (`tools/artifact_lib.py`, unit-tested)

- Constants: `DOC_TYPE_CODES` (8), `DOC_STATUSES` (5), `DOC_LIFECYCLE_PHASES` (9 — the document enum,
  broader than the 5 project phases), `REVIEW_CYCLES` (6), `DOC_CLASSIFICATIONS` (4),
  `STORAGE_SYSTEMS` (7).
- `next_doc_id(existing, dept_code, type_code)` — `_DOC_ID = re.compile(r"^THG-[A-Z]+-[A-Z]+-(\d{3,})$")`,
  max+1 over the per-(dept,type) `existing`, `THG-{dept}-{type}-{NNN:03d}`, **widen-not-truncate**
  (the `next_risk_code` clone).
- `validate_document(it)` — required `DocTypeCode`∈`DOC_TYPE_CODES`, `Title`, `PrimaryDepartment`∈
  `DEPARTMENTS`, `Owner` resolvable (picker or author-fallback); domain membership for
  Status/LifecyclePhase/ReviewCycle/Classification/StorageSystem when present.
- `build_document_row(it, type_id, dept_id, owner_id, approver_id, lifecycle_phase, review_cycle,
  doc_id)` — column dict; applies `current_version="0.1"` and the StoragePath default.

## `process_document` (`tools/sync_artifacts.py`)

Mirrors `process_change_request` (create / update+status-audit / heal). `DOC_FIELDS` /
`normalize_document` (Owner author-fallback, mirroring `normalize_change_request`) / `DOC_SELECT`;
new resolvers `department_by_name(conn, name)` → `(department_id, code)` and
`document_type_by_code(conn, code)` → `(document_type_id, lifecycle_phase, default_review_cycle)`
(promote `sync_intake`'s inline `department WHERE name=%s` to a shared helper); registry entry at the
**end of `ARTIFACTS`** (after `phase_gate`).

Per item:
1. `validate_document`; resolve type, dept (→ id + code), owner (author-fallback), approver
   (optional) — any miss → Error. Derive `lifecycle_phase`/`review_cycle` from the type when blank.
2. **New** → mint `doc_id` (`existing = SELECT doc_id FROM doc_mgmt.document WHERE
   primary_department_id=%s AND document_type_id=%s`) → INSERT (`document_id =
   uuid5(NS,"thg/artifact/document/{item_id}")`, `external_ref = item_id`) →
   `write_trail("DOCUMENT_CREATE", actor=owner, "document", document_id, None, {status})` →
   write-back DocID + Synced.
3. **Existing** → `row_changed` → UPDATE the mutable cols; `write_trail("DOCUMENT_STATUS", …)` when
   `status` changes; heal a lost write-back; no-op when unchanged.
4. **Immutable-identity guard** → if the resolved `document_type_id` or `primary_department_id`
   differs from the stored row (the two parts that define the `doc_id`), reject:
   `"DocTypeCode/PrimaryDepartment changed after sync - create a new document instead"`. Orphan-keep.

## Audit trail
Reuse `tools/audit_lib.write_trail` (inside the per-item txn): `DOCUMENT_CREATE` (after INSERT),
`DOCUMENT_STATUS` (`before/after = {"status": …}` when status changes). Actor = resolved owner.

## BI + model (`db/16` view; TMDL)
- `bi.document` (above).
- New `Controlled Document.tmdl` (mirror `Decision.tmdl`: hidden `Document ID` key + `bi.document`
  M-partition). One relationship `Controlled Document[Department]` → `Department[Department]` (the
  existing `Risk.Department → Department.Department` precedent — single-direction, no ambiguity, since
  documents don't reach Project). Measures (folder **Documents**): Controlled Documents, Draft
  Documents, Baseline Documents, Retired Documents, Documents Due for Review.
- **Schema additions require an Allen republish** (folds into the standing Decision / Project Baseline
  / Phase Gate Log / Change Impact Assessment republish).

## Error handling, testing, out of scope
Same airlock: failed items → `SyncStatus=Error` + message; lost write-backs heal; one bad item never
blocks the batch; exit 1 on any error. Pure logic unit-tested (minting widen + per-(dept,type)
scoping; every validator rule; builder defaults). I/O verified live in T5–T6 + the T8 e2e. The
**seeder is a one-time idempotent run** that gates the stage — never `load_postgres.py`. Out of scope
for 2c-3: document↔compliance-frame links, `controlled_template` provisioning, the
version/approval/RACI/gov-CR surfaces (2c-4…2c-6), a status-legality gate, and a "Document Control"
report page (measures land now; visuals later).
