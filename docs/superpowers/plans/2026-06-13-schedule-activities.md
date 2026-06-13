# Schedule Activities + Auto-WBS — Implementation Plan (Phase 2a)

Spec: `docs/superpowers/specs/2026-06-13-schedule-activities-design.md`
Process: subagent-driven, fresh subagent per task, two-stage review (spec then quality).

Hard riders (every task):
- NEVER run `tools/load_postgres.py` or any reseed. DDL via inline psycopg; data writes
  only through `tools/sync_artifacts.py` + listed probe cleanups.
- Never commit `db/.pg.local.json`, `db/.m365.local.json`, `db/.graph_token_cache.json`.
- `python -m pytest tests/ -q` green at every commit.
- Both syncs are LIVE (5:30 / 5:40 AM). Any touch to shared files
  (`sync_artifacts.py`, `artifact_lib.py`, `graph_client.py`) must keep the existing
  artifact dry-run output unchanged for the three current Lists (capture before/after).
- Graph identity richard.allen@theragen.com (cached token). Site/list ids in
  `db/.m365.local.json`. Mirror the established patterns: `process_risk` (per-item),
  the `area_map` pre-pass in `main()` (per-project context), `create_artifact_lists.py`
  (List creation), `tests/test_artifact_lib.py` (pure tests).

---

### Task 1: Activity external_ref migration

**Files:** create `db/07_activity_external_ref.sql`; modify `tools/load_postgres.py` (DDL tuple only).

```sql
-- db/07_activity_external_ref.sql
-- Idempotency anchor for M365-authored schedule activities: the SharePoint List
-- item id. WBS elements need none - they are derived and keyed deterministically
-- by uuid5 over (project_code, workstream[, workpackage]).
ALTER TABLE pmbok.schedule_activity ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
```

Append `"07_activity_external_ref.sql"` to the loader's DDL filename tuple (after
`"06_artifact_external_ref.sql"`). Apply live (inline psycopg, creds `db/.pg.local.json`);
verify `information_schema.columns` shows `external_ref` VARCHAR(64) on
`pmbok.schedule_activity` and the UNIQUE constraint exists. `pytest` green.
Commit: `git commit -m "Add schedule_activity external_ref migration"`.

---

### Task 2: Pure activity + WBS logic with tests (TDD)

**Files:** `tests/test_artifact_lib.py` (extend, write tests FIRST), `tools/artifact_lib.py` (extend).

Add to `tools/artifact_lib.py` (after the existing constants/helpers; reuse `_blank`,
`_norm`, `next_risk_code` regex style):

