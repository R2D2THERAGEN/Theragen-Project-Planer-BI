# Document RACI — Implementation Plan (Phase 2c-4)

Design: [`2026-06-13-document-raci-design.md`](../specs/2026-06-13-document-raci-design.md).
Subagent per task, two-stage review, a final whole-stage review, live verification on the 2c-3
documents. `python -m pytest tests/ -q` green at every commit. The parent documents
`THG-OPS-CHR-001` / `THG-IT-SOP-001` already exist from the 2c-3 e2e.

Patterns to mirror (read, do not reinvent):
- `process_impact_assessment` (`tools/sync_artifacts.py`) — the parent-child child processor +
  re-parent guard (the closest template).
- `resolve_parent_cr` — the analog for `resolve_parent_document` (but single-key, doc_id is global).
- `department_by_name` (`tools/sync_artifacts.py`, from 2c-3) — resolve the assignee department.
- `db/16_document_external_ref_and_bi.sql` — the migration + bi-view style.
- `Change Impact Assessment.tmdl` + its `[CR ID] → Change Request[CR ID]` relationship — the
  model-table + single-relationship template (here: `[Document ID] → Controlled Document[Document ID]`).

## T1 — `db/17_raci_external_ref_and_bi.sql`
`ALTER TABLE doc_mgmt.raci_assignment ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;` +
`CREATE OR REPLACE VIEW bi.raci_assignment` (JOIN document + department; `role_name` CASE). Append to
the loader DDL tuple. Apply live via inline psycopg; `information_schema` (column) + `SELECT * FROM
bi.raci_assignment LIMIT 0` (view compiles) verify. Commit.

## T2 — `artifact_lib` + tests (tests first)
`RACI_ROLES`, `validate_raci`, `build_raci_row`. Tests in `tests/test_artifact_lib.py` first:
- validator: all-valid → `[]`; each missing required (`ParentDocID`/`Department`/`Role`) flagged;
  unknown Department / Role flagged; `ValidTo` < `ValidFrom` flagged; equal/after ok; blank ValidTo ok.
- builder: full shape; blank `touchpoint`/`valid_to` → None.
Green. Commit.

## T3 — "Document RACI" List in `create_artifact_lists.py`
Add the `"raci_list_id": ("Document RACI", [...])` entry (ParentDocID text, Department
`choice(al.DEPARTMENTS)`, Role `choice(al.RACI_ROLES)`, Touchpoint ml, ValidFrom/ValidTo date_only +
BOOKKEEPING). Run live (idempotent); confirm `raci_list_id` merged into `db/.m365.local.json`. Commit.

## T4 — sync read / normalize / dry-run + resolver
`RACI_FIELDS`, `normalize_raci` (ValidFrom createdDate default), `RACI_SELECT`, `resolve_parent_document`,
and `process_raci_assignment` **stub** (validate → resolve document + dept → `DRY …` intent, no
writes); registry entry after `document`. Dry-run on one probe (a RACI row on `THG-OPS-CHR-001`).
**Verify the other artifacts' dry-run output is byte-identical.** Commit.

## T5 — write path (insert + update/heal + re-parent guard) live
Flesh out `process_raci_assignment`. Live on the 2c-3 documents:
1. assign `THG-OPS-CHR-001` an `A` for `Operations / PMO` (Touchpoint "Owns and approves the charter")
   → `doc_mgmt.raci_assignment` row + `Synced`;
2. add a `C` for another department;
3. immediate re-run → no-op;
4. edit a Role → targeted UPDATE;
5. flip `ParentDocID` → `THG-IT-SOP-001` → Error (re-parent guard), DB unchanged;
6. delete a List row → orphan-keep INFO.
Probe cleanup. Commit.

## T6 — TMDL model table + relationship + measures
New `Document RACI.tmdl` (mirror `Decision.tmdl`; hidden `RACI ID` + `Document ID` keys + the
`bi.raci_assignment` partition; date columns `Valid From`/`Valid To`). Relationship `Document
RACI[Document ID]` → `Controlled Document[Document ID]` in `relationships.tmdl` (single-direction; **do
NOT** add a Department relationship). Register in `model.tmdl`. 5 measures in `_Measures.tmdl` (folder
**Documents**). Verify: Tabular Editor BPA **zero violations** + `python tools/validate_pbir.py`.
Republish note. (Generate the new table file with a Python `open(...,"w")`; use the Edit tool for the
existing-file TMDL changes — the file-protect hook blocks shell overwrites of tracked files.) Commit.

## T7 — docs + e2e + final review
- `docs/artifact-entry-setup.md`: new **§R Document RACI** (the ParentDocID link, 8 departments, R/A/C/I,
  effective-dating, the no-reparent rule, no-audit note); update title + Lists-at-a-glance; add Appendix
  rows. `README.md`: extend the Controlled documents paragraph (or a new sentence) with RACI.
- **e2e:** give `THG-OPS-CHR-001` a real R/A/C/I matrix (Operations/PMO = A, Regulatory/Quality = C,
  Clinical = I) → `python tools/sync_artifacts.py` → `SELECT … FROM bi.raci_assignment` probe →
  `python tools/service_refresh.py`.
- **Final** whole-stage review (most capable model) over the full 2c-4 diff; fix loop. pytest green.
  Commit.

## Verification summary
- Unit: `validate_raci` + `build_raci_row` (T2).
- Live I/O: parent-doc resolution + dry-run (T4); insert/update/heal/re-parent-guard/orphan (T5).
- Model: BPA zero + `validate_pbir` (T6).
- e2e: `bi.raci_assignment` populated for `THG-OPS-CHR-001`; idempotent re-run = no-ops (T7).
