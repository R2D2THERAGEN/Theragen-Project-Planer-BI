# Artifact Entry Setup — Risks, Milestones, Status Reports, Project Activities, Change Requests, Decisions, Baselines, Phase Gates, Change Impact Assessments, Controlled Documents, Document RACI, Document Versions, Document Approvals, Governance Change Requests, Governance Change Assessments, Risk Responses, Cost Actuals

This is the PM-facing reference for filling in the four execution-artifact SharePoint
Lists that feed the **Project Status Report** Power BI page. The daily 5:40 AM sync
(`tools/sync_artifacts.py`, Task Scheduler job `Theragen\SyncArtifacts`) reads these
Lists, validates every item, writes records into PostgreSQL, and writes results back to
each List row.

**Auth:** open each List as **richard.allen@theragen.com** — the account whose cached
Graph token the sync runs under. Read access is available to other accounts; write
access (creating and editing items) requires at minimum Edit permission on the site.

---

## Lists at a glance

| List | Purpose |
|------|---------|
| **Project Risks** | One row per identified risk per project |
| **Project Milestones** | One row per key milestone per project |
| **Project Status Reports** | One row per weekly/periodic report per project |
| **Project Activities** | One row per schedule activity per project — auto-derives the WBS |
| **Project Change Requests** | One row per change request per project — tracks the approval lifecycle |
| **Project Decisions** | One row per governance decision per project |
| **Project Baselines** | One row per frozen Schedule / Budget / Scope baseline per project — see §N |
| **Project Phase Gates** | One row per lifecycle-phase handoff per project — see §O |
| **Change Impact Assessments** | One row per department's impact statement on a change request — see §P |
| **Controlled Documents** | One row per controlled document (org-wide; minted DocID) — see §Q |
| **Document RACI** | One row per (document, department) R/A/C/I assignment — see §R |
| **Document Versions** | One row per document version (child of a document) — see §S |
| **Document Approvals (e-sig)** | One row per per-version sign-off **attestation** (non-§11) — see §T |
| **Governance Change Requests** | One row per change request against a controlled document (project-less, `CHG-NNN`) — see §U |
| **Governance Change Assessments** | One row per department's impact statement on a governance CR — see §V |
| **Risk Responses** | One row per risk response action (child of a risk) — see §X |
| **Cost Actuals** | One row per actual cost (work package × period) — the EVM AC feed — see §Y |

All these Lists live on the root SharePoint site (same site as Project Intake).

---

## A. Project Risks

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Short label for the risk (auto-populated by SharePoint as item title) |
| **ProjectCode** | Text | Must exactly match an existing project code — see §J |
| **Category** | Choice | See allowed values below |
| **Description** | Multi-line text | Full description of the risk |
| **Likelihood** | Choice | `1` through `5` |
| **Impact** | Choice | `1` through `5` |
| **ResponseType** | Choice | See allowed values below |
| **RiskOwner** | Person | M365 people picker — must resolve to a user in the person directory |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **Trigger** | Multi-line text | Early-warning signal; can be blank |
| **DueDate** | Date | Target date for the response action |
| **RiskStatus** | Choice | Defaults to `Open` if left blank |
| **ResidualScore** | Number | Post-response score; must be 1–25 if entered |
| **ComplianceFlag** | Choice | Defaults to `None` if left blank |

### Choice values — use exactly as shown

**Category** (one of):
```
Technical
Schedule
Cost
Regulatory
Vendor
People
Safety
Reputational
```

**Likelihood** and **Impact** (numeric strings):
```
1
2
3
4
5
```

The sync computes `score = Likelihood × Impact`. Both must be in 1–5 or the item is
marked Error.

**ResponseType** (one of):
```
Mitigate
Accept
Avoid
Transfer
```

**RiskStatus** (one of):
```
Open
Mitigating
Monitoring
Closed
Realized
```

**ComplianceFlag** (one of):
```
None
HIPAA
GxP
FDA 21 CFR Part 11
```

### Read-only write-back columns

The sync populates these automatically — **do not edit them**:

| Column | Meaning |
|--------|---------|
| **RiskCode** | Auto-minted sequential code within the project, e.g. `R-001`, `R-002`. Never changes after creation. |
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail when `SyncStatus = Error`; blank on success |

---

## B. Project Milestones

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Milestone name |
| **ProjectCode** | Text | Must exactly match an existing project code — see §J |
| **BaselineDate** | Date | Original planned completion date |
| **OwnerRole** | Choice | Role responsible for delivery |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **ForecastDate** | Date | Updated forecast; can be blank |
| **ActualDate** | Date | Required when `MilestoneStatus = Achieved` — see §G |
| **MilestoneStatus** | Choice | Defaults to `On track` if left blank |

### Choice values

**MilestoneStatus** (one of):
```
On track
At risk
Achieved
Slipped
```

**OwnerRole** (one of, or free-text):
```
Project Manager
Sponsor
Workstream Lead
Work Package Owner
```

(The column allows custom text entries for roles not in this list.)

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` or `Error` |
| **SyncMessage** | Error detail; blank on success |

---

## C. Project Status Reports

One row covers one reporting period for one project. The sync fans this out into a
parent report row plus nine knowledge-area health rows in PostgreSQL.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Short label, e.g. `wk24` or `2026-06-W3` |
| **ProjectCode** | Text | Must exactly match an existing project code — see §J |
| **PeriodStart** | Date | Start of the reporting period |
| **PeriodEnd** | Date | Must be on or after PeriodStart |
| **ExecutiveSummary** | Multi-line text | 2–5 sentence narrative |
| **SubmittedBy** | Person | Report author; people picker — must resolve to the person directory |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **OverallStatus** | Choice | Defaults to `Green` if left blank |
| **Trend** | Choice | Defaults to `Steady` if left blank |
| **DecisionsNeeded** | Multi-line text | Decisions required from leadership; can be blank |
| **{KA}Health** columns | Choice | Nine knowledge-area health columns; default `Green` |

### Choice values

**OverallStatus** and all nine **{KA}Health** columns (one of):
```
Green
Yellow
Red
```

**Trend** (one of):
```
Improving
Steady
Worsening
```

### The nine knowledge-area health columns

Each maps to a row in `bi.status_report_area` and drives the 9-cell health grid on the
Project Status Report page. They are evaluated in this order:

```
ScopeHealth
ScheduleHealth
CostHealth
QualityHealth
RiskHealth
StakeholdersHealth
ComplianceHealth
ProcurementHealth
CommunicationsHealth
```

All nine default to `Green` if left blank.

### Duplicate-period rule

Only one status report per project per `PeriodStart` date is allowed. If a second item
is submitted with the same `ProjectCode` and `PeriodStart`, the sync marks it `Error`:
`Duplicate report period for <code>: <date>`. Fix by correcting one of the two items'
`PeriodStart` dates, then reset its `SyncStatus` to `Pending`.

### Sign-off columns

Once the PM or Sponsor has reviewed and approved a status report, they (or the sync
operator) record the approval by filling these two columns on the List item:

| Column | Type | Notes |
|--------|------|-------|
| **ApprovedBy** | Person | M365 people picker — the person signing off the report |
| **ApprovedDate** | Date | Date the sign-off was recorded |

Both columns are **all-or-nothing**: either both are set or both must be blank.
Entering one without the other causes a validation error. Once the sync writes
`is_signed_off = true` to the database the report's submitter field is immutable —
the sync rejects a `SubmittedBy` change on a signed-off report.

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` or `Error` |
| **SyncMessage** | Error detail; blank on success |

