# Theragen Project Planner — Business Glossary

Plain-language definitions of every business term used across the Theragen PMBOK BI system — PMBOK / project-management vocabulary, Earned Value (EVM) terms, governance & compliance terms, and Theragen-specific conventions. Each entry, where useful, names the **model object or measure** that realizes it (a table in single quotes `'…'`, a measure in brackets `[…]`, a column as `'Table'[Column]`, or a database/code artifact in backticks).

This is the *concept* layer. For the object-by-object catalogue (every table, column, measure, relationship), see the generated **[data dictionary](data-dictionary.md)**. For how any of this is allowed to *change*, see the **[change-control process](change-control-process.md)**.

**Architecture in one line:** PMs author in **SharePoint Lists** → a daily **Python sync** writes **Azure PostgreSQL** → read-only **`bi.*` views** → the **Power BI semantic model** → reports.

---

## A

- **AC — Actual Cost** — Cumulative money actually spent to date, summed from logged cost actuals. *Realized by* `[AC (Actual Cost)]` over `'Cost Actual'[Amount]`.
- **Accountable** — In RACI, the single role answerable for an outcome (the "A"). *Realized by* `[Accountable Assignments]` / `[Accountable Count]`.
- **Activity** — A unit of schedule work a PM authors (planned/actual start & finish, % complete, owner, department). *Realized by* `'Schedule Activity'`; minted code `{wbs_code}-A{n}` (e.g. `1.1-A1`).
- **Airlock** — The sync's rule that a row referencing something unresolved (an unknown project code, parent code, department, or person) is rejected as an **Error** rather than written — one bad row never blocks the batch. See also **soft-authority warning**, **orphan-keep**.
- **Amendment** — A controlled-document status (`AMENDED`) indicating a baselined document changed under change control. See **document status**.
- **Approval (attestation)** — A recorded sign-off on a document version. In this system it is an **honest attestation** (a server-computed hash), **not** a 21 CFR Part 11 signature. *Realized by* `'Document Approval'`, surfaced as `'Document Approval'[Attestation Kind]`; see **§11**, **attestation**.
- **Approval authority** — Who is entitled to decide a change. Enforced **softly** by default (a note if the decider isn't the Sponsor/PM or doc Owner/Approver) and **hard** only when `enforce_decision_authority` is on. See **soft-authority warning**.
- **Assumption / Constraint** — Charter-level planning premises and limits. Captured in the database; not currently surfaced as their own model tables.
- **Attestation** — A non-§11 electronic sign-off: the system records who attested, when, the meaning, and a SHA-256 hash binding those facts. Labelled "Attestation (non-§11)" everywhere it appears so it is never mistaken for a regulatory signature.
- **Audit trail** — An append-only log of every governance state change (who, what, before→after, when, why). *Realized by* `doc_mgmt.audit_trail_entry`; actions include `CR_DECISION`, `STATUS_SIGNOFF`, `BASELINE_CREATE`, `PHASE_GATE`, `DOCUMENT_STATUS`, `APPROVAL_SIGN`, `GOVCR_DECISION`, `ACCESS_GRANT/REVOKE/CHANGE`.

## B

- **BAC — Budget at Completion** — The total authorized EVM budget, taken from work-package estimates. *Realized by* `[BAC (WBS Estimates)]` = sum of level-2 `'WBS Element'[Estimated Cost]`.
- **Baseline** — A frozen, point-in-time snapshot of the **Schedule**, **Budget**, or **Scope**, used as the yardstick for variance. Re-baselining mints a new version (`1.0`, `2.0`, …) and supersedes the prior one. *Realized by* `'Project Baseline'` (status `BASELINED`/`SUPERSEDED`); the snapshot is stored as immutable JSON.
- **bi view** — A read-only PostgreSQL view (`bi.*`) that reshapes the raw tables into report-ready columns. The **only** layer the Power BI model reads from — never the base tables directly.
- **Budget (funded)** — The detailed, contingency-inclusive budget the project is funded at. *Realized by* `[Budget Total]` over `'Budget Line'`; `[Budget Subtotal]` excludes contingency; `[Contingency Amount]` is the reserve.
- **Budget variance vs baseline** — Drift of the current approved budget from the frozen Budget baseline. *Realized by* `[Budget Variance vs Baseline]`.

## C

- **Change class** — The severity/control level of a change request: **A – Minor**, **B – Substantive**, **C – Controlling**, **Emergency / Safety**. *Realized by* `'Change Request'[CR Class]`.
- **Change Impact Assessment** — A per-department statement of how a change request affects that department (scope/schedule/cost/quality). *Realized by* `'Change Impact Assessment'`; a department may file more than one.
- **Change Request (CR)** — A controlled request to change project scope/schedule/cost/quality, routed through a two-axis gate. Project CRs are minted `C-NNN` per project. *Realized by* `'Change Request'`; see **Decision**, **CR status**.
- **CHANGELOG** — The platform change register (`CHANGELOG.md`) recording every change to the system (version, category, summary, approver, git SHA) per the change-control process.
- **Closure item** — A project-closeout checklist entry. *Realized by* `'Closure Item'`; completion via `[Closure Complete Pct]`.
- **Controlled document** — An org-wide governed document (SOP, charter, plan, policy, etc.) with an owner, lifecycle, version, and status. *Realized by* `'Controlled Document'`; identified by a minted **Doc ID** `THG-{DEPT}-{TYPE}-NNN`.
- **CPI — Cost Performance Index** — `EV ÷ AC`. Below 1.0 = over budget. *Realized by* `[CPI]`.
- **CR status** — The workflow state of a change request: Open / In Assessment / Implementing / Verified / Closed / Rejected. *Realized by* `'Change Request'[CR Status]` (the second axis alongside **Decision**).
- **CV — Cost Variance** — `EV − AC`. Negative = over budget. *Realized by* `[Cost Variance (CV)]`.
- **Cycle time (CR)** — Days from request to decision on a CR. *Realized by* `[Avg CR Cycle Days]`.

## D

- **Decision (governance)** — A formally logged project decision with a rationale, decider, and date. Minted `D-NNN` per project. *Realized by* `'Decision'` / `[Decisions Logged]`.
- **Decision (CR axis)** — The gate verdict on a change request: **Pending** / **Approved** / **Deferred** / **Rejected**. *Realized by* `'Change Request'[Decision]`.
- **Default-deny** — The RLS posture: a user with **no** active access grant sees **nothing**. The PMO must seed grants before sharing. See **RLS**, **Report Access**.
- **Department** — One of the **8 Theragen departments** (exact strings): Clinical / Medical Affairs · Regulatory / Quality · R&D / Engineering · Operations / PMO · Finance / Procurement · Commercial / Marketing · IT / Data / Security · HR / People. *Realized by* `'Department'`.
- **Doc ID** — A controlled document's minted identifier, `THG-{DEPT}-{TYPE}-NNN` (e.g. `THG-OPS-CHR-001`), where DEPT is the department code and TYPE is the document-type code (CHR/SOP/PLN/SCP/RPT/POL/WI/FRM). Globally unique.
- **Document status** — A controlled document's / version's lifecycle state: **DRAFT** / **REVIEW** / **BASELINE** / **AMENDED** / **RETIRED**. *Realized by* `'Controlled Document'[Status]`, `'Document Version'[Status]`.
- **Document version** — A specific revision of a controlled document (version string, change summary, author, status). *Realized by* `'Document Version'`; may cite the governance CR that drove it via **Linked CR**.
- **Duration (working days)** — An activity's planned span counted Mon–Fri inclusive. *Realized by* `'Schedule Activity'[Duration Days]`.

## E

- **EAC — Estimate at Completion** — Performance-adjusted forecast of total cost, `BAC ÷ CPI`. *Realized by* `[EAC]`.
- **Earned Value (EV)** — The budgeted value of work actually completed, work-package estimate × mean % complete. *Realized by* `[Earned Value]`.
- **EVM — Earned Value Management** — The cost/schedule performance discipline relating planned value, earned value, and actual cost (PV/EV/AC) to derive CV, SV, CPI, SPI, EAC, VAC, TCPI. All in the **EVM** measure folder.
- **External grantee (B2B guest)** — A non-Theragen person (CRO, contractor, vendor) given report access. Granted by their **real email**; the `'Scoped Viewer'` role resolves their mangled Entra guest UPN automatically. Policy: externals get **Project** scope only.
- **external_ref** — The SharePoint List item id stored on a synced row, giving each artifact a stable identity so re-syncs **update** rather than duplicate (idempotency).

## F

- **FTE — Full-Time Equivalent** — Team allocation expressed as full-time headcount (allocation % ÷ 100). *Realized by* `[Total FTE]`, `[Avg Allocation Pct]`.

## G

- **Governance Change Assessment** — A per-department impact statement on a **governance** CR. *Realized by* `'Governance Change Assessment'`.
- **Governance Change Request (Gov CR)** — A **document-scoped** (project-less) controlled change to a controlled document, minted `CHG-NNN` (globally unique). Reuses the same two-axis Decision × Status workflow as project CRs. *Realized by* `'Governance Change Request'`.

## H

- **Health (project)** — Overall and per-knowledge-area condition reported each period as Green / Yellow / Red. *Realized by* `[Latest Overall Status]`, `[Health Score]`, `'Status Report Area'`.
- **Hold (phase gate)** — A gate decision that keeps the project in its current phase (no advance). *Realized by* `'Phase Gate Log'[Gate Decision]` = `Held`, counted by `[Gates Held]`.

## I

- **Idempotency** — The property that running the sync again with no source changes produces no database changes (no-ops). Anchored on **external_ref**.
- **Impact (risk)** — The severity score (1–5) of a risk if it occurs; one axis of the 5×5 matrix. *Realized by* `'Risk'[Impact]`.
- **Informed** — In RACI, a role kept up to date (the "I").

## K

- **Knowledge Area** — A PMI knowledge area (Scope, Schedule, Cost, Quality, Risk, etc.) used to structure status reporting. *Realized by* `'Knowledge Area'`, `'Status Report Area'`.

## L

- **Lesson Learned** — A captured retrospective insight (Open / Adopted). *Realized by* `'Lesson Learned'`.
- **Lifecycle phase** — The PMI process group a project is in: **Initiating → Planning → Executing → Monitoring & Controlling → Closing**. Advanced only through a **phase gate**. *Realized by* `'Project'[Lifecycle Phase]`, `[Current Phase]`.
- **Likelihood** — The probability score (1–5) of a risk; the other axis of the 5×5 matrix. *Realized by* `'Risk'[Likelihood]`.
- **Linked CR** — On a document version, the governance CR (`CHG-NNN`) that drove the revision. *Realized by* `'Document Version'[Linked CR]`.

## M

- **Milestone** — A schedule checkpoint with a baseline date and an actual/forecast date; status Achieved / At risk / Slipped. *Realized by* `'Milestone'`; on-time landing via `[Milestone Hit Rate]`, drift via `[Avg Milestone Slip Days]`.

## O

- **Orphan-keep** — The delete policy: removing a SharePoint List row does **not** delete the database row; it is retained (logged INFO). Data is additive and audited, never silently dropped.
- **Overall status** — The project-level Green/Yellow/Red from the latest status report. *Realized by* `[Latest Overall Status]`, rendered as a traffic light by `[Main Status]` / `[Status Color]`.

## P

- **Phase gate** — A control point where a project is approved to advance (or held) between lifecycle phases. **Forward-only**: backward transitions are rejected; Held is always legal. *Realized by* `'Phase Gate Log'`, decisions Approved / Approved with conditions / Held; advances counted by `[Phase Gates Passed]`.
- **Planned Value (PV)** — The budgeted value of work *scheduled* to be done as of today. *Realized by* `[Planned Value]`.
- **Portfolio** — The full set of projects. *Realized by* `[Projects]`, `[Active Projects]`, `[Portfolio Charter Budget]` (the **Portfolio** measure folder).
- **Provenance stamp** — The header on the generated data dictionary recording when/what it was generated from (date, git SHA, model version, object counts) — the versioning marker on that artifact.

## R

- **RACI** — Responsibility-assignment scheme: **R**esponsible / **A**ccountable / **C**onsulted / **I**nformed. Applied per-department to controlled documents. *Realized by* `'Document RACI'[Role]` ∈ {R, A, C, I}.
- **Realized risk** — A risk that has occurred. *Realized by* `[Realized Risks]`; status `'Risk'[Risk Status]` = Realized.
- **Report Access** — The authored grant list driving RLS: each row grants a user a **scope** (Project / Department / All). *Realized by* `'Report Access'` (a hidden, disconnected table) → `pmbok.report_access`.
- **Republish** — Re-publishing the `.pbip` from Power BI Desktop. Required to surface **new model tables/columns/measures/descriptions/roles**; the nightly service refresh is **data-only** and cannot do this.
- **Residual (risk)** — The risk score expected to remain *after* planned mitigation. *Realized by* `'Risk'[Residual Score]`, `[Residual Exposure]`, `[Risk Reduction Pct]`.
- **Responsible** — In RACI, the role(s) that do the work (the "R"). *Realized by* `[Responsible Assignments]`.
- **Risk** — An uncertain event scored on a **5×5** matrix. **Risk Score = Likelihood × Impact** (max 25); **High ≥ 12**, **Critical ≥ 20**. *Realized by* `'Risk'`; status Open / Mitigating / Monitoring / Realized / Closed.
- **Risk response / action** — A planned action against a risk, typed **Mitigation / Transfer / Acceptance / Avoidance**, with its own status. *Realized by* `'Risk Response'`; `[Open Risk Actions]`, `[Overdue Risk Actions]`, `[Mitigation Coverage %]`.
- **RLS — Row-Level Security** — Data-driven visibility: the `'Scoped Viewer'` role filters every fact to the projects a user is granted, via `USERPRINCIPALNAME()` matched against active **Report Access** grants. `'All Access'` is the admin bypass. Default-deny.

## S

- **§11 (21 CFR Part 11)** — The FDA regulation governing legally-binding electronic signatures on GxP records. This system records **attestations**, explicitly **not** §11 signatures; a true §11 ceremony is decision-gated (pending a Quality/Regulatory scope call).
- **Scope (baseline type)** — The charter/scope snapshot frozen as a baseline (business case, in/out of scope, acceptance). One of the three baseline types alongside Schedule and Budget.
- **Semantic model** — The Power BI data model (tables, columns, measures, relationships, roles) maintained as **TMDL** text in git. The model reads only from `bi.*` views.
- **Sign-off (status report)** — Formal approver acceptance of a status report. *Realized by* `'Status Report'[Is Signed Off]`, `[Signed-off Reports]`, `[Sign-off Rate]`.
- **Soft-authority warning** — When a decider isn't the project Sponsor/PM (or document Owner/Approver), the row still syncs but carries a note; the audit trail records the real decider. Hard rejection requires `enforce_decision_authority`.
- **SPI — Schedule Performance Index** — `EV ÷ PV`. Below 1.0 = behind schedule. *Realized by* `[SPI]`.
- **Stakeholder** — A person or group with interest/influence in a project, plotted on the influence/interest grid. *Realized by* `'Stakeholder'`; `[Key Players]` = high-influence & high-interest.
- **Status report** — A period status submission with overall G/Y/R, trend, per-area health, and optional sign-off. *Realized by* `'Status Report'` + `'Status Report Area'`.
- **SV — Schedule Variance** — `EV − PV`. Negative = behind schedule. *Realized by* `[Schedule Variance (SV)]`.
- **Sync** — The registry-driven Python job (`tools/sync_artifacts.py`) that reads the SharePoint Lists and writes PostgreSQL each morning. Pure logic lives in `tools/artifact_lib.py`.

## T

- **TCPI — To-Complete Performance Index** — `(BAC − EV) ÷ (BAC − AC)`: the cost efficiency required on remaining work to finish on budget. Above 1.0 = tighter control needed. *Realized by* `[TCPI]`.
- **Team member** — A person assigned to a project with an allocation %. *Realized by* `'Team Member'`; see **FTE**.
- **TMDL** — Tabular Model Definition Language, the text format the semantic model is authored in. A `///` line above an object is its **description** (the source of field tooltips and the data dictionary).
- **Trend** — The direction of project health on the latest report (improving / steady / declining). *Realized by* `[Latest Trend]`.

## V

- **VAC — Variance at Completion** — `BAC − EAC`. Negative = projected overrun. *Realized by* `[VAC]`.
- **Verified (CR)** — An approved change request whose implementation has been confirmed. *Realized by* `[Verified CRs]`, `[Verified Governance CRs]`.

## W

- **WBS — Work Breakdown Structure** — The two-tier decomposition of project work: **Workstream** (level 1) → **Work Package** (level 2) → activities. Codes are minted append-only (`1`, `1.1`, `2`…). *Realized by* `'WBS Element'` (`'WBS Element'[WBS Level]` 1 or 2).
- **Work package** — A level-2 WBS node grouping related activities; the unit EVM estimates attach to. *Realized by* level-2 `'WBS Element'`.
- **Working budget** — Funded budget adjusted for approved CR cost impact. *Realized by* `[Working Budget]`.
- **Workstream** — A level-1 WBS node (a major stream of work). Rolled-up status via `[Workstream Status]` (COMPLETED / AT RISK / NOT STARTED / ON TRACK).
