# Theragen Project Planner BI — Semantic Model Design

**Source of truth:** `THG-ENT-DBS-001_Database_Schema_Specification_v1.0.xlsx` (PMBOK schema, 31 entities)
plus the 14 PMBOK template documents and the Development Documentation Reference Book.

**Target:** Power BI Project (PBIP) with TMDL semantic model + PBIR report, stored in git.

---

## 1. Modeling approach

The PMBOK schema is an OLTP design (UUID keys, 3NF, CASCADE deletes). For analytics we reshape it
into a **star schema** per Power BI best practice:

- Conformed dimensions: `Date`, `Project`, `Department`, `Person`, `WBS Element`, `Knowledge Area`
- One fact table per PMBOK transactional entity that carries measures or events
- Single-direction filtering everywhere; no bidirectional relationships
- Enum lookups (35 sets) become text columns on facts (low cardinality) — except
  `department_code` and `knowledge_area`, which are promoted to dimensions because they
  conform across many facts
- Surrogate UUIDs are kept as hidden keys; human codes (`THG-CLN-014`, `R-014`, `C-007`)
  are the visible identifiers

### Source mapping

| Model table | PMBOK entity | Type | Grain |
|---|---|---|---|
| Project | P01 project (+ P02 charter denorm.) | Dimension | 1 row / project |
| Department | DM D01 department | Dimension | 8 rows |
| Person | DM D02 person | Dimension | 1 row / person |
| WBS Element | P08 wbs_element (+ P09 dictionary) | Dimension (mid-tier) | 1 row / WBS node |
| Knowledge Area | enum `knowledge_area` | Dimension | 9 rows |
| Date | DAX `CALENDAR(2025-01-01 … 2027-12-31)` | Date dimension | 1 row / day |
| Schedule Activity | P10 schedule_activity | Fact | 1 row / activity |
| Milestone | P11 milestone | Fact | 1 row / milestone |
| Budget Line | P13 budget_line_item | Fact | 1 row / cost line |
| Risk | P14 risk | Fact | 1 row / risk |
| Risk Response | P15 risk_response | Fact | 1 row / response action |
| Change Request | P21 change_request | Fact | 1 row / CR |
| Status Report | P23 status_report | Fact | 1 row / report period |
| Status Report Area | P24 status_report_area | Fact | 1 row / report × knowledge area |
| Stakeholder | P03 stakeholder | Fact (attribute fact) | 1 row / stakeholder entry |
| Team Member | P31 project_team_member | Fact | 1 row / assignment |
| Lesson Learned | P25 lesson_learned | Fact | 1 row / lesson |
| Closure Item | P26 closure_checklist_item | Fact | 1 row / checklist item |
| _Measures | — | Measure home | empty |

Entities **not** modeled in v1 (no analytic payload, or document-body content):
P04–P07 scope statement details, P12 schedule_dependency (network analysis is Phase 2),
P16–P20 comms/quality plans (static plan rows; Phase 2), P22 change_impact_assessment,
P27–P30 assumptions/constraints/decisions/approvals (registers; Phase 2), and the DM
governance schema except `person`/`department`. The TMDL layout makes adding them additive.

## 2. Relationship graph

```
Department ──< Schedule Activity >── WBS Element >── Project
Department ──< Risk              >── Project
Department ──< Stakeholder       >── Project
Department ──< Team Member       >── Project
Person ──< Schedule Activity / Risk / Change Request / Stakeholder / Team Member
Project ──< WBS Element ──< Schedule Activity, Budget Line
Project ──< Milestone, Risk, Change Request, Status Report, Stakeholder,
            Team Member, Lesson Learned, Closure Item
Risk ──< Risk Response
Status Report ──< Status Report Area >── Knowledge Area
Date ──< (active) Activity[Planned Finish], Milestone[Baseline], Risk[Due],
          CR[Requested], Status Report[Period End], Team Member[Start]
Date ──< (inactive) Activity[Planned Start / Actual Finish],
          Milestone[Forecast / Actual], CR[Decided]
```

