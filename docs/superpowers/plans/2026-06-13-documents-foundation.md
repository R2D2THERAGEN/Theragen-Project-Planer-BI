# Documents Foundation — Implementation Plan (Phase 2c-3)

Design: [`2026-06-13-documents-foundation-design.md`](../specs/2026-06-13-documents-foundation-design.md).
Subagent per task, two-stage review, a final whole-stage review, live verification on the real
`doc_mgmt` schema. `python -m pytest tests/ -q` green at every commit.

Patterns to mirror (read, do not reinvent):
- `process_change_request` (`tools/sync_artifacts.py`) — create / update + status-audit / heal skeleton.
- `normalize_change_request` — Owner author-fallback + date-default.
- `next_risk_code` / `next_cr_code` (`tools/artifact_lib.py`) — the regex + max+1 widen minting.
- `sync_intake.py` department lookup (`department WHERE name=%s`) — promote to a shared resolver.
- `audit_lib.write_trail` + its `process_change_request` call sites (`CR_CREATE`, `CR_STATUS`).
- `load_postgres.py` `uid()` / `insert()` helpers + the DM seed section (for the parity block).
- `Decision.tmdl` + the `Risk.Department → Department.Department` relationship in `relationships.tmdl`.

## T1 — `tools/seed_doc_lookups.py` (lookup seeder) + parity block
New idempotent script: connect via `db/.pg.local.json`, `INSERT … ON CONFLICT (code) DO NOTHING`
into `doc_mgmt.document_type` (8 codes, each with `lifecycle_phase`/`default_review_cycle`/
`requires_approval`) and `doc_mgmt.compliance_frame` (7 frames, each with `authority`/`applies_to`).
uuid5-keyed ids. Add the **same rows** to `load_postgres.py`'s DM seed section (via `uid()`/`insert()`)
so from-scratch rebuilds match. Run once live; `SELECT count(*)` = 8 / 7. **Never** run
`load_postgres.py`. Commit.

## T2 — `db/16_document_external_ref_and_bi.sql`
`ALTER TABLE doc_mgmt.document ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;` +
`CREATE OR REPLACE VIEW bi.document` (joins document_type + department + owner person, LEFT JOIN
approver). Append to the loader DDL tuple. Apply live via inline psycopg; `information_schema` (column)
+ `SELECT * FROM bi.document LIMIT 0` (view compiles) verify. Commit.

## T3 — `artifact_lib` document logic + tests (tests first)
Constants (`DOC_TYPE_CODES`, `DOC_STATUSES`, `DOC_LIFECYCLE_PHASES`, `REVIEW_CYCLES`,
`DOC_CLASSIFICATIONS`, `STORAGE_SYSTEMS`), `next_doc_id`, `validate_document`, `build_document_row`.
Tests in `tests/test_artifact_lib.py` first:
- `next_doc_id`: `[]` → `-001`; widen past 999; per-(dept,type) scoping (different families number
  independently); ignores non-matching codes.
- `validate_document`: all-valid → `[]`; each missing required flagged; unknown DocTypeCode/Department
  flagged; each domain-enum violation (status/lifecycle/cycle/classification/storage) flagged.
- `build_document_row`: full shape; `current_version="0.1"`; StoragePath default; nullable subtitle/
  approver/next_review_due pass through.
Green. Commit.

## T4 — "Controlled Documents" List in `create_artifact_lists.py`
Add the `"document_list_id": ("Controlled Documents", [...])` entry (columns per the spec; choices use
`al.DOC_TYPE_CODES`, `al.DEPARTMENTS`, `al.DOC_STATUSES`, `al.DOC_LIFECYCLE_PHASES`,
`al.REVIEW_CYCLES`, `al.DOC_CLASSIFICATIONS`, `al.STORAGE_SYSTEMS`; Owner/Approver person columns;
`DocID` write-back). Run live (idempotent); confirm `document_list_id` merged into
`db/.m365.local.json`. Commit.

