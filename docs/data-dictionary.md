# Theragen Project Planner — Data Dictionary

_Generated from the semantic-model TMDL by `tools/build_data_dictionary.py` — **do not edit by hand**; regenerate after model changes (see [change-control process](change-control-process.md)). Business definitions live in the [glossary](glossary.md)._

> Generated from model `e314b11` (2026-06-14) · platform **v2.6**  
> 33 tables · 339 columns · 154 measures · 47 relationships · 2 roles

## Model index

| Table | Source | Cols | Measures | Description |
|---|---|---|---|---|
| [_Measures](#_measures) | — | 1 | 154 | Measure home table. All portfolio analytics measures live here. |
| [Budget Line](#budget-line) | `bi.budget_line_item` | 13 | 0 | Fact - cost budget estimate lines (PMBOK P13), one per level-1 deliverable. |
| [Change Impact Assessment](#change-impact-assessment) | `bi.change_impact_assessment` | 11 | 0 | Fact - per-department change-impact assessments (PMBOK P22). One row per department's impact statement on a change request. |
| [Change Request](#change-request) | `bi.change_request` | 24 | 0 | Fact - project change requests (PMBOK P21) with impact and decision cycle. |
| [Closure Item](#closure-item) | `bi.closure_checklist_item` | 7 | 0 | Fact - project closure checklist items (PMBOK P26). |
| [Controlled Document](#controlled-document) | `bi.document` | 17 | 0 | Fact - controlled-document register (doc_mgmt spine). One row per controlled document, org-wide. |
| [Cost Actual](#cost-actual) | `bi.cost_actual` | 10 | 0 | Fact - per-work-package, per-period actual cost (EVM AC). One row per logged cost actual against a WBS work package. |
| [Date](#date) | — | 7 | 0 | Marked date dimension covering 2025-2027. |
| [Decision](#decision) | `bi.decision` | 7 | 0 | Fact - governance decisions (PMBOK P21). Formal decisions logged against a project. |
| [Department](#department) | `bi.department` | 3 | 0 | Conformed department dimension (DM D01). Filters executing departments on facts. |
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
| Value | string | yes |  |  |

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
| Budget Line ID | string | yes |  |  |
| WBS ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Cost Category | string |  |  |  |
| Labor Amount | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Materials Amount | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Vendor Amount | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Other Amount | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Subtotal | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Contingency Pct | double |  | #,0.0 |  |
| Total | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Funding Source | string |  |  |  |

<a id="change-impact-assessment"></a>
## Change Impact Assessment

Fact - per-department change-impact assessments (PMBOK P22). One row per department's impact statement on a change request.

**Source:** `bi.change_impact_assessment`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Impact ID | string | yes |  |  |
| CR ID | string | yes |  |  |
| CR Code | string |  |  |  |
| Project Code | string |  |  |  |
| Department | string |  |  |  |
| Scope Impact | string |  |  |  |
| Schedule Impact Days | int64 |  | #,0 |  |
| Cost Impact | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Quality Impact | string |  |  |  |
| Submitted By | string |  |  |  |
| Submitted Date | dateTime |  | yyyy-mm-dd |  |

<a id="change-request"></a>
## Change Request

Fact - project change requests (PMBOK P21) with impact and decision cycle.

**Source:** `bi.change_request`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| CR ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| CR Code | string |  |  |  |
| Intake ID | string |  |  |  |
| Requested Date | dateTime |  | yyyy-mm-dd |  |
| Requested By ID | string | yes |  |  |
| Requested By | string |  |  |  |
| CR Class | string |  |  |  |
| Change Type | string |  |  |  |
| CR Description | string |  |  |  |
| Reason | string |  |  |  |
| Schedule Impact Days | int64 |  | #,0 |  |
| Cost Impact | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Decision | string |  |  |  |
| Decided Date | dateTime |  | yyyy-mm-dd |  |
| Cycle Time Days | int64 |  | #,0 |  |
| CR Status | string |  |  |  |
| Decided By | string |  |  |  |
| Impact Scope | string |  |  |  |
| Impact Quality | string |  |  |  |
| Affected Artifacts | string |  |  |  |
| Implementation Verified | boolean |  |  |  |
| Linked Artifacts Updated | boolean |  |  |  |

<a id="closure-item"></a>
## Closure Item

Fact - project closure checklist items (PMBOK P26).

**Source:** `bi.closure_checklist_item`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Closure Item ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Closure Item | string |  |  |  |
| Owner Role | string |  |  |  |
| Done | boolean |  |  |  |
| Evidence | string |  |  |  |

<a id="controlled-document"></a>
## Controlled Document

Fact - controlled-document register (doc_mgmt spine). One row per controlled document, org-wide.

**Source:** `bi.document`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Document ID | string | yes |  |  |
| Doc ID | string |  |  |  |
| Document Type | string |  |  |  |
| Department | string |  |  |  |
| Title | string |  |  |  |
| Subtitle | string |  |  |  |
| Lifecycle Phase | string |  |  |  |
| Status | string |  |  |  |
| Current Version | string |  |  |  |
| Owner | string |  |  |  |
| Approver | string |  |  |  |
| Review Cycle | string |  |  |  |
| Next Review Due | dateTime |  | yyyy-mm-dd |  |
| Classification | string |  |  |  |
| Storage System | string |  |  |  |
| Storage Path | string |  |  |  |
| Created Date | dateTime |  | yyyy-mm-dd |  |

<a id="cost-actual"></a>
## Cost Actual

Fact - per-work-package, per-period actual cost (EVM AC). One row per logged cost actual against a WBS work package.

**Source:** `bi.cost_actual`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Cost Actual ID | string | yes |  |  |
| WBS ID | string | yes |  |  |
| Project Code | string |  |  |  |
| WBS Code | string |  |  |  |
| Work Package | string |  |  |  |
| Period | dateTime |  | yyyy-mm-dd |  |
| Amount | double |  | \$#,##0.00;(\$#,##0.00);\$0 |  |
| Category | string |  |  |  |
| Entered By | string |  |  |  |
| Notes | string |  |  |  |

<a id="date"></a>
## Date

Marked date dimension covering 2025-2027.

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Date | dateTime |  | yyyy-mm-dd |  |
| Year = YEAR('Date'[Date]) | int64 |  | #,0 |  |
| Quarter = "Q" & QUARTER('Date'[Date]) | string |  |  |  |
| 'Month Number' = MONTH('Date'[Date]) | int64 | yes |  |  |
| Month = FORMAT('Date'[Date], "MMM") | string |  |  |  |
| 'Year Month' = FORMAT('Date'[Date], "YYYY-MM") | string |  |  |  |
| 'Week Of' = 'Date'[Date] - WEEKDAY('Date'[Date], 2) + 1 | dateTime |  | yyyy-mm-dd |  |

<a id="decision"></a>
## Decision

Fact - governance decisions (PMBOK P21). Formal decisions logged against a project.

**Source:** `bi.decision`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Decision ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Decision | string |  |  |  |
| Rationale | string |  |  |  |
| Decided By | string |  |  |  |
| Decided Date | dateTime |  | yyyy-mm-dd |  |

<a id="department"></a>
## Department

Conformed department dimension (DM D01). Filters executing departments on facts.

**Source:** `bi.department`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Department ID | string | yes |  |  |
| Department Code | string |  |  |  |
| Department | string |  |  |  |

<a id="document-approval"></a>
## Document Approval

Fact - per-version sign-off ATTESTATION (non-Part-11; see esig_kind).

**Source:** `bi.document_approval`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Approval ID | string | yes |  |  |
| Version ID | string | yes |  |  |
| Doc ID | string |  |  |  |
| Document Title | string |  |  |  |
| Version | string |  |  |  |
| Approver | string |  |  |  |
| Signature Meaning | string |  |  |  |
| Signed At | dateTime |  | yyyy-mm-dd hh:nn:ss |  |
| Attestation Hash | string |  |  |  |
| Attestation Kind | string |  |  |  |
| Reason | string |  |  |  |

<a id="document-raci"></a>
## Document RACI

Fact - per-document, per-department R/A/C/I assignment (effective-dated).

**Source:** `bi.raci_assignment`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| RACI ID | string | yes |  |  |
| Document ID | string | yes |  |  |
| Doc ID | string |  |  |  |
| Document Title | string |  |  |  |
| Department | string |  |  |  |
| Role | string |  |  |  |
| Role Name | string |  |  |  |
| Touchpoint | string |  |  |  |
| Valid From | dateTime |  | yyyy-mm-dd |  |
| Valid To | dateTime |  | yyyy-mm-dd |  |

<a id="document-version"></a>
## Document Version

Fact - controlled-document version history.

**Source:** `bi.document_version`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Version ID | string | yes |  |  |
| Document ID | string | yes |  |  |
| Doc ID | string |  |  |  |
| Document Title | string |  |  |  |
| Version | string |  |  |  |
| Status | string |  |  |  |
| Change Summary | string |  |  |  |
| Change Class | string |  |  |  |
| Author | string |  |  |  |
| Effective Date | dateTime |  | yyyy-mm-dd |  |
| Storage Path | string |  |  |  |
| Created Date | dateTime |  | yyyy-mm-dd |  |
| Linked CR | string |  |  |  |

<a id="governance-change-assessment"></a>
## Governance Change Assessment

Fact - per-department impact assessments on a governance change request. One row per department's impact statement on a gov CR.

**Source:** `bi.change_assessment_gov`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Gov Impact ID | string | yes |  |  |
| CR Gov ID | string | yes |  |  |
| CR Code | string |  |  |  |
| Doc ID | string |  |  |  |
| Doc Title | string |  |  |  |
| Department | string |  |  |  |
| Impact Summary | string |  |  |  |
| Compliance Impact | string |  |  |  |
| Submitted Date | dateTime |  | yyyy-mm-dd |  |

<a id="governance-change-request"></a>
## Governance Change Request

Fact - governance change requests (CHG-NNN) against controlled documents (SOP-003). Document-scoped, project-less; reuses the two-axis Decision/Status workflow.

**Source:** `bi.change_request_gov`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| CR Gov ID | string | yes |  |  |
| Document ID | string | yes |  |  |
| CR Code | string |  |  |  |
| Doc ID | string |  |  |  |
| Doc Title | string |  |  |  |
| Requested Date | dateTime |  | yyyy-mm-dd |  |
| Requested By | string |  |  |  |
| CR Class | string |  |  |  |
| Description | string |  |  |  |
| Reason | string |  |  |  |
| Decision | string |  |  |  |
| Decided By | string |  |  |  |
| Decided Date | dateTime |  | yyyy-mm-dd |  |
| Implementation Verified | boolean |  |  |  |
| Status | string |  |  |  |
| Intake ID | string |  |  |  |

<a id="knowledge-area"></a>
## Knowledge Area

PMBOK knowledge areas (enum knowledge_area) used by status report health entries.

**Source:** `bi.knowledge_area`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Knowledge Area | string |  |  |  |
| KA Sort | int64 | yes |  |  |

<a id="lesson-learned"></a>
## Lesson Learned

Fact - lessons learned (PMBOK P25).

**Source:** `bi.lesson_learned`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Lesson ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Lesson Category | string |  |  |  |
| Lesson | string |  |  |  |
| What Happened | string |  |  |  |
| Recommendation | string |  |  |  |
| Follow-up Owner | string |  |  |  |
| Lesson Status | string |  |  |  |

<a id="milestone"></a>
## Milestone

Fact - milestones (PMBOK P11). Baseline vs forecast vs actual dates.

**Source:** `bi.milestone`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Milestone ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Milestone | string |  |  |  |
| Baseline Date | dateTime |  | yyyy-mm-dd |  |
| Forecast Date | dateTime |  | yyyy-mm-dd |  |
| Actual Date | dateTime |  | yyyy-mm-dd |  |
| Milestone Status | string |  |  |  |
| Owner Role | string |  |  |  |
| 'Slip Days' = DATEDIFF('Milestone'[Baseline Date], COALESCE('Milestone'[Actual Date], 'Milestone'[Forecast Date], 'Milestone'[Baseline Date]), DAY) | int64 |  |  | Days between baseline and actual (or forecast) date. Positive = slip. |

<a id="person"></a>
## Person

Person directory (DM D02). Owners, requesters and assignees on facts.

**Source:** `bi.person`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Person ID | string | yes |  |  |
| Person | string |  |  |  |
| Email | string |  |  |  |
| Person Department | string |  |  |  |
| Role Title | string |  |  |  |
| Employee Number | string |  |  |  |

<a id="phase-gate-log"></a>
## Phase Gate Log

Fact - append-only record of lifecycle-phase handoffs (PMBOK). Captures who approved each phase transition, when, and the gate decision.

**Source:** `bi.phase_gate_log`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Phase Gate ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| From Phase | string |  |  |  |
| To Phase | string |  |  |  |
| Gate Decision | string |  |  |  |
| Decided Date | dateTime |  | yyyy-mm-dd |  |
| Gate Notes | string |  |  |  |
| Approved By | string |  |  |  |

<a id="project"></a>
## Project

Project dimension - one row per project (PMBOK P01 project, charter fields denormalized).

**Source:** `bi.project`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Intake ID | string |  |  |  |
| Project Name | string |  |  |  |
| Project Description | string |  |  |  |
| Business Value | string |  |  |  |
| Sponsor | string |  |  |  |
| Project Manager | string |  |  |  |
| Primary Department | string |  |  |  |
| Approach | string |  |  |  |
| Lifecycle Phase | string |  |  |  |
| Project Status | string |  |  |  |
| Planned Start | dateTime |  | yyyy-mm-dd |  |
| Planned Finish | dateTime |  | yyyy-mm-dd |  |
| Actual Start | dateTime |  | yyyy-mm-dd |  |
| Actual Finish | dateTime |  | yyyy-mm-dd |  |
| Charter Budget | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Strategic Objective | string |  |  |  |

<a id="project-baseline"></a>
## Project Baseline

Fact - immutable schedule/scope/budget baselines (PMBOK). Each new baseline mints the next version; prior BASELINED rows go SUPERSEDED.

**Source:** `bi.project_baseline`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Baseline ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Baseline Type | string |  |  |  |
| Version | string |  |  |  |
| Status | string |  |  |  |
| Change Summary | string |  |  |  |
| Baselined Date | dateTime |  | yyyy-mm-dd |  |
| Baselined By | string |  |  |  |
| Baseline Budget Total | double |  | \$#,##0;(\$#,##0);\$0 |  |
| Baseline Activity Count | int64 |  | #,0 |  |

<a id="recent-accomplishment"></a>
## Recent Accomplishment

Leadership view - work completed in the last 35 days (done activities + achieved milestones).

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Project ID | string | yes |  |  |
| Accomplishment | string |  |  |  |
| Completed Date | dateTime |  | yyyy-mm-dd |  |
| Source | string |  |  |  |

<a id="report-access"></a>
## Report Access

Security - data-driven RLS grants. Disconnected (no relationships): the "Scoped Viewer" role reads it via USERPRINCIPALNAME() to filter Project. Hidden so the access map never appears in the field list.

**Source:** `bi.report_access`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Access ID | string | yes |  |  |
| User Email | string |  |  |  |
| Scope Type | string |  |  |  |
| Scope Value | string |  |  |  |
| Active | boolean |  |  |  |
| Granted By | string |  |  |  |
| Granted Date | dateTime |  | yyyy-mm-dd |  |

<a id="risk"></a>
## Risk

Fact - risk register (PMBOK P14). 5x5 likelihood x impact scoring.

**Source:** `bi.risk`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Risk ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Risk Code | string |  |  |  |
| Risk Category | string |  |  |  |
| Risk Description | string |  |  |  |
| Likelihood | int64 |  | #,0 |  |
| Impact | int64 |  | #,0 |  |
| Risk Score | int64 |  | #,0 |  |
| Response Type | string |  |  |  |
| Owner ID | string | yes |  |  |
| Owner | string |  |  |  |
| Department | string |  |  |  |
| Due Date | dateTime |  | yyyy-mm-dd |  |
| Risk Status | string |  |  |  |
| Residual Score | int64 |  | #,0 |  |
| Compliance Frame | string |  |  |  |
| Severity = SWITCH(TRUE(), 'Risk'[Risk Score] >= 20, "Critical", 'Risk'[Risk Score] >= 12, "High", 'Risk'[Risk Score] >= 6, "Medium", "Low") | string |  |  | Banding of Risk Score on the 5x5 matrix: >=20 Critical, >=12 High, >=6 Medium. |
| 'RAID Type' = IF('Risk'[Risk Status] = "Realized", "Issue", "Risk") | string |  |  | RAID classification: a realized risk is reported as an Issue. |

<a id="risk-response"></a>
## Risk Response

Fact - risk response actions (PMBOK P15).

**Source:** `bi.risk_response`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Response ID | string | yes |  |  |
| Risk ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Risk Code | string |  |  |  |
| Action Type | string |  |  |  |
| Action Description | string |  |  |  |
| Action Owner | string |  |  |  |
| Action Due Date | dateTime |  | yyyy-mm-dd |  |
| Action Status | string |  |  |  |

<a id="schedule-activity"></a>
## Schedule Activity

Fact - schedule activities (PMBOK P10). One row per activity with planned/actual dates and percent complete.

**Source:** `bi.schedule_activity`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Activity ID | string | yes |  |  |
| WBS ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Activity Code | string |  |  |  |
| Activity Name | string |  |  |  |
| Planned Start | dateTime |  | yyyy-mm-dd |  |
| Planned Finish | dateTime |  | yyyy-mm-dd |  |
| Actual Start | dateTime |  | yyyy-mm-dd |  |
| Actual Finish | dateTime |  | yyyy-mm-dd |  |
| Duration Days | int64 |  | #,0 |  |
| Owner ID | string | yes |  |  |
| Owner | string |  |  |  |
| Department | string |  |  |  |
| Activity Status | string |  |  |  |
| Pct Complete | double |  | 0\% |  |

<a id="stakeholder"></a>
## Stakeholder

Fact - stakeholder register entries (PMBOK P03) with RACI engagement and interest/influence.

**Source:** `bi.stakeholder`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Stakeholder ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Stk Code | string |  |  |  |
| Person ID | string | yes |  |  |
| Stakeholder | string |  |  |  |
| Stakeholder Role | string |  |  |  |
| Department | string |  |  |  |
| Engagement | string |  |  |  |
| Interest | string |  |  |  |
| Influence | string |  |  |  |
| Comm Preference | string |  |  |  |

<a id="status-report"></a>
## Status Report

Fact - periodic status reports (PMBOK P23). Overall G/Y/R health and trend per period.

**Source:** `bi.status_report`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Report ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Report Number | int64 |  | #,0 |  |
| Period Start | dateTime |  | yyyy-mm-dd |  |
| Period End | dateTime |  | yyyy-mm-dd |  |
| Overall Status | string |  |  |  |
| Trend | string |  |  |  |
| Executive Summary | string |  |  |  |
| Decisions Needed | string |  |  |  |
| Submitted By | string |  |  |  |
| Submitted Date | dateTime |  | yyyy-mm-dd |  |
| Approved By | string |  |  |  |
| Approved Date | dateTime |  | yyyy-mm-dd |  |
| Is Signed Off | boolean |  |  |  |

<a id="status-report-area"></a>
## Status Report Area

Fact - per-knowledge-area health entries within each status report (PMBOK P24).

**Source:** `bi.status_report_area`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Area ID | string | yes |  |  |
| Report ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Knowledge Area | string |  |  |  |
| Area Status | string |  |  |  |

<a id="team-member"></a>
## Team Member

Fact - project team assignments (PMBOK P31) with allocation percentage.

**Source:** `bi.project_team_member`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Team Member ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| Person ID | string | yes |  |  |
| Member | string |  |  |  |
| Team Role | string |  |  |  |
| Department | string |  |  |  |
| Allocation Pct | double |  | 0\% |  |
| Start Date | dateTime |  | yyyy-mm-dd |  |
| End Date | dateTime |  | yyyy-mm-dd |  |

<a id="upcoming-next-step"></a>
## Upcoming Next Step

Leadership view - open work targeted in the next 45 days (activities + milestones).

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| Project ID | string | yes |  |  |
| Next Step | string |  |  |  |
| Target Date | dateTime |  | yyyy-mm-dd |  |
| Owner | string |  |  |  |
| Source | string |  |  |  |

<a id="wbs-element"></a>
## WBS Element

Work breakdown structure dimension (PMBOK P08). Two-level hierarchy: deliverable > work package.

**Source:** `bi.wbs_element`

**Columns**

| Column | Type | Hidden | Format | Description |
|---|---|---|---|---|
| WBS ID | string | yes |  |  |
| Project ID | string | yes |  |  |
| Project Code | string |  |  |  |
| WBS Code | string |  |  |  |
| Parent WBS ID | string | yes |  |  |
| WBS Level | int64 |  | #,0 |  |
| WBS Name | string |  |  |  |
| Owning Department | string |  |  |  |
| Owner Role | string |  |  |  |
| Estimated Effort Hrs | double |  | #,0 |  |
| Estimated Cost | double |  | \$#,##0;(\$#,##0);\$0 |  |
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

