# Document Versions + e-signature Attestations — Design (Phase 2c-5)

Status: approved 2026-06-13 (plan-mode review). Fifth sub-stage of the decomposed Phase 2c
(2c-1 → 2c-2 → 2c-3 documents → 2c-4 RACI → **2c-5 versions + e-sig** → 2c-6 governance CRs). This
spec covers **2c-5 only** — the **first grandchild chain** (`document → document_version →
document_approval`) on the 2c-3 documents, with an explicitly **non-§11** attestation hash.

## Problem

Controlled documents (2c-3) have no **version history** and no record of **who signed off** a
version. `doc_mgmt.document_version` and `doc_mgmt.document_approval` exist but are empty, with no
authoring surface and no bi views. The approval table's schema comment aspires to "21 CFR Part 11
§11.50" — but a true §11 signing ceremony (re-authentication, signer-controlled key, content-binding,
captured signer IP) is **not achievable** through a SharePoint form + nightly server sync, so this
sub-stage delivers an **honest attestation**, never presented as a §11 signature.

## Decisions

- Two new authoring surfaces synced by the registry-driven `tools/sync_artifacts.py`:
  **"Document Versions"** → `document_version` (child→document by `doc_id`) and **"Document Approvals
  (e-sig)"** → `document_approval` (grandchild→version by `(doc_id, version)`).
- **Versions are editable** (status transitions DRAFT→…→BASELINE, summary/path corrections), with an
  **immutable identity** `(document_id, version)` — changing `ParentDocID` or `Version` after sync is
  rejected. Audited: `VERSION_CREATE` + `VERSION_STATUS`.
- **Approvals are append-once / immutable** — an attestation, once made, is frozen. The `esig_hash` is
  computed **once** at first sync and never recomputed; substantive edits are rejected. Audited:
  `APPROVAL_SIGN`.
- **The attestation hash (honest scoping):** `esig_hash = SHA-256(doc_id|version|approver_email|
  signature_meaning|signed_at)`, computed server-side. `signed_at` = the item `createdDateTime` (the
  moment of attestation). `ip_address` = **NULL** (we do **not** fabricate a signer IP). Every surface
  labels this **"Attestation (non-§11)"**; true §11 signing is deferred.
- **`linked_cr_id` deferred to 2c-6** — it FKs `change_request_gov`, which doesn't exist until 2c-6.
- All FKs (document/version/author/approver) are **real DB constraints** → resolve every id up front,
  airlock misses. Two new bi views + two new TMDL model tables.

## "Document Versions" List → `doc_mgmt.document_version`

DDL (`db/01_dm.sql:99-111`). **NOT NULL, no default:** `version_id PK, document_id, version
VARCHAR(10), change_summary TEXT, author_person_id, storage_path VARCHAR(500)`. **NOT NULL w/ default:**
`status` (`DRAFT`), `created_at`. **Nullable:** `change_class`, `linked_cr_id`, `effective_date`.
**No DDL `UNIQUE(document_id, version)`** — the sync treats `(document_id, version)` as the identity.

Columns: **Required** `ParentDocID`, `Version`, `ChangeSummary`, `Author` (person, author-fallback).
**Optional/defaults** `Status` (choice `DOC_STATUSES`, def DRAFT), `ChangeClass` (choice `CR_CLASSES`),
`EffectiveDate` (date), `StoragePath` (text, **defaults to `{ParentDocID}/v{Version}`**). + bookkeeping.
`version_id = uuid5(NS,"thg/artifact/version/{item_id}")`; `external_ref = item_id`. `version_list_id`
→ config. (**LinkedCRCode deferred to 2c-6.**)

## "Document Approvals (e-sig)" List → `doc_mgmt.document_approval`

DDL (`db/01_dm.sql:125-134`). **NOT NULL:** `approval_id PK, version_id, approver_person_id,
signature_meaning (def 'Approval'), signed_at, esig_hash VARCHAR(128)`. **Nullable:** `ip_address`,
`reason`.

Columns: **Required** `ParentDocID` + `ParentVersion` (resolve `version_id`), `Approver` (person,
author-fallback), `SignatureMeaning` (choice {Approval, Review, Authorship}, def Approval).
**Optional** `Reason` (ml). **Server-derived:** `signed_at` = item `createdDateTime`; `esig_hash`
(above); `ip_address` = NULL. + bookkeeping. `approval_id = uuid5(NS,"thg/artifact/approval/{item_id}")`.
`approval_list_id` → config.

## Migration

