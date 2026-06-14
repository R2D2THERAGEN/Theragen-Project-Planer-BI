# Governance Change Requests + Assessments — Implementation Plan (Phase 2c-6)

Design: [`2026-06-14-governance-crs-design.md`](../specs/2026-06-14-governance-crs-design.md).
Subagent per task, two-stage review, a final whole-stage review, live verification on the 2c-3
documents (`THG-OPS-CHR-001`, `THG-IT-SOP-001`). `python -m pytest tests/ -q` green at every commit
(the suite is ~90s on this archive path — expected, not a failure). **The final sub-stage of Phase 2c.**

Patterns to mirror (read, do not reinvent):
- `process_change_request` (`tools/sync_artifacts.py:980`) — the **editable + two-axis + audit**
  template for the gov-CR processor (soft-authority, mint, `CR_CREATE`/`CR_DECISION`/`CR_STATUS`).
- `process_impact_assessment` (`tools/sync_artifacts.py:1196`) — the **child-by-code, no-audit,
  re-parent-guard** template for the gov-assessment processor.
- `process_document_version` (`tools/sync_artifacts.py:1424`) — the version processor to extend for the
  LinkedCR closure (the INSERT already carries `linked_cr_id`; `VERSION_SELECT:495` already selects it).
- `next_cr_code` / `validate_change_request` / `build_cr_row` (`tools/artifact_lib.py:286/298/341`) —
  the minting + two-axis validator + builder to clone (drop ProjectCode + ChangeType).
- `resolve_parent_document` (`:403`), `project_leads` (`:420`), `person_id_by_email` (`:364`),
  `department_by_name` (`:376`), `intake_exists` (`:390`) — resolvers; add `resolve_parent_govcr` +
  `doc_leads`.
- `audit_lib.write_trail` + the `process_change_request` audit call sites.
- `db/16`/`db/17`/`db/18` — the ALTER + CREATE VIEW migration style; `Change Impact
  Assessment.tmdl` / `Decision.tmdl` — the model-table + single-relationship template.

## T1 — `db/19_govcr_external_ref_and_bi.sql`
Two `ALTER … ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE` (change_request_gov,
change_assessment_gov) + `CREATE OR REPLACE VIEW bi.change_request_gov` + `bi.change_assessment_gov` +
**widen `bi.document_version`** with `linked_cr_id`/`linked_cr_code` (LEFT JOIN change_request_gov on
`linked_cr_id`). Append to the loader tuple. Apply live; `information_schema` (both external_ref
columns) + `SELECT * FROM bi.change_request_gov/change_assessment_gov LIMIT 0` + re-`SELECT` the widened
`bi.document_version` verify. Commit.

## T2 — `artifact_lib` + tests (tests first)
`_GOVCR_CODE`, `next_govcr_code`, `validate_govcr`, `build_govcr_row`, `validate_govassessment`,
`build_govassessment_row` (reuse `CR_CLASSES`/`CR_DECISIONS`/`CR_STATUSES`/`DEPARTMENTS`). Tests first:
- `next_govcr_code`: global widen (`[]`→`CHG-001`; `CHG-009`→`CHG-010`; `CHG-999`→`CHG-1000` widen).
- `validate_govcr`: required fields; CRClass/Decision/CRStatus domains; **all four two-axis coherence
  rules** + date order; no ProjectCode/ChangeType required.
- `validate_govassessment`: required ParentCRCode/Department(∈DEPARTMENTS)/ImpactSummary.
- builders: shapes + None passthroughs; `cr_gov_id`/`gov_impact_id` uuid5 determinism (fixed item_id →
  fixed uuid).
Green. Commit.

## T3 — both Lists in `create_artifact_lists.py` + LinkedCRCode on Versions
`"govcr_list_id": ("Governance Change Requests", [...])` and `"govassessment_list_id": ("Governance
Change Assessments", [...])` (columns per the spec; gov CR has **no ProjectCode**). **Add a
`LinkedCRCode` (text) column to the existing Document Versions List entry.** Run live (idempotent);
confirm `govcr_list_id`/`govassessment_list_id` merged into `db/.m365.local.json` and the version list
gained `LinkedCRCode`. Commit.

## T4 — sync read / normalize / dry-run + resolvers + registry
`GOVCR_FIELDS`/`normalize_govcr`/`GOVCR_SELECT`, `GOVASSESS_FIELDS`/`normalize_govassessment`/
`GOVASSESS_SELECT`, `resolve_parent_govcr`, `doc_leads`, and both processors as **stubs** (validate →
resolve all ids → soft-warn → `DRY …` intent, no writes). Extend `normalize_version` + `VERSION_FIELDS`
to capture `LinkedCRCode` (the processor stays write-free here; the resolve+set lands in T6). Registry
entries: insert `govcr` + `govassessment` **immediately after `document`** (order: document, govcr,
govassessment, raci, version, approval — govcr precedes version). Dry-run on one probe each (a gov CR on
`THG-OPS-CHR-001`, an assessment on it). **Verify other artifacts' dry-run byte-identical.** Commit.

