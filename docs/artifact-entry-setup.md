# Artifact Entry Setup — Risks, Milestones, Status Reports, Project Activities

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

All four Lists live on the root SharePoint site (same site as Project Intake).

---

## A. Project Risks

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Short label for the risk (auto-populated by SharePoint as item title) |
| **ProjectCode** | Text | Must exactly match an existing project code — see §H |
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
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §F) |
| **SyncMessage** | Human-readable error detail when `SyncStatus = Error`; blank on success |

---

## B. Project Milestones

### Required columns

| Column | Type | Notes |
|--------|------|-------|
| **Title** | Text | Milestone name |
| **ProjectCode** | Text | Must exactly match an existing project code — see §H |
| **BaselineDate** | Date | Original planned completion date |
| **OwnerRole** | Choice | Role responsible for delivery |

### Optional columns

| Column | Type | Notes |
|--------|------|-------|
| **ForecastDate** | Date | Updated forecast; can be blank |
| **ActualDate** | Date | Required when `MilestoneStatus = Achieved` — see §E |
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
| **ProjectCode** | Text | Must exactly match an existing project code — see §H |
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
| **ProjectCode** | Text | Must exactly match an existing project code — see §H |
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
| **FinishActual** | Date | Required when `ActivityStatus = Done` — see §E |
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
| **SyncStatus** | `Pending` → `Synced` (success) or `Error` (see §F) |
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

## E. The Achieved milestone / Done activity and the 35-day accomplishment window

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

## F. The Error → fix → next-run-heals loop

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
| `Unknown ProjectCode: THG-XX-999` | Correct the code — see §H |
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

---

## G. Delete policy — never delete List rows to close a record

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

## H. Where to find valid ProjectCodes

`ProjectCode` must exactly match a project code that already exists in PostgreSQL
(created by the intake sync). Two ways to look it up:

- **Project Intake List** — open the SharePoint List; find the project row; copy
  the value in the **ProjectCode** column.
- **Portfolio Overview** — open the Power BI report; the Portfolio Overview page lists
  every active project with its code.

ProjectCodes follow the pattern `THG-<DEPT>-<NNN>` (e.g. `THG-IT-001`). Capitalisation
and hyphens are significant — the sync does a case-sensitive match.

---

## I. Pipeline timing

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

## J. Morning health check

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

## K. Hard rules — never do these

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
| `--dry-run` flag | Prints intent only; no DB writes; no List writes |