```python
ACTIVITY_STATUSES = ["Not started", "In progress", "At risk", "Done", "Cancelled"]
# The 8 Theragen departments (exact strings; also doc_mgmt.department.name).
DEPARTMENTS = ["Clinical / Medical Affairs", "Regulatory / Quality",
               "R&D / Engineering", "Operations / PMO", "Finance / Procurement",
               "Commercial / Marketing", "IT / Data / Security", "HR / People"]

_ACTIVITY_CODE = re.compile(r"-A(\d+)$")


def working_days(start, finish):
    """Inclusive Mon-Fri count between two ISO date strings (yyyy-mm-dd).
    Returns 0 if either is blank or finish < start."""
    if _blank(start) or _blank(finish):
        return 0
    s = datetime.date.fromisoformat(str(start)[:10])
    f = datetime.date.fromisoformat(str(finish)[:10])
    if f < s:
        return 0
    days, d = 0, s
    while d <= f:
        if d.weekday() < 5:
            days += 1
        d += datetime.timedelta(days=1)
    return days


def next_wbs_code(existing_codes, parent_code=None):
    """Append-only WBS code. Level-1 (parent_code None): next unused integer.
    Level-2: '{parent}.{next unused child int}'. Never renumbers existing codes."""
    if parent_code is None:
        nums = [int(c) for c in existing_codes if c and c.isdigit()]
        return str(max(nums) + 1 if nums else 1)
    prefix = f"{parent_code}."
    nums = [int(c[len(prefix):]) for c in existing_codes
            if c and c.startswith(prefix) and c[len(prefix):].isdigit()]
    return f"{prefix}{max(nums) + 1 if nums else 1}"


def next_activity_code(existing_codes, wbs_code):
    """Next '{wbs_code}-A{n}' for one work package. Widens, never truncates."""
    nums = [int(m.group(1)) for c in existing_codes
            if c and (m := _ACTIVITY_CODE.search(c)) and c.startswith(f"{wbs_code}-A")]
    return f"{wbs_code}-A{max(nums) + 1 if nums else 1}"


def validate_activity(it):
    errs = [f"Missing: {k}" for k in
            ("ProjectCode", "Title", "Workstream", "WorkPackage",
             "StartPlanned", "FinishPlanned", "Department") if _blank(it.get(k))]
    if _blank(it.get("OwnerEmail")):
        errs.append("Missing: Owner")
    if it.get("ActivityStatus") not in ACTIVITY_STATUSES:
        errs.append(f"ActivityStatus not recognized: {it.get('ActivityStatus')}")
    if not _blank(it.get("Department")) and it["Department"] not in DEPARTMENTS:
        errs.append(f"Department not recognized: {it['Department']}")
    if (not _blank(it.get("StartPlanned")) and not _blank(it.get("FinishPlanned"))
            and it["FinishPlanned"] < it["StartPlanned"]):
        errs.append("FinishPlanned must be on/after StartPlanned")
    pct = it.get("PctComplete")
    if pct is not None and not (0 <= float(pct) <= 100):
        errs.append("PctComplete must be 0-100")
    # Recent Accomplishment DAX filters Done AND non-blank Actual Finish.
    if it.get("ActivityStatus") == "Done" and _blank(it.get("FinishActual")):
        errs.append("Done requires FinishActual (report hides it otherwise)")
    return errs


def build_wbs_row(project_id, wbs_code, parent_id, level, name, owning_department, owner_role):
    return {"project_id": project_id, "wbs_code": wbs_code,
            "parent_wbs_element_id": parent_id, "level": level, "name": name[:200],
            "owning_department": owning_department, "owner_role": owner_role}


def build_activity_row(it, wbs_element_id, owner_person_id, activity_code):
    return {
        "wbs_element_id": wbs_element_id,
        "activity_code": activity_code,
        "name": it["Title"][:200],
        "start_planned": it["StartPlanned"],
        "finish_planned": it["FinishPlanned"],
        "start_actual": it["StartActual"],
        "finish_actual": it["FinishActual"],
        "duration_days": working_days(it["StartPlanned"], it["FinishPlanned"]),
        "owner_person_id": owner_person_id,
        "department": it["Department"],
        "status": it["ActivityStatus"],
        "pct_complete": float(it["PctComplete"]) if it["PctComplete"] is not None else 0,
    }
```

Tests (`tests/test_artifact_lib.py`, write first, watch fail, then green) — cover:
`working_days` (a full week = 5; Sat→Sun = 0; single weekday = 1; finish<start = 0; blank
= 0; a known span e.g. 2026-06-01..2026-06-05 = 5, 2026-06-01..2026-06-08 = 6);
`next_wbs_code` (`[]`→"1"; `["1","2"]`→"3"; parent "1" with `["1.1","1.2"]`→"1.3"; widen
`["1","2",...,"9","10"]`→"11"); `next_activity_code` (`[]`,"1.1"→"1.1-A1";
`["1.1-A1","1.1-A2"]`,"1.1"→"1.1-A3"; codes for a different WBS ignored); `validate_activity`
(happy; each missing required; bad status/department; finish<start; pct 101; Done without
FinishActual → error, Done with it → ok); `build_activity_row` (duration computed, pct
default 0 when None, name truncated). Reuse the `_risk()`-style fixture pattern.

`pytest` green. Commit: `git commit -m "Add pure activity + WBS logic: working days, code minting, validate, builders"`.

---

### Task 3: Project Activities List in the creator

**Files:** modify `tools/create_artifact_lists.py`.

Add a fourth entry to the `LISTS` dict (reuse `choice/text/date_only`, import `DEPARTMENTS`
and `ACTIVITY_STATUSES` from `artifact_lib`; person column shape per existing Owner/Sponsor):