---

## D. Project Activities

PMs schedule their work by creating rows in the **Project Activities** List — one row per
activity. The sync automatically derives a two-tier Work Breakdown Structure
(Workstream → Work Package → activity) from the Workstream and WorkPackage text you enter.
**PMs never create WBS rows directly.** The derived WBS is what fills the **Key Project
Areas** panel on the Project Status Report page and the **Schedule & Milestones** page.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Activity name |
| **ProjectCode** | Text | Must exactly match an existing project code — see §J |
| **Workstream** | Text | Level-1 WBS grouping, e.g. `Platform` or `Clinical Trial Setup` |
| **WorkPackage** | Text | Level-2 grouping under the workstream, e.g. `Email delivery` |
| **StartPlanned** | Date | Planned start date |
| **FinishPlanned** | Date | Planned finish date; must be on or after StartPlanned |
| **Owner** | Person | M365 people picker — must resolve to a user in the person directory |
| **Department** | Choice | See allowed values below |
| **ActivityStatus** | Choice | See allowed values below; defaults to `Not started` if blank |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **StartActual** | Date | Actual start date; can be blank |
| **FinishActual** | Date | Required when `ActivityStatus = Done` — see §G |
| **PctComplete** | Number | 0–100; defaults to 0 if blank |

### Choice values — use exactly as shown

**ActivityStatus** (one of):
```
Not started
In progress
At risk
Done
Cancelled
```

**Department** (one of):
```
Clinical / Medical Affairs
Regulatory / Quality
R&D / Engineering
Operations / PMO
Finance / Procurement
Commercial / Marketing
IT / Data / Security
HR / People
```

### Read-only write-back columns

The sync populates these automatically — **do not edit them**:

| Column | Meaning |
|--------|---------|
| **ActivityCode** | Auto-minted code within the work package, e.g. `1.1-A1`, `1.1-A2`. Never changes after creation. |
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail when `SyncStatus = Error`; blank on success |

### Derived fields

**`duration_days`** is computed automatically as the inclusive count of working days
(Monday through Friday) between `StartPlanned` and `FinishPlanned`. You do not enter it;
the sync calls `working_days(StartPlanned, FinishPlanned)` on every insert or update.

**`ActivityCode`** is minted by the sync the first time the row is saved. The format is
`{work-package WBS code}-A{n}` (e.g. `1.1-A1`, `2.3-A4`). Once assigned it is immutable
— editing it by hand breaks the database link.

**WBS codes** (`1`, `1.1`, `2`, `2.1`, …) are assigned automatically. A new Workstream
name gets the next integer (`1`, `2`, …). A new WorkPackage under an existing Workstream
gets the next decimal child (`1.1`, `1.2`, …). Codes are append-only and never renumbered.

**Owning department** for a WBS node is taken from the `Department` of the first activity
filed under that workstream or work package and does not change afterward (first-write-wins);
to change it a PM would need to recreate the workstream or work-package grouping under a
new name.

### The two-tier WBS — grouping rules

Activities in the same **Workstream** roll up to the same Level-1 WBS node. Activities in
the same **Workstream + WorkPackage** roll up to the same Level-2 WBS node. Spelling is
the grouping key — entering `Platform` and `platform` creates two separate WBS nodes.
Copy-paste the Workstream and WorkPackage values from an existing row if you want the
new activity to join the same group.

### Re-parent rule — do not move an activity after sync

Once an activity has been synced (`SyncStatus = Synced`), **do not change its
`ProjectCode`, `Workstream`, or `WorkPackage`**. The sync rejects any such change with:

```
ProjectCode changed after sync - create a new row instead
```
or
```
Workstream/WorkPackage changed after sync - create a new row instead
```

To move an activity to a different work package: create a fresh row in the new location
and set the old row's `ActivityStatus` to `Cancelled`. This keeps the WBS rollup
consistent.

> **Note:** a rejected re-parent attempt leaves the existing activity unchanged in the
> database. If the old work package no longer has any active activities it will appear in
> Key Project Areas as `NOT STARTED` until the Cancelled activity drops it from the
> rollup — this is harmless and resolves itself on the next nightly refresh.

### What lights up in the reports

| Report section | What it shows |
|----------------|---------------|
| **Key Project Areas** | Each Workstream rolls up its activities: earliest planned start, latest planned finish, weighted % complete, and worst-case status |
| **Recent Accomplishments** | Activities with `ActivityStatus = Done` and `FinishActual` within the last **35 days** |
| **Upcoming Next Steps** | Open activities (not Done or Cancelled) with `FinishPlanned` from **7 days ago to 45 days ahead** |
| **Schedule & Milestones page** | Activities grouped by department and status; % complete, overdue, and on-time counts |

---

## E. Project Change Requests

PMs submit change requests by creating rows in the **Project Change Requests** List —
one row per CR per project. The sync validates each item, inserts or updates the
corresponding `pmbok.change_request` row, mints a sequential `CRCode` (`C-001`,
`C-002`, …) on first sync, and writes results back to the List item.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Short label for the change (auto-populated by SharePoint as item title) |
| **ProjectCode** | Text | Must exactly match an existing project code — see §J |
| **CRClass** | Choice | Severity class — see allowed values below |
| **ChangeType** | Choice | Type of change — see allowed values below; single value only |
| **Description** | Multi-line text | Full description of what is being changed |
| **Reason** | Multi-line text | Business justification for the change |

### Optional / workflow columns

| Column | Type | Notes |
|--------|------|-------|
| **RequestedDate** | Date | Date the request was raised; defaults to the item creation date if left blank |
| **RequestedBy** | Person | M365 people picker — the requestor; defaults to the item author if left blank |
| **AffectedArtifacts** | Multi-line text | Comma-separated list of impacted artifacts; defaults to `n/a` |
| **ImpactScope** | Multi-line text | Scope impact narrative; can be blank |
| **ImpactQuality** | Multi-line text | Quality impact narrative; can be blank |
| **ImpactScheduleDays** | Number | Estimated schedule impact in working days; defaults to `0` |
| **ImpactCost** | Number | Estimated cost impact; defaults to `0` |
| **IntakeID** | Text | Optional link to the originating intake submission |

### Approval columns

These columns are filled by the approver (Sponsor or PM) directly in the List UI:

| Column | Type | Notes |
|--------|------|-------|
| **Decision** | Choice | The approval gate — see allowed values below; defaults to `Pending` |
| **DecidedBy** | Person | M365 people picker — the person who made the decision |
| **DecidedDate** | Date | Date the decision was recorded |
| **ImplementationVerified** | Choice | `Yes` / `No` — set to `Yes` once the change is confirmed implemented |
| **LinkedArtifactsUpdated** | Choice | `Yes` / `No` — set to `Yes` once affected artifacts have been updated |
| **CRStatus** | Choice | Lifecycle status — see allowed values below; defaults to `Open` |

### Choice values — use exactly as shown

**CRClass** (one of):
```
A - Minor
B - Substantive
C - Controlling
Emergency / Safety
```

**ChangeType** (one of — single selection only):
```
Scope
Schedule
Cost
Quality
Compliance
```

**Decision** (one of):
```
Pending
Approved
Deferred
Rejected
```

**CRStatus** (one of):
```
Open
In Assessment
Implementing
Verified
Closed
Rejected
```

### The two-axis approval workflow

A change request has two independent but constrained axes:

- **Decision** is the approval gate. It answers "has this CR been decided?" The
  approver edits this column in the List UI.
