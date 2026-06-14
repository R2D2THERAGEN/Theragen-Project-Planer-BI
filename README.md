# Theragen Project Planner BI

Power BI semantic model and report for the Theragen **PMBOK Integrated Documentation
System**, modeled directly from `THG-ENT-DBS-001_Database_Schema_Specification_v1.0`
(PMBOK project-management schema) and the 14 PMBOK template documents.

The project is stored in **PBIP format** (TMDL semantic model + PBIR report) so every
table, measure, relationship and visual is plain text, diff-able, and reviewable in git.

## Quick start

1. Install [Power BI Desktop](https://aka.ms/pbidesktop) (any 2024+ release; PBIP/PBIR are GA).
2. Open `Theragen Project Planner.pbip`.
3. If the sample data folder is not at the default location, update the **DataFolder**
   parameter (Transform data → Edit parameters) to point at `SampleData/` in this repo.
4. Refresh. All 17 source tables load from the seeded sample CSVs.

## What's inside

```
Theragen Project Planner.pbip            Project pointer (open this)
Theragen Project Planner.SemanticModel/  TMDL model: 21 tables, 94 measures, 36 relationships
Theragen Project Planner.Report/         PBIR report: 8 pages, 85 visuals
SampleData/                              Seeded 6-project portfolio (17 CSVs, schema-faithful)
paginated/                               Constant-layout .rdl status report (DAX on the model)
docs/MODEL_DESIGN.md                     Star-schema design decisions and source mapping
_source_extracts/                        Schema spec sheets extracted to TSV (reference)
tools/                                   Bootstrap generators + PBIR schema validator
```

## Semantic model

Star schema reshaped from the OLTP PMBOK schema (31 entities → 18 model tables):

- **Dimensions:** Date (marked, 2025–2027), Project, Department, Person, WBS Element,
  Knowledge Area
- **Facts:** Schedule Activity, Milestone, Budget Line, Risk, Risk Response,
  Change Request, Status Report, Status Report Area, Stakeholder, Team Member,
  Lesson Learned, Closure Item
- **`_Measures`** hosts 78 documented measures in folders: Portfolio, Schedule, EVM,
  Milestones, Cost, Risk, Change, Health, Stakeholders, Team, Closing

Conventions: single-direction filtering only; `Project` reaches activities/budget through
`WBS Element` (no ambiguous paths); inactive Date relationships for secondary dates
(actuals, forecasts, decisions) ready for `USERELATIONSHIP`; UUID keys hidden; every
table, measure and calculated column carries a description.

Full design rationale: [docs/MODEL_DESIGN.md](docs/MODEL_DESIGN.md)

## Report pages

| Page | Mirrors PMBOK artifact |
|---|---|
| Portfolio Overview | Executive roll-up across all projects |
| Project Status Report | The Theragen leadership one-pager (traffic light, health check, RAID, key project areas, accomplishments, next steps) + Template 13 |
| Schedule & Milestones | Template 06 — Schedule (activities, % complete, slip) |
| Cost & Budget | Template 07 — Cost Budget Estimate (+ EVM: PV/EV/SV/SPI) |
| Risk Management | Template 09 — Risk Register (5×5 heat map, exposure, responses) |
| Change Control | Template 12 — Change Request Log (pipeline, cycle time, impact) |
| Stakeholders & Team | Template 02 — Stakeholder Register + RACI (interest × influence) |
| Lessons & Closure | Template 14 — Lessons Learned & Closure checklist |

## Production database

The model loads from **Azure PostgreSQL Flexible Server**
(`psql-theragen-pmbok.postgres.database.azure.com`, database `theragen_pmbok`). The
spec's DDL lives in `db/` (`doc_mgmt` + `pmbok` schemas, FKs hoisted to
`04_foreign_keys.sql`), and a `bi` schema of views re-shapes the OLTP tables to the
original CSV contracts so every model partition navigates to `bi.*` with unchanged
column names. `tools/load_postgres.py` seeds it from `SampleData/` — **destructive**:
it drops all three schemas and requires `--reseed` plus a typed database-name
confirmation. The `DataFolder` parameter remains for offline dev/test fixtures.
`Approval`, `Decision`, `Assumption/Constraint`, scope detail and the DM governance
schema are deliberate Phase-2 additions (see MODEL_DESIGN.md §1).

## Project ingestion

New projects enter through **Microsoft Forms → Power Automate → SharePoint List →
nightly sync**:

- Form submissions land on the **Project Intake** SharePoint List as
  `TriageStatus = Submitted`, `SyncStatus = Pending`, with people pickers resolved
  from the M365 directory.
