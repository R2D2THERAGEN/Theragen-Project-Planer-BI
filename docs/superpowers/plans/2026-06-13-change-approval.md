# Change & Approval — Implementation Plan (Phase 2b)

Spec: `docs/superpowers/specs/2026-06-13-change-approval-design.md`. Deep design: the approved
plan file (Stage 2b). Process: subagent-driven, fresh subagent per task, two-stage review.

Hard riders (every task): NEVER run `tools/load_postgres.py`/reseed (DDL via inline psycopg,
data writes only through `sync_artifacts.py` + listed probe cleanups); never commit
`db/.pg.local.json`/`db/.m365.local.json`/`db/.graph_token_cache.json`; `python -m pytest
tests/ -q` green at every commit; both syncs are LIVE — keep existing artifact dry-run output
unchanged for the current Lists (capture before/after when touching shared files); Graph
identity richard.allen@theragen.com (cached token); **mirror the established patterns**:
`process_risk` (per-item create/update/heal/guard), `validate_risk`/`build_risk_row`/
`next_risk_code` (pure), the migration/List/test conventions from 2a, the `normalize_report`
author-fallback. The exact reusable code shapes are quoted in the approved plan file.

---

### Task 1: Governance migrations
Create `db/08_change_request_external_ref.sql`, `db/09_decision_external_ref.sql`,
`db/10_status_report_signoff.sql` (exact SQL in the spec/plan); append all three to the
`load_postgres.py` DDL tuple after `07_`. Apply live via inline psycopg; verify via
`information_schema.columns` (external_ref on change_request + decision; approved_by_person_id
+ approved_at on status_report) and that the three UNIQUE constraints exist; confirm seeded
row counts unchanged (no data loss). pytest green. Commit `"Add change/decision external_ref +
status_report sign-off migrations"`.

### Task 2: Pure CR/decision logic with tests (TDD)
Tests FIRST in `tests/test_artifact_lib.py`, then code in `tools/artifact_lib.py`.

Constants + minting:
```python
CR_CLASSES = ["A - Minor", "B - Substantive", "C - Controlling", "Emergency / Safety"]
CHANGE_TYPES = ["Scope", "Schedule", "Cost", "Quality", "Compliance"]
CR_DECISIONS = ["Pending", "Approved", "Deferred", "Rejected"]
CR_STATUSES = ["Open", "In Assessment", "Implementing", "Verified", "Closed", "Rejected"]
_CR_CODE = re.compile(r"^C-(\d{3,})$")
_DECISION_CODE = re.compile(r"^D-(\d{3,})$")

def next_cr_code(existing):
    nums = [int(m.group(1)) for s in existing if s and (m := _CR_CODE.match(s))]
    return f"C-{(max(nums) + 1 if nums else 1):03d}"

def next_decision_code(existing):
    nums = [int(m.group(1)) for s in existing if s and (m := _DECISION_CODE.match(s))]
    return f"D-{(max(nums) + 1 if nums else 1):03d}"
```

`validate_change_request(it)` (returns error list):
```python
def validate_change_request(it):
    errs = [f"Missing: {k}" for k in
            ("ProjectCode", "Description", "Reason", "CRClass", "ChangeType")
            if _blank(it.get(k))]
    if _blank(it.get("RequestedByEmail")):
        errs.append("Missing: RequestedBy (picker empty and item author unknown)")
    if it.get("CRClass") and it["CRClass"] not in CR_CLASSES:
        errs.append(f"CRClass not recognized: {it['CRClass']}")
    if it.get("ChangeType") and it["ChangeType"] not in CHANGE_TYPES:
        errs.append(f"ChangeType not recognized: {it['ChangeType']}")
    dec, st = it.get("Decision") or "Pending", it.get("CRStatus") or "Open"
    if dec not in CR_DECISIONS:
        errs.append(f"Decision not recognized: {dec}")
    if st not in CR_STATUSES:
        errs.append(f"CRStatus not recognized: {st}")
    if dec != "Pending":
        if _blank(it.get("DecidedByEmail")):
            errs.append("Decision set but DecidedBy is empty")
        if _blank(it.get("DecidedDate")):
            errs.append("Decision set but DecidedDate is empty")
    elif not _blank(it.get("DecidedDate")):
        errs.append("DecidedDate must be blank while Decision is Pending")
    if dec == "Rejected" and st != "Rejected":
        errs.append("Rejected decision requires CRStatus = Rejected")
    if st in ("Verified", "Closed") and dec != "Approved":
        errs.append(f"CRStatus {st} requires Decision = Approved")
    if (not _blank(it.get("DecidedDate")) and not _blank(it.get("RequestedDate"))
            and it["DecidedDate"] < it["RequestedDate"]):
        errs.append("DecidedDate must be on/after RequestedDate")
    return errs
```