- **CRStatus** is the lifecycle. It answers "where is this CR in the process?"

The sync enforces these coherence rules:

| Condition | Rule |
|-----------|------|
| `Decision` ≠ `Pending` | `DecidedBy` and `DecidedDate` must both be set |
| `Decision = Pending` | `DecidedDate` must be blank |
| `Decision = Rejected` | `CRStatus` must also be `Rejected` |
| `CRStatus ∈ {Verified, Closed}` | `Decision` must be `Approved` |
| `DecidedDate` set | Must be on or after `RequestedDate` |

A typical lifecycle: `Open` → `In Assessment` → `Implementing` (once Approved) →
`Verified` (once `ImplementationVerified = Yes`) → `Closed`.

### Soft-authority note

The sync does not block a decision by someone who is not the project Sponsor or PM,
but it records a note in `SyncMessage`:

```
DecidedBy <email> is not the project sponsor or PM — authority advisory only
```

The `SyncStatus` is still written as `Synced`. The audit trail records who decided.
To clear the advisory, the Sponsor or PM should re-enter themselves as `DecidedBy`.

### Audit trail

Every CR creation, decision change, and status change is recorded as an append-only
entry in `doc_mgmt.audit_trail_entry` (action codes `CR_CREATE`, `CR_DECISION`,
`CR_STATUS`). The before and after values are stored, so the full decision history
is preserved even if the List item is later edited. These entries are never deleted
by the sync.

### ProjectCode-change rule

Once a CR has been synced, **do not change its `ProjectCode`**. The sync rejects the
change with:

```
ProjectCode changed after sync - create a new row instead
```

Create a fresh row for the corrected project and set the original row's `CRStatus`
to `Closed`.

### Read-only write-back columns

The sync populates these automatically — **do not edit them**:

| Column | Meaning |
|--------|---------|
| **CRCode** | Auto-minted sequential code within the project, e.g. `C-001`, `C-002`. Never changes after creation. |
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail when `SyncStatus = Error`; blank (or soft-authority advisory) on success |

---

## F. Project Decisions

PMs record governance decisions by creating rows in the **Project Decisions** List —
one row per decision per project. The Title field is the decision statement itself.
The sync validates each item, inserts or updates the corresponding `pmbok.decision`
row, mints a sequential `DecisionCode` (`D-001`, `D-002`, …) on first sync, and
writes results back to the List item.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | The decision statement — state what was decided, not what was discussed |
| **ProjectCode** | Text | Must exactly match an existing project code — see §J |
| **Rationale** | Multi-line text | Why this decision was made |
| **DecidedBy** | Person | M365 people picker — must resolve to a user in the person directory |
| **DecidedDate** | Date | Date the decision was made |

### Read-only write-back columns

The sync populates these automatically — **do not edit them**:

| Column | Meaning |
|--------|---------|
| **DecisionCode** | Auto-minted sequential code within the project, e.g. `D-001`, `D-002`. Never changes after creation. |
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Error detail; blank on success |

### Audit trail

Project decisions are **not** individually written to `doc_mgmt.audit_trail_entry`
in this release — the append-only audit trail covers change-request transitions
(`CR_CREATE`, `CR_DECISION`, `CR_STATUS`) and status-report sign-off
(`STATUS_SIGNOFF`). The decision record itself (with `DecidedBy` and `DecidedDate`)
is the durable trail for decisions; richer decision auditing is a later-phase item.

### Common errors

| Error message | Fix |
|---------------|-----|
| `Missing: Rationale` | Enter the decision rationale |
| `Missing: DecidedBy` | Set the people picker |
| `DecidedBy <email> not in person directory` | Ask PMO to add that person, then reset Pending |
| `Missing: DecidedDate` | Enter the date the decision was made |
| `Unknown ProjectCode: THG-XX-999` | Correct the code — see §J |

---

## G. The Achieved milestone / Done activity and the 35-day accomplishment window

The same rule applies to both milestones and activities:

**Milestones** — when `MilestoneStatus` is set to `Achieved`:

1. **`ActualDate` is required.** If `ActualDate` is blank, the sync marks the item
   `Error: Achieved requires ActualDate (report hides it otherwise)`. Set the actual
   completion date and reset `SyncStatus` to `Pending`.

2. **The report only shows accomplishments within 35 days of today.** The DAX measure
   that populates the *Recent Accomplishments* section of the Project Status Report page
   filters `Milestone Status = "Achieved"` AND `Actual Date` within the last 35 days.
   Milestones achieved more than 35 days ago no longer appear in that section — they
   remain in the database and in the Schedule & Milestones page.

**Activities** — when `ActivityStatus` is set to `Done`:

1. **`FinishActual` is required.** If `FinishActual` is blank, the sync marks the item
   `Error: Done requires FinishActual (report hides it otherwise)`. Set the actual finish
   date and reset `SyncStatus` to `Pending`.

2. **The same 35-day window applies.** The *Recent Accomplishments* section filters
   `ActivityStatus = "Done"` AND `FinishActual` within the last 35 days. Done activities
   older than 35 days remain in the database and in the Schedule & Milestones page.

---

## H. The Error → fix → next-run-heals loop

When the sync encounters a validation problem or an unresolvable reference, it:

1. Sets `SyncStatus = Error` and `SyncMessage = <detail>` on the List item.
2. Prints the error to `logs\artifact_sync.log`.
3. Exits with code 1 (the log line reads `exit code 1`).

**To fix:** read `SyncMessage`, correct the data in the List item (edit the row in the
SharePoint UI), then set `SyncStatus` back to `Pending`. The next sync run (5:40 AM, or
a manual run) will pick up the corrected item and either sync it successfully or report a
new error.

You do not need to ask IT to re-run anything — just fix the row and reset `SyncStatus`.

### Common errors and fixes

| Error message | Fix |
|---------------|-----|
| `Missing: ProjectCode` | Enter the ProjectCode |
| `Unknown ProjectCode: THG-XX-999` | Correct the code — see §J |
| `Missing: Likelihood` / `Missing: Impact` | Select a value in the choice column |
| `Likelihood/Impact must be 1-5` | Choose a value between 1 and 5 |
| `Category not recognized: Weather` | Use one of the exact Category strings in §A |
| `Missing: RiskOwner` | Set the people picker |
| `RiskOwner <email> not in person directory` | Ask PMO to add that person, then reset Pending |
| `Achieved requires ActualDate` | Set ActualDate on the milestone, then reset Pending |
| `Duplicate report period for <code>: <date>` | Fix PeriodStart on one of the two rows |
| `SubmittedBy not in person directory` | Ask PMO to add that person, then reset Pending |
| `Missing: Workstream` / `Missing: WorkPackage` | Enter both text fields on the activity row |
| `ActivityStatus not recognized: <value>` | Use one of the exact ActivityStatus strings in §D |
| `Department not recognized: <value>` | Use one of the exact Department strings in §D |
| `Done requires FinishActual` | Set FinishActual on the activity, then reset Pending |
| `FinishPlanned must be on/after StartPlanned` | Correct the planned dates |
| `PctComplete must be 0-100` | Enter a number between 0 and 100 |
| `Workstream/WorkPackage changed after sync - create a new row instead` | Create a new activity row in the new location; set the old row to Cancelled |
| `Missing: Description` / `Missing: Reason` | Enter the required CR fields |
| `CRClass not recognized: <value>` | Use one of the exact CRClass strings in §E |
| `ChangeType not recognized: <value>` | Use one of the exact ChangeType strings in §E |
| `Decision set but DecidedBy is empty` | Set the DecidedBy people picker |
| `Decision set but DecidedDate is empty` | Enter the DecidedDate |
| `DecidedDate must be blank while Decision is Pending` | Clear DecidedDate — decisions cannot be pre-dated |
| `Rejected decision requires CRStatus = Rejected` | Set CRStatus to `Rejected` to match the decision |
| `CRStatus Verified requires Decision = Approved` | Set Decision to `Approved` before marking Verified |
| `DecidedDate must be on/after RequestedDate` | Correct one of the two dates |
| `DecidedBy <email> not in person directory` | Ask PMO to add that person, then reset Pending |
| `ApprovedBy set but ApprovedDate missing` | Enter both ApprovedBy and ApprovedDate, or clear both |
| `ApprovedDate set but ApprovedBy missing` | Enter both ApprovedBy and ApprovedDate, or clear both |