```python
"activity_list_id": ("Project Activities", [
    text("ProjectCode"),
    text("Workstream"),
    text("WorkPackage"),
    date_only("StartPlanned"),
    date_only("FinishPlanned"),
    date_only("StartActual"),
    date_only("FinishActual"),
    {"name": "Owner", "personOrGroup": {"allowMultipleSelection": False}},
    choice("Department", al.DEPARTMENTS),
    choice("ActivityStatus", al.ACTIVITY_STATUSES, default="Not started"),
    {"name": "PctComplete", "number": {"decimalPlaces": "none"}},
    text("ActivityCode"),
] + BOOKKEEPING),
```

Run it (idempotent — the three existing Lists print "already exists"; the new one
"created" + "OK all present"); confirm `db/.m365.local.json` gains `activity_list_id`
(print KEY NAMES only — 7 keys); re-run → "already exists". `pytest` green.
Commit (script only): `git commit -m "Add Project Activities List to the creator"`.

---

### Task 4: Sync — WBS reconcile pre-pass + activity dry-run

**Files:** modify `tools/sync_artifacts.py` (FIELDS, normalizer, SELECT, WBS reconcile,
registry entry, `main()` special-case; STUB processor returning DRY/ERROR strings only —
no DB writes from the processor in this task; the reconcile pre-pass also does NO writes in
T4, it only computes the map from existing WBS rows so dry-run can resolve ids).

Add:
- `ACTIVITY_FIELDS` = `"Title,ProjectCode,Workstream,WorkPackage,StartPlanned,FinishPlanned,StartActual,FinishActual,Owner,OwnerLookupId,Department,ActivityStatus,PctComplete,ActivityCode,SyncStatus,SyncMessage"`.
- `normalize_activity(item, people)` (mirror `normalize_risk`): trims dates with `_date`,
  `OwnerEmail = people.email(f.get("OwnerLookupId"))`, ProjectCode stripped, PctComplete
  passthrough (number or None), ActivityStatus default "Not started", ActivityCode default "".
- `ACTIVITY_SELECT` = current rows for compare, joining WBS to expose project + wbs codes:
  `SELECT a.external_ref, a.activity_id, a.wbs_element_id, w.project_id, a.activity_code, a.name, a.start_planned, a.finish_planned, a.start_actual, a.finish_actual, a.duration_days, a.owner_person_id, a.department, a.status, a.pct_complete FROM pmbok.schedule_activity a JOIN pmbok.wbs_element w USING (wbs_element_id) WHERE a.external_ref IS NOT NULL`.
- `WBS_SELECT` per project for reconciliation: `SELECT wbs_code, parent_wbs_element_id, level, name, owning_department FROM pmbok.wbs_element WHERE project_id=%s`.

WBS reconciliation (the new pre-pass; in T4 read-only — computes the map, no inserts):

```python
def reconcile_wbs(conn, project_id, project_code, project_activities, dry):
    """Ensure L1 workstream + L2 work-package WBS nodes exist for every
    (workstream, workpackage) referenced by this project's activities.
    Returns {(workstream, workpackage): wbs_element_id}. In T4/dry, computes
    deterministic ids + would-be codes without writing."""
    existing = {r[0]: r for r in conn.execute(WBS_SELECT, (project_id,)).fetchall()}
    # ... build maps by name via deterministic uuid5; mint codes append-only from
    # existing wbs_code set; in real mode INSERT missing nodes / UPDATE changed
    # owning_department inside conn.transaction(); return (ws, wp) -> level-2 id.
```

Key rules the implementer must honor (full write lands in T5; T4 returns the map for dry):
- L1 id = `uuid5(NS, f"thg/wbs/{project_code}/ws/{ws}")`, L2 id =
  `uuid5(NS, f"thg/wbs/{project_code}/wp/{ws}/{wp}")`.
- L1 code via `al.next_wbs_code(all_existing_codes)`; L2 code via
  `al.next_wbs_code(all_existing_codes, parent_code)`. Accumulate minted codes into the
  working set so two new workstreams in one run get distinct integers.