## T5 — gov-CR write path (editable + two-axis + audit + guards) live
Real `process_change_request_gov`. Live on `THG-OPS-CHR-001`: file a gov CR (Pending/Open) → row +
`GOVCR_CREATE` + minted `CHG-001`; flip Decision→Approved + CRStatus→Implementing→Verified across runs
→ UPDATE + `GOVCR_DECISION`/`GOVCR_STATUS`; decider ≠ doc Owner/Approver → Synced + soft-warn note;
contradictory two-axis combo → Error; change `ParentDocID` → Error (identity guard); re-run no-op;
delete → orphan-keep. Verify `doc_mgmt.change_request_gov` + `audit_trail_entry` rows. Probe cleanup.
Commit.

## T6 — gov-assessment write path + LinkedCR loop closure live
Real `process_change_assessment_gov` (child→gov CR by `cr_code`; INSERT + write-back; `row_changed`
UPDATE + heal; re-parent guard `ParentCRCode`→another CR → Error; orphan-keep) **+ the LinkedCR
closure**: extend `process_document_version` to resolve `LinkedCRCode` → `linked_cr_id` (add to the
`mut` list; `build_version_row` sets it). Live: two dept assessments on `CHG-001`; file/edit a version
with `LinkedCRCode=CHG-001` → `document_version.linked_cr_id` set → verify
`bi.document_version.linked_cr_code='CHG-001'`; unknown `LinkedCRCode` → Error; re-run no-op; delete →
orphan-keep. Probe cleanup. Commit.

## T7 — TMDL model tables + relationships + Linked CR column + measures
New `Governance Change Request.tmdl` (relate `[Document ID]` → `Controlled Document[Document ID]`) and
`Governance Change Assessment.tmdl` (relate `[CR Gov ID]` → `Governance Change Request[CR Gov ID]`).
Register both in `model.tmdl` (`ref table` + `PBI_QueryOrder`). Add a `Linked CR` text column to
`Document Version.tmdl` + extend its partition SELECT (sourced from `bi.document_version.linked_cr_code`).
6 measures in `_Measures.tmdl` (folder **Change**). Verify: Tabular Editor BPA **zero violations** +
`python tools/validate_pbir.py`. Republish note. (New table files via Python `open(...,"w")`;
existing-file edits via the Edit tool — the file-protect hook blocks shell overwrites of tracked files.)
Commit.

## T8 — docs + e2e + final whole-stage review + push
- `docs/artifact-entry-setup.md`: new **§U Governance Change Requests** (project-less/document-targeted,
  global `CHG-NNN`, the two-axis workflow, doc Owner/Approver soft-authority, no-reparent, `GOVCR_*`
  audit) + **§V Governance Change Assessments** (the `ParentCRCode` link, department-scoped, no-audit,
  no-reparent) + a note in **§S Document Versions** documenting the now-live `LinkedCRCode` closure;
  update title + Lists-at-a-glance; add Appendix rows. `README.md`: a governance-CR paragraph.
- **e2e:** a real `CHG-001` against `THG-IT-SOP-001` (Pending→Approved→Verified across runs) + two
  department assessments + a version citing `CHG-001` → `python tools/sync_artifacts.py` → `SELECT …
  FROM bi.change_request_gov` + `bi.change_assessment_gov` + `bi.document_version` (incl. `linked_cr_code`)
  → `python tools/service_refresh.py`.
- **Final** whole-stage review (most capable model) over the full 2c-6 diff. Fix loop. pytest green.
  Commit. **Push** (`git push origin main`) — the close-out of Phase 2c.

## Verification summary
- Unit: `next_govcr_code` global widen + validators (two-axis coherence) + builders + uuid5 (T2).
- Live I/O: dry-run resolution (T4); gov-CR insert/update/two-axis/soft-warn/identity-guard (T5);
  gov-assessment insert/update/re-parent-guard + LinkedCR closure (`linked_cr_id` set + verifiable via
  `bi.document_version.linked_cr_code`) (T6).
- Model: BPA zero + `validate_pbir` (T7).
- e2e: `bi.change_request_gov` + `bi.change_assessment_gov` populated for `THG-IT-SOP-001`; a version
  cites `CHG-001`; idempotent re-run = no-ops (T8).