---

## I. Delete policy — never delete List rows to close a record

Deleting a SharePoint List row does **not** delete the corresponding database record.
The sync treats a missing List row as an **orphan** and logs:

```
INFO orphaned external_ref <kind>/<item_id>: List row deleted; DB row kept (system of record)
```

The database record remains and will continue to appear in the Power BI reports.

**To close a risk or milestone:** set its `RiskStatus` to `Closed` (or `Realized`) or
its `MilestoneStatus` to `Achieved` or `Slipped`. The sync updates the database row on
the next run.

**To retire an activity:** set its `ActivityStatus` to `Cancelled`. Do not delete the
List row — the database record and its WBS membership are preserved, and the activity
drops cleanly out of Next Steps and Key Project Areas rollups on the next refresh.

**To retract a status report:** there is no retract status — contact the PMO to correct
or remove the database record directly.

**Never delete and recreate a whole List.** SharePoint item ids restart at 1 in a new
List, and the sync matches rows to database records by item id — a recreated List's
first row would silently alias an old record. The Lists are permanent infrastructure.

---

## J. Where to find valid ProjectCodes

`ProjectCode` must exactly match a project code that already exists in PostgreSQL
(created by the intake sync). Two ways to look it up:

- **Project Intake List** — open the SharePoint List; find the project row; copy
  the value in the **ProjectCode** column.
- **Portfolio Overview** — open the Power BI report; the Portfolio Overview page lists
  every active project with its code.

ProjectCodes follow the pattern `THG-<DEPT>-<NNN>` (e.g. `THG-IT-001`). Capitalisation
and hyphens are significant — the sync does a case-sensitive match.

---

## K. Pipeline timing

| Time | Action |
|------|--------|
| 5:30 AM | `sync_intake.py` — new Project Intake items → PostgreSQL |
| 5:40 AM | `sync_artifacts.py` — Risk / Milestone / Status Report / **Project Activities** items → PostgreSQL; auto-creates WBS nodes |
| 6:00 AM | Power BI service scheduled refresh — picks up all overnight changes |
| Morning | Project Status Report and Portfolio Overview show current data |

The 10-minute gap between intake (5:30) and artifact sync (5:40) ensures that a project
created by a same-morning intake submission is available in PostgreSQL before the
artifact sync resolves ProjectCodes.

---

## L. Morning health check

Check `logs\artifact_sync.log` each morning to confirm there were no errors. The wrapper
brackets every run with a `---- <date> <time> ----` header and a final `exit code N`
line:

```
---- Fri 06/13/2026 05:40:02.34 ----
risk: 0 list item(s) fetched
milestone: 3 list item(s) fetched
  OK milestone item 12: no change
  OK milestone item 13: no change
  OK new milestone (Go-live, item 14)
report: 1 list item(s) fetched
  OK new report + 9 areas (THG-IT-001 2026-06-08, item 9)
activity: 4 list item(s) fetched
  OK new activity 1.1-A1 (Platform / Email delivery, item 5)
  OK activity item 6: no change
  OK activity item 7: no change
  OK activity item 8: no change
exit code 0
```

A successful run ends with `exit code 0`. Any item-level error exits with code 1 and
the relevant line contains `ERROR`. Because output lines are indented with two spaces,
use a non-anchored search:

```cmd
findstr "ERROR" logs\artifact_sync.log
```

> **Scheduled runs and exit codes:** Task Scheduler's "last run result" reflects the
> wrapper script, which forwards Python's exit code (`exit /b %errorlevel%`) — but the
> **log file is the primary diagnostic**: it records the exit code per run alongside the
> error lines, so always check `logs\artifact_sync.log` rather than relying solely on
> Task Scheduler's last-run status.

---

## M. Hard rules — never do these

> **NEVER run `tools/load_postgres.py --reseed` after go-live.**
>
> The `--reseed` flag drops and recreates all three database schemas (`doc_mgmt`,
> `pmbok`, `bi`). This destroys every live project intake record AND every synced
> artifact (risks, milestones, status reports, activities, and WBS nodes) that has
> accumulated since go-live. There is no undo. `load_postgres.py` is a bootstrap tool
> for initial setup only.
>
> If you need to correct database data after go-live, edit the List rows and let the
> sync heal them, or ask the PMO to make a targeted database correction.

---

## N. Project Baselines

PMs freeze an **immutable snapshot** of a project's Schedule, Budget, or Scope by creating
a row in the **Project Baselines** List — one row per baseline. The sync builds the snapshot
**automatically, server-side**, from the project's live tables at the moment of sync; the PM
never types snapshot content. A baseline answers the question *"what was the approved plan,
and what has changed since?"*

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Short label for the baseline (auto-populated by SharePoint as item title) |
| **ProjectCode** | Text | Must exactly match an existing project code — see §J |
| **BaselineType** | Choice | What is being frozen — see allowed values below |
| **BaselinedBy** | Person | M365 people picker — the person freezing the baseline; must resolve to the person directory |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **ChangeSummary** | Multi-line text | Why this baseline was taken (e.g. `re-baseline after approved scope change`); can be blank |
| **LinkedCRCode** | Text | Optional link to the change request that drove the re-baseline, e.g. `C-007` |

### Choice values — use exactly as shown

**BaselineType** (one of):
```
Schedule
Scope
Budget
```

### How the snapshot is built (you never type it)

The sync assembles the frozen JSONB snapshot from the project's live data:

- **Schedule** — every activity (code, name, planned start/finish, duration days), every
  milestone (name, baseline date), and the project's planned start/finish headline.
- **Budget** — the project's approved budget total plus every budget line (WBS code,
  category, amount, funding source).
- **Scope** — the charter business case and high-level in/out-of-scope text, plus the scope
  inclusions, exclusions, and acceptance criteria.

The snapshot is deterministic (stably sorted) so the same project state always freezes to the
same bytes.

### Immutability — a baseline is never rewritten

Once a baseline is synced it is **append-once**: the sync will never rebuild or overwrite its
frozen snapshot. To re-baseline after an approved change, **file a NEW baseline of the same
type** — do not edit the existing one. The new baseline:

1. Mints the next version (`1.0` → `2.0` → `3.0`, …) for that project + type.
2. Marks the prior `BASELINED` row of the same type as `SUPERSEDED` (kept as history, with a
   pointer to its successor).

Editing a substantive field on an already-synced baseline is **rejected** with a message like
`Baselines are immutable; create a new baseline to re-baseline`. The prior versions are
retained — nothing is deleted — so the full re-baseline history is preserved.

### Audit trail

