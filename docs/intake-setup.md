# Intake Setup — Form, Flow, Schedule

This is the click-by-click recipe for wiring Microsoft Forms → Power Automate → the
**Project Intake** SharePoint List, and for scheduling the daily 5:30 AM
`tools/sync_intake.py` run on Allen's PC.

**Prerequisites:** The SharePoint List already exists (created by `tools/create_intake_list.py`
in Task 4). Do not re-run the creator script.

---

## Before you start

Sign in to Forms, Power Automate, and SharePoint as **ai@theragen.com** — the same account
that owns the SharePoint site and ran `create_intake_list.py`. Using a different account
will cause permission errors when the Flow tries to write to the list.

Confirm the account is licensed for:
- **Microsoft Forms** — included in M365 E3/E5 and most business plans.
- **Power Automate** with the **Office 365 Users** connector — this is a standard
  (non-premium) connector included in M365 E3/E5 seeded plans. No separate Power Automate
  per-user licence is required for this Flow.

---

## A. Microsoft Form (~10 min)

Go to [forms.office.com](https://forms.office.com) → **New Form**.

**Form title:** `Theragen Project Intake`

### Sharing settings

Settings (gear icon) → **Only people in my organization can respond** → enable
**Record name** (this is how the form captures the submitter's identity) → Save.

### Questions — create in this exact order

The question **name** in the Form UI must match the column name used in the Flow mapping
(Section B). Do not rename questions after the Flow is connected.

| # | Question text | Type | Notes |
|---|---|---|---|
| 1 | Request title | Text (Short answer) | Required |
| 2 | Request type | Choice | Required. See choices below. |
| 3 | Requesting department | Choice | Required. See choices below. |
| 4 | Business problem | Text | Long answer. Required. |
| 5 | Desired outcome / business value | Text | Long answer. Required. |
| 6 | Sponsor — full name | Text | Short answer. Required. |
| 7 | Project manager — full name | Text | Short answer. Required. |
| 8 | Planned start | Date | Required. |
| 9 | Planned finish | Date | Required. |
| 10 | Estimated budget USD | Number | Optional. |
| 11 | Effort | Choice | Required. See choices below. |
| 12 | PHI involved? | Choice | Yes / No. Required. |
| 13 | 21 CFR Part 11? | Choice | Yes / No. Required. |
| 14 | Clinical / study? | Choice | Yes / No. Required. |
| 15 | Vendor involved? | Choice | Yes / No. Required. |
| 16 | External data sharing? | Choice | Yes / No. Required. |
| 17 | Strategic objective ref | Text | Short answer. Optional. |

### Choice values — use EXACTLY as shown

**Request type (Q2)** — these are the exact values in the SharePoint List column:

```
Project / Initiative
Clinical or study request
Cross-dept work request
System change
Vendor / procurement
Other
```

**Requesting department (Q3)** — these are the exact values in the SharePoint List column
and in the `doc_mgmt.department.name` column in PostgreSQL:

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

> **Warning — exact match required:** `sync_intake.py` looks up the department by name
> with `WHERE name = %s`. Any spelling or spacing difference between the form answer and
> the List choice (and the database row) will cause the sync to write `SyncStatus = Error`
> on that item. The three sources (Form choices, List column choices, `department.csv`) are
> already aligned — do not alter these strings.

**Effort (Q11)** — these are the exact values in the SharePoint List column:

```
Small (<4 wk)
Medium (1-3 mo)
Large (3-12 mo)
Program (>12 mo)
```

**Yes/No questions (Q12–Q16)** — for each of the five flag questions, add exactly two
choices: `Yes` and `No`. The Flow maps these with `equals(<answer>, 'Yes')` to produce
booleans in the List.

---

## B. Power Automate flow (~10 min)

Go to [make.powerautomate.com](https://make.powerautomate.com) → **Create** →
**Automated cloud flow**.

**Flow name:** `Theragen Project Intake — to SharePoint`

**Trigger:** search for and select **When a new response is submitted**
(Microsoft Forms connector). Select form: **Theragen Project Intake**.

### Steps

#### Step 1 — Get response details

Action: **Microsoft Forms — Get response details**
- Form Id: same form
- Response Id: `List of response notifications Response Id` (dynamic content from trigger)

#### Step 2 — Resolve Sponsor to a user account

Action: **Office 365 Users — Search for users (V2)**
- Rename this action to `Search_sponsor` — click the action card's `...` (ellipsis) menu
  → **Rename**. Expressions reference the action by this name with spaces converted to
  underscores (e.g. `body('Search_sponsor')`), so the exact name matters.
- Search term: dynamic content → **Sponsor — full name** (Q6 answer)
- Top: `1`

#### Step 3 — Resolve Project Manager to a user account

Action: **Office 365 Users — Search for users (V2)**
- Rename this action to `Search_pm` — same method: `...` menu → **Rename**.
- Search term: dynamic content → **Project manager — full name** (Q7 answer)
- Top: `1`

#### Step 4 — Create SharePoint item

Action: **SharePoint — Create item**
- **Site address:** the URL shown in your browser when you open the SharePoint site
  (e.g. `https://neurotechus.sharepoint.com`). This is the root tenant URL —
  **not** the Graph site id stored in `db/.m365.local.json`.
- **List name:** `Project Intake`

Map the fields as follows:

| List column | Value |
|---|---|
| Title | Q1 — Request title answer |
| RequestType | Q2 — Request type answer |
| Department | Q3 — Requesting department answer |
| BusinessProblem | Q4 — Business problem answer |
| DesiredOutcome | Q5 — Desired outcome answer |
| PlannedStart | Q8 — Planned start answer |
| PlannedFinish | Q9 — Planned finish answer |
| EstimatedBudget | Q10 — Estimated budget answer |
| EffortBucket | Q11 — Effort answer |
| Sponsor — Claims field | `first(body('Search_sponsor')?['value'])?['UserPrincipalName']` |
| ProjectManager — Claims field | `first(body('Search_pm')?['value'])?['UserPrincipalName']` |
| PHIFlag | `equals(outputs('Get_response_details')?['body/r<ID>'], 'Yes')` |
| CFR11Flag | `equals(outputs('Get_response_details')?['body/r<ID>'], 'Yes')` |
| ClinicalFlag | `equals(outputs('Get_response_details')?['body/r<ID>'], 'Yes')` |
| VendorFlag | `equals(outputs('Get_response_details')?['body/r<ID>'], 'Yes')` |
| DataSharingFlag | `equals(outputs('Get_response_details')?['body/r<ID>'], 'Yes')` |
| StrategicObjective | Q17 — Strategic objective answer |

Replace `<ID>` in the flag expressions with the actual response field token that Power
Automate generates for each question. Use the expression editor to switch from the
default text picker to expression mode, or use the dynamic content panel to insert the
answer and then wrap it in `equals(..., 'Yes')`.

Leave **TriageStatus** and **SyncStatus** at their column defaults (`Submitted` and
`Pending`). Do not map IntakeID, ProjectCode, or SyncMessage — the sync script writes
those.

> **Person column inputs:** Each person column (Sponsor, ProjectManager) shows two inputs
> in the Create item action: a display-name/people-picker field and a **Claims** sub-field.
> The Claims sub-field may be hidden — click **Show advanced options** to reveal it.
> The `first(body('Search_sponsor')?['value'])?['UserPrincipalName']` expression must go
> in the **Claims** field, not the display-name picker. Entering it in the wrong field
> causes a type mismatch at runtime and the Flow run fails.

### Person-field behaviour

If a people search returns no results (name not found in the directory), the Sponsor or
ProjectManager column on the List item is left empty. The next sync run will mark that
item `SyncStatus = Error` with a message like
`Sponsor <email> not in person directory` or `PM <email> not in person directory`
(the code uses `PM` for the project manager prefix, not `ProjectManager`).
The PMO fixes the people picker by hand and resets `SyncStatus` to `Pending` to trigger
a re-sync. This is intentional: it acts as a data-quality gate before the record enters
PostgreSQL.

---

## C. Daily sync schedule

The sync runs as Allen's Windows account at 5:30 AM daily. Task Scheduler discards
stdout by default, so the command wraps the Python call in `cmd /c` and redirects all
output to a log file.

### One-time: create the logs folder

Run once in the repo root (PowerShell or cmd.exe):

```powershell
mkdir logs
```

This folder is gitignored. It must exist before the scheduled task runs for the first time.

### Register the scheduled task

Run the following in **cmd.exe** (not PowerShell — schtasks /TR quoting works differently
there). Replace `<REPO>` with the full path to your local repository, e.g.
`C:\Users\Allen\OneDrive - Neurotech NA\Documents\GitHub\Theragen-Project-Planer-BI`.

```cmd
schtasks /Create /TN "Theragen\SyncIntake" /TR "cmd /c \"\"C:\Python314\python.exe\" \"<REPO>\tools\sync_intake.py\" >> \"<REPO>\logs\intake_sync.log\" 2>&1\"" /SC DAILY /ST 05:30 /RL LIMITED /F
```

> **Note on quoting:** The outer `"cmd /c \"..."\"` pattern is required so that
> `schtasks` passes the redirect operator (`>>`) and `2>&1` to `cmd.exe` rather than
> interpreting them itself. The inner executable paths must be double-quoted if they
> contain spaces (the OneDrive path does).

After creating the task, open **Task Scheduler** → `Theragen` folder → `SyncIntake` →
Properties → **Settings** tab → check **Run task as soon as possible after a scheduled
start is missed**. This ensures the sync catches up if the PC was off at 5:30 AM.

### Enable the task

The `/F` flag above overwrites any existing task with the same name. To verify it is
enabled:

```cmd
schtasks /Query /TN "Theragen\SyncIntake" /FO LIST
```

`Status` should show `Ready`.

### Pipeline timing

| Time | Action |
|---|---|
| 5:30 AM | sync_intake.py runs — new List items → PostgreSQL |
| 6:00 AM | Power BI service scheduled refresh — picks up new data |
| Morning | Portfolio Overview shows new Proposed projects |

### Morning health check

Review `logs\intake_sync.log` each morning (or after a manual run) to confirm there were
no errors. A successful run ends with exit code 0; any item-level error exits with code 1
and the relevant line contains `ERROR item <id>:` (each result line is printed with a
two-space indent, so the log line reads `  ERROR item <id>: …`). Because of the indent,
`grep "^ERROR"` finds nothing — use a non-anchored search instead:

```cmd
findstr "ERROR" logs\intake_sync.log
```

or on Linux/macOS:

```sh
grep ERROR logs/intake_sync.log
```

> **Scheduled runs and exit codes:** Task Scheduler's "last run result" reflects the
> `cmd /c` wrapper, not Python's exit code directly. Python's exit code 1 is only clearly
> visible on manual runs. For scheduled runs the **log file is the primary diagnostic** —
> always check `logs\intake_sync.log` rather than relying solely on Task Scheduler's
> last-run status.

To trigger a manual refresh of the semantic model outside the 6:00 AM schedule:

```powershell
python tools/service_refresh.py
```

(Running `service_refresh.py` also rebinds the PostgreSQL credentials and re-applies the
nightly schedule — it is harmless to re-run at any time.)

---

## D. End-to-end smoke test

Follow these steps after the Form, Flow, and schedule are all wired up.

1. **Submit the form** — go to the form's fill URL (Share → Copy link), submit a test
   entry with a known sponsor and PM (both must be in the M365 directory and in
   `doc_mgmt.person`).

2. **Verify the List row** — open the **Project Intake** list in SharePoint. A new item
   should appear within a minute with `TriageStatus = Submitted`, `SyncStatus = Pending`,
   and the Sponsor / ProjectManager people pickers resolved.

3. **Dry-run the sync** — in a terminal in the repo root:

   ```powershell
   python tools/sync_intake.py --dry-run
   ```

   You should see a line like:
   `DRY item <id>: would create INT-2026-0001 / THG-CLN-001 (<title>)`

4. **Real sync run** — run without `--dry-run`:

   ```powershell
   python tools/sync_intake.py
   ```

   The List row should update: `SyncStatus = Synced`, `IntakeID` and `ProjectCode`
   populated.

5. **Trigger a model refresh** (or wait for the 6:00 AM schedule):

   ```powershell
   python tools/service_refresh.py
   ```

6. **Confirm in Portfolio Overview** — open the Power BI report. The new submission
   should appear in the Portfolio Overview page as a **Proposed** project.

7. **Clean up the test item** — in the **Project Intake** SharePoint List, set the test
   item's `TriageStatus` to **Rejected**. Then re-run the sync (or wait for the 5:30 AM
   scheduled run):

   ```powershell
   python tools/sync_intake.py
   ```

   The test project's status flips to `Cancelled` in PostgreSQL and it drops out of the
   Proposed portfolio view on the next model refresh. Do not delete rows directly from
   the database — use `TriageStatus` in the List as the authoritative signal.

---

## Appendix — sync behaviour reference

| Scenario | sync_intake.py behaviour |
|---|---|
| New item, all fields valid, people resolved | Creates intake + Proposed project + charter in PG; writes IntakeID / ProjectCode / Synced to List |
| New item, validation error or unknown department | Writes `SyncStatus = Error` + message to List; exits with code 1 |
| New item, person email resolves but not in `doc_mgmt.person` | Same error path; PMO must add person then reset SyncStatus to Pending |
| Existing item, TriageStatus changed (Approved / Rejected / On Hold) | Updates `pmbok.project.status`; writes Synced back |
| Existing item, status already correct but write-back was lost | Heals the List fields; no DB change |
| Run with `--dry-run` | Prints intent; no DB writes; no List writes |
| Sync is idempotent | Re-running after a successful sync is safe; already-Synced items are skipped |
