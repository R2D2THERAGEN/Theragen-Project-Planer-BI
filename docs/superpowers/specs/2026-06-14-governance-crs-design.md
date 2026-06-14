# Governance Change Requests + Assessments — Design (Phase 2c-6)

Status: approved 2026-06-14 (plan-mode review). **Sixth and final** sub-stage of the decomposed
Phase 2c (2c-1 → 2c-2 → 2c-3 documents → 2c-4 RACI → 2c-5 versions/e-sig → **2c-6 governance CRs**).
This spec covers **2c-6 only** — the governance analog of the 2b project-CR surface, plus the closure
of the `LinkedCRCode` loop deferred from 2c-5.

## Problem

`doc_mgmt.change_request_gov` (CHG-NNN, document-scoped) and `doc_mgmt.change_assessment_gov`
(per-department impact) exist but are empty, with no authoring surface and no bi views. The 2c-3
documents have versions (2c-5) but a version cannot yet cite the **governance change request** that
drove it (`document_version.linked_cr_id` FKs `change_request_gov`, which had no rows until now). This
sub-stage makes governance CRs + their assessments authorable and closes that loop.

## Decisions

- Two new authoring surfaces synced by the registry-driven `tools/sync_artifacts.py`:
  **"Governance Change Requests"** → `change_request_gov` (child→document by `doc_id`, **project-less**)
  and **"Governance Change Assessments"** → `change_assessment_gov` (child→gov CR by global `cr_code`).
- **Governance CRs reuse the 2b two-axis workflow verbatim** (`Decision` × `CRStatus` + the same
  coherence rules) — the gov enums are **byte-identical** to `CR_CLASSES`/`CR_DECISIONS`/`CR_STATUSES`,
  so the 2b constants are reused (no governance-specific enum sets). Gov CRs have **no `change_type`**
  column and **no `project_id`** (document-scoped) — drop both from the 2b shape.
- **Code minting is global:** `cr_code` is `UNIQUE` (db/01_dm.sql:221), *not* per-project, so
  `next_govcr_code` is a single global counter `CHG-NNN`.
- **Editable + audited** (the `process_change_request` template): `GOVCR_CREATE`, `GOVCR_DECISION`,
  `GOVCR_STATUS`. The **document is the gov CR's target identity** → a changed `ParentDocID` after
  sync is rejected (`cr_code` is minted, immutable).
- **Soft authority, document-scoped:** the 2b sponsor/PM soft warning is re-homed onto the document —
  if `Decision != Pending` and the decider is neither the target document's **Owner** nor **Approver**,
  the row still syncs with a `SyncMessage` note (the audit records the actual decider). Hard role
  enforcement stays deferred.
- **Assessments are authored content, no audit** (the 2c-2 `process_impact_assessment` template):
  child→gov CR by `cr_code`, department-scoped (FK→`department`, no person column), `impact_summary` +
  optional `compliance_impact`; re-parent guard; orphan-keep.
- **LinkedCR loop closure (2c-5 surface):** the Document Versions List gains a `LinkedCRCode` column;
  the version processor resolves it via `resolve_parent_govcr` → sets `document_version.linked_cr_id`.
  A present-but-unknown `LinkedCRCode` Errors (airlock); blank → NULL. Surfaced as a **data column**
  `Linked CR` on the model (no `Document Version`↔gov-CR relationship — that would make the path to
  `Controlled Document` ambiguous).
- All FKs (document/requester/decider on the CR; gov CR/department on the assessment) are **real DB
  constraints** → resolve every id up front, airlock misses. Two new bi views + two new TMDL model
  tables; `bi.document_version` widened with `linked_cr_id`/`linked_cr_code`.

## "Governance Change Requests" List → `doc_mgmt.change_request_gov`

DDL (`db/01_dm.sql:219-234`). **NOT NULL, no default:** `cr_gov_id PK, cr_code VARCHAR(8) UNIQUE
(CHG-NNN, global), document_id (FK→document), requested_at, requested_by_person_id (FK→person),
cr_class, description, reason`. **NOT NULL w/ default:** `decision` (`Pending`), `status` (`Open`).
**Nullable:** `intake_id` (FK→intake_submission), `decided_by_person_id` (FK→person), `decided_at`,
`implementation_verified` (def FALSE). **No `project_id`.**