Every baseline freeze writes an append-only entry to `doc_mgmt.audit_trail_entry`
(`BASELINE_CREATE`, plus `BASELINE_SUPERSEDE` on the row that was superseded). These entries
are never deleted by the sync.

### Read-only write-back columns

The sync populates these automatically — **do not edit them**:

| Column | Meaning |
|--------|---------|
| **BaselineVersion** | Auto-minted version for this project + type, e.g. `1.0`, `2.0`. Never changes after creation. |
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error or immutability-reject detail; blank on success |

---

## O. Project Phase Gates

PMs record a **lifecycle-phase handoff** by creating a row in the **Project Phase Gates**
List — one row per gate. A gate documents who signed off the move from one PMI process group
to the next, when, and why. The project's **current phase is read live** at sync time, so the
gate is evaluated against where the project actually is.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Short label for the gate (auto-populated by SharePoint as item title) |
| **ProjectCode** | Text | Must exactly match an existing project code — see §J |
| **TargetPhase** | Choice | The phase the project is moving to — see allowed values below |
| **GateDecision** | Choice | The gate outcome — see allowed values below; defaults to `Approved` |
| **ApprovedBy** | Person | M365 people picker — the person signing off the gate; must resolve to the person directory |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **DecidedDate** | Date | Date the gate decision was made |
| **GateNotes** | Multi-line text | Conditions, caveats, or review notes; can be blank |

### Choice values — use exactly as shown

**TargetPhase** (one of, in lifecycle order):
```
Initiating
Planning
Executing
Monitoring
Closing
```

**GateDecision** (one of):
```
Approved
Approved with conditions
Held
```

### Forward-only + Hold — how a gate is applied

The five lifecycle phases are ordered `Initiating → Planning → Executing → Monitoring →
Closing`. The gate's `from` phase is the project's current `lifecycle_phase` at sync time:

- **Approved / Approved with conditions, forward** (`TargetPhase` is *after* the current
  phase) → advances the project to the target phase, writes the gate log row, and audits it.
- **Held** → records the review **without advancing** the project (the `from` and `to` phase
  are the same); the project stays put.
- **Backward** (`TargetPhase` is *before* the current phase) → **rejected** with
  `Backward phase transition rejected`. Projects move forward only.
- **Same phase** (`TargetPhase` equals the current phase) on an Approved gate → no-op (no
  advance, no double-count).

A synced gate is **never re-applied** — the log row is the idempotency anchor, so re-running
the sync never double-advances a project. To correct a gate filed by mistake, contact the PMO.

### Audit trail

Every gate writes an append-only entry to `doc_mgmt.audit_trail_entry` (`PHASE_GATE` on an
advance, `PHASE_GATE_HOLD` on a Held decision), recording the from/to phases, the approver,
and the decision. These entries are never deleted by the sync.

### Read-only write-back columns

The sync populates these automatically — **do not edit them**:

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail (e.g. a rejected backward transition); blank on success |

---

## P. Change Impact Assessments

A department records the **impact a change request has on its area** by creating a row in the
**Change Impact Assessments** List — one row per department per CR. Each row is a *child* of an
existing change request: it names the parent CR by its code, and the sync attaches the assessment
to that CR. This is the per-department fan-out behind the impact roll-up on the Change Control page.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **ProjectCode** | Text | Must exactly match an existing project code — see §J; scopes the parent-CR lookup |
| **ParentCRCode** | Text | The code of the parent change request (e.g. `C-001`) — must already exist on that project (see §E) |
| **Department** | Choice | The assessing department — see allowed values below |
| **SubmittedBy** | Person | M365 people picker — the assessor; **falls back to the item author** if left blank, so the row always has a submitter |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **ScopeImpact** | Multi-line text | How the change affects this department's scope |
| **ScheduleImpactDays** | Number | Whole-number schedule delta in days; blank = none recorded |
| **CostImpact** | Number | Cost delta (two decimals); blank = none recorded |
| **QualityImpact** | Multi-line text | Quality / compliance impact |
| **SubmittedDate** | Date | Date of the assessment; **defaults to the item's created date** when blank |

### Choice values — use exactly as shown

**Department** (one of the eight Theragen departments):
```
Clinical / Medical Affairs
Regulatory / Quality
R&D / Engineering
Operations / PMO
Finance / Procurement
Commercial / Marketing
IT / Data / Security
HR / People
```

### Parent-CR link — how a child finds its parent

The sync resolves the parent change request by **(ProjectCode, ParentCRCode)** — CR codes are
unique *within a project*, so both are required. The parent CR is read live at sync time, so a CR
filed the same morning is available to its assessments in the same run (change requests sync before
impact assessments). If no CR matches, the row is rejected with
`Unknown ParentCRCode <code> for project <ProjectCode>`.

### Re-parent rule — do not move an assessment after sync

Once an assessment has synced, its parent CR is fixed. Editing `ProjectCode` or `ParentCRCode` to
point at a **different** CR is rejected with `Reparenting not allowed; create a new impact
assessment`. To assess a different CR, create a new row. (Editing the impact fields, department,
submitter, or date on the *same* CR is fine — those update in place.)

### No audit trail

An impact assessment is descriptive content attached to a CR, not a governance state transition, so
it is **not** written to `doc_mgmt.audit_trail_entry` (the same treatment as Project Decisions). The
parent CR's own decision/status changes are still audited (see §E).

### Read-only write-back columns

The sync populates these automatically — **do not edit them**:

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail (e.g. an unknown parent CR); blank on success |

---

## Q. Controlled Documents

The PMO registers a **controlled document** by creating a row in the **Controlled Documents** List —
one row per document. Documents are **org-wide** (not tied to a project): each carries a minted
**DocID** of the form `THG-{DEPT}-{TYPE}-NNN` (e.g. `THG-OPS-CHR-001`), where `{DEPT}` is the owning
department's code and `{TYPE}` is the document-type code.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **DocTypeCode** | Choice | The document type — one of the eight codes below; sets the `{TYPE}` segment of the DocID |
| **Title** | Text | Document title (the SharePoint item title) |
| **PrimaryDepartment** | Choice | The owning department (one of the eight); sets the `{DEPT}` segment of the DocID |
| **Owner** | Person | M365 people picker — the document owner; **falls back to the item author** if blank |

### Optional columns (smart defaults)

| Column | Type | Notes |
|--------|------|-------|
| **Subtitle** | Text | One-line subtitle |
| **Approver** | Person | Designated approver (may be blank) |
| **LifecyclePhase** | Choice | One of the nine document lifecycle phases; **defaults from the document type** when blank |
| **Status** | Choice | `DRAFT` / `REVIEW` / `BASELINE` / `AMENDED` / `RETIRED`; defaults to `DRAFT` |
| **ReviewCycle** | Choice | One of the six review cycles; **defaults from the document type** when blank |
| **Classification** | Choice | Public / Confidential – Internal / Confidential – Restricted / PHI – HIPAA (defaults to Confidential – Internal) |
| **StorageSystem** | Choice | PMO SharePoint / eQMS / eTMF / HIPAA-controlled store / ERP / HRIS / Other |
| **StoragePath** | Text | File path or URL; **defaults to `{StorageSystem}/{DocID}`** when blank |
| **NextReviewDue** | Date | Next periodic review date (drives the "Documents Due for Review" measure) |
| **IntakeID** | Text | Originating intake id, if any |

### Choice values