`validate_decision(it)`: required Title, ProjectCode, Rationale, DecidedDate; DecidedBy
resolvable (`_blank(it.get("DecidedByEmail"))` → "Missing: DecidedBy").

`build_cr_row(it, project_id, requester_id, decider_id, cr_code)` → the 18 change_request
columns (requested_at = it["RequestedDate"], change_types = it["ChangeType"], affected_artifacts
= it["AffectedArtifacts"] or "n/a", impact_schedule_days/impact_cost coerced to int/float with
0 default, implementation_verified/linked_artifacts_updated via `coerce_bool` from graph_client,
decision/status defaults Pending/Open, decided_by_person_id=decider_id, decided_at=DecidedDate).
`build_decision_row(it, project_id, decider_id, code)` → decision/rationale/decided_by/decided_at.

Extend `build_report_row(it, project_id, submitted_by_person_id, approved_by_person_id=None)` to
add `"approved_by_person_id": approved_by_person_id` and `"approved_at": it.get("ApprovedDate")`.

`_trail_states(current, desired, keys)` → `({k: current.get(k) for k in keys}, {k: desired[k]
for k in keys})` (pure, for audit before/after).

Tests: minting widen for C-/D-; every validate_change_request rule (each missing required;
each bad domain; Decision/DecidedBy/DecidedDate coherence both directions; both cross-axis
rules; date order); validate_decision; builders (column sets, defaults, bool coercion); the
extended build_report_row carries approver; `_trail_states`. Green. Commit `"Add pure CR +
decision logic: minting, validators, builders, audit states"`.

### Task 3: Change Requests + Decisions Lists in the creator
Add two `LISTS` entries (mirror the activity entry shape; person columns
`{"name": "...", "personOrGroup": {"allowMultipleSelection": False}}`; Yes/No flags as
`choice(name, ["Yes", "No"])`) and `ApprovedBy`(person)+`ApprovedDate`(date_only) on the Status
Reports entry. **The status-report list already exists**, so add a column-ensure step: after the
create/exists check, for each column not present on an existing list, `g.post(.../columns, col)`
(so ApprovedBy/ApprovedDate get added to the live Status Reports list). Run live (idempotent;
`change_request_list_id`/`decision_list_id` merged into `db/.m365.local.json`; verify the two
new columns appear on the Status Reports list). Commit (script only) `"Add Change Requests +
Decisions Lists; status-report sign-off columns"`.

### Task 4: Sync read/validate/dry-run (CR, decision, sign-off)
`CR_FIELDS`/`DECISION_FIELDS` (incl. RequestedByLookupId/DecidedByLookupId); `normalize_change_request`
(author fallback for RequestedByEmail like normalize_report; `_date` for dates; `coerce_bool`
passthrough kept as raw choice for the row builder), `normalize_decision`; `CR_SELECT`/
`DECISION_SELECT` (synced_map templates incl. external_ref + comparable columns); `project_leads(conn,
project_id)` helper. Extend `REPORT_FIELDS`+`normalize_report` (ApprovedByEmail, ApprovedDate) +
`process_report` validation (ApprovedBy⇔ApprovedDate, approver resolvable). STUB
`process_change_request`/`process_decision` (validate → resolve project/requester/decider →
soft-authority note → report DRY/ERROR intent; NO writes). Registry entries. Dry-run live against
1 probe per List (a CR Pending, a decision, a status report with ApprovedBy); confirm the existing
Lists' dry-run lines unchanged. Commit `"Governance sync: fields, normalize, validate, dry-run"`.

### Task 5: Write path + audit trail
Create `tools/audit_lib.py` (the `write_trail` from the plan; `from psycopg.types.json import
Jsonb`). Real `process_change_request` (create: mint C-NNN, INSERT change_request + `write_trail`
CR_CREATE, soft-warn write-back; update: row_changed UPDATE + `write_trail` CR_DECISION/CR_STATUS
when those columns change + heal), `process_decision` (create/update/heal, mint D-NNN),
`process_report` sign-off (UPDATE approved_by/at in the existing update path + `write_trail`
STATUS_SIGNOFF when approved_at NULL→set). All audit writes INSIDE the per-item `conn.transaction()`.
Live: file a CR (Pending) → flip Decision=Approved+DecidedBy/Date → CRStatus Implementing→Verified
across runs; a decision; sign a status report. Verify `pmbok.change_request`/`pmbok.decision`/
`pmbok.status_report` rows + `doc_mgmt.audit_trail_entry` rows (actions, before/after) + List
write-backs (CRCode/DecisionCode/Synced). Idempotent re-run = no-ops. Commit `"Governance sync:
write path, approval transitions, audit trail"`.