## T5 — sync read / normalize / dry-run + resolvers
`DOC_FIELDS`, `normalize_document` (Owner author-fallback, mirroring `normalize_change_request`),
`DOC_SELECT`; resolvers `department_by_name(conn, name)` → `(department_id, code)` and
`document_type_by_code(conn, code)` → `(document_type_id, lifecycle_phase, default_review_cycle)`;
`process_document` **stub** (validate → resolve all four ids → derive lifecycle/cycle → return a
`DRY …` intent, no writes); registry entry at the **end of `ARTIFACTS`** (after `phase_gate`).
Dry-run live on one probe document. **Verify the other artifacts' dry-run output is byte-identical.**
Commit.

## T6 — write path + audit + guards (live)
Flesh out `process_document`: mint `doc_id` + INSERT + `DOCUMENT_CREATE` audit + DocID write-back on
new; `row_changed` → UPDATE the mutable cols + `DOCUMENT_STATUS` audit (status change) + heal on edit;
the **immutable-identity guard** (resolved `document_type_id`/`primary_department_id` ≠ stored →
Error); orphan-keep. Live on a probe: create a `DRAFT` doc (e.g. `THG-OPS-CHR-001`) → `doc_mgmt.document`
row + minted DocID + `DOCUMENT_CREATE` audit; flip `Status`→`BASELINE` → UPDATE + `DOCUMENT_STATUS`
audit; immediate re-run → no-op; change `DocTypeCode` → Error (identity guard); delete the List row →
orphan-keep INFO. Probe cleanup (delete the DB row + List item). Commit.

## T7 — TMDL model table + relationship + measures
New `Theragen Project Planner.SemanticModel/definition/tables/Controlled Document.tmdl` (mirror
`Decision.tmdl`: hidden `Document ID` key + `bi.document → SelectColumns → RenameColumns` partition;
date columns `Next Review Due`/`Created Date` with `UnderlyingDateTimeDataType = Date`). Add the
relationship `Controlled Document[Department]` → `Department[Department]` to `relationships.tmdl`
(match the existing `Risk.Department → Department.Department` form). Register in `model.tmdl`
(`ref table` + `PBI_QueryOrder`). Add 5 measures to `_Measures.tmdl` (folder **Documents**, fresh
uuid5 lineageTags). Verify: Tabular Editor BPA **zero violations** + `python tools/validate_pbir.py`.
Republish note. Commit. (Use the Edit tool for the existing-file TMDL changes — a file-protect hook
blocks shell overwrites of tracked files; generate the new table file with a Python `open(...,"w")`
since creating a new file is allowed.)

## T8 — docs + e2e + final review
- `docs/artifact-entry-setup.md`: new **§Q Controlled Documents** (columns; the DocTypeCode/
  PrimaryDepartment-define-the-DocID rule; the type-derived lifecycle/cycle defaults; the permissive
  status + `DOCUMENT_CREATE`/`DOCUMENT_STATUS` audit; org-wide note); update the title + Lists-at-a-
  glance inventory; add Appendix behaviour rows. `README.md`: new **Documents** paragraph.
- **e2e:** file 2–3 real controlled documents (`THG-OPS-CHR-001` a charter, `THG-IT-SOP-001` an SOP) →
  `python tools/sync_artifacts.py` → `SELECT … FROM bi.document` probe → `python tools/service_refresh.py`.
- **Final** whole-stage review (most capable model) over the full 2c-3 diff; fix loop. pytest green.
  Commit.

## Verification summary
- Unit: `next_doc_id` + `validate_document` + `build_document_row` (T3).
- One-time seed: `document_type`=8, `compliance_frame`=7 (T1).
- Live I/O: dry-run resolution (T5); insert/mint/audit/update/status-audit/identity-guard/orphan (T6).
- Model: BPA zero + `validate_pbir` (T7).
- e2e: `bi.document` populated with minted doc_ids; idempotent re-run = no-ops (T8).