- `owning_department` = the first activity (by item id order) under the node.
- `owner_role` "Workstream Lead" (L1) / "Work Package Owner" (L2).

`main()`: special-case `art["kind"] == "activity"` — group `items` by ProjectCode, run
`reconcile_wbs` per project to build `wbs_map[(project_code, ws, wp)] = l2_id` and a
companion `wbs_code_map` (for activity-code minting), then pass both to the processor via
kwargs (exactly like `area_map` for report). Unknown ProjectCode rows skip reconciliation
and surface a normal Unknown-ProjectCode error in the processor.

STUB `process_activity(conn, g, it, dry, current, wbs_map=None, wbs_code_map=None)`:
validate; resolve project (`project_by_code`) → error if unknown; resolve owner
(`person_id_by_email`) → error if unresolved; look up `wbs_id` from `wbs_map`; return
`f"DRY activity item {id}: would create {would_be_activity_code} ({ws} / {wp})"` for new,
`"...existing (write path lands in T5)"` for current, Error write-back via `_error` for
failures (dry-guarded).

Verify live: create one probe activity per a real project (e.g. THG-IT-005) via Graph POST
(Owner via `{"OwnerLookupId":"485"}`); `python tools/sync_artifacts.py --dry-run` → the
three existing Lists behave as before PLUS `activity: N fetched` and a sensible
`DRY activity ... would create 1.1-A1 (Workstream / WorkPackage)`. Negative: PATCH
ProjectCode bogus → `ERROR activity ... Unknown ProjectCode`. Confirm the three existing
Lists' dry-run lines are unchanged vs a pre-change capture. Leave the probe for T5.
Commit: `git commit -m "Activity sync: fields, normalize, WBS reconcile map, dry-run"`.

---

### Task 5: Activity write path — WBS upsert + insert + minting + write-backs

**Files:** modify `tools/sync_artifacts.py` (make `reconcile_wbs` actually upsert; replace
the stub create branch with real inserts).

- `reconcile_wbs` now, in real mode, INSERTs missing WBS nodes (L1 before L2 for the FK)
  and UPDATEs `owning_department` when changed, inside `conn.transaction()` per project;
  deterministic ids make it idempotent. In dry mode, no writes (map still returned).
- `process_activity` create branch (mirror `process_risk`): mint `activity_code` via
  `al.next_activity_code(existing_codes_for_wbs, wbs_code)` where existing codes come from
  `SELECT activity_code FROM pmbok.schedule_activity WHERE wbs_element_id=%s`; build via
  `al.build_activity_row(it, wbs_id, owner, activity_code)`; INSERT
  `pmbok.schedule_activity` (all 13 cols + `external_ref`, `activity_id =
  uuid5(NS, f"thg/artifact/activity/{item_id}")`) in `conn.transaction()`; write back
  `{"SyncStatus":"Synced","SyncMessage":"","ActivityCode":activity_code}`; return
  `f"OK new activity {activity_code} ({ws}/{wp}, item {id})"`. Dry returns the would-be code.
  The `current:` branch keeps a T6 placeholder.

Verify live (probe from T4): dry-run shows minted code; real run → WBS nodes created +
`OK new activity 1.1-A1`; `SELECT` probes: `bi.wbs_element` shows the L1+L2 nodes for the
project, `bi.schedule_activity` shows the activity with computed `duration_days`, resolved
`owner_name`, and `project_code`. Add a SECOND activity in the same workstream, different
work package → re-run → new L2 node `1.2`, code `1.2-A1`. Immediate re-run → both
`OK ... existing`, no new rows/nodes (idempotent). Leave probes for T6.
Commit: `git commit -m "Activity sync: WBS upsert, activity insert, code minting, write-backs"`.

---

### Task 6: Update path, healing, orphan, ProjectCode-guard + cleanup

**Files:** modify `tools/sync_artifacts.py` (replace the `current:` placeholder, mirror the
risk update branch).

- Re-parent guard: WBS/project change after sync → Error "create a new row instead"
  (compare `current["project_id"]` to the resolved project; also if the activity's
  workstream/work-package changed such that `wbs_element_id` differs, treat as Error — an
  activity moving work packages should be a new row, to keep WBS rollups stable).