**DocTypeCode** (8): `CHR` Charter · `SOP` Standard Operating Procedure · `PLN` Plan · `SCP` Scope ·
`RPT` Report · `POL` Policy · `WI` Work Instruction · `FRM` Form.
**LifecyclePhase** (9): Initiating · Planning · Executing · Monitoring · Closing · Cross-Lifecycle ·
Intake · Governance · Reference.
**ReviewCycle** (6): Annual · Semi-Annual · Quarterly · Monthly · On Major Revision · On Phase Gate.

### The DocID and the immutable-identity rule

The sync mints the DocID per **(department, type)** family — the first OPS charter is
`THG-OPS-CHR-001`, the next `THG-OPS-CHR-002`, and so on; each family numbers independently. Because
**DocTypeCode and PrimaryDepartment define the DocID**, they are fixed once a document has synced:
editing either after sync is rejected with `DocTypeCode/PrimaryDepartment changed after sync - create
a new document instead`. Everything else (title, status, owner, dates, storage, …) edits in place.

### Status + audit

`Status` moves freely between the five values (no enforced ordering in v1). Every document writes an
append-only `doc_mgmt.audit_trail_entry` row: `DOCUMENT_CREATE` on first sync and `DOCUMENT_STATUS`
whenever the status changes. The document version (`current_version`, starts at `0.1`) is managed by
the version sync, not by this List.

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **DocID** | The minted `THG-{DEPT}-{TYPE}-NNN` identifier — set by the sync; do not edit |
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail; blank on success |

---

## R. Document RACI

The PMO records a document's **responsibility matrix** in the **Document RACI** List — one row per
(document, department, role). Each row attaches an effective-dated **R/A/C/I** role to a controlled
document for one department: who is **R**esponsible, **A**ccountable, **C**onsulted, or **I**nformed.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **ParentDocID** | Text | The `DocID` of the parent document (e.g. `THG-OPS-CHR-001`) — must already exist (see §Q) |
| **Department** | Choice | The department holding the role (one of the eight) |
| **Role** | Choice | `R` / `A` / `C` / `I` (Responsible / Accountable / Consulted / Informed) |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **Touchpoint** | Multi-line text | What the department does on this document (e.g. "Owns and approves the charter") |
| **ValidFrom** | Date | Effective-from date; **defaults to the item's created date** when blank |
| **ValidTo** | Date | Effective-to date; leave blank for an open-ended (still-current) assignment |

### Parent link + the no-reparent rule

The sync resolves the parent document by its globally-unique `DocID`; an unknown id is rejected with
`Unknown ParentDocID: <id>`. Once a row has synced, its **parent document is fixed**: editing
`ParentDocID` to point at a different document is rejected with `ParentDocID changed after sync -
create a new RACI assignment instead`. The Department, Role, Touchpoint, and dates all edit in place.

### Assignee is a department; no audit

RACI is recorded **per department**, not per person. A row is **descriptive assignment metadata**, so
— like Change Impact Assessments — it is **not** written to the audit trail. (RACI best practice is
exactly one **Accountable** per document; the system records the matrix as authored and does not
enforce that in v1.)

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail (e.g. an unknown parent document); blank on success |

---

## S. Document Versions

The PMO records a document's **version history** in the **Document Versions** List — one row per
version, a child of a controlled document (linked by `DocID`). It captures what changed, who authored
it, and the version's status.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **ParentDocID** | Text | The `DocID` of the parent document (e.g. `THG-OPS-CHR-001`) — must already exist (see §Q) |
| **Version** | Text | The version string (e.g. `1.0`, `1.1`) — PM-supplied |
| **ChangeSummary** | Multi-line text | What changed in this version |
| **Author** | Person | The author; **falls back to the item author** if blank |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **Status** | Choice | `DRAFT` / `REVIEW` / `BASELINE` / `AMENDED` / `RETIRED` (default DRAFT) |
| **ChangeClass** | Choice | `A - Minor` / `B - Substantive` / `C - Controlling` / `Emergency / Safety` |
| **EffectiveDate** | Date | When this version takes effect |
| **StoragePath** | Text | Versioned file path; **defaults to `{ParentDocID}/v{Version}`** |
| **LinkedCRCode** | Text | Optional governance change request (`CHG-NNN`, see §U) that drove this version. Must already exist; an unknown code is an error. Surfaced as the model's `Linked CR` column |

### Identity + audit

`(ParentDocID, Version)` is the version's identity — both are fixed after first sync; editing either is
rejected (`ParentDocID/Version changed after sync - create a new version instead`). `Status` moves
freely (DRAFT → … → BASELINE), with each create + status change written to the audit trail
(`VERSION_CREATE` / `VERSION_STATUS`). `LinkedCRCode` binds the version to the governance change request
that drove it (`document_version.linked_cr_id`); blank leaves it unlinked, a non-existent code is
rejected (`Unknown LinkedCRCode: <code>`).

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail; blank on success |

---

## T. Document Approvals — attestations (NOT 21 CFR Part 11 signatures)

> **Honesty note.** A row in this List records a **server-computed attestation**, not a true 21 CFR
> Part 11 electronic signature. The `esig_hash` is a SHA-256 over
> `doc_id | version | approver_email | meaning | signed_at`, computed by the nightly sync — it provides
> **traceability**, not signer-controlled cryptographic non-repudiation. No signer IP is captured
> (`ip_address` is null). The model and views label this **"Attestation (non-§11)"**. A real §11 signing
> ceremony (re-authentication, signer-held key, content binding, captured signer IP) is **deferred**.
> Do not represent these as §11 signatures.

A row attests that a person signed off a specific document **version**; it is a child of a version
(linked by `ParentDocID` + `ParentVersion`).

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **ParentDocID** | Text | The parent document's `DocID` |
| **ParentVersion** | Text | The version string (e.g. `1.0`) — with ParentDocID resolves the version |
| **Approver** | Person | The attesting person; **falls back to the item author** if blank |
| **SignatureMeaning** | Choice | `Approval` / `Review` / `Authorship` (default Approval) |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **Reason** | Multi-line text | Reason / context for the attestation |

### Server-derived (never typed)

| Field | How it is set |
|-------|---------------|
| **signed_at** | The item's created timestamp (truncated to the second) — the moment of attestation |
| **esig_hash** | The SHA-256 attestation hash (above), computed once and **frozen** |
| **ip_address** | **null** — no signer IP is captured |

### Immutability

An attestation is **append-once**: once synced, the row is frozen and the `esig_hash` is never
recomputed; List edits to a synced approval do not propagate (create a new approval to re-sign). Each
attestation is written to the audit trail (`APPROVAL_SIGN`). Because the hash is deterministic, a stored
attestation is **verifiable** by recomputing it from its row — read `signed_at` back **in UTC** and
canonicalize it the same way (`YYYY-MM-DDTHH:MM:SSZ`, whole seconds) before re-hashing.

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail (e.g. an unknown parent version); blank on success |

---

## U. Governance Change Requests

The PMO raises a controlled change against a **document** in the **Governance Change Requests** List —
one row per change request (`CHG-NNN`), a child of a controlled document (linked by `ParentDocID`).
Unlike a project change request (§E), a governance CR is **project-less** (there is no `ProjectCode`) and
targets a document. It reuses the **two-axis approval workflow** (`Decision` × `CRStatus`) from §E
verbatim.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **ParentDocID** | Text | The `DocID` of the target controlled document (e.g. `THG-IT-SOP-001`) — must already exist (see §Q) |
| **Description** | Multi-line text | The proposed change |
| **Reason** | Multi-line text | The driver for the change |
| **CRClass** | Choice | `A - Minor` / `B - Substantive` / `C - Controlling` / `Emergency / Safety` |
| **RequestedBy** | Person | The requester; **falls back to the item author** if blank |