`db/18_version_approval_external_ref_and_bi.sql`: `ALTER … document_version`/`document_approval ADD
COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE`; `CREATE OR REPLACE VIEW bi.document_version`
(`version_id, document_id, doc_id, doc_title, version, status, change_summary, change_class,
author_name, effective_date, storage_path, created_at`; JOIN document + author); `CREATE OR REPLACE
VIEW bi.document_approval` (`approval_id, version_id, doc_id, doc_title, version, approver_name,
signature_meaning, signed_at, esig_hash, 'Attestation (non-§11)' AS esig_kind, reason`; JOIN
version→document + approver). Additive; inline psycopg; appended to the loader tuple.

## Pure logic (`tools/artifact_lib.py`, unit-tested)

- Reuse `DOC_STATUSES` (2c-3), `CR_CLASSES` (2b). Add `SIGNATURE_MEANINGS = ["Approval","Review",
  "Authorship"]`.
- `esig_hash(doc_id, version, approver_email, meaning, signed_at)` →
  `hashlib.sha256("|".join([...]).encode("utf-8")).hexdigest()` (pure, **byte-deterministic**;
  unit-test a fixed input → fixed 64-char hex).
- `validate_version(it)` — required `ParentDocID`/`Version`/`ChangeSummary`/`Author`; `Status ∈
  DOC_STATUSES`; `ChangeClass ∈ CR_CLASSES` when set.
- `build_version_row(it, document_id, author_id)` → the column dict (StoragePath default;
  `linked_cr_id=None`; blank change_class/effective_date → None).
- `validate_approval(it)` — required `ParentDocID`/`ParentVersion`/`Approver`; `SignatureMeaning ∈
  SIGNATURE_MEANINGS`.
- `build_approval_row(it, version_id, approver_id, signed_at, esig)` → the column dict
  (`ip_address=None`; blank reason → None).

## Processors (`tools/sync_artifacts.py`)

New `resolve_parent_version(conn, document_id, version)` →
`SELECT version_id FROM doc_mgmt.document_version WHERE document_id=%s AND version=%s`. Registry
entries at the **end of `ARTIFACTS`** in the order `… document … version … approval` (each parent
precedes its child; autocommit).
- **`process_document_version`** (mirror `process_document`, **editable + audited**): resolve document
  + author → INSERT + `VERSION_CREATE` audit; `row_changed` over `status, change_summary, change_class,
  effective_date, storage_path` → UPDATE + `VERSION_STATUS` audit (status change) + heal; **identity
  guard** → a changed `ParentDocID` or `Version` → reject "create a new version"; orphan-keep.
- **`process_document_approval`** (mirror `process_baseline`, **append-once / immutable**): resolve
  document → version (Unknown ParentDocID/ParentVersion → Error) → approver → `signed_at` (createdDate)
  + `esig_hash` → INSERT + `APPROVAL_SIGN` audit (`after={meaning, esig_hash}`) → write-back. Existing
  → heal a lost write-back; **reject** substantive edits ("attestations are immutable; create a new
  approval"); `esig_hash` **never recomputed**; orphan-keep.

## Audit trail
Reuse `audit_lib.write_trail` (inside the per-item txn): `VERSION_CREATE`, `VERSION_STATUS` (actor =
author), `APPROVAL_SIGN` (actor = approver).

## BI + model (`db/18` views; TMDL)
- `bi.document_version`, `bi.document_approval` (above; the approval view carries the literal
  `esig_kind` honesty label).
- New `Document Version.tmdl` (relate `[Document ID]` → `Controlled Document[Document ID]`) and
  `Document Approval.tmdl` (relate `[Version ID]` → `Document Version[Version ID]`; columns include
  **`Attestation Kind`** = esig_kind and `Attestation Hash` = esig_hash — **no "signature"/"§11"
  naming**). Single-direction relationships only (no extra Department path — the impact/RACI
  precedent). Measures (folder **Documents**): Document Versions, Baseline Versions, Document Approvals,
  Attested Versions (`DISTINCTCOUNT([Version ID])`), Approval Attestations (`SignatureMeaning="Approval"`).
- **Schema additions require an Allen republish** (folds into the standing set).

## Error handling, testing, out of scope
Same airlock; pure logic unit-tested (validators, builders, **esig_hash determinism**). I/O verified
live in T4–T6 + the T8 e2e. **The honesty bar is a hard requirement** — never present the attestation
as a §11 signature; `ip_address` stays NULL; `esig_hash` is frozen at first sign. Out of scope:
`document_review` events; true §11 signing (re-auth/signer key/content-binding/signer IP) → post-2c;
`LinkedCRCode` on versions → 2c-6; governance CRs → 2c-6.