Ambiguity rules respected:
- `Project` reaches `Schedule Activity`/`Budget Line` **only** through `WBS Element`
  (no direct relationship → no dual path).
- `Department` relates **only to facts** (executing department). Project- and WBS-level
  department remain display columns (`Project[Primary Department]`,
  `WBS Element[Owning Department]`).
- `Person` relates only to facts; `Person[Department]` is a display column.

All relationships: many-to-one, single cross-filter direction (fact → filtered by dim).

## 3. Measure families (on `_Measures`)

| Family | Measures |
|---|---|
| Portfolio | Projects, Active Projects, Projects On Hold, Portfolio Budget (BAC), Projects by Phase |
| Schedule | % Complete (effort-weighted), Activities, Activities Overdue, Overdue %, On-Time Completion %, Activities At Risk, Avg Duration |
| EVM | BAC, Planned Value (PV), Earned Value (EV), Schedule Variance (SV), SPI, % Schedule Elapsed. *AC/CPI/EAC deferred — the schema has no cost-actuals feed yet; documented as Phase 2.* |
| Milestones | Milestones, Achieved, At Risk, Slipped, Hit Rate %, Avg Slip Days |
| Cost | Budget Total, Budget ex Contingency, Contingency Amount, Contingency %, Labor/Materials/Vendor/Other Amounts, Approved CR Cost Impact, Working Budget (BAC + approved CRs) |
| Risk | Open Risks, High Risks (score ≥ 12), Critical Risks (≥ 20), Total Exposure, Residual Exposure, Risk Reduction %, Risks Past Due, Avg Risk Score, Open Responses |
| Change | CRs, Open CRs, Approved/Rejected/Pending, Approval Rate %, Avg Cycle Days, Net Cost Impact, Net Schedule Impact (days), Emergency CRs |
| Health | Latest Overall Status, Latest Trend, Health Score (G=3/Y=2/R=1), Red Areas, Yellow Areas, Reports Submitted |
| Stakeholders | Stakeholders, High Influence, High Interest, Key Players (H/H), RACI coverage counts |
| Team | Team Members, Total FTE, Avg Allocation % |
| Closing | Lessons, Open Lessons, Adopted Lessons, Closure Items, Closure Complete % |

Thresholds follow the templates: 5×5 risk matrix (score = likelihood × impact, high ≥ 12,
critical ≥ 20), G/Y/R health, milestone status enum.

## 4. Data source strategy

v1 ships with **generated sample data** (CSV, seeded, realistic 6-project portfolio) under
`SampleData/`, loaded through a single `DataFolder` M parameter. When the PostgreSQL
implementation of THG-ENT-DBS-001 comes online, repoint each table's partition from
`Csv.Document` to `PostgreSQL.Database` — table and column names in the model match the
DDL exactly (snake_case sources renamed to friendly names in one step).

## 5. Report pages (PBIR)

| Page | Mirrors | Content |
|---|---|---|
| Portfolio Overview | Master Document Index roll-up | KPI cards, project health table, budget by department, phase distribution |
| Project Status | Template 13 Status Report | Overall G/Y/R, trend, KA health matrix, decisions needed, period selector |
| Schedule & Milestones | Template 06 Schedule | Activity table w/ variance, % complete by WBS, milestone status, overdue list |
| Cost & Budget | Template 07 Cost Budget | BAC cards, category breakdown, WBS cost matrix, CR cost impact |
| Risk Management | Template 09 Risk Register | 5×5 heat matrix, exposure KPIs, top risks, response tracking |
| Change Control | Template 12 Change Log | CR pipeline, approval rate, cycle time, impact summary |
| Stakeholders & Team | Templates 02 + RACI | Engagement grid, interest/influence, team allocation |
| Lessons & Closure | Template 14 | Lessons by category/status, closure checklist completion |

Canvas 1280×720, Theragen palette, slicer panel (Project / Department / Date) consistent
across pages.