### Optional / workflow columns

| Column | Type | Notes |
|--------|------|-------|
| **RequestedDate** | Date | Defaults to the item's created date when blank |
| **IntakeID** | Text | Optional originating intake reference |
| **Decision** | Choice | `Pending` (default) / `Approved` / `Deferred` / `Rejected` |
| **CRStatus** | Choice | `Open` (default) / `In Assessment` / `Implementing` / `Verified` / `Closed` / `Rejected` |
| **DecidedBy** | Person | The approver — required once `Decision ≠ Pending` |
| **DecidedDate** | Date | The decision date — required once `Decision ≠ Pending` |
| **ImplementationVerified** | Choice | `Yes` / `No` (default No) |

### The two-axis workflow + coherence

Identical to §E: `Decision` is the approval gate; `CRStatus` is the lifecycle. `Decision ≠ Pending`
requires `DecidedBy` + `DecidedDate`; `Pending` requires a blank `DecidedDate`; `Rejected` decision
requires `CRStatus = Rejected`; `CRStatus ∈ {Verified, Closed}` requires `Decision = Approved`;
`DecidedDate ≥ RequestedDate`. Violations are errors; no DB change.

### Soft-authority note (document-scoped)

Anyone may record a decision, but if the decider is **neither the target document's Owner nor its
Approver**, the row still syncs with an advisory in `SyncMessage` (the audit trail records the actual
decider). This is the document-scoped analog of the §E Sponsor/PM check. Hard role enforcement is
deferred.

### Identity + audit

`CHG-NNN` is minted globally (the code is unique across all governance CRs, not per document). The target
document is fixed after first sync — editing `ParentDocID` is rejected
(`ParentDocID changed after sync - create a new governance change request instead`). Create + each
decision/status change is written to the audit trail (`GOVCR_CREATE` / `GOVCR_DECISION` / `GOVCR_STATUS`).

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **CRCode** | The minted `CHG-NNN` (written back on first sync) |
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Advisory (soft-authority) or error detail; blank on a clean success |

---

## V. Governance Change Assessments

Each department records its **impact statement** on a governance CR in the **Governance Change
Assessments** List — one row per department per CR, a child of a governance CR (linked by `ParentCRCode`).
This mirrors §P (Change Impact Assessments) but is **department-scoped** (no person) and attaches to a
governance CR by its global `CHG-NNN` code.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **ParentCRCode** | Text | The governance CR's `CHG-NNN` (globally unique, see §U) — must already exist |
| **Department** | Choice | One of the 8 Theragen departments |
| **ImpactSummary** | Multi-line text | The department's impact statement |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **ComplianceImpact** | Multi-line text | Compliance / regulatory impact, if any |
| **SubmittedDate** | Date | Defaults to the item's created date when blank |

### Re-parent rule + audit

The parent governance CR is fixed after first sync — editing `ParentCRCode` to point at a different CR is
rejected (`ParentCRCode changed after sync - create a new governance assessment instead`). Department,
impact, and compliance text are freely editable. Like §P, an assessment is **descriptive content** — no
audit-trail entry is written (only governance *state transitions* are audited).

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail (e.g. an unknown `ParentCRCode`); blank on success |

---

## X. Risk Responses

Each risk's **response plan** — the concrete action items implementing it — is authored in the **Risk
Responses** List → `pmbok.risk_response`, a child of a risk (linked by `ParentRiskCode`). This is
distinct from the risk's own **ResponseType** (§A: the *strategy* — Mitigate / Accept / Avoid /
Transfer); a Risk Response row is a tracked *action* with an owner, a due date, and a status.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **ProjectCode** | Text | Scopes the parent-risk lookup (`RiskCode` is unique per project) |
| **ParentRiskCode** | Text | The parent risk's `RiskCode` (e.g. `R-001`) — must already exist (see §A) |
| **ActionType** | Choice | `Mitigation` / `Transfer` / `Acceptance` / `Avoidance` |
| **Description** | Multi-line text | What the action is |
| **Owner** | Person | The action owner; **falls back to the item author** if blank |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **DueDate** | Date | Target date (open-ended when blank) |
| **Status** | Choice | `Open` (default) / `In progress` / `Blocked` / `Done` |

### Re-parent rule

The parent risk is fixed after first sync — editing `ProjectCode`/`ParentRiskCode` to point at a
different risk is rejected (`Reparenting not allowed; create a new risk response`). Action type, owner,
due date, and status are freely editable. No audit-trail entry is written (a response action is
descriptive content, like §P / §R). Resolution: `SELECT risk_id FROM pmbok.risk WHERE
project_id = ? AND risk_code = ?`.

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail (e.g. an unknown `ParentRiskCode`); blank on success |

---

## Y. Cost Actuals (EVM)

Actual cost is logged per **work package** per **period** in the **Cost Actuals** List →
`pmbok.cost_actual`, a child of a WBS element (linked by `WBSCode`). This is the **actual-cost (AC)**
feed that completes Earned Value Management: BAC / EV / PV / SPI already derive from WBS estimates +
activity % complete; the cost actuals supply **AC**, which lights up `Cost Variance (CV)`, `CPI`, `EAC`,
`VAC`, and `TCPI`.

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **ProjectCode** | Text | Scopes the WBS lookup (`WBSCode` is unique per project) |
| **WBSCode** | Text | The work-package WBS code (e.g. `1.1`) — must already exist (it is derived from the project's activities, see §D) |
| **Period** | Date | The period the cost was incurred (e.g. a month-end) |
| **Amount** | Number | The actual cost in that period (a number; 0 is allowed) |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **Category** | Choice | `Labor` / `Materials` / `Services` / `Other` |
| **Notes** | Multi-line text | Free text |
| **EnteredBy** | Person | Who logged it; **falls back to the item author** if blank |

### Grain + rules

One row per (work package, period[, category]) — the sync sums them into the cumulative **AC**. The
parent WBS element is fixed after first sync (editing `ProjectCode`/`WBSCode` is rejected:
`Reparenting not allowed; create a new cost actual`); amount, period, category, and notes are freely
editable. No audit-trail entry (actuals are descriptive content). `AC = SUM(Amount)` cumulative;
`CPI = EV / AC`; `EAC = BAC / CPI`; `CV = EV − AC`; `VAC = BAC − EAC`; `TCPI = (BAC − EV) / (BAC − AC)`.

### Read-only write-back columns

| Column | Meaning |
|--------|---------|
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §H) |
| **SyncMessage** | Human-readable error detail (e.g. an unknown `WBSCode`); blank on success |

---

## W. Governance health digest

`tools/governance_health.py` is a **read-only** exceptions report that surfaces the governance items
needing human action — so the framework drives work, not just records it. It complements the §L morning
sync-log check: §L confirms the *pipeline* ran; this confirms the *governance* is being kept up.

Run it any time (it only `SELECT`s):

```cmd
python tools\governance_health.py
```

It prints one section per check; an empty check shows `[ OK ]`, a populated one shows a count + a table:

| Check | Flags |
|-------|-------|
| Documents overdue for review | `next_review_due` is in the past and the document is not RETIRED |
| Documents with no Accountable | no current `A` RACI assignment (a §R governance gap) |
| Baselined versions with no attestation | a `BASELINE` version (§S) with no sign-off attestation (§T) |
| Governance CRs approved but not verified | Approved ≥ 30 days with `Implementation Verified = No` and not yet Verified/Closed |
| Governance CRs pending too long | a `Pending` decision older than 14 days |
| Project CRs approved but not verified | the §E equivalent for project change requests |
| Status reports (recent period) unsigned | a closed-period report from the last 90 days with no sign-off (§C) |

Thresholds (`PENDING_CR_DAYS`, `APPROVED_UNVERIFIED_DAYS`, `RECENT_REPORT_DAYS`, `MAX_ROWS`) are
constants at the top of the script. To **schedule a daily snapshot**, register
`tools\run_governance_health.cmd` in Task Scheduler (it appends the digest to
`logs\governance_health.log`, exactly like the sync wrappers). To **e-mail it**, pipe the script's
stdout into your mail step — it is plain text and self-contained.

---

## Appendix — sync behaviour reference

| Scenario | sync_artifacts.py behaviour |
|----------|------------------------------|
| New item, all fields valid, project/person resolved | Inserts row; mints RiskCode (risks only); writes `Synced` + code back to List |
| New status report, valid, fans out | Inserts 1 parent + 9 area rows atomically; writes `Synced` back |
| New activity, valid | Ensures L1 + L2 WBS nodes exist (creates if new); mints ActivityCode; inserts row; writes `Synced` + ActivityCode back to List |
| New item, validation error | Writes `Error` + message to List; exits code 1 |
| New item, unknown ProjectCode | Writes `Error: Unknown ProjectCode: <code>` |
| New item, person not in directory | Writes `Error: <field> not in person directory` |
| Duplicate status report period | Writes `Error: Duplicate report period` |
| Existing item, data changed | Updates DB row; heals write-back; writes `Synced` |
| Existing item, ProjectCode changed | Writes `Error: ProjectCode changed after sync - create a new row instead` |
| Activity, Workstream/WorkPackage changed | Writes `Error: Workstream/WorkPackage changed after sync - create a new row instead` |
| Existing item, no data change, write-back lost | Heals write-back only; no DB change |
| Existing item, no change, write-back intact | Skips; no DB or List writes |
| List row deleted (orphan) | Logs `INFO orphaned external_ref`; DB row kept; exits 0 |
| New change request, valid, Pending | Mints `C-NNN`; inserts row; writes `CR_CREATE` audit entry; writes `Synced` + CRCode back to List |
| New change request, Decision ≠ Pending | Same as above plus soft-authority check; if decider is not Sponsor or PM, writes advisory to SyncMessage |
| CR Decision or CRStatus changed | Updates DB row; writes `CR_DECISION` and/or `CR_STATUS` audit entries inside the transaction; heals write-back |
| CR cross-axis coherence violation | Writes `Error` + message; no DB change |
| CR, ProjectCode changed after sync | Writes `Error: ProjectCode changed after sync - create a new row instead` |
| New decision, valid | Mints `D-NNN`; inserts row; writes `Synced` + DecisionCode back to List |
| Status report, ApprovedBy + ApprovedDate set | Sets `is_signed_off = true`; writes `STATUS_SIGNOFF` audit entry; `SyncStatus = Synced` |
| Status report, sign-off fields partially set | Writes `Error: ApprovedBy/ApprovedDate must both be set or both blank` |
| New impact assessment, valid | Resolves parent CR by (ProjectCode, ParentCRCode); inserts row; writes `Synced` back (no code minted) |
| Impact assessment, unknown ParentCRCode | Writes `Error: Unknown ParentCRCode <code> for project <code>` |
| Impact assessment, fields changed (same CR) | Updates DB row; heals write-back; writes `Synced` |
| Impact assessment, re-parented after sync | Writes `Error: Reparenting not allowed; create a new impact assessment` |
| New document, valid | Mints `THG-{DEPT}-{TYPE}-NNN` per (dept,type); inserts row; writes `DOCUMENT_CREATE` audit; writes `Synced` + DocID back |
| Document, unknown DocTypeCode / PrimaryDepartment | Writes `Error: Unknown DocTypeCode/PrimaryDepartment` |
| Document, status (or other field) changed | Updates DB row; writes `DOCUMENT_STATUS` audit on a status change; heals write-back |
| Document, DocTypeCode/PrimaryDepartment changed after sync | Writes `Error: ...changed after sync - create a new document instead` |
| New RACI assignment, valid | Resolves the parent document by DocID + the department; inserts row; writes `Synced` back (no code) |
| RACI, unknown ParentDocID / Department | Writes `Error: Unknown ParentDocID/Department` |
| RACI, fields changed (same document) | Updates DB row; heals write-back; writes `Synced` |
| RACI, re-parented after sync | Writes `Error: ParentDocID changed after sync - create a new RACI assignment instead` |
| New document version, valid | Resolves the parent document + author; inserts row; writes `VERSION_CREATE` audit; writes `Synced` back |
| Version, status changed | Updates DB row; writes `VERSION_STATUS` audit; heals write-back |
| Version, ParentDocID/Version changed after sync | Writes `Error: ...create a new version instead` |
| New approval (attestation), valid | Resolves document→version→approver; computes + freezes the `esig_hash`; writes `APPROVAL_SIGN` audit; writes `Synced` |
| Approval, unknown ParentVersion | Writes `Error: Unknown ParentVersion <v> for <DocID>` |
| Approval, already synced (immutable) | No-op; the attestation is frozen (create a new approval to re-sign) |
| Version with LinkedCRCode | Resolves the governance CR by `CHG-NNN`; sets `linked_cr_id`; unknown code → `Error: Unknown LinkedCRCode: <code>` |
| New governance CR, valid, Pending | Mints `CHG-NNN` (global); resolves the parent document; inserts row; writes `GOVCR_CREATE` audit; writes `Synced` + CRCode back |
| Governance CR, Decision ≠ Pending | Same plus the doc Owner/Approver soft-authority check; advisory to SyncMessage if the decider is neither |
| Governance CR Decision/CRStatus changed | Updates DB row; writes `GOVCR_DECISION` and/or `GOVCR_STATUS` audit; heals write-back |
| Governance CR, cross-axis coherence violation | Writes `Error` + message; no DB change |
| Governance CR, ParentDocID changed after sync | Writes `Error: ParentDocID changed after sync - create a new governance change request instead` |
| New governance assessment, valid | Resolves the parent gov CR by `CHG-NNN` + the department; inserts row; writes `Synced` back (no code, no audit) |
| Governance assessment, unknown ParentCRCode / Department | Writes `Error: Unknown ParentCRCode/Department` |
| Governance assessment, re-parented after sync | Writes `Error: ParentCRCode changed after sync - create a new governance assessment instead` |
| New risk response, valid | Resolves the parent risk by (ProjectCode, ParentRiskCode) + the owner; inserts row; writes `Synced` back (no code, no audit) |
| Risk response, unknown ParentRiskCode | Writes `Error: Unknown ParentRiskCode <code> for project <code>` |
| Risk response, re-parented after sync | Writes `Error: Reparenting not allowed; create a new risk response` |
| New cost actual, valid | Resolves the WBS work package by (ProjectCode, WBSCode); inserts row; writes `Synced` back (no code, no audit) |
| Cost actual, unknown WBSCode | Writes `Error: Unknown WBSCode <code> for project <code>` |
| Cost actual, re-parented after sync | Writes `Error: Reparenting not allowed; create a new cost actual` |
| `--dry-run` flag | Prints intent only; no DB writes; no List writes |