Columns: **Required** `ParentDocID`, `Description`, `Reason`, `CRClass` (choice `CR_CLASSES`),
`RequestedBy` (person, author-fallback). **Optional/defaults** `RequestedDate` (date, default
`createdDateTime`), `IntakeID`, `Decision` (choice, def Pending), `CRStatus` (choice, def Open),
`DecidedBy` (person), `DecidedDate` (date), `ImplementationVerified` (Yes/No→bool). **Write-back**
`CRCode` + bookkeeping. `cr_gov_id = uuid5(NS,"thg/artifact/govcr/{item_id}")`; `external_ref =
item_id`. `govcr_list_id` → config. **No `ProjectCode`** (project-less).

## "Governance Change Assessments" List → `doc_mgmt.change_assessment_gov`

DDL (`db/01_dm.sql:237-244`). **NOT NULL, no default:** `gov_impact_id PK, cr_gov_id (FK→
change_request_gov), department_id (FK→department), impact_summary, submitted_at`. **Nullable:**
`compliance_impact`. **No person column** (department-scoped); no `(cr_gov_id, department)` uniqueness.

Columns: **Required** `ParentCRCode` (→ gov CR `cr_code`), `Department` (choice = 8 `DEPARTMENTS`),
`ImpactSummary` (ml). **Optional** `ComplianceImpact` (ml), `SubmittedDate` (date, default
`createdDateTime`). + bookkeeping (no write-back code). `gov_impact_id =
uuid5(NS,"thg/artifact/govimpact/{item_id}")`; `external_ref = item_id`. `govassessment_list_id` →
config. **No `ProjectCode`** — the gov CR code is global.

## Migration

`db/19_govcr_external_ref_and_bi.sql` (additive, `IF NOT EXISTS`, inline psycopg; appended to the
`load_postgres.py` DDL tuple):
- `ALTER TABLE doc_mgmt.change_request_gov ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;`
- `ALTER TABLE doc_mgmt.change_assessment_gov ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;`
- `CREATE OR REPLACE VIEW bi.change_request_gov` (`cr_gov_id, cr_code, document_id, doc_id, doc_title,
  intake_id, requested_at, requested_by_name, cr_class, description, reason, decision, decided_by_name,
  decided_at, implementation_verified, status`; JOIN document + requester person; **LEFT JOIN** decider
  person).
- `CREATE OR REPLACE VIEW bi.change_assessment_gov` (`gov_impact_id, cr_gov_id, cr_code, doc_id,
  doc_title, department, impact_summary, compliance_impact, submitted_at`; JOIN change_request_gov →
  document, department).
- **Widen `bi.document_version`** (CREATE OR REPLACE — additive): add `v.linked_cr_id, lcr.cr_code AS
  linked_cr_code` via `LEFT JOIN doc_mgmt.change_request_gov lcr ON lcr.cr_gov_id = v.linked_cr_id`.

## Pure logic (`tools/artifact_lib.py`, unit-tested)

- Reuse `CR_CLASSES`, `CR_DECISIONS`, `CR_STATUSES`, `DEPARTMENTS`.
- `_GOVCR_CODE = re.compile(r"^CHG-(\d{3,})$")`; `next_govcr_code(existing)` → `f"CHG-{(max+1):03d}"`,
  widen-not-truncate (the `next_cr_code` clone; **global** — caller passes *all* gov CR codes).
- `validate_govcr(it)` — required `ParentDocID`/`Description`/`Reason`/`CRClass`; requester resolvable
  (picker or author-fallback); `CRClass ∈ CR_CLASSES`; the **2b two-axis coherence rules verbatim**
  (`Decision`/`CRStatus` domains; `Decision != Pending` ⇒ DecidedBy + DecidedDate; `Decision ==
  Pending` ⇒ DecidedDate blank; `Rejected` ⇒ `CRStatus == Rejected`; `{Verified,Closed}` ⇒ `Approved`;
  DecidedDate ≥ RequestedDate). **No `ProjectCode`, no `ChangeType`.**
- `build_govcr_row(it, document_id, requester_id, decider_id, cr_code)` → the column dict (`intake_id`,
  defaults `decision`/`status`, `implementation_verified` passthrough bool).
