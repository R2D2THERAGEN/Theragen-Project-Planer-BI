# Document Versions + e-sig Attestations — Implementation Plan (Phase 2c-5)

Design: [`2026-06-13-versions-esig-design.md`](../specs/2026-06-13-versions-esig-design.md).
Subagent per task, two-stage review, a final whole-stage review, live verification on the 2c-3
documents (`THG-OPS-CHR-001`, `THG-IT-SOP-001`). `python -m pytest tests/ -q` green at every commit
(the suite is ~90s on this archive path — expected, not a failure).

Patterns to mirror (read, do not reinvent):
- `process_document` (`tools/sync_artifacts.py`) — editable + audited template for the **version** processor.
- `process_baseline` (`tools/sync_artifacts.py`) — the **append-once / immutable** template for the **approval** processor (heal-only on existing, reject edits).
- `resolve_parent_document` (2c-4) — the doc lookup; add `resolve_parent_version`.
- `normalize_change_request` / `normalize_document` — author-fallback + the `CreatedAt = createdDateTime` capture (needed for `signed_at`).
- `audit_lib.write_trail` + the `process_change_request`/`process_document` audit call sites.
- `db/16` / `db/17` — the ALTER + CREATE VIEW migration style.
- `Controlled Document.tmdl` + its `[Document ID]` relationship — the model-table template.

## T1 — `db/18_version_approval_external_ref_and_bi.sql`
Two `ALTER … ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE` (document_version,
document_approval) + `CREATE OR REPLACE VIEW bi.document_version` + `bi.document_approval` (the latter
with the literal `'Attestation (non-§11)' AS esig_kind`). Append to the loader tuple. Apply live;
`information_schema` (both columns) + `SELECT * FROM bi.document_version/document_approval LIMIT 0`
verify. Commit.

## T2 — `artifact_lib` + tests (tests first)
`SIGNATURE_MEANINGS`, `esig_hash`, `validate_version`/`build_version_row`, `validate_approval`/
`build_approval_row` (reuse `DOC_STATUSES`, `CR_CLASSES`). Tests first:
- `esig_hash`: a fixed `(doc, ver, email, meaning, signed_at)` → a fixed known 64-char hex (lock the
  byte-determinism); different inputs → different hashes.
- validators: required-field + domain rules; builders: defaults (StoragePath, None passthroughs),
  `linked_cr_id`/`ip_address` = None.
Green. Commit.

## T3 — both Lists in `create_artifact_lists.py`
`"version_list_id": ("Document Versions", [...])` and `"approval_list_id": ("Document Approvals
(e-sig)", [...])` (columns per the spec; the approval List has **no** signed_at/esig_hash inputs — those
are server-derived). Run live (idempotent); confirm both ids merged into `db/.m365.local.json`. Commit.

## T4 — sync read / normalize / dry-run + resolver
`VERSION_FIELDS`/`normalize_version`/`VERSION_SELECT`, `APPROVAL_FIELDS`/`normalize_approval` (capture
`CreatedAt`)/`APPROVAL_SELECT`, `resolve_parent_version`, and both processors as **stubs** (validate →
resolve all ids → for approval, compute the would-be hash → `DRY …` intent, no writes). Registry
entries after `document` (order: document, raci, version, approval — version before approval). Dry-run
on one probe each (a version + an approval on `THG-OPS-CHR-001`). **Verify other artifacts'
dry-run byte-identical.** Commit.

## T5 — version write path (editable + identity guard + audit) live
Real `process_document_version`. Live on `THG-OPS-CHR-001`: file `Version=1.0` (DRAFT) → row +
`VERSION_CREATE`; flip Status→BASELINE → UPDATE + `VERSION_STATUS`; re-run no-op; change `Version`→`1.1`
→ Error (identity guard); delete → orphan-keep. Probe cleanup. Commit.

## T6 — approval write path (append-once esig + audit + immutability) live
Real `process_document_approval`. Live: file an Approval (`SignatureMeaning=Approval`) on
`THG-OPS-CHR-001` `v1.0` → row with computed `esig_hash` + `APPROVAL_SIGN` audit + `ip_address` NULL;
**re-run = no-op** (hash unchanged); edit the List item's Reason → **reject** (immutable) or heal-only;
unknown ParentVersion → Error; delete → orphan-keep. **Verify the stored `esig_hash` equals
`esig_hash(doc_id, version, approver_email, meaning, signed_at)` recomputed from the row** (the
attestation is verifiable). Probe cleanup. Commit.

## T7 — TMDL model tables + relationships + measures
New `Document Version.tmdl` (relate `[Document ID]` → `Controlled Document[Document ID]`) and `Document
Approval.tmdl` (relate `[Version ID]` → `Document Version[Version ID]`; columns include `Attestation
Kind` + `Attestation Hash`). Register both in `model.tmdl` (`ref table` + `PBI_QueryOrder`). 5 measures
in `_Measures.tmdl` (folder **Documents**). Verify: Tabular Editor BPA **zero violations** + `python
tools/validate_pbir.py`. Republish note. (New table files via Python `open(...,"w")`; existing-file
edits via the Edit tool — the file-protect hook blocks shell overwrites of tracked files.) Commit.

## T8 — docs + e2e + final review
- `docs/artifact-entry-setup.md`: new **§S Document Versions** + **§T Document Approvals
  (attestations)** — the grandchild link, immutability, server-derived fields, and a **prominent
  non-§11 honesty note**; update title + Lists-at-a-glance; add Appendix rows. `README.md`: a Versions
  + attestations paragraph (with the honesty note).
- **e2e:** a real `1.0` → `1.1` version history on `THG-OPS-CHR-001` + an `Approval` attestation on
  `1.0` → `python tools/sync_artifacts.py` → `SELECT … FROM bi.document_version` + `bi.document_approval`
  (incl. `esig_kind`) → `python tools/service_refresh.py`.
- **Final** whole-stage review (most capable model) over the full 2c-5 diff — **specifically check the
  honesty bar** (no surface presents the hash as a §11 signature). Fix loop. pytest green. Commit.

## Verification summary
- Unit: `esig_hash` determinism + validators + builders (T2).
- Live I/O: dry-run resolution (T4); version insert/update/identity-guard (T5); approval append-once +
  hash-reproducibility + immutability (T6).
- Model: BPA zero + `validate_pbir` (T7).
- e2e: `bi.document_version` + `bi.document_approval` populated for `THG-OPS-CHR-001`; idempotent
  re-run = no-ops; the attestation hash verifies from the stored row (T8).