- Desired via `build_activity_row(it, current["wbs_element_id"], owner, current["activity_code"])`
  (activity_code immutable on update); `row_changed`-gated UPDATE of the mutable columns
  (name, planned/actual dates, duration_days, owner_person_id, department, status,
  pct_complete) WHERE external_ref; write-back Synced + ActivityCode; heal branch
  (`SyncStatus != "Synced"` or ActivityCode mismatch); no-change branch.

Verify live: PATCH probe `PctComplete` 50→100 + `ActivityStatus` "Done" + `FinishActual` →
run → updated; `bi.schedule_activity` reflects it; the Done activity (if Actual Finish
within 35d) is eligible for Recent Accomplishments. PATCH `SyncStatus` Pending → heal.
PATCH ProjectCode to another project → Error. DELETE one probe List item → orphan INFO,
DB row kept. **Cleanup:** delete the probe List items + targeted DB deletes by external_ref
(`schedule_activity` rows; then the WBS nodes created for the probe project IF they hold no
other activities — delete L2 then L1 by their uuid5 ids); verify zero probe rows remain and
bi counts return to pre-probe. `pytest` green.
Commit: `git commit -m "Activity sync: update path, healing, orphan, re-parent guard"`.

---

### Task 7: Docs

**Files:** modify `docs/artifact-entry-setup.md` (new Activities section), `README.md`.

Activities/WBS section grounded in code: the two-tier model (Workstream → Work Package →
activity), that WBS is auto-derived (PMs never create WBS rows), the column meanings + exact
choice strings (ActivityStatus, the 8 Departments), derived fields (duration auto-computed
working days; ActivityCode minted, read-only), the **Done-requires-FinishActual** rule and
the 35-day Accomplishments / −7…+45 Next-Steps windows, the keep-on-delete policy (deleting
an activity row keeps the DB row; set status Cancelled instead), and that the 5:40 sync
already covers the new List. README: one line under Execution tracking. `pytest` green.
Commit: `git commit -m "Document schedule activities + auto-WBS for PMs"`.

---

### Task 8: E2E on APNE + final review

- Populate THG-IT-005 with real activities from the repo's phases (e.g. Workstream
  "Platform" / WorkPackage "Email delivery" with Done activities at real dates; Workstream
  "Board UX" / WorkPackage "Pagination" with an In-progress/At-risk activity due in the
  Next-Steps window) — a handful spanning 2 workstreams, mixing Done (with FinishActual) and
  open. File via Graph (Owner LookupId 485).
- `python tools/sync_artifacts.py --dry-run` → intents; real run → all OK + WBS nodes;
  `python tools/service_refresh.py` → THG-IT-005 status page **Key Project Areas** shows
  the workstreams with rollup status/%, and the **Schedule & Milestones** page populates
  (by-dept/status, % complete). Open activities appear under Next Steps; any Done-within-35d
  under Accomplishments.
- Next morning: `logs\artifact_sync.log` shows the unattended 5:40 run exit 0 with the
  activities.
- Whole-stage review (most capable model) across T1–T7; fix loop; final commit.

---

## Self-review

- **Spec coverage:** migration (T1), pure logic+tests (T2), List (T3), reconcile+dry-run
  (T4), write path incl. WBS upsert + minting (T5), update/heal/orphan/guard (T6), docs
  (T7), e2e (T8). WBS authoring intentionally absent (derived). ✓
- **Type consistency:** `working_days/next_wbs_code/next_activity_code/validate_activity/
  build_wbs_row/build_activity_row` signatures match tests (T2) and call sites (T4–T6);
  `wbs_map`/`wbs_code_map` passed via kwargs exactly like `area_map`; `activity_list_id`
  written by T3, read by T4. ✓
- **Reuse:** `process_risk` skeleton, `area_map` pre-pass pattern, `_error`/`writeback`/
  `person_id_by_email`/`project_by_code`/`synced_map`/`row_changed`, the migration/List/test
  conventions — all reused, not reinvented. ✓
