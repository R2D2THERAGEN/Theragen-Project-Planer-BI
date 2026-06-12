# Project Ingestion — Design

**Date:** 2026-06-12 · **Status:** Approved (pending spec review)
**Goal:** Real projects enter the PMBOK system through Microsoft 365 and appear
in both Power BI reports automatically, honoring SOP-002's intake → triage flow.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Intake surface | Microsoft Form → Power Automate → SharePoint List (the List is the triage hub) |
| v1 scope | Submission creates intake record **and** a project (status *Proposed*, phase *Initiating*); triage column drives later status |
| Sync runner | `tools/sync_intake.py` on Allen's PC via Windows Task Scheduler |
| Sync cadence | **Once daily, 5:30 AM ET** — 30 minutes before the 6:00 AM model refresh |
| Hosting cost | $0 (all M365-native + existing PC + existing database) |

## Architecture

```
Microsoft Form "Theragen Project Intake"   (org-only; submitter identity captured)
        │  Power Automate flow (standard connectors)
        ▼
SharePoint List "Project Intake"           (people pickers, choice columns,
        │                                   Triage Status — PMO works here)
        ▼  tools/sync_intake.py            (Graph API, az-signed-in identity,
        │                                   daily 5:30 AM, idempotent)
        ▼
PostgreSQL psql-theragen-pmbok             (doc_mgmt.intake_submission,
        │                                   pmbok.project, pmbok.project_charter)
        ▼  6:00 AM scheduled service refresh
Both reports (interactive + paginated)
```

PostgreSQL remains the system of record; the List is the workflow surface;
reports never read M365 directly.

## Components

### 1. Microsoft Form (manual build, field spec below)

Org-only so responder identity is captured. Fields:
request title · request type (spec enum) · requesting department (8 choices) ·
business problem (long text) · desired outcome / business value (long text) ·
sponsor name (text) · project manager name (text) · planned start (date) ·
planned finish (date) · estimated budget (number) · effort bucket (spec enum) ·
five compliance yes/nos (PHI, CFR-11, clinical, vendor, data-sharing) ·
strategic objective ref (text, optional).

### 2. SharePoint List "Project Intake" (created programmatically via Graph)

Typed columns mirroring the form plus:

- **Sponsor / Project Manager**: *person* columns. The flow attempts to resolve
  the form's free-text names; unresolved stays empty and the item surfaces in a
  "Needs attention" view — the data-quality airlock before the database.
- **Triage Status** (choice): Submitted | Approved | Rejected | On Hold —
  the PMO's working column.
- Sync bookkeeping (set by the sync, read-only by convention): **Intake ID**,
  **Project Code**, **Sync Status** (Pending | Synced | Error), **Sync Message**.

### 3. Power Automate flow (manual build, recipe provided)

Three steps: *When a new response is submitted* → *Get response details* →
*Create item* in the List (Triage Status = Submitted, Sync Status = Pending).
Person resolution: `Office 365 Users – Search` on the typed names; empty on no
unique match.

### 4. `tools/sync_intake.py`

- **Auth:** Graph token from the existing `az` CLI sign-in (no new app
  registration in v1).
- **Selection:** List items where Sync Status ≠ Synced, **or** Triage Status
  changed since last sync (detected by comparing against the project's current
  status in PostgreSQL).
- **New item →** one transaction: mint `INT-2026-NNNN` (max+1 per year) and
  `THG-<DEPT>-NNN` (max+1 per department); insert `doc_mgmt.intake_submission`,
  `pmbok.project` (Proposed / Initiating), minimal `pmbok.project_charter`
  (business case = desired outcome). `budget_envelope` derives from estimated
  budget per the spec enum: <25k → "$0-25k", <250k → "$25-250k",
  <1M → "$250k-1M", else ">$1M"; missing budget → "Unknown". Sponsor/PM resolved to `doc_mgmt.person`
  by email from the person columns; if either is unresolved the item errors
  (people are NOT NULL in the spec).
- **Triage transition →** Submitted→*Proposed* (birth state), Approved→*Active*
  (+ `actual_start` = today if empty), Rejected→*Cancelled*, On Hold→*Paused*.
- **Write-back:** assigned Intake ID + Project Code, Sync Status, and any
  validation message are written onto the List row — outcomes visible where the
  PMO works.
- **Idempotency:** List item ID is stored in `intake_submission` (new column
  `external_ref VARCHAR(64)` via migration `db/05_intake_external_ref.sql`);
  re-runs match on it and never duplicate. Per-item transactions; one bad item
  never blocks the rest.
- **`--dry-run`** prints intended inserts/updates without writing.

### 5. Safety riders

- `tools/load_postgres.py` gains a guard: requires `--reseed` **and**
  interactive confirmation by typing the database name. The seeder can never
  silently wipe real intakes again.
- New-person policy v1: sponsors/PMs must already exist in `doc_mgmt.person`;
  unknown people = item error with a clear message (person onboarding is a
  separate concern).

### 6. Scheduling

Windows Task Scheduler, daily **5:30 AM ET**: `python tools\sync_intake.py`.
(The 6:00 AM Power BI refresh is already scheduled service-side.) Manual runs
any time for ad-hoc pulls.

## Error handling

| Failure | Behavior |
|---|---|
| Person unresolved / validation fails | Item marked Sync Status = Error + message on the List row; others proceed |
| Graph or DB unreachable | Run aborts non-zero, nothing partial (per-item transactions); next day retries |
| Duplicate submit / re-run | `external_ref` match → skipped or treated as update; no duplicates |
| PC off at 5:30 | Task Scheduler "run as soon as possible after missed start" enabled |

## Testing

- Unit: sequence minting (INT/project-code, incl. year/department rollover),
  triage-transition mapping, payload validation.
- Integration: insert + rollback against the live DB; Graph read of the real List.
- E2E smoke: test form submission → flow → List → `sync_intake.py` →
  `bi.project` shows the row → visible as Proposed in Portfolio Overview after
  refresh (or immediate `service_refresh.py`).

## Out of scope (v1)

PMO notification emails (v1.1, trivial in the same flow) · editing existing
projects beyond triage status · WBS/milestone/risk entry (Phase 2 app per spec)
· new-person onboarding · Azure Function runner (the v2 home for the sync when
PC-independence matters).

## Build order

1. `db/05_intake_external_ref.sql` migration + loader guard
2. List creation script (Graph) → run, verify columns
3. `sync_intake.py` + unit tests + dry-run against empty List
4. Form + Flow (Allen clicks, recipe provided) → test submission
5. E2E smoke → schedule the task → commit everything