- `tools/sync_intake.py` runs daily at **5:30 AM** (Task Scheduler job
  `Theragen\SyncIntake` → `tools/run_intake_sync.cmd`, log in `logs/intake_sync.log`).
  New items become `doc_mgmt.intake_submission` + `pmbok.project` (status
  **Proposed**) + a charter row in one transaction; afterwards, `TriageStatus` edits
  on the List drive transitions (Approved → Active, Rejected → Cancelled,
  On Hold → Paused).
- Results are written back onto each List item (`SyncStatus`, `IntakeID`,
  `ProjectCode`, error messages), so the List is the PMO's triage surface; the sync
  is idempotent via `intake_submission.external_ref` = List item id.
- The 6:00 AM semantic-model refresh picks the new rows up into the reports.

Setup recipe (Form questions, Flow steps, schedule, smoke test):
[docs/intake-setup.md](docs/intake-setup.md). Design rationale:
[docs/superpowers/specs/2026-06-12-project-ingestion-design.md](docs/superpowers/specs/2026-06-12-project-ingestion-design.md).

### Execution tracking

Once a project is active, PMs file risks, milestones, and weekly status reports directly
in three SharePoint Lists — **Project Risks**, **Project Milestones**, and **Project
Status Reports**. `tools/sync_artifacts.py` runs daily at **5:40 AM** (Task Scheduler
job `Theragen\SyncArtifacts` → `tools/run_artifact_sync.cmd`, log in
`logs/artifact_sync.log`), ten minutes after the intake sync so same-morning project
codes are available. Each sync validates every List item, inserts or updates the
corresponding `pmbok.risk`, `pmbok.milestone`, and `pmbok.status_report` rows
(status reports fan out to nine `pmbok.status_report_area` rows, one per PMBOK
knowledge area), and writes results back onto the List item (`SyncStatus`,
`SyncMessage`, and — for risks — the auto-minted `RiskCode`). The write-back columns
are managed by the sync and should not be edited by hand. PM entry guide and column
reference: [docs/artifact-entry-setup.md](docs/artifact-entry-setup.md). Design
rationale:
[docs/superpowers/specs/2026-06-12-execution-tracking-design.md](docs/superpowers/specs/2026-06-12-execution-tracking-design.md).

PMs also enter schedule activities in the **Project Activities** List (one row per activity); the same 5:40 AM sync auto-derives a two-tier WBS (Workstream → Work Package) from the Workstream and WorkPackage text columns, mints an `ActivityCode` per activity, and writes the result back — the derived WBS is what fills the **Key Project Areas** panel on the Project Status Report page. See [docs/artifact-entry-setup.md §D](docs/artifact-entry-setup.md) for the full column reference and grouping rules.

**Change & approval:** change requests are filed in the **Project Change Requests** List (one row per CR; auto-minted `CRCode`); governance decisions in the **Project Decisions** List (one row per decision; auto-minted `DecisionCode`). Both sync through the same 5:40 AM job. The sync enforces a two-axis approval workflow: **Decision** (Pending / Approved / Deferred / Rejected) is the approval gate; **CRStatus** (Open → In Assessment → Implementing → Verified → Closed) is the lifecycle. Status reports can be signed off by setting **ApprovedBy** + **ApprovedDate** on the List item; the `is_signed_off` flag is set in PostgreSQL on the next sync. Every CR decision/status change and status-report sign-off is written to an append-only `doc_mgmt.audit_trail_entry` record. Per-department **change impact assessments** are filed in the **Change Impact Assessments** List (one row per department per CR; each child row links to its parent CR by `ParentCRCode`) and feed the per-department impact roll-up on the Change Control page. Column references, choice values, and coherence rules: [docs/artifact-entry-setup.md §E–§F, §P](docs/artifact-entry-setup.md). **Schema additions** (new tables or columns, such as the Decision and Change Impact Assessment tables and the new governance measures) require Allen to republish the `.pbip` from Power BI Desktop — a data-only service refresh will not surface them.

**Baselines & phase gates:** PMs freeze immutable Schedule / Budget / Scope snapshots in the **Project Baselines** List (the sync builds the snapshot server-side, mints `BaselineVersion`, and supersedes the prior baseline on re-baseline) and record lifecycle-phase handoffs in the **Project Phase Gates** List (forward-only advances + Held, audited). Both sync through the same 5:40 AM job; column references and the immutability / forward-only rules: [docs/artifact-entry-setup.md §N–§O](docs/artifact-entry-setup.md). The new `Project Baseline` and `Phase Gate Log` model tables and their measures require Allen to republish the `.pbip` from Power BI Desktop — a data-only service refresh will not surface them.