- `validate_govassessment(it)` — required `ParentCRCode`/`Department` (∈ DEPARTMENTS)/`ImpactSummary`.
- `build_govassessment_row(it, cr_gov_id, department_id, submitted_at)` → the column dict (blank
  `compliance_impact` → None).

## Processors (`tools/sync_artifacts.py`)

New `resolve_parent_govcr(conn, cr_code)` → `SELECT cr_gov_id FROM doc_mgmt.change_request_gov WHERE
cr_code=%s` (global single key). New `doc_leads(conn, document_id)` → `SELECT owner_person_id,
approver_person_id FROM doc_mgmt.document WHERE document_id=%s` (the doc-scoped `project_leads` analog).

Registry order: `… phase_gate, document, govcr, govassessment, raci, version, approval` — **govcr
precedes version** so a same-run `LinkedCRCode` resolves (autocommit; parents commit before children).

- **`process_change_request_gov`** (mirror `process_change_request`): resolve document via
  `resolve_parent_document(ParentDocID)` (Unknown → Error) + requester (author-fallback) + decider +
  optional `intake_exists`. Soft-authority via `doc_leads` (Owner/Approver). **New** → mint `cr_code`
  via `next_govcr_code(SELECT cr_code FROM doc_mgmt.change_request_gov)` (global) → INSERT +
  `GOVCR_CREATE` audit → write-back `CRCode`. **Existing** → ParentDocID immutability guard;
  `row_changed` over the mutable cols → UPDATE + `GOVCR_DECISION`/`GOVCR_STATUS` audit (when
  decision/status differs) + heal. Orphan-keep.
- **`process_change_assessment_gov`** (mirror `process_impact_assessment`, **no audit**): resolve gov
  CR via `resolve_parent_govcr(ParentCRCode)` (Unknown → Error) + department. **New** → INSERT →
  write-back. **Existing** → re-parent guard (resolved `cr_gov_id` ≠ stored → Error); `row_changed`
  over `department_id, impact_summary, compliance_impact, submitted_at` → UPDATE + heal. Orphan-keep.
- **`process_document_version` extension (loop closure):** `normalize_version` captures `LinkedCRCode`;
  the processor resolves it via `resolve_parent_govcr` when present (present-but-unknown → Error; blank
  → NULL), passes the resolved id to `build_version_row` (which now sets `linked_cr_id`); `linked_cr_id`
  joins the version's mutable-col set. (`VERSION_SELECT` already selects `linked_cr_id`.)

## Audit trail
Reuse `audit_lib.write_trail` (inside the per-item txn): `GOVCR_CREATE` (after insert),
`GOVCR_DECISION`/`GOVCR_STATUS` (on update when the axis differs). Actor = decider or requester.
Assessments write **no** audit row (descriptive content, the 2c-2 precedent).

## BI + model (`db/19` views; TMDL)
- `bi.change_request_gov`, `bi.change_assessment_gov`, widened `bi.document_version` (above).
- New `Governance Change Request.tmdl` (relate `[Document ID]` → `Controlled Document[Document ID]`)
  and `Governance Change Assessment.tmdl` (relate `[CR Gov ID]` → `Governance Change
  Request[CR Gov ID]`). Single-direction only. Add a `Linked CR` text column to `Document Version.tmdl`
  (from `linked_cr_code`) — **no** Document Version↔gov-CR relationship (ambiguous path). Measures
  (folder **Change**): Governance CRs, Open/Approved/Verified Governance CRs, Governance Assessments,
  Assessed Governance CRs (`DISTINCTCOUNT([CR Gov ID])`).
- **Schema additions require an Allen republish** (folds into the standing set).

## Error handling, testing, out of scope
Same airlock (`_error` + per-item `SyncStatus=Error`). Pure logic unit-tested (minting global widen,
all validators incl. two-axis coherence, builders, uuid5 determinism). I/O verified live in T4–T6 + the
T8 e2e. Out of scope (carried deferrals): hard role-based approval *authority* enforcement (v1 =
person-exists + doc Owner/Approver soft warning + `GOVCR_*` audit); `(cr_gov_id, department)`
uniqueness; a dedicated "Governance / Document Control" report page (measures land now; visuals later);
true §11 signing (post-2c).
