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

## Swapping in the production database

The PMBOK schema is specified for PostgreSQL (DDL in `_source_extracts/PMBOK_DDL.tsv`).
When it goes live:

1. Each table's partition M query reads one CSV named exactly like its source table
   (`project.csv` ← `pmbok.project`). Replace the `Csv.Document(File.Contents(...))`
   step with `PostgreSQL.Database(server, db)` navigation to the same table — column
   names match the DDL, so the rename step keeps working.
2. Delete the `DataFolder` parameter or keep it for dev/test fixtures.
3. `Approval`, `Decision`, `Assumption/Constraint`, scope detail and the DM governance
   schema are deliberate Phase-2 additions (see MODEL_DESIGN.md §1).

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