**Controlled documents:** the PMO registers org-wide controlled documents in the **Controlled Documents** List (one row per document; auto-minted `DocID` = `THG-{DEPT}-{TYPE}-NNN`, scoped per department + type). Document types and compliance frames are seeded once by `tools/seed_doc_lookups.py` (idempotent — **not** a reseed). The sync resolves the type / department / owner / approver, derives the lifecycle phase and review cycle from the type, and drives a permissive `Status` (DRAFT → REVIEW → BASELINE → AMENDED → RETIRED); `DocTypeCode` + `PrimaryDepartment` are fixed after first sync (they define the DocID). Every create and status change writes an append-only `doc_mgmt.audit_trail_entry` row. Column reference: [docs/artifact-entry-setup.md §Q](docs/artifact-entry-setup.md). The new `Controlled Document` model table + measures (and the `bi.document` view) require Allen to republish the `.pbip` from Power BI Desktop. This is the **documents foundation** the document RACI, versions/e-signatures, and governance change requests build on.

**Document RACI:** each controlled document carries an effective-dated **R/A/C/I** responsibility matrix in the **Document RACI** List (one row per (document, department); child rows link to the parent by `DocID`, which is globally unique). The sync resolves the assignee department and records who is Responsible / Accountable / Consulted / Informed, with `ValidFrom`/`ValidTo` effective-dating; the parent document is fixed after first sync. Column reference: [docs/artifact-entry-setup.md §R](docs/artifact-entry-setup.md). The new `Document RACI` model table + measures and the `bi.raci_assignment` view require Allen to republish the `.pbip`.

**Document versions & sign-off attestations:** a document's version history is authored in the **Document Versions** List (child of a document; `(DocID, Version)` identity; status DRAFT → … → BASELINE, audited) and per-version sign-offs in the **Document Approvals** List (grandchild — linked by `ParentDocID` + `ParentVersion`). **Honest scoping:** an approval is a server-computed **attestation**, *not* a 21 CFR Part 11 signature — `esig_hash` is a SHA-256 over `doc_id|version|approver_email|meaning|signed_at` (deterministic, so it verifies by recomputation from the stored row); `ip_address` is null (no signer IP); every surface labels it **"Attestation (non-§11)"**. Attestations are append-once (the hash is frozen at first sign). A true §11 signing ceremony is deferred. Column reference + the full honesty note: [docs/artifact-entry-setup.md §S–§T](docs/artifact-entry-setup.md). The new `Document Version` / `Document Approval` model tables and the `bi.document_version` / `bi.document_approval` views require Allen to republish the `.pbip`.

**Governance change requests:** controlled changes against a document are raised in the **Governance Change Requests** List (one row per CR; auto-minted **global** `CHG-NNN`; child of a document by `ParentDocID`, **project-less**) and reuse the same two-axis Decision/CRStatus workflow + audit (`GOVCR_CREATE` / `GOVCR_DECISION` / `GOVCR_STATUS`) as the project CRs, with a document-scoped Owner/Approver soft-authority advisory. Per-department impact statements attach in the **Governance Change Assessments** List (child of a gov CR by `CHG-NNN`, department-scoped, no audit). This also **closes the version → CR loop**: a document version can cite the governance CR that drove it via the optional **LinkedCRCode** column (`document_version.linked_cr_id`), surfaced as the model's `Linked CR`. Column references: [docs/artifact-entry-setup.md §U–§V](docs/artifact-entry-setup.md). The new `Governance Change Request` / `Governance Change Assessment` model tables, the `Linked CR` column, the six governance measures, and the `bi.change_request_gov` / `bi.change_assessment_gov` views require Allen to republish the `.pbip`.

**EVM note:** the v1.0 schema has no cost-actuals entity, so AC/CPI/EAC are intentionally
absent; SPI/SV/EV/PV derive from WBS estimates and activity percent-complete. Add an
actuals feed (ERP extract) in Phase 2 to complete the EVM family.

## Validation

- TMDL compiles via **Tabular Editor 2** CLI (also used for the Best Practice Analyzer —
  currently zero violations):
  `TabularEditor.exe "Theragen Project Planner.SemanticModel/definition" -A`
- Every PBIR JSON validates against Microsoft's published Fabric schemas:
  `python tools/validate_pbir.py`

## Regenerating from scratch

The `tools/` scripts are bootstrap generators — after initial generation, the TMDL/PBIR
files are the maintained artifacts (edit in Power BI Desktop or Tabular Editor):

```
python tools/generate_sample_data.py    # reseed SampleData/*.csv
python tools/build_semantic_model.py    # rewrite SemanticModel TMDL
python tools/build_report.py            # rewrite Report PBIR pages
```

## Source documents

Modeled from `C:\Users\Allen\OneDrive - Neurotech NA\Org Deployment Optimization`:
- `THG-ENT-DBS-001_Database_Schema_Specification_v1.0.xlsx` — authoritative schema
  (PMBOK + Document Management, bridge keys `intake_id`/`doc_id`/`person_id`)
- Templates 01–14 (Charter → Lessons Learned) — define the report page requirements
- `DEVELOPMENT_files/` — documentation lifecycle framework (governance track feeds
  the status-report and document-control analytics)
