# Theragen Project Planner — Data Dictionary

_Generated from the semantic-model TMDL by `tools/build_data_dictionary.py` — **do not edit by hand**; regenerate after model changes (see [change-control process](change-control-process.md)). Business definitions live in the [glossary](glossary.md)._

> Generated from model `59d8b95` (2026-06-17) · platform **v2.8**  
> 35 tables · 360 columns · 162 measures · 47 relationships · 2 roles

## Model index

| Table | Source | Cols | Measures | Description |
|---|---|---|---|---|
| [_Measures](#_measures) | — | 1 | 162 | Measure home table. All portfolio analytics measures live here. |
| [Budget Line](#budget-line) | `bi.budget_line_item` | 13 | 0 | Fact - cost budget estimate lines (PMBOK P13), one per level-1 deliverable. |
| [Change Impact Assessment](#change-impact-assessment) | `bi.change_impact_assessment` | 11 | 0 | Fact - per-department change-impact assessments (PMBOK P22). One row per department's impact statement on a change request. |
| [Change Request](#change-request) | `bi.change_request` | 24 | 0 | Fact - project change requests (PMBOK P21) with impact and decision cycle. |
| [Closure Item](#closure-item) | `bi.closure_checklist_item` | 7 | 0 | Fact - project closure checklist items (PMBOK P26). |
| [Controlled Document](#controlled-document) | `bi.document` | 17 | 0 | Fact - controlled-document register (doc_mgmt spine). One row per controlled document, org-wide. |
| [Cost Actual](#cost-actual) | `bi.cost_actual` | 10 | 0 | Fact - per-work-package, per-period actual cost (EVM AC). One row per logged cost actual against a WBS work package. |
| [Date](#date) | — | 7 | 0 | Marked date dimension covering 2025-2027. |
| [Decision](#decision) | `bi.decision` | 7 | 0 | Fact - governance decisions (PMBOK P21). Formal decisions logged against a project. |
| [Department](#department) | `bi.department` | 3 | 0 | Conformed department dimension (DM D01). Filters executing departments on facts. |
| [Directory](#directory) | `bi.org_directory` | 12 | 0 | Org directory: Theragen staff from Entra (enabled members on theragen.com / actastim.com) plus the sample seed persons, with the PMO-curated department. Sourced by tools/sync_directory.py; consumes bi.org_directory. Standalone (no relationships) - department slices via the local Department column. |
| [Document Approval](#document-approval) | `bi.document_approval` | 11 | 0 | Fact - per-version sign-off ATTESTATION (non-Part-11; see esig_kind). |
| [Document RACI](#document-raci) | `bi.raci_assignment` | 10 | 0 | Fact - per-document, per-department R/A/C/I assignment (effective-dated). |
| [Document Version](#document-version) | `bi.document_version` | 13 | 0 | Fact - controlled-document version history. |
| [Governance Change Assessment](#governance-change-assessment) | `bi.change_assessment_gov` | 9 | 0 | Fact - per-department impact assessments on a governance change request. One row per department's impact statement on a gov CR. |
| [Governance Change Request](#governance-change-request) | `bi.change_request_gov` | 16 | 0 | Fact - governance change requests (CHG-NNN) against controlled documents (SOP-003). Document-scoped, project-less; reuses the two-axis Decision/Status workflow. |
| [Knowledge Area](#knowledge-area) | `bi.knowledge_area` | 2 | 0 | PMBOK knowledge areas (enum knowledge_area) used by status report health entries. |
| [Lesson Learned](#lesson-learned) | `bi.lesson_learned` | 9 | 0 | Fact - lessons learned (PMBOK P25). |
| [Milestone](#milestone) | `bi.milestone` | 10 | 0 | Fact - milestones (PMBOK P11). Baseline vs forecast vs actual dates. |
| [Person](#person) | `bi.person` | 6 | 0 | Person directory (DM D02). Owners, requesters and assignees on facts. |
| [Phase Gate Log](#phase-gate-log) | `bi.phase_gate_log` | 9 | 0 | Fact - append-only record of lifecycle-phase handoffs (PMBOK). Captures who approved each phase transition, when, and the gate decision. |
| [Platform Change](#platform-change) | `bi.platform_change` | 9 | 0 | Fact - platform change register (Round 2 dogfood). One row per logged change to the BI platform itself, in a change-control-process.md category. |
| [Project](#project) | `bi.project` | 18 | 0 | Project dimension - one row per project (PMBOK P01 project, charter fields denormalized). |
| [Project Baseline](#project-baseline) | `bi.project_baseline` | 11 | 0 | Fact - immutable schedule/scope/budget baselines (PMBOK). Each new baseline mints the next version; prior BASELINED rows go SUPERSEDED. |
| [Recent Accomplishment](#recent-accomplishment) | — | 4 | 0 | Leadership view - work completed in the last 35 days (done activities + achieved milestones). |
| [Report Access](#report-access) | `bi.report_access` | 7 | 0 | Security - data-driven RLS grants. Disconnected (no relationships): the "Scoped Viewer" role reads it via USERPRINCIPALNAME() to filter Project. Hidden so the access map never appears in the field list. |
| [Risk](#risk) | `bi.risk` | 19 | 0 | Fact - risk register (PMBOK P14). 5x5 likelihood x impact scoring. |
| [Risk Response](#risk-response) | `bi.risk_response` | 9 | 0 | Fact - risk response actions (PMBOK P15). |
| [Schedule Activity](#schedule-activity) | `bi.schedule_activity` | 16 | 0 | Fact - schedule activities (PMBOK P10). One row per activity with planned/actual dates and percent complete. |
| [Stakeholder](#stakeholder) | `bi.stakeholder` | 12 | 0 | Fact - stakeholder register entries (PMBOK P03) with RACI engagement and interest/influence. |
| [Status Report](#status-report) | `bi.status_report` | 15 | 0 | Fact - periodic status reports (PMBOK P23). Overall G/Y/R health and trend per period. |
| [Status Report Area](#status-report-area) | `bi.status_report_area` | 5 | 0 | Fact - per-knowledge-area health entries within each status report (PMBOK P24). |
| [Team Member](#team-member) | `bi.project_team_member` | 10 | 0 | Fact - project team assignments (PMBOK P31) with allocation percentage. |
| [Upcoming Next Step](#upcoming-next-step) | — | 5 | 0 | Leadership view - open work targeted in the next 45 days (activities + milestones). |
| [WBS Element](#wbs-element) | `bi.wbs_element` | 13 | 0 | Work breakdown structure dimension (PMBOK P08). Two-level hierarchy: deliverable > work package. |

**Roles (RLS):** `All Access` (read) — PMO / admin all-access role: no table filters, sees the whole portfolio. The bootstrap safety net so admins are never locked out by default-deny (equivalent to an "All" grant). · `Scoped Viewer` (read) — Data-driven RLS: a member sees only the projects granted to their UPN in the Report Access table (Project / Department / All), via the union of their active grants. Default-deny - no grant = no rows. Matches internal UPNs directly AND Entra B2B guests (whose UPN is jane_cro.com#EXT#@<tenant>.onmicrosoft.com) by forward-mangling the grant email (@->_) and comparing to the pre-#EXT# prefix - so externals can be granted by their real email.

<a id="_measures"></a>
## _Measures

Measure home table. All portfolio analytics measures live here.

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Value | string | yes |  | Hidden placeholder column for the measure-host table; carries no data. |

**Measures**

| Measure | Format | Folder | Description | DAX |
|---|---|---|---|---|
| Baselines | #,0 | Baselines | Count of baseline rows in context (all versions and statuses). | `COUNTROWS('Project Baseline')` |
| Budget Variance vs Baseline | \$#,##0;(\$#,##0);\$0 | Baselines | Drift of the current approved budget from the frozen BASELINED Budget baseline (current charter budget minus the baseline's snapshot budget_total). Positive = budget grew since baseline. | `SUM('Project'[Charter Budget]) - SUMX(FILTER('Project Baseline', 'Project Baseline'[Baseline Type]="Budget" && 'Project Baseline'[Status]="BASELINED"), 'Project Baseline'[Baseline Budget Total])` |
| Current Baselines | #,0 | Baselines | Baselines that are currently the active (BASELINED) version. | `CALCULATE([Baselines], 'Project Baseline'[Status] = "BASELINED")` |
| Current Budget Baseline Version |  | Baselines | Active Budget baseline version (highest among BASELINED). | `CALCULATE(MAX('Project Baseline'[Version]), 'Project Baseline'[Baseline Type] = "Budget", 'Project Baseline'[Status] = "BASELINED")` |
| Current Schedule Baseline Version |  | Baselines | Active Schedule baseline version (highest among BASELINED). | `CALCULATE(MAX('Project Baseline'[Version]), 'Project Baseline'[Baseline Type] = "Schedule", 'Project Baseline'[Status] = "BASELINED")` |
| Current Scope Baseline Version |  | Baselines | Active Scope baseline version (highest among BASELINED). | `CALCULATE(MAX('Project Baseline'[Version]), 'Project Baseline'[Baseline Type] = "Scope", 'Project Baseline'[Status] = "BASELINED")` |
| Approved CRs | #,0 | Change | CRs approved. | `CALCULATE([Change Requests], 'Change Request'[Decision] = "Approved")` |
| Approved Governance CRs | #,0 | Change | Governance CRs whose decision is Approved. | `CALCULATE([Governance CRs], 'Governance Change Request'[Decision] = "Approved")` |
| Assessed CRs | #,0 | Change | Distinct CRs with at least one impact assessment. | `DISTINCTCOUNT('Change Impact Assessment'[CR ID])` |
| Assessed Cost Impact | \$#,##0;(\$#,##0);\$0 | Change | Total assessed cost impact across departments. | `SUM('Change Impact Assessment'[Cost Impact])` |
| Assessed Governance CRs | #,0 | Change | Distinct governance CRs that have at least one department assessment. | `DISTINCTCOUNT('Governance Change Assessment'[CR Gov ID])` |
| Assessed Schedule Impact Days | #,0 | Change | Total assessed schedule impact across departments (days). | `SUM('Change Impact Assessment'[Schedule Impact Days])` |
| Avg CR Cycle Days | #,0.0 | Change | Mean days from request to decision. | `AVERAGE('Change Request'[Cycle Time Days])` |
| CR Approval Rate | 0.0%;-0.0%;0.0% | Change | Approved share of decided CRs. | `DIVIDE([Approved CRs], [Approved CRs] + [Rejected CRs])` |
| CRs Pending Verification | #,0 | Change | Approved CRs awaiting implementation verification. | `CALCULATE([Change Requests], 'Change Request'[Decision] = "Approved", 'Change Request'[Implementation Verified] = FALSE())` |
| Change Requests | #,0 | Change | Count of CRs. | `COUNTROWS('Change Request')` |
| Decisions Logged | #,0 | Change | Governance decisions formally logged for the project(s) in context. | `COUNTROWS('Decision')` |
| Departments Assessed | #,0 | Change | Distinct departments that assessed a CR. | `DISTINCTCOUNT('Change Impact Assessment'[Department])` |
| Emergency CRs | #,0 | Change | Emergency / safety class CRs. | `CALCULATE([Change Requests], 'Change Request'[CR Class] = "Emergency / Safety")` |
| Governance Assessments | #,0 | Change | Per-department impact assessments on governance CRs. | `COUNTROWS('Governance Change Assessment')` |
| Governance CRs | #,0 | Change | Governance change requests against controlled documents (CHG-NNN). | `COUNTROWS('Governance Change Request')` |
| Impact Assessments | #,0 | Change | Count of per-department impact assessments. | `COUNTROWS('Change Impact Assessment')` |
| Net Schedule Impact Days | #,0 | Change | Net schedule delta from approved CRs. | `CALCULATE(SUM('Change Request'[Schedule Impact Days]), 'Change Request'[Decision] = "Approved")` |
| Open CRs | #,0 | Change | CRs still in the pipeline. | `CALCULATE([Change Requests], NOT 'Change Request'[CR Status] IN {"Closed", "Rejected"})` |
| Open Governance CRs | #,0 | Change | Governance CRs not yet closed. | `CALCULATE([Governance CRs], 'Governance Change Request'[Status] = "Open")` |
| Pending CRs | #,0 | Change | CRs awaiting a decision. | `CALCULATE([Change Requests], 'Change Request'[Decision] = "Pending")` |
| Rejected CRs | #,0 | Change | CRs rejected. | `CALCULATE([Change Requests], 'Change Request'[Decision] = "Rejected")` |
| Verified CRs | #,0 | Change | Approved CRs with implementation confirmed in the artifact library. | `CALCULATE([Change Requests], 'Change Request'[Implementation Verified] = TRUE())` |
| Verified Governance CRs | #,0 | Change | Governance CRs whose implementation has been verified (mirrors Verified CRs). | `CALCULATE([Governance CRs], 'Governance Change Request'[Implementation Verified] = TRUE())` |
| Adopted Lessons | #,0 | Closing | Lessons adopted into practice. | `CALCULATE([Lessons], 'Lesson Learned'[Lesson Status] = "Adopted")` |
| Closure Complete Pct | 0.0%;-0.0%;0.0% | Closing | Closure checklist completion. | `DIVIDE([Closure Items Done], [Closure Items])` |
| Closure Items | #,0 | Closing | Closure checklist items. | `COUNTROWS('Closure Item')` |
| Closure Items Done | #,0 | Closing | Checklist items complete. | `CALCULATE([Closure Items], 'Closure Item'[Done] = TRUE())` |
| Lessons | #,0 | Closing | Lessons captured. | `COUNTROWS('Lesson Learned')` |
| Open Lessons | #,0 | Closing | Lessons awaiting action. | `CALCULATE([Lessons], 'Lesson Learned'[Lesson Status] = "Open")` |
| Approved CR Cost Impact | \$#,##0;(\$#,##0);\$0 | Cost | Net cost impact of approved change requests. | `CALCULATE(SUM('Change Request'[Cost Impact]), 'Change Request'[Decision] = "Approved")` |
| Budget Subtotal | \$#,##0;(\$#,##0);\$0 | Cost | Budget before contingency. | `SUM('Budget Line'[Subtotal])` |
| Budget Total | \$#,##0;(\$#,##0);\$0 | Cost | Funded budget including contingency (budget_line_item.total). | `SUM('Budget Line'[Total])` |
| Budget vs Charter | \$#,##0;(\$#,##0);\$0 | Cost | Detailed budget vs charter-approved total. Positive = over charter. | `[Budget Total] - [Portfolio Charter Budget]` |
| Contingency Amount | \$#,##0;(\$#,##0);\$0 | Cost | Contingency reserve in the funded budget. | `[Budget Total] - [Budget Subtotal]` |
| Labor Amount | \$#,##0;(\$#,##0);\$0 | Cost | Labor component. | `SUM('Budget Line'[Labor Amount])` |
| Materials Amount | \$#,##0;(\$#,##0);\$0 | Cost | Materials component. | `SUM('Budget Line'[Materials Amount])` |
| Other Amount | \$#,##0;(\$#,##0);\$0 | Cost | Other cost component. | `SUM('Budget Line'[Other Amount])` |
| Vendor Amount | \$#,##0;(\$#,##0);\$0 | Cost | Vendor / contractor component. | `SUM('Budget Line'[Vendor Amount])` |
| Working Budget | \$#,##0;(\$#,##0);\$0 | Cost | Funded budget adjusted for approved change requests. | `[Budget Total] + [Approved CR Cost Impact]` |
| Active Staff | #,0 | Directory | People whose Entra account is enabled. | `CALCULATE(COUNTROWS('Directory'), 'Directory'[Active] = TRUE())` |
| Departments Assigned | #,0 | Directory | Distinct departments with at least one assigned person (excludes Unassigned). | `CALCULATE(DISTINCTCOUNT('Directory'[Department]), 'Directory'[Department Unassigned] = FALSE())` |
| Headcount | #,0 | Directory | Total people in the directory (Entra staff + sample seed persons). | `COUNTROWS('Directory')` |
| Staff with Report Access | #,0 | Directory | People holding at least one active Report Access (RLS) grant. | `CALCULATE(COUNTROWS('Directory'), 'Directory'[Has Report Access] = TRUE())` |
| Unassigned Staff | #,0 | Directory | People with no curated department yet (awaiting PMO assignment in the Staff Directory List). | `CALCULATE(COUNTROWS('Directory'), 'Directory'[Department Unassigned] = TRUE())` |
| Accountable Assignments | #,0 | Documents | RACI rows with the Accountable role. | `CALCULATE([RACI Assignments], 'Document RACI'[Role] = "A")` |
| Approval Attestations | #,0 | Documents | Attestations whose meaning is Approval. | `CALCULATE([Document Approvals], 'Document Approval'[Signature Meaning] = "Approval")` |
| Attested Versions | #,0 | Documents | Distinct versions carrying at least one attestation. | `DISTINCTCOUNT('Document Approval'[Version ID])` |
| Baseline Documents | #,0 | Documents | Documents at BASELINE. | `CALCULATE([Controlled Documents], 'Controlled Document'[Status] = "BASELINE")` |
| Baseline Versions | #,0 | Documents | Versions at BASELINE. | `CALCULATE([Document Versions], 'Document Version'[Status] = "BASELINE")` |
| Controlled Documents | #,0 | Documents | Count of controlled documents. | `COUNTROWS('Controlled Document')` |
| Current RACI Assignments | #,0 | Documents | RACI assignments currently in effect (open-ended or not yet expired). | `CALCULATE([RACI Assignments], FILTER('Document RACI', ISBLANK('Document RACI'[Valid To]) \|\| 'Document RACI'[Valid To] >= TODAY()))` |
| Document Approvals | #,0 | Documents | Count of sign-off attestations (non-Part-11; see 'Document Approval'[Attestation Kind]). | `COUNTROWS('Document Approval')` |
| Document Versions | #,0 | Documents | Count of controlled-document versions. | `COUNTROWS('Document Version')` |
| Documents Due for Review | #,0 | Documents | Active documents past their next review date. | `CALCULATE([Controlled Documents], FILTER('Controlled Document', NOT ISBLANK('Controlled Document'[Next Review Due]) && 'Controlled Document'[Next Review Due] <= TODAY() && 'Controlled Document'[Status] <> "RETIRED"))` |
| Documents with RACI | #,0 | Documents | Documents that have at least one RACI assignment. | `DISTINCTCOUNT('Document RACI'[Document ID])` |
| Draft Documents | #,0 | Documents | Documents in DRAFT. | `CALCULATE([Controlled Documents], 'Controlled Document'[Status] = "DRAFT")` |
| RACI Assignments | #,0 | Documents | Count of document RACI assignments. | `COUNTROWS('Document RACI')` |
| Responsible Assignments | #,0 | Documents | RACI rows with the Responsible role. | `CALCULATE([RACI Assignments], 'Document RACI'[Role] = "R")` |
| Retired Documents | #,0 | Documents | Documents retired. | `CALCULATE([Controlled Documents], 'Controlled Document'[Status] = "RETIRED")` |
| AC (Actual Cost) | \$#,##0;(\$#,##0);\$0 | EVM | AC - cumulative actual cost to date (sum of logged cost actuals). | `SUM('Cost Actual'[Amount])` |
| BAC (WBS Estimates) | \$#,##0;(\$#,##0);\$0 | EVM | Budget at completion from work-package estimates (wbs_element.estimated_cost). EVM baseline. | `CALCULATE(SUM('WBS Element'[Estimated Cost]), 'WBS Element'[WBS Level] = 2)` |
| CPI | 0.00 | EVM | Cost Performance Index = EV / AC. Below 1.0 = over budget. | `DIVIDE([Earned Value], [AC (Actual Cost)])` |
| Cost Variance (CV) | \$#,##0;(\$#,##0);\$0 | EVM | CV = EV - AC. Negative = over budget. | `[Earned Value] - [AC (Actual Cost)]` |
| EAC | \$#,##0;(\$#,##0);\$0 | EVM | Estimate at Completion = BAC / CPI (performance-based forecast). | `DIVIDE([BAC (WBS Estimates)], [CPI])` |
| Earned Value | \$#,##0;(\$#,##0);\$0 | EVM | EV = work-package estimate x mean percent complete of its activities. | `SUMX(FILTER('WBS Element', 'WBS Element'[WBS Level] = 2), 'WBS Element'[Estimated Cost] * CALCULATE(AVERAGE('Schedule Activity'[Pct Complete])) / 100)` |
| Planned Value | \$#,##0;(\$#,##0);\$0 | EVM | PV = work-package estimate x planned-elapsed fraction of its activities as of today. | `VAR AsOf = TODAY() RETURN SUMX(FILTER('WBS Element', 'WBS Element'[WBS Level] = 2), 'WBS Element'[Estimated Cost] * CALCULATE(AVERAGEX('Schedule Activity', VAR s = 'Schedule Activity'[Planned Start] VAR f = 'Schedule Activity'[Planned Finish] RETURN IF(AsOf >= f, 1, IF(AsOf <= s, 0, DIVIDE(AsOf - s, f - s))))))` |
| SPI | 0.00 | EVM | Schedule Performance Index = EV / PV. Below 1.0 = behind schedule. CPI/EAC require a cost-actuals feed (Phase 2 - not in THG-ENT-DBS-001 v1.0). | `DIVIDE([Earned Value], [Planned Value])` |
| Schedule Variance (SV) | \$#,##0;(\$#,##0);\$0 | EVM | EV minus PV. Negative = behind schedule. | `[Earned Value] - [Planned Value]` |
| TCPI | 0.00 | EVM | To-Complete Performance Index = (BAC - EV) / (BAC - AC). Above 1.0 = tighter cost control needed to finish on budget. | `DIVIDE([BAC (WBS Estimates)] - [Earned Value], [BAC (WBS Estimates)] - [AC (Actual Cost)])` |
| VAC | \$#,##0;(\$#,##0);\$0 | EVM | Variance at Completion = BAC - EAC. Negative = projected overrun. | `[BAC (WBS Estimates)] - [EAC]` |
| Gates Held | #,0 | Governance | Phase gates where the decision was Held. | `CALCULATE(COUNTROWS('Phase Gate Log'), 'Phase Gate Log'[Gate Decision] = "Held")` |
| Phase Gates Passed | #,0 | Governance | Phase gates that advanced the project a real step forward (Approved / Approved with conditions, From != To). | `COUNTROWS(FILTER('Phase Gate Log', 'Phase Gate Log'[Gate Decision] IN {"Approved", "Approved with conditions"} && 'Phase Gate Log'[From Phase] <> 'Phase Gate Log'[To Phase]))` |
| Area Entries | #,0 | Health | Knowledge-area health entries in context. | `COUNTROWS('Status Report Area')` |
| Green Areas | #,0 | Health | Knowledge-area entries reported Green. | `CALCULATE(COUNTROWS('Status Report Area'), 'Status Report Area'[Area Status] = "Green")` |
| Health Score | 0.00 | Health | Mean knowledge-area health: Green=3, Yellow=2, Red=1. | `AVERAGEX('Status Report Area', SWITCH('Status Report Area'[Area Status], "Green", 3, "Yellow", 2, "Red", 1))` |
| Latest Overall Status |  | Health | Overall G/Y/R from the most recent report in context. | `VAR d0 = MAX('Status Report'[Period End]) RETURN MAXX(FILTER('Status Report', 'Status Report'[Period End] = d0), 'Status Report'[Overall Status])` |
| Latest Report Date | yyyy-mm-dd | Health | Most recent reporting period end. | `MAX('Status Report'[Period End])` |
| Latest Trend |  | Health | Trend from the most recent report in context. | `VAR d0 = MAX('Status Report'[Period End]) RETURN MAXX(FILTER('Status Report', 'Status Report'[Period End] = d0), 'Status Report'[Trend])` |
| Red Areas | #,0 | Health | Knowledge-area entries reported Red. | `CALCULATE(COUNTROWS('Status Report Area'), 'Status Report Area'[Area Status] = "Red")` |
| Sign-off Rate | 0.0%;-0.0%;0.0% | Health | Proportion of status reports that have been signed off. | `DIVIDE([Signed-off Reports], COUNTROWS('Status Report'))` |
| Signed-off Reports | #,0 | Health | Status reports that have been formally signed off by the approver. | `CALCULATE(COUNTROWS('Status Report'), 'Status Report'[Is Signed Off] = TRUE())` |
| Status Reports | #,0 | Health | Reports submitted. | `COUNTROWS('Status Report')` |
| Yellow Areas | #,0 | Health | Knowledge-area entries reported Yellow. | `CALCULATE(COUNTROWS('Status Report Area'), 'Status Report Area'[Area Status] = "Yellow")` |
| Avg Milestone Slip Days | #,0.0 | Milestones | Mean slip days (actual/forecast vs baseline). Positive = late. | `AVERAGE('Milestone'[Slip Days])` |
| Milestone Hit Rate | 0.0%;-0.0%;0.0% | Milestones | Achieved milestones that landed on or before baseline. | `DIVIDE(COUNTROWS(FILTER('Milestone', 'Milestone'[Milestone Status] = "Achieved" && NOT ISBLANK('Milestone'[Actual Date]) && 'Milestone'[Actual Date] <= 'Milestone'[Baseline Date])), [Milestones Achieved])` |
| Milestones | #,0 | Milestones | Count of milestones. | `COUNTROWS('Milestone')` |
| Milestones Achieved | #,0 | Milestones | Milestones achieved. | `CALCULATE([Milestones], 'Milestone'[Milestone Status] = "Achieved")` |
| Milestones At Risk | #,0 | Milestones | Milestones at risk. | `CALCULATE([Milestones], 'Milestone'[Milestone Status] = "At risk")` |
| Milestones Slipped | #,0 | Milestones | Milestones slipped. | `CALCULATE([Milestones], 'Milestone'[Milestone Status] = "Slipped")` |
| Changes Deployed | #,0 | Platform | Platform changes deployed (Status = Deployed). | `CALCULATE([Platform Changes], 'Platform Change'[Status] = "Deployed")` |
| Changes Pending Approval | #,0 | Platform | Platform changes still awaiting approval (Status = Proposed). | `CALCULATE([Platform Changes], 'Platform Change'[Status] = "Proposed")` |
| Platform Changes | #,0 | Platform | Count of platform changes logged in the change register (Round 2 dogfood). | `COUNTROWS('Platform Change')` |
| Active Projects | #,0 | Portfolio | Projects with status Active. | `CALCULATE([Projects], 'Project'[Project Status] = "Active")` |
| Portfolio Charter Budget | \$#,##0;(\$#,##0);\$0 | Portfolio | Sum of charter-approved budget totals (project.budget_total). | `SUM('Project'[Charter Budget])` |
| Projects | #,0 | Portfolio | Count of projects in context. | `COUNTROWS('Project')` |
| Proposed Projects | #,0 | Portfolio | Projects with status Proposed. | `CALCULATE([Projects], 'Project'[Project Status] = "Proposed")` |
| Avg Impact (Open) | #,0.0 | Risk | Mean impact (1-5) of open risks. | `CALCULATE(AVERAGE('Risk'[Impact]), 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| Avg Likelihood (Open) | #,0.0 | Risk | Mean likelihood (1-5) of open risks. | `CALCULATE(AVERAGE('Risk'[Likelihood]), 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| Avg Residual Score (Open) | #,0.0 | Risk | Mean residual score of open risks after planned mitigation. | `CALCULATE(AVERAGE('Risk'[Residual Score]), 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| Avg Risk Score | #,0.0 | Risk | Mean risk score. | `AVERAGE('Risk'[Risk Score])` |
| Avg Risk Score (Open) | #,0.0 | Risk | Mean L x I score of open risks on the 1-25 scale. Gauge value. | `CALCULATE(AVERAGE('Risk'[Risk Score]), 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| Critical Risks | #,0 | Risk | Open risks with score >= 20. | `CALCULATE([Risks], 'Risk'[Risk Score] >= 20, 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| High Risk Threshold | #,0 | Risk | Score at which a risk is rated High (>=12). Gauge target line. | `12` |
| High Risks | #,0 | Risk | Open risks with score >= 12 on the 5x5 matrix. | `CALCULATE([Risks], 'Risk'[Risk Score] >= 12, 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| Mitigation Coverage % | 0.0%;-0.0%;0.0% | Risk | Share of open risks that have at least one response action planned. | `DIVIDE(COUNTROWS(FILTER(CALCULATETABLE('Risk', 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"}), CALCULATE(COUNTROWS('Risk Response')) > 0)), [Open Risks])` |
| Open Response Actions | #,0 | Risk | Risk response actions not yet done. | `CALCULATE(COUNTROWS('Risk Response'), NOT 'Risk Response'[Action Status] IN {"Done"})` |
| Open Risk Actions | #,0 | Risk | Response actions not yet Done. | `CALCULATE([Risk Actions], 'Risk Response'[Action Status] <> "Done")` |
| Open Risks | #,0 | Risk | Risks not yet closed or realized. | `CALCULATE([Risks], 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| Overdue Risk Actions | #,0 | Risk | Open response actions past their due date. | `COUNTROWS(FILTER('Risk Response', NOT ISBLANK('Risk Response'[Action Due Date]) && 'Risk Response'[Action Due Date] < TODAY() && 'Risk Response'[Action Status] <> "Done"))` |
| Realized Risks | #,0 | Risk | Risks that materialized. | `CALCULATE([Risks], 'Risk'[Risk Status] = "Realized")` |
| Residual Exposure | #,0 | Risk | Sum of residual scores across open risks (post-mitigation). | `CALCULATE(SUM('Risk'[Residual Score]), 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| Response Actions | #,0 | Risk | Risk response actions in context. | `COUNTROWS('Risk Response')` |
| Risk Actions | #,0 | Risk | Per-risk response actions (Mitigation / Transfer / Acceptance / Avoidance). | `COUNTROWS('Risk Response')` |
| Risk Index | 0.0%;-0.0%;0.0% | Risk | Severity index: average open-risk score normalized to the 5x5 maximum (25). | `DIVIDE([Avg Risk Score (Open)], 25)` |
| Risk Rating |  | Risk | Banded rating of the average open-risk score: <6 LOW, <12 MODERATE, <20 HIGH, else CRITICAL. | `SWITCH(TRUE(), ISBLANK([Avg Risk Score (Open)]), "-", [Avg Risk Score (Open)] < 6, "LOW", [Avg Risk Score (Open)] < 12, "MODERATE", [Avg Risk Score (Open)] < 20, "HIGH", "CRITICAL")` |
| Risk Rating Color |  | Risk | Deck-aligned color for the Risk Rating band (conditional formatting). | `SWITCH([Risk Rating], "LOW", "#107C10", "MODERATE", "#C19C00", "HIGH", "#C0392B", "CRITICAL", "#8B1A1A", "#605E5C")` |
| Risk Reduction Pct | 0.0%;-0.0%;0.0% | Risk | Exposure reduction achieved by planned mitigations. | `1 - DIVIDE([Residual Exposure], [Total Risk Exposure])` |
| Risk Scale Max | #,0 | Risk | Maximum of the 5x5 risk matrix. Gauge maximum. | `25` |
| Risks | #,0 | Risk | Count of risks. | `COUNTROWS('Risk')` |
| Risks Past Due | #,0 | Risk | Open risks whose mitigation due date has passed. | `COUNTROWS(FILTER('Risk', NOT ISBLANK('Risk'[Due Date]) && 'Risk'[Due Date] < TODAY() && 'Risk'[Risk Status] IN {"Open", "Mitigating"}))` |
| Total Risk Exposure | #,0 | Risk | Sum of L x I scores across open risks. | `CALCULATE(SUM('Risk'[Risk Score]), 'Risk'[Risk Status] IN {"Open", "Mitigating", "Monitoring"})` |
| Activities | #,0 | Schedule | Count of schedule activities. | `COUNTROWS('Schedule Activity')` |
| Activities At Risk | #,0 | Schedule | Activities flagged at risk. | `CALCULATE([Activities], 'Schedule Activity'[Activity Status] = "At risk")` |
| Activities Done | #,0 | Schedule | Activities completed. | `CALCULATE([Activities], 'Schedule Activity'[Activity Status] = "Done")` |
| Activities In Progress | #,0 | Schedule | Activities currently in progress. | `CALCULATE([Activities], 'Schedule Activity'[Activity Status] = "In progress")` |
| Activities Overdue | #,0 | Schedule | Open activities past their planned finish date. | `COUNTROWS(FILTER('Schedule Activity', 'Schedule Activity'[Planned Finish] < TODAY() && NOT 'Schedule Activity'[Activity Status] IN {"Done", "Cancelled"}))` |
| Avg Duration Days | #,0.0 | Schedule | Average planned working-day duration. | `AVERAGE('Schedule Activity'[Duration Days])` |
| On-Time Completion Pct | 0.0%;-0.0%;0.0% | Schedule | Done activities that finished on or before planned finish. | `DIVIDE(COUNTROWS(FILTER('Schedule Activity', 'Schedule Activity'[Activity Status] = "Done" && NOT ISBLANK('Schedule Activity'[Actual Finish]) && 'Schedule Activity'[Actual Finish] <= 'Schedule Activity'[Planned Finish])), [Activities Done])` |
| Overdue Pct | 0.0%;-0.0%;0.0% | Schedule | Share of activities overdue. | `DIVIDE([Activities Overdue], [Activities])` |
| Pct Complete (Duration Weighted) | 0.0%;-0.0%;0.0% | Schedule | Percent complete weighted by activity duration. | `DIVIDE(SUMX('Schedule Activity', 'Schedule Activity'[Duration Days] * 'Schedule Activity'[Pct Complete]), SUMX('Schedule Activity', 'Schedule Activity'[Duration Days]) * 100)` |
| Accountable Count | #,0 | Stakeholders | RACI = Accountable. | `CALCULATE([Stakeholders], 'Stakeholder'[Engagement] = "A")` |
| High Influence Stakeholders | #,0 | Stakeholders | Influence = High. | `CALCULATE([Stakeholders], 'Stakeholder'[Influence] = "High")` |
| Key Players | #,0 | Stakeholders | High interest and high influence (manage closely). | `CALCULATE([Stakeholders], 'Stakeholder'[Influence] = "High", 'Stakeholder'[Interest] = "High")` |
| Responsible Count | #,0 | Stakeholders | RACI = Responsible. | `CALCULATE([Stakeholders], 'Stakeholder'[Engagement] = "R")` |
| Stakeholders | #,0 | Stakeholders | Stakeholder register entries. | `COUNTROWS('Stakeholder')` |
| Area Status Color |  | Status Page | Deck-exact font color for the Health Check status column (conditional formatting). | `SWITCH([Latest Area Status], "Green", "#107C10", "Yellow", "#C19C00", "Red", "#C0392B", "#252423")` |
| Business Value (Selected) |  | Status Page | Business value text block (charter business case). | `SELECTEDVALUE('Project'[Business Value], "Select a single project")` |
| Current Phase |  | Status Page | Current PMI process group of the selected project. | `SELECTEDVALUE('Project'[Lifecycle Phase], "Multiple")` |
| Decisions Needed (Latest) |  | Status Page | Open decisions called out in the latest status report. | `VAR d0 = MAX('Status Report'[Period End]) RETURN CALCULATE(MAX('Status Report'[Decisions Needed]), 'Status Report'[Period End] = d0)` |
| Latest Area Status |  | Status Page | Health-check status of a knowledge area from the most recent report. | `VAR d0 = MAX('Status Report'[Period End]) RETURN CALCULATE(MAX('Status Report Area'[Area Status]), 'Status Report'[Period End] = d0)` |
| Main Status |  | Status Page | Traffic-light letter from the latest status report: G / Y / R. | `SWITCH([Latest Overall Status], "Green", "G", "Yellow", "Y", "Red", "R", BLANK())` |
| Phase Key |  | Status Page | Legend for PMI lifecycle phases used on this report. | `"PHASES:   Initiating - Planning - Executing - Monitoring - Closing"` |
| Project Description (Selected) |  | Status Page | Project description text block. | `SELECTEDVALUE('Project'[Project Description], "Select a single project")` |
| Project Manager (Selected) |  | Status Page | Selected project's PM for the status report header. | `SELECTEDVALUE('Project'[Project Manager], "-")` |
| Report Date |  | Status Page | Date of the latest status report. | `VAR d = MAX('Status Report'[Period End]) RETURN IF(ISBLANK(d), "-", FORMAT(d, "M/D/YYYY"))` |
| Status Color |  | Status Page | Hex color for the Main Status traffic light. Values match the Theragen status deck exactly (G #107C10 / Y #C19C00 / R #C0392B). | `SWITCH([Latest Overall Status], "Green", "#107C10", "Yellow", "#C19C00", "Red", "#C0392B", "#605E5C")` |
| Status Key |  | Status Page | Legend for status letters (matches the Theragen status report key). | `"KEY:   G = Green   \|   Y = Yellow   \|   R = Off Track   \|   C = Completed   \|   NS = Not Started   \|   H = Hold   \|   CN = Cancelled"` |
| Target Date Completion |  | Status Page | Planned finish of the selected project; TBD when not set. | `VAR d = MAX('Project'[Planned Finish]) RETURN IF(ISBLANK(d), "TBD", FORMAT(d, "M/D/YYYY"))` |
| Theragen Project Name |  | Status Page | Selected project name for the status report header. | `SELECTEDVALUE('Project'[Project Name], "All projects - select one")` |
| Workstream Start | yyyy-mm-dd | Status Page | Earliest planned start of activities in context (workstream start date). | `MIN('Schedule Activity'[Planned Start])` |
| Workstream Status |  | Status Page | Roll-up status per workstream: COMPLETED / AT RISK / NOT STARTED / ON TRACK. | `VAR tot = [Activities] VAR done = [Activities Done] VAR atRisk = [Activities At Risk] + [Activities Overdue] VAR started = [Activities In Progress] + done RETURN SWITCH(TRUE(), ISBLANK(tot) \|\| tot = 0, "-", done = tot, "COMPLETED", atRisk > 0, "AT RISK", started = 0, "NOT STARTED", "ON TRACK")` |
| Workstream Status Color |  | Status Page | Deck-exact font color for the Key Project Areas status column (conditional formatting). | `SWITCH([Workstream Status], "ON TRACK", "#107C10", "AT RISK", "#C19C00", "#252423")` |
| Workstream Target | yyyy-mm-dd | Status Page | Latest planned finish of activities in context (target implementation date). | `MAX('Schedule Activity'[Planned Finish])` |
| Avg Allocation Pct | 0.0%;-0.0%;0.0% | Team | Mean allocation per assignment. | `AVERAGE('Team Member'[Allocation Pct]) / 100` |
| Team Members | #,0 | Team | Team assignments. | `COUNTROWS('Team Member')` |
| Total FTE | #,0.0 | Team | Sum of allocation percentages as full-time equivalents. | `SUM('Team Member'[Allocation Pct]) / 100` |

<a id="budget-line"></a>
## Budget Line

Fact - cost budget estimate lines (PMBOK P13), one per level-1 deliverable.

**Source:** `bi.budget_line_item`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Budget Line ID | string | yes |  | (hidden) Surrogate key for the budget line; joins to bi.budget_line_item. |
| WBS ID | string | yes |  | (hidden) Surrogate key of the level-1 WBS deliverable this budget line estimates. |
| Project ID | string | yes |  | (hidden) Surrogate key of the owning project; joins to the Project dimension. |
| Project Code | string |  |  | Human-readable project code this budget line belongs to. |
| Cost Category | string |  |  | Cost classification of this budget line: Labor, Materials, Services, or Other. |
| Labor Amount | double |  | \$#,##0;(\$#,##0);\$0 | Labor (staff effort) component of this budget line, in USD. |
| Materials Amount | double |  | \$#,##0;(\$#,##0);\$0 | Materials (supplies, consumables) component of this budget line, in USD. |
| Vendor Amount | double |  | \$#,##0;(\$#,##0);\$0 | Vendor / contractor component of this budget line, in USD. |
| Other Amount | double |  | \$#,##0;(\$#,##0);\$0 | Other-cost component of this budget line not covered by labor, materials, or vendor, in USD. |
| Subtotal | double |  | \$#,##0;(\$#,##0);\$0 | Budget line total before contingency (sum of labor, materials, vendor, and other), in USD. |
| Contingency Pct | double |  | #,0.0 | Contingency reserve applied to the subtotal, as a percentage. |
| Total | double |  | \$#,##0;(\$#,##0);\$0 | Funded budget line including contingency (subtotal plus contingency), in USD. |
| Funding Source | string |  |  | Funding source bankrolling this budget line (e.g. grant, internal, capital). |

<a id="change-impact-assessment"></a>
## Change Impact Assessment

Fact - per-department change-impact assessments (PMBOK P22). One row per department's impact statement on a change request.

**Source:** `bi.change_impact_assessment`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Impact ID | string | yes |  | (hidden) Surrogate key of this per-department impact assessment. |
| CR ID | string | yes |  | (hidden) Surrogate key of the assessed change request; joins to Change Request. |
| CR Code | string |  |  | Human-readable code of the change request being assessed (e.g. C-001). |
| Project Code | string |  |  | Human-readable project code the assessed change request belongs to (e.g. PRJ-001). |
| Department | string |  |  | Theragen department filing this impact statement on the change request. |
| Scope Impact | string |  |  | This department's narrative of how the change affects its scope of work. |
| Schedule Impact Days | int64 |  | #,0 | This department's estimated schedule impact of the change, in days (positive = delay). |
| Cost Impact | double |  | \$#,##0;(\$#,##0);\$0 | This department's estimated cost impact of the change (positive = added cost). |
| Quality Impact | string |  |  | This department's narrative of how the change affects deliverable quality. |
| Submitted By | string |  |  | Display name of the person who submitted this department's assessment. |
| Submitted Date | dateTime |  | yyyy-mm-dd | Date this department submitted its impact assessment. |

<a id="change-request"></a>
## Change Request

Fact - project change requests (PMBOK P21) with impact and decision cycle.

**Source:** `bi.change_request`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| CR ID | string | yes |  | (hidden) Surrogate key of the change request; joins to its impact assessments. |
| Project ID | string | yes |  | (hidden) Surrogate key of the owning project; joins to the Project dimension. |
| Project Code | string |  |  | Human-readable project code the change request belongs to (e.g. PRJ-001). |
| CR Code | string |  |  | Human-readable change-request code, minted per project (e.g. C-001). |
| Intake ID | string |  |  | Source SharePoint List item id for this change request (sync idempotency anchor). |
| Requested Date | dateTime |  | yyyy-mm-dd | Date the change request was raised; start of the CR cycle time. |
| Requested By ID | string | yes |  | (hidden) Surrogate key of the requester; joins to the Person directory. |
| Requested By | string |  |  | Display name of the person who raised the change request. |
| CR Class | string |  |  | Change severity class: A - Minor, B - Substantive, C - Controlling, or Emergency / Safety. |
| Change Type | string |  |  | Nature of the change requested (scope, schedule, cost, quality, or a combination). |
| CR Description | string |  |  | Free-text description of what the change request proposes to change. |
| Reason | string |  |  | Business justification for why the change is being requested. |
| Schedule Impact Days | int64 |  | #,0 | Estimated net schedule impact of the change, in days (positive = delay). |
| Cost Impact | double |  | \$#,##0;(\$#,##0);\$0 | Estimated net cost impact of the change (positive = added cost). |
| Decision | string |  |  | Gate verdict on the change request: Pending, Approved, Deferred, or Rejected. |
| Decided Date | dateTime |  | yyyy-mm-dd | Date the gate decision was made; end of the CR cycle time. |
| Cycle Time Days | int64 |  | #,0 | Days from request to decision; basis for the Avg CR Cycle Days measure. |
| CR Status | string |  |  | Workflow state: Open, In Assessment, Implementing, Verified, Closed, or Rejected. |
| Decided By | string |  |  | Display name of the person who decided the change request. |
| Impact Scope | string |  |  | Narrative of how the change affects project scope. |
| Impact Quality | string |  |  | Narrative of how the change affects deliverable quality. |
| Affected Artifacts | string |  |  | Project artifacts (plans, baselines, documents) the change touches. |
| Implementation Verified | boolean |  |  | TRUE when an approved change's implementation has been confirmed in the artifact library. |
| Linked Artifacts Updated | boolean |  |  | TRUE when the artifacts affected by the change have been updated to reflect it. |

<a id="closure-item"></a>
## Closure Item

Fact - project closure checklist items (PMBOK P26).

**Source:** `bi.closure_checklist_item`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Closure Item ID | string | yes |  | (hidden) Surrogate key of the closure-checklist row; joins to the closure source. |
| Project ID | string | yes |  | (hidden) Surrogate key of the owning project; joins to the Project dimension. |
| Project Code | string |  |  | Human-readable project code the closure item belongs to. |
| Closure Item | string |  |  | Text of the project-closeout checklist entry to be completed. |
| Owner Role | string |  |  | Role accountable for completing the checklist item. |
| Done | boolean |  |  | TRUE when the checklist item has been completed. |
| Evidence | string |  |  | Reference or note evidencing that the item was completed. |

<a id="controlled-document"></a>
## Controlled Document

Fact - controlled-document register (doc_mgmt spine). One row per controlled document, org-wide.

**Source:** `bi.document`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Document ID | string | yes |  | (hidden) Surrogate key of the controlled document; joins RACI, version and approval facts back to this register. |
| Doc ID | string |  |  | Human-readable document id, THG-{DEPT}-{TYPE}-NNN (e.g. THG-OPS-CHR-001); globally unique. |
| Document Type | string |  |  | Document-type code embedded in the Doc ID: CHR/SOP/PLN/SCP/RPT/POL/WI/FRM. |
| Department | string |  |  | Owning department, one of the 8 Theragen departments (Clinical/Regulatory/R&D/Operations/Finance/Commercial/IT/HR). |
| Title | string |  |  | Official title of the controlled document. |
| Subtitle | string |  |  | Optional secondary title or descriptive subline for the document. |
| Lifecycle Phase | string |  |  | Lifecycle phase the document sits in (authoring/review/effective stage of its governed life). |
| Status | string |  |  | Document lifecycle status: DRAFT / REVIEW / BASELINE / AMENDED / RETIRED. |
| Current Version | string |  |  | Version string of the document's currently effective revision. |
| Owner | string |  |  | Display name of the document owner accountable for keeping it current. |
| Approver | string |  |  | Display name of the approver authorized to sign off the document. |
| Review Cycle | string |  |  | Recurring review cadence for the document (how often it must be re-reviewed). |
| Next Review Due | dateTime |  | yyyy-mm-dd | Date the document's next periodic review falls due per its review cycle. |
| Classification | string |  |  | Information classification / sensitivity label governing how the document may be handled. |
| Storage System | string |  |  | Repository system where the document file is stored (e.g. SharePoint). |
| Storage Path | string |  |  | Location of the document file within its storage system. |
| Created Date | dateTime |  | yyyy-mm-dd | Date the controlled document was first created in the register. |

<a id="cost-actual"></a>
## Cost Actual

Fact - per-work-package, per-period actual cost (EVM AC). One row per logged cost actual against a WBS work package.

**Source:** `bi.cost_actual`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Cost Actual ID | string | yes |  | (hidden) Surrogate key for the cost actual; joins to bi.cost_actual. |
| WBS ID | string | yes |  | (hidden) Surrogate key of the WBS work package this cost was charged against. |
| Project Code | string |  |  | Human-readable project code this cost actual belongs to. |
| WBS Code | string |  |  | Human-readable WBS code of the work package this cost was charged against. |
| Work Package | string |  |  | Name of the level-2 WBS work package the actual cost was incurred on. |
| Period | dateTime |  | yyyy-mm-dd | Accounting period (month) the actual cost was booked to. |
| Amount | double |  | \$#,##0.00;(\$#,##0.00);\$0 | Money actually spent in this entry, in USD; summed gives EVM actual cost (AC). |
| Category | string |  |  | Cost classification of the spend: Labor, Materials, Services, or Other. |
| Entered By | string |  |  | Display name of the person who logged this cost actual. |
| Notes | string |  |  | Free-text note explaining or itemizing the logged cost. |

<a id="date"></a>
## Date

Marked date dimension covering 2025-2027.

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Date | dateTime |  | yyyy-mm-dd | The calendar day; the key of the marked date dimension that every date relationship joins to. |
| Year = YEAR('Date'[Date]) | int64 |  | #,0 | Calendar year of the date, for year-level grouping and filtering. |
| Quarter = "Q" & QUARTER('Date'[Date]) | string |  |  | Calendar quarter label (Q1-Q4) of the date, for quarter-level grouping. |
| 'Month Number' = MONTH('Date'[Date]) | int64 | yes |  | (hidden) Month number 1-12; the sort key that orders the Month name column chronologically. |
| Month = FORMAT('Date'[Date], "MMM") | string |  |  | Three-letter month abbreviation (Jan-Dec), sorted by Month Number. |
| 'Year Month' = FORMAT('Date'[Date], "YYYY-MM") | string |  |  | Year-month key in YYYY-MM form, for chronological month-over-month trending across years. |
| 'Week Of' = 'Date'[Date] - WEEKDAY('Date'[Date], 2) + 1 | dateTime |  | yyyy-mm-dd | Monday-start date of the week the date falls in; for weekly bucketing of activity and milestones. |

<a id="decision"></a>
## Decision

Fact - governance decisions (PMBOK P21). Formal decisions logged against a project.

**Source:** `bi.decision`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Decision ID | string | yes |  | (hidden) Surrogate key of the logged governance decision. |
| Project ID | string | yes |  | (hidden) Surrogate key of the owning project; joins to the Project dimension. |
| Project Code | string |  |  | Human-readable project code the decision was logged against (e.g. PRJ-001). |
| Decision | string |  |  | Statement of the governance decision made (the resolution reached). |
| Rationale | string |  |  | Reasoning recorded for why the decision was made. |
| Decided By | string |  |  | Display name of the person who made the decision. |
| Decided Date | dateTime |  | yyyy-mm-dd | Date the governance decision was made and logged. |

<a id="department"></a>
## Department

Conformed department dimension (DM D01). Filters executing departments on facts.

**Source:** `bi.department`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Department ID | string | yes |  | (hidden) Surrogate key uniquely identifying the department; the relationship anchor for department joins on facts. |
| Department Code | string |  |  | Short department code used in minted Doc IDs (e.g. OPS, REG, IT); the human-readable department key. |
| Department | string |  |  | Full department name; one of the 8 Theragen departments (e.g. Operations / PMO, Regulatory / Quality). |

<a id="directory"></a>
## Directory

Org directory: Theragen staff from Entra (enabled members on theragen.com / actastim.com) plus the sample seed persons, with the PMO-curated department. Sourced by tools/sync_directory.py; consumes bi.org_directory. Standalone (no relationships) - department slices via the local Department column.

**Source:** `bi.org_directory`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Person ID | string | yes |  | (hidden) Surrogate key of the person row in doc_mgmt.person. |
| Display Name | string |  |  | The person's full display name. |
| Email | string |  |  | The person's sign-in email (matches the Report Access grant email + USERPRINCIPALNAME). |
| UPN | string |  |  | The person's Entra user principal name (UPN). |
| Job Title | string |  |  | The person's Entra job title (blank for many service / unconfigured accounts). |
| Active | boolean |  |  | TRUE when the account is enabled in Entra. |
| Source | string |  |  | Provenance of the row: 'entra' (roster pull) or 'sharepoint' (resolved from a person field). |
| Employment Type | string |  |  | Employment type (defaults to Employee for Entra-sourced rows). |
| Department Code | string |  |  | The department code (CLN/REG/.../UNAS); UNAS = Unassigned. |
| Department | string |  |  | The person's department - the PMO-curated assignment, or "Unassigned". |
| Department Unassigned | boolean |  |  | TRUE when the person has no curated department yet (sentinel UNAS) - awaiting PMO assignment. |
| Has Report Access | boolean |  |  | TRUE when the person holds at least one active Report Access (RLS) grant. |

<a id="document-approval"></a>
## Document Approval

Fact - per-version sign-off ATTESTATION (non-Part-11; see esig_kind).

**Source:** `bi.document_approval`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Approval ID | string | yes |  | (hidden) Surrogate key for this attestation record. |
| Version ID | string | yes |  | (hidden) Surrogate key joining this attestation to the Document Version it signs off. |
| Doc ID | string |  |  | Minted document identifier (THG-{DEPT}-{TYPE}-NNN) of the attested document. |
| Document Title | string |  |  | Human-readable title of the attested document. |
| Version | string |  |  | Version string of the document revision this attestation signs off. |
| Approver | string |  |  | Display name of the person who recorded this attestation (the sign-off, not a Part-11 signer). |
| Signature Meaning | string |  |  | What the sign-off asserts: Approval / Review / Authorship (a meaning, not a Part-11 signature). |
| Signed At | dateTime |  | yyyy-mm-dd hh:nn:ss | Timestamp when the attestation was recorded by the server. |
| Attestation Hash | string |  |  | SHA-256 hash binding the signed facts (who, when, meaning) for tamper-evidence; not a Part-11 signature. |
| Attestation Kind | string |  |  | Always "Attestation (non-Part-11)" - an honest sign-off record, not a 21 CFR Part 11 signature. |
| Reason | string |  |  | Free-text justification the attester gave for the sign-off. |

<a id="document-raci"></a>
## Document RACI

Fact - per-document, per-department R/A/C/I assignment (effective-dated).

**Source:** `bi.raci_assignment`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| RACI ID | string | yes |  | (hidden) Surrogate key of the RACI assignment row; uniquely identifies one document-department-role record. |
| Document ID | string | yes |  | (hidden) Surrogate key joining each RACI assignment to its controlled document. |
| Doc ID | string |  |  | Human-readable document id (THG-{DEPT}-{TYPE}-NNN) of the controlled document this assignment applies to. |
| Document Title | string |  |  | Title of the controlled document this RACI assignment applies to. |
| Department | string |  |  | Department holding this RACI role, one of the 8 Theragen departments (Clinical/Regulatory/R&D/Operations/Finance/Commercial/IT/HR). |
| Role | string |  |  | RACI role code: R / A / C / I (Responsible / Accountable / Consulted / Informed). |
| Role Name | string |  |  | Full role label spelled out from the RACI code (Responsible / Accountable / Consulted / Informed). |
| Touchpoint | string |  |  | Lifecycle touchpoint at which the department's involvement applies (the review/approval stage it engages on). |
| Valid From | dateTime |  | yyyy-mm-dd | Effective-dating start: date this RACI assignment took effect. |
| Valid To | dateTime |  | yyyy-mm-dd | Effective-dating end: date this RACI assignment expired; blank means still in effect. |

<a id="document-version"></a>
## Document Version

Fact - controlled-document version history.

**Source:** `bi.document_version`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Version ID | string | yes |  | (hidden) Surrogate key for this document version; joins to Document Approval attestations. |
| Document ID | string | yes |  | (hidden) Surrogate key of the parent controlled document this version revises. |
| Doc ID | string |  |  | Minted document identifier (THG-{DEPT}-{TYPE}-NNN) of the parent controlled document. |
| Document Title | string |  |  | Human-readable title of the parent controlled document. |
| Version | string |  |  | Version string of this revision (e.g. 1.0, 2.0) within the document's version history. |
| Status | string |  |  | Lifecycle state of this version: DRAFT / REVIEW / BASELINE / AMENDED / RETIRED. |
| Change Summary | string |  |  | Narrative of what changed in this revision relative to the prior version. |
| Change Class | string |  |  | Severity of the revision: A (Minor) / B (Substantive) / C (Controlling) / Emergency. |
| Author | string |  |  | Display name of the person who authored this revision. |
| Effective Date | dateTime |  | yyyy-mm-dd | Date this version takes effect as the governing revision. |
| Storage Path | string |  |  | Location where this version's file is stored. |
| Created Date | dateTime |  | yyyy-mm-dd | Date this version record was created. |
| Linked CR | string |  |  | The governance CR (CHG-NNN) that drove this revision, if any. |

<a id="governance-change-assessment"></a>
## Governance Change Assessment

Fact - per-department impact assessments on a governance change request. One row per department's impact statement on a gov CR.

**Source:** `bi.change_assessment_gov`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Gov Impact ID | string | yes |  | (hidden) Surrogate key for this per-department assessment row. |
| CR Gov ID | string | yes |  | (hidden) Surrogate key of the parent governance CR; joins to 'Governance Change Request'. |
| CR Code | string |  |  | Human-readable code of the governance CR being assessed, CHG-NNN. |
| Doc ID | string |  |  | Minted identifier of the controlled document the parent CR targets, THG-{DEPT}-{TYPE}-NNN. |
| Doc Title | string |  |  | Title of the controlled document the parent CR targets. |
| Department | string |  |  | Theragen department filing this impact statement (one row per assessing department). |
| Impact Summary | string |  |  | The department's narrative of how the change affects it. |
| Compliance Impact | string |  |  | The department's read on the change's regulatory/compliance implications. |
| Submitted Date | dateTime |  | yyyy-mm-dd | Date the department submitted this assessment. |

<a id="governance-change-request"></a>
## Governance Change Request

Fact - governance change requests (CHG-NNN) against controlled documents (SOP-003). Document-scoped, project-less; reuses the two-axis Decision/Status workflow.

**Source:** `bi.change_request_gov`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| CR Gov ID | string | yes |  | (hidden) Surrogate key for the governance change request; joins assessments via change_request_gov.cr_gov_id. |
| Document ID | string | yes |  | (hidden) Surrogate key of the controlled document this CR targets; joins to 'Controlled Document'. |
| CR Code | string |  |  | Human-readable governance change-request code, CHG-NNN (e.g. CHG-001); globally unique, project-less. |
| Doc ID | string |  |  | Minted identifier of the targeted controlled document, THG-{DEPT}-{TYPE}-NNN. |
| Doc Title | string |  |  | Title of the controlled document the change request targets. |
| Requested Date | dateTime |  | yyyy-mm-dd | Date the governance change request was raised. |
| Requested By | string |  |  | Display name of the person who raised the change request. |
| CR Class | string |  |  | Severity/control level of the change: A - Minor, B - Substantive, C - Controlling, or Emergency / Safety. |
| Description | string |  |  | Narrative of the proposed change to the controlled document. |
| Reason | string |  |  | Justification for why the change is needed. |
| Decision | string |  |  | Gate verdict (first workflow axis): Pending, Approved, Deferred, or Rejected. |
| Decided By | string |  |  | Display name of the person who recorded the decision. |
| Decided Date | dateTime |  | yyyy-mm-dd | Date the decision was recorded. |
| Implementation Verified | boolean |  |  | TRUE when an approved change's implementation has been confirmed in the artifact library. |
| Status | string |  |  | Workflow state (second axis): Open, In Assessment, Implementing, Verified, Closed, or Rejected. |
| Intake ID | string |  |  | SharePoint List item id of the source intake row, giving the CR a stable identity for idempotent re-syncs. |

<a id="knowledge-area"></a>
## Knowledge Area

PMBOK knowledge areas (enum knowledge_area) used by status report health entries.

**Source:** `bi.knowledge_area`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Knowledge Area | string |  |  | PMI knowledge area (e.g. Scope, Schedule, Cost, Quality, Risk) used to structure status-report health entries. |
| KA Sort | int64 | yes |  | (hidden) Sort order that lays out knowledge areas in canonical PMI sequence rather than alphabetically. |

<a id="lesson-learned"></a>
## Lesson Learned

Fact - lessons learned (PMBOK P25).

**Source:** `bi.lesson_learned`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Lesson ID | string | yes |  | (hidden) Surrogate key of the lessons-learned row; joins to the lesson source. |
| Project ID | string | yes |  | (hidden) Surrogate key of the owning project; joins to the Project dimension. |
| Project Code | string |  |  | Human-readable project code the lesson belongs to. |
| Lesson Category | string |  |  | Theme classifying the lesson (e.g. schedule, cost, quality, process). |
| Lesson | string |  |  | Short title of the retrospective insight captured. |
| What Happened | string |  |  | Narrative of the situation or event that prompted the lesson. |
| Recommendation | string |  |  | Recommended action or practice change to carry forward. |
| Follow-up Owner | string |  |  | Role accountable for acting on the recommendation. |
| Lesson Status | string |  |  | Adoption state of the lesson: Open (awaiting action) or Adopted (folded into practice). |

<a id="milestone"></a>
## Milestone

Fact - milestones (PMBOK P11). Baseline vs forecast vs actual dates.

**Source:** `bi.milestone`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Milestone ID | string | yes |  | (hidden) Surrogate key for the milestone row. |
| Project ID | string | yes |  | (hidden) Foreign key to the owning project; joins to 'Project'[Project ID]. |
| Project Code | string |  |  | Human-readable project code this milestone belongs to (e.g. PRJ-001). |
| Milestone | string |  |  | Name of the schedule checkpoint (the milestone's title). |
| Baseline Date | dateTime |  | yyyy-mm-dd | Frozen baseline target date; the yardstick slip days are measured against. |
| Forecast Date | dateTime |  | yyyy-mm-dd | Current expected landing date while the milestone is still open. |
| Actual Date | dateTime |  | yyyy-mm-dd | Date the milestone was actually achieved; blank until reached. |
| Milestone Status | string |  |  | Landing state of the milestone: Achieved / At risk / Slipped. |
| Owner Role | string |  |  | Role title accountable for delivering the milestone (e.g. Project Manager). |
| 'Slip Days' = DATEDIFF('Milestone'[Baseline Date], COALESCE('Milestone'[Actual Date], 'Milestone'[Forecast Date], 'Milestone'[Baseline Date]), DAY) | int64 |  |  | Days between baseline and actual (or forecast) date. Positive = slip. |

<a id="person"></a>
## Person

Person directory (DM D02). Owners, requesters and assignees on facts.

**Source:** `bi.person`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Person ID | string | yes |  | (hidden) Surrogate key uniquely identifying the person; the relationship anchor for owner/requester/assignee joins on facts. |
| Person | string |  |  | Display name of the person; the label shown for owners, requesters and assignees across facts. |
| Email | string |  |  | Person's email address (work UPN); the identity used to match RLS report-access grants. |
| Person Department | string |  |  | The Theragen department the person belongs to (one of the 8 departments). |
| Role Title | string |  |  | The person's job title or role within the organization. |
| Employee Number | string |  |  | HR employee identifier for the person; the directory's stable payroll key. |

<a id="phase-gate-log"></a>
## Phase Gate Log

Fact - append-only record of lifecycle-phase handoffs (PMBOK). Captures who approved each phase transition, when, and the gate decision.

**Source:** `bi.phase_gate_log`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Phase Gate ID | string | yes |  | (hidden) Surrogate primary key for the phase-gate event row. |
| Project ID | string | yes |  | (hidden) Surrogate key of the project this gate belongs to; joins to 'Project'. |
| Project Code | string |  |  | Human-readable project code the gate belongs to. |
| From Phase | string |  |  | Lifecycle phase the project was leaving at the gate (forward-only; backward transitions are rejected). |
| To Phase | string |  |  | Lifecycle phase the project advanced to (equals From Phase when the gate is Held). |
| Gate Decision | string |  |  | Gate verdict: Approved, Approved with conditions, or Held (keeps the project in its current phase). |
| Decided Date | dateTime |  | yyyy-mm-dd | Date the gate decision was made. |
| Gate Notes | string |  |  | Free-text rationale or conditions recorded for the gate decision. |
| Approved By | string |  |  | Display name of the person who approved the phase transition. |

<a id="platform-change"></a>
## Platform Change

Fact - platform change register (Round 2 dogfood). One row per logged change to the BI platform itself, in a change-control-process.md category.

**Source:** `bi.platform_change`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Change ID | string | yes |  | (hidden) Surrogate key of the logged platform change. |
| Category | string |  |  | Change-control category: Lists & schema / Sync + automation code / Semantic model / DB migration / Security & RLS / Documentation. |
| Summary | string |  |  | One-line description of what the change did. |
| Version | string |  |  | Platform version this change targets (e.g. 2.7). |
| Status | string |  |  | Workflow state of the change: Proposed / Approved / Deployed. |
| Requested By | string |  |  | Display name of the person who requested / authored the change. |
| Approved By | string |  |  | Display name of the person who approved the change. |
| Git SHA | string |  |  | The git commit hash that implements the change. |
| Changed Date | dateTime |  | yyyy-mm-dd | Date the change was logged. |

<a id="project"></a>
## Project

Project dimension - one row per project (PMBOK P01 project, charter fields denormalized).

**Source:** `bi.project`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Project ID | string | yes |  | (hidden) Surrogate key uniquely identifying the project; the relationship anchor every fact joins to. |
| Project Code | string |  |  | Human-readable project code (e.g. THG-IT-005); the business key shown across reports. |
| Intake ID | string |  |  | SharePoint intake-form item id the project was created from; ties the project back to its request of record. |
| Project Name | string |  |  | Full project title as chartered; the primary label for the project in reports. |
| Project Description | string |  |  | Narrative charter description of what the project delivers and its scope. |
| Business Value | string |  |  | Charter business-case statement of the value or benefit the project is expected to deliver. |
| Sponsor | string |  |  | Display name of the executive sponsor accountable for funding and championing the project. |
| Project Manager | string |  |  | Display name of the project manager responsible for day-to-day delivery. |
| Primary Department | string |  |  | The lead Theragen department that owns the project (one of the 8 departments). |
| Approach | string |  |  | Delivery approach the project follows (e.g. Predictive / Agile / Hybrid). |
| Lifecycle Phase | string |  |  | Current PMI process group: Initiating, Planning, Executing, Monitoring & Controlling, or Closing; advanced only via a phase gate. |
| Project Status | string |  |  | Lifecycle state of the project (e.g. Proposed, Active, Completed); drives [Active Projects] and [Proposed Projects]. |
| Planned Start | dateTime |  | yyyy-mm-dd | Charter-planned project start date. |
| Planned Finish | dateTime |  | yyyy-mm-dd | Charter-planned project finish date; the target completion surfaced by [Target Date Completion]. |
| Actual Start | dateTime |  | yyyy-mm-dd | Date the project actually started; blank until work begins. |
| Actual Finish | dateTime |  | yyyy-mm-dd | Date the project actually completed; blank until closed. |
| Charter Budget | double |  | \$#,##0;(\$#,##0);\$0 | Charter-approved total budget for the project; basis of [Portfolio Charter Budget] and baseline variance. |
| Strategic Objective | string |  |  | Reference to the strategic objective or portfolio goal this project advances. |

<a id="project-baseline"></a>
## Project Baseline

Fact - immutable schedule/scope/budget baselines (PMBOK). Each new baseline mints the next version; prior BASELINED rows go SUPERSEDED.

**Source:** `bi.project_baseline`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Baseline ID | string | yes |  | (hidden) Surrogate key for the baseline snapshot; joins to bi.project_baseline. |
| Project ID | string | yes |  | (hidden) Surrogate key of the baselined project; joins to the Project dimension. |
| Project Code | string |  |  | Human-readable project code this baseline was captured for. |
| Baseline Type | string |  |  | Which plan this baseline froze: Schedule, Budget, or Scope. |
| Version | string |  |  | Baseline version vM.0 (1.0, 2.0, ...); each re-baseline mints the next. |
| Status | string |  |  | Baseline lifecycle state: BASELINED (active yardstick) or SUPERSEDED (replaced). |
| Change Summary | string |  |  | Note on why this baseline was taken (the re-baselining rationale). |
| Baselined Date | dateTime |  | yyyy-mm-dd | Date this baseline snapshot was frozen. |
| Baselined By | string |  |  | Display name of the person who took this baseline. |
| Baseline Budget Total | double |  | \$#,##0;(\$#,##0);\$0 | Frozen budget_total captured in this baseline's snapshot, in USD; the EVM cost yardstick. |
| Baseline Activity Count | int64 |  | #,0 | Number of schedule activities frozen in this baseline's snapshot. |

<a id="recent-accomplishment"></a>
## Recent Accomplishment

Leadership view - work completed in the last 35 days (done activities + achieved milestones).

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Project ID | string | yes |  | (hidden) Surrogate key of the owning project; joins to the Project dimension. |
| Accomplishment | string |  |  | Name of the completed activity or achieved milestone reported as an accomplishment. |
| Completed Date | dateTime |  | yyyy-mm-dd | Date the activity finished or the milestone was achieved. |
| Source | string |  |  | Origin of the accomplishment row: Activity or Milestone. |

<a id="report-access"></a>
## Report Access

Security - data-driven RLS grants. Disconnected (no relationships): the "Scoped Viewer" role reads it via USERPRINCIPALNAME() to filter Project. Hidden so the access map never appears in the field list.

**Source:** `bi.report_access`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Access ID | string | yes |  | (hidden) Surrogate key of the RLS grant row; joins to the access-grant source. |
| User Email | string |  |  | Sign-in email of the grantee whose report access this grant authorizes (matched against USERPRINCIPALNAME). |
| Scope Type | string |  |  | Breadth of the grant: Project, Department, or All. |
| Scope Value | string |  |  | The specific project code or department the grant applies to (blank for an All-scope grant). |
| Active | boolean |  |  | TRUE when the grant is currently in force; revoked grants are FALSE and grant no access. |
| Granted By | string |  |  | Display name of the PMO administrator who authored the grant. |
| Granted Date | dateTime |  | yyyy-mm-dd | Date the access grant was authored. |

<a id="risk"></a>
## Risk

Fact - risk register (PMBOK P14). 5x5 likelihood x impact scoring.

**Source:** `bi.risk`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Risk ID | string | yes |  | (hidden) Surrogate key for the risk register row; joins risk responses back to their parent risk. |
| Project ID | string | yes |  | (hidden) Surrogate key of the owning project; joins the risk to the Project dimension. |
| Project Code | string |  |  | Human-readable project code the risk belongs to (e.g. PRJ-001). |
| Risk Code | string |  |  | Human-readable risk code (e.g. R-001); the per-project identifier shown on the risk register. |
| Risk Category | string |  |  | Classification of the risk by type (e.g. technical, schedule, regulatory, financial). |
| Risk Description | string |  |  | Free-text statement of the uncertain event and its potential effect on the project. |
| Likelihood | int64 |  | #,0 | Probability score (1-5) that the risk occurs; one axis of the 5x5 matrix. |
| Impact | int64 |  | #,0 | Severity score (1-5) of the risk if it occurs; the other axis of the 5x5 matrix. |
| Risk Score | int64 |  | #,0 | Likelihood x Impact on the 5x5 matrix (1-25); the headline severity score (High >=12, Critical >=20). |
| Response Type | string |  |  | Planned response strategy for the risk: Mitigation, Transfer, Acceptance, or Avoidance. |
| Owner ID | string | yes |  | (hidden) Surrogate key of the risk owner; joins to the Person directory. |
| Owner | string |  |  | Display name of the person accountable for managing the risk. |
| Department | string |  |  | Theragen department that owns or is most exposed to the risk. |
| Due Date | dateTime |  | yyyy-mm-dd | Target date by which the planned mitigation should be completed. |
| Risk Status | string |  |  | Lifecycle state of the risk: Open, Mitigating, Monitoring, Realized, or Closed. |
| Residual Score | int64 |  | #,0 | Risk score expected to remain after planned mitigation; drives residual exposure. |
| Compliance Frame | string |  |  | Regulatory or compliance framework the risk maps to (e.g. 21 CFR Part 11, ISO, GxP). |
| Severity = SWITCH(TRUE(), 'Risk'[Risk Score] >= 20, "Critical", 'Risk'[Risk Score] >= 12, "High", 'Risk'[Risk Score] >= 6, "Medium", "Low") | string |  |  | Banding of Risk Score on the 5x5 matrix: >=20 Critical, >=12 High, >=6 Medium. |
| 'RAID Type' = IF('Risk'[Risk Status] = "Realized", "Issue", "Risk") | string |  |  | RAID classification: a realized risk is reported as an Issue. |

<a id="risk-response"></a>
## Risk Response

Fact - risk response actions (PMBOK P15).

**Source:** `bi.risk_response`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Response ID | string | yes |  | (hidden) Surrogate key for the risk response action row. |
| Risk ID | string | yes |  | (hidden) Surrogate key of the parent risk; joins the action back to the Risk register. |
| Project Code | string |  |  | Human-readable project code the response action belongs to (e.g. PRJ-001). |
| Risk Code | string |  |  | Human-readable code of the risk this action addresses (e.g. R-001). |
| Action Type | string |  |  | Response strategy of the action: Mitigation, Transfer, Acceptance, or Avoidance. |
| Action Description | string |  |  | Free-text statement of the response action to be taken against the risk. |
| Action Owner | string |  |  | Display name of the person responsible for carrying out the response action. |
| Action Due Date | dateTime |  | yyyy-mm-dd | Target date by which the response action should be completed; drives overdue-action flags. |
| Action Status | string |  |  | Progress state of the response action: Open, In progress, Blocked, or Done. |

<a id="schedule-activity"></a>
## Schedule Activity

Fact - schedule activities (PMBOK P10). One row per activity with planned/actual dates and percent complete.

**Source:** `bi.schedule_activity`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Activity ID | string | yes |  | (hidden) Surrogate key for the activity; joins to fact and leadership-view tables. |
| WBS ID | string | yes |  | (hidden) Foreign key to the parent work package; joins to 'WBS Element'[WBS ID]. |
| Project ID | string | yes |  | (hidden) Foreign key to the owning project; joins to 'Project'[Project ID]. |
| Project Code | string |  |  | Human-readable project code this activity belongs to (e.g. PRJ-001). |
| Activity Code | string |  |  | Human-readable activity code minted under its work package (e.g. 1.1-A1). |
| Activity Name | string |  |  | Descriptive title of the schedule activity as authored by the PM. |
| Planned Start | dateTime |  | yyyy-mm-dd | Scheduled (planned) start date of the activity. |
| Planned Finish | dateTime |  | yyyy-mm-dd | Scheduled (planned) finish date of the activity. |
| Actual Start | dateTime |  | yyyy-mm-dd | Date the activity actually started; blank until work begins. |
| Actual Finish | dateTime |  | yyyy-mm-dd | Date the activity actually finished; blank until completed. |
| Duration Days | int64 |  | #,0 | Planned span in working days (Mon-Fri inclusive) between planned start and finish. |
| Owner ID | string | yes |  | (hidden) Foreign key to the activity owner; joins to 'Person'[Person ID]. |
| Owner | string |  |  | Display name of the person accountable for delivering the activity. |
| Department | string |  |  | Theragen department executing the activity (one of the 8 departments). |
| Activity Status | string |  |  | Workflow state of the activity: Not started / In progress / Done / At risk / Cancelled. |
| Pct Complete | double |  | 0\% | Percent of the activity completed (0-100), as reported by the owner. |

<a id="stakeholder"></a>
## Stakeholder

Fact - stakeholder register entries (PMBOK P03) with RACI engagement and interest/influence.

**Source:** `bi.stakeholder`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Stakeholder ID | string | yes |  | (hidden) Surrogate key for the stakeholder register entry. |
| Project ID | string | yes |  | (hidden) Surrogate key joining the stakeholder to its project. |
| Project Code | string |  |  | Human-readable project code the stakeholder belongs to. |
| Stk Code | string |  |  | Minted stakeholder code identifying this register entry within the project. |
| Person ID | string | yes |  | (hidden) Surrogate key joining the stakeholder to the Person directory. |
| Stakeholder | string |  |  | Display name of the stakeholder (person or group with interest in the project). |
| Stakeholder Role | string |  |  | The stakeholder's role or title relative to the project. |
| Department | string |  |  | Theragen department the stakeholder is affiliated with. |
| Engagement | string |  |  | RACI engagement role on the project: R, A, C, or I. |
| Interest | string |  |  | Stakeholder's level of interest in the project: High, Medium, or Low. |
| Influence | string |  |  | Stakeholder's level of influence over the project: High, Medium, or Low. |
| Comm Preference | string |  |  | The stakeholder's preferred communication channel or cadence. |

<a id="status-report"></a>
## Status Report

Fact - periodic status reports (PMBOK P23). Overall G/Y/R health and trend per period.

**Source:** `bi.status_report`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Report ID | string | yes |  | (hidden) Surrogate key for the status report; child area rows join on this. |
| Project ID | string | yes |  | (hidden) Surrogate key joining the report to its project. |
| Project Code | string |  |  | Human-readable project code the report belongs to. |
| Report Number | int64 |  | #,0 | Sequential number of this report in the project's reporting cadence. |
| Period Start | dateTime |  | yyyy-mm-dd | First day of the reporting period this status covers. |
| Period End | dateTime |  | yyyy-mm-dd | Last day of the reporting period; the report's effective as-of date. |
| Overall Status | string |  |  | Overall project health for the period: Green, Yellow, or Red. |
| Trend | string |  |  | Direction of project health since the prior report: improving, steady, or declining. |
| Executive Summary | string |  |  | Narrative summary of progress, issues, and outlook for the period. |
| Decisions Needed | string |  |  | Open decisions or escalations the report flags for leadership action. |
| Submitted By | string |  |  | Display name of the person who submitted the status report. |
| Submitted Date | dateTime |  | yyyy-mm-dd | Date the status report was submitted. |
| Approved By | string |  |  | Display name of the approver who signed off the status report. |
| Approved Date | dateTime |  | yyyy-mm-dd | Date the approver signed off the status report. |
| Is Signed Off | boolean |  |  | TRUE when the report has received formal approver sign-off. |

<a id="status-report-area"></a>
## Status Report Area

Fact - per-knowledge-area health entries within each status report (PMBOK P24).

**Source:** `bi.status_report_area`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Area ID | string | yes |  | (hidden) Surrogate key for the per-knowledge-area health entry. |
| Report ID | string | yes |  | (hidden) Surrogate key joining the area entry to its parent status report. |
| Project Code | string |  |  | Human-readable project code the area entry belongs to. |
| Knowledge Area | string |  |  | PMI knowledge area this health entry rates (Scope, Schedule, Cost, Quality, Risk, etc.). |
| Area Status | string |  |  | Health of this knowledge area for the period: Green, Yellow, or Red. |

<a id="team-member"></a>
## Team Member

Fact - project team assignments (PMBOK P31) with allocation percentage.

**Source:** `bi.project_team_member`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Team Member ID | string | yes |  | (hidden) Surrogate key for the team assignment row. |
| Project ID | string | yes |  | (hidden) Surrogate key joining the assignment to its project. |
| Project Code | string |  |  | Human-readable project code the team member is assigned to. |
| Person ID | string | yes |  | (hidden) Surrogate key joining the assignment to the Person directory. |
| Member | string |  |  | Display name of the person assigned to the project team. |
| Team Role | string |  |  | The member's role on the project team. |
| Department | string |  |  | Theragen department the team member belongs to. |
| Allocation Pct | double |  | 0\% | Share of the member's time committed to the project; 100% = one FTE. |
| Start Date | dateTime |  | yyyy-mm-dd | Date the member's assignment to the project began. |
| End Date | dateTime |  | yyyy-mm-dd | Date the member's assignment ends; blank while still active. |

<a id="upcoming-next-step"></a>
## Upcoming Next Step

Leadership view - open work targeted in the next 45 days (activities + milestones).

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Project ID | string | yes |  | (hidden) Surrogate key of the owning project; joins to the Project dimension. |
| Next Step | string |  |  | Name of the open activity or upcoming milestone targeted next. |
| Target Date | dateTime |  | yyyy-mm-dd | Planned finish (activity) or forecast/baseline date (milestone) the next step is due. |
| Owner | string |  |  | Activity owner or milestone owner role responsible for the next step. |
| Source | string |  |  | Origin of the next-step row: Activity or Milestone. |

<a id="wbs-element"></a>
## WBS Element

Work breakdown structure dimension (PMBOK P08). Two-level hierarchy: deliverable > work package.

**Source:** `bi.wbs_element`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| WBS ID | string | yes |  | (hidden) Surrogate key for the WBS node; activities and budget lines join to this. |
| Project ID | string | yes |  | (hidden) Foreign key to the owning project; joins to 'Project'[Project ID]. |
| Project Code | string |  |  | Human-readable project code this WBS node belongs to (e.g. PRJ-001). |
| WBS Code | string |  |  | Human-readable WBS code minted append-only (e.g. 1 = workstream, 1.1 = work package). |
| Parent WBS ID | string | yes |  | (hidden) Self-referencing key to the parent workstream; blank for level-1 nodes. |
| WBS Level | int64 |  | #,0 | Depth in the WBS hierarchy: 1 = workstream, 2 = work package (EVM estimates attach here). |
| WBS Name | string |  |  | Descriptive name of the workstream or work package. |
| Owning Department | string |  |  | Theragen department accountable for this WBS node (one of the 8 departments). |
| Owner Role | string |  |  | Role title responsible for the WBS node (e.g. Project Manager, Lead Engineer). |
| Estimated Effort Hrs | double |  | #,0 | Planned effort for the node in person-hours. |
| Estimated Cost | double |  | \$#,##0;(\$#,##0);\$0 | Estimated cost of the node; level-2 sums form the EVM Budget at Completion (BAC). |
| Deliverable = IF('WBS Element'[WBS Level] = 1, 'WBS Element'[WBS Name], LOOKUPVALUE('WBS Element'[WBS Name], 'WBS Element'[WBS ID], 'WBS Element'[Parent WBS ID])) | string |  |  | Level-1 deliverable this node rolls up to. |
| 'WBS Label' = 'WBS Element'[WBS Code] & "  " & 'WBS Element'[WBS Name] | string |  |  | Code + name for axis labels. |

## Relationships

| From | To | Cross-filter | Active |
|---|---|---|---|
| `Budget Line`[WBS ID] | `WBS Element`[WBS ID] | single | yes |
| `Change Impact Assessment`[CR ID] | `Change Request`[CR ID] | single | yes |
| `Change Request`[Decided Date] | `Date`[Date] | single | no |
| `Change Request`[Project ID] | `Project`[Project ID] | single | yes |
| `Change Request`[Requested By ID] | `Person`[Person ID] | single | yes |
| `Change Request`[Requested Date] | `Date`[Date] | single | yes |
| `Closure Item`[Project ID] | `Project`[Project ID] | single | yes |
| `Controlled Document`[Department] | `Department`[Department] | single | yes |
| `Cost Actual`[WBS ID] | `WBS Element`[WBS ID] | single | yes |
| `Decision`[Project ID] | `Project`[Project ID] | single | yes |
| `Document Approval`[Version ID] | `Document Version`[Version ID] | single | yes |
| `Document RACI`[Document ID] | `Controlled Document`[Document ID] | single | yes |
| `Document Version`[Document ID] | `Controlled Document`[Document ID] | single | yes |
| `Governance Change Assessment`[CR Gov ID] | `Governance Change Request`[CR Gov ID] | single | yes |
| `Governance Change Request`[Document ID] | `Controlled Document`[Document ID] | single | yes |
| `Lesson Learned`[Project ID] | `Project`[Project ID] | single | yes |
| `Milestone`[Actual Date] | `Date`[Date] | single | no |
| `Milestone`[Baseline Date] | `Date`[Date] | single | yes |
| `Milestone`[Forecast Date] | `Date`[Date] | single | no |
| `Milestone`[Project ID] | `Project`[Project ID] | single | yes |
| `Phase Gate Log`[Project ID] | `Project`[Project ID] | single | yes |
| `Project Baseline`[Project ID] | `Project`[Project ID] | single | yes |
| `Recent Accomplishment`[Project ID] | `Project`[Project ID] | single | yes |
| `Risk`[Department] | `Department`[Department] | single | yes |
| `Risk`[Due Date] | `Date`[Date] | single | yes |
| `Risk`[Owner ID] | `Person`[Person ID] | single | yes |
| `Risk`[Project ID] | `Project`[Project ID] | single | yes |
| `Risk Response`[Risk ID] | `Risk`[Risk ID] | single | yes |
| `Schedule Activity`[Actual Finish] | `Date`[Date] | single | no |
| `Schedule Activity`[Department] | `Department`[Department] | single | yes |
| `Schedule Activity`[Owner ID] | `Person`[Person ID] | single | yes |
| `Schedule Activity`[Planned Finish] | `Date`[Date] | single | yes |
| `Schedule Activity`[Planned Start] | `Date`[Date] | single | no |
| `Schedule Activity`[WBS ID] | `WBS Element`[WBS ID] | single | yes |
| `Stakeholder`[Department] | `Department`[Department] | single | yes |
| `Stakeholder`[Person ID] | `Person`[Person ID] | single | yes |
| `Stakeholder`[Project ID] | `Project`[Project ID] | single | yes |
| `Status Report`[Period End] | `Date`[Date] | single | yes |
| `Status Report`[Project ID] | `Project`[Project ID] | single | yes |
| `Status Report Area`[Knowledge Area] | `Knowledge Area`[Knowledge Area] | single | yes |
| `Status Report Area`[Report ID] | `Status Report`[Report ID] | single | yes |
| `Team Member`[Department] | `Department`[Department] | single | yes |
| `Team Member`[Person ID] | `Person`[Person ID] | single | yes |
| `Team Member`[Project ID] | `Project`[Project ID] | single | yes |
| `Team Member`[Start Date] | `Date`[Date] | single | yes |
| `Upcoming Next Step`[Project ID] | `Project`[Project ID] | single | yes |
| `WBS Element`[Project ID] | `Project`[Project ID] | single | yes |