### Task 6: Update/heal/orphan/guard + soft-authority + cleanup
Full update/heal/orphan/ProjectCode-guard for CR + decision (mirror risk T6). Live verify:
soft-authority warning (decider ≠ sponsor/PM → Synced with the SyncMessage note; decider = PM →
clean); each cross-axis validation error (Rejected without CRStatus Rejected; Verified without
Approved); a heal; an orphan; ProjectCode-change rejection. Probe cleanup (List rows + targeted DB
deletes by external_ref for change_request/decision; delete probe status_report sign-off columns
back to NULL; delete probe audit rows by entity_id). Commit `"Governance sync: update, heal,
orphan, guards, soft-authority"`.

### Task 7: BI governance views
`db/11_bi_governance_views.sql` — widen `bi.change_request` (decided_by id+name LEFT JOIN,
impact_scope/quality, affected_artifacts, implementation_verified, linked_artifacts_updated);
extend `bi.status_report` (approved_by id+name LEFT JOIN, approved_at, is_signed_off); add
`bi.decision` + `bi.change_impact_assessment`. Apply live; `SELECT` verify new columns;
re-verify the existing model partitions still load (the widened views are additive). Append to
the loader tuple. Commit `"Add bi governance views: CR widen, status sign-off, decision, impact"`.

### Task 8: TMDL model + measures
Add columns to `Change Request.tmdl` (Decided By, Impact Scope, Impact Quality, Affected
Artifacts, Implementation Verified[bool], Linked Artifacts Updated[bool]) + partition SELECT;
`Status Report.tmdl` (Approved By, Approved Date, Is Signed Off[bool]) + partition; NEW
`Decision.tmdl` (from bi.decision) + a single-direction relationship Decision→Project (mirror an
existing fact-table relationship verbatim); 5 measures in `_Measures.tmdl` (exact block format,
fresh uuid5 lineageTags): Verified CRs, CRs Pending Verification, Decisions Logged (Change folder),
Signed-off Reports, Sign-off Rate (Health folder). Optional light visual edits (Decided By +
Implementation Verified on the Change-log table; a Signed-off card on the status header). Verify:
Tabular Editor BPA zero violations + `python tools/validate_pbir.py` + `python tools/service_refresh.py`
succeeds and the model loads the new columns/table. Commit `"Model: governance columns, Decision
table, sign-off + CR measures"`.

### Task 9: Docs + e2e + final review
`docs/artifact-entry-setup.md`: new Change Requests + Decisions sections (the two-axis workflow,
the soft-authority note, the sign-off columns on status reports) + README pointer. E2e on
APNE/THG-IT-005: file 1–2 CRs through Pending→Approved→Verified, 1 decision, sign off the existing
status report; sync → refresh → Change Control page shows authored CRs with approver/verified,
Decisions Logged counts, status page shows Signed-off. Confirm the next-morning unattended 5:40 run.
Whole-stage review (most capable model); fix loop; final commit.

---

## Self-review
- **Spec coverage:** migrations (T1), pure logic+tests (T2), Lists (T3), dry-run incl. sign-off
  validation (T4), write path + audit (T5), update/guards/soft-authority (T6), bi views (T7),
  model+measures (T8), docs+e2e (T9). Impact-assessment authoring deferred to 2c. ✓
- **Type consistency:** `next_cr_code`/`next_decision_code`/`validate_change_request`/
  `validate_decision`/`build_cr_row`/`build_decision_row`/extended `build_report_row`/
  `_trail_states` match tests (T2) and call sites (T4–T6); `write_trail` signature matches its
  call sites; `change_request_list_id`/`decision_list_id` written by T3, read by T4. ✓
- **Reuse:** process_risk skeleton, normalize_report author-fallback, `_error`/`writeback`/
  `person_id_by_email`/`project_by_code`/`synced_map`/`row_changed`/`coerce_bool`, migration/List/
  test conventions — reused, not reinvented. ✓
