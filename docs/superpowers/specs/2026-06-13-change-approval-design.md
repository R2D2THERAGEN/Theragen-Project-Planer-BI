# Change & Approval — Design (Phase 2b)

Status: approved 2026-06-13 (plan-mode review). Stage 2b of the staged Phase 2 roadmap
(2a Schedule & WBS [shipped] → **2b Change & Approval** → 2c Versioning & Handoffs). Full
arc: the approved plan. This spec covers **2b only**.

## Problem

Projects can be created, tracked (risks/milestones/status), and scheduled (activities/WBS),
but there is no controlled way to **change** a project or to **approve** anything. The
`pmbok.change_request` table and the **Change Control** report page + its measures already
exist but have no authoring surface — no real change requests flow in. Status reports are
auto-`Synced` with no sign-off. Project decisions aren't logged. There is no audit trail
behind state changes.

## Decisions

- **Surfaces:** two new SharePoint Lists — "Project Change Requests" → `pmbok.change_request`,
  "Project Decisions" → `pmbok.decision` — plus a **sign-off extension** to the existing
  Project Status Reports List. Synced by the existing registry-driven `tools/sync_artifacts.py`.
- **Two-axis CR approval workflow:** the CR carries `Decision` (the gate: Pending/Approved/
  Deferred/Rejected) and `CRStatus` (the lifecycle: Open/In Assessment/Implementing/Verified/
  Closed/Rejected). Both are approver-edited on the List and re-applied via the proven
  full-row-compare path; validation enforces coherence between them.
- **Soft authority warning** (locked): anyone may record a decision, but if the decider isn't
  the project Sponsor or PM the row still syncs with a `SyncMessage` note. The audit trail
  records who decided. (No hard role enforcement in v1.)
- **Decisions register** (locked): a lightweight `pmbok.decision` List (D-NNN), mirroring the
  risk pattern.
- **Status-report sign-off:** additive nullable `approved_by_person_id` + `approved_at` on
  `pmbok.status_report`; the report becomes "signed" when `approved_at` is set.
- **Audit trail:** every state transition (CR create/decision/status, status sign-off) writes
  an append-only row to `doc_mgmt.audit_trail_entry` inside the same transaction.
- **Impact-assessment authoring deferred to 2c** (locked): 2b ships only the read-only
  `bi.change_impact_assessment` view.
- **No new pmbok core tables** — all four targets exist. One new *model* table (Decision,
  consuming `bi.decision`) is the only new modeling object.

## Authoring surfaces

### "Project Change Requests" List → `pmbok.change_request`
Domains (no DB CHECKs — enforced in app code): CRClass {A - Minor, B - Substantive, C -
Controlling, Emergency / Safety}; ChangeType single-select {Scope, Schedule, Cost, Quality,
Compliance} stored verbatim in `change_types` (single token, never JSON — the DDL comment is
stale); Decision {Pending(def), Approved, Deferred, Rejected}; CRStatus {Open(def), In
Assessment, Implementing, Verified, Closed, Rejected}.

Columns: ProjectCode; RequestedDate→`requested_at` (default item createdDate); RequestedBy
(person, fallback to item author for the NOT-NULL requester); CRClass; ChangeType;
AffectedArtifacts (default "n/a"); Description; Reason; ImpactScope; ImpactQuality;
ImpactScheduleDays; ImpactCost; IntakeID (optional); Decision; DecidedBy (person); DecidedDate;
ImplementationVerified (Yes/No); LinkedArtifactsUpdated (Yes/No); CRStatus; CRCode (write-back,
`C-NNN` per project) + SyncStatus/SyncMessage.

Validation (`validate_change_request`): required ProjectCode/Description/Reason/CRClass/
ChangeType; requester resolvable; domain membership for all four choice axes; Decision≠Pending
⇒ DecidedBy + DecidedDate; Decision=Pending ⇒ DecidedDate blank; cross-axis (hard error)
Rejected⇒CRStatus Rejected and Verified/Closed⇒Decision Approved; DecidedDate ≥ RequestedDate;
ProjectCode-change guard on update. Soft authority warning when the decider isn't the
Sponsor/PM (note in SyncMessage, still Synced).

### "Project Decisions" List → `pmbok.decision`
Title→decision statement, ProjectCode, Rationale (required), DecidedBy (person, required),
DecidedDate (required), DecisionCode (`D-NNN`, write-back) + bookkeeping. Straight
create/update/heal (no workflow axes).

### Status-report sign-off
Add ApprovedBy (person) + ApprovedDate to the existing List; `process_report`'s update path
resolves the approver and sets `approved_by_person_id`/`approved_at`; create leaves them NULL.

## Audit trail (`tools/audit_lib.py`)
`write_trail(conn, actor, action, entity_type, entity_id, before, after, reason)` → INSERT
into `doc_mgmt.audit_trail_entry` (append-only, before/after JSONB), called inside the per-item
transaction so it commits atomically. Actions: CR_CREATE, CR_DECISION, CR_STATUS,
STATUS_SIGNOFF. `ip_address` NULL (batch); actor = the resolved decider/approver person id.

## BI exposure (`db/11_bi_governance_views.sql`)
Widen `bi.change_request` (decided_by id+name, impact_scope/quality, affected_artifacts,
implementation_verified, linked_artifacts_updated); extend `bi.status_report` (approver id+name,
approved_at, is_signed_off); add `bi.decision` and `bi.change_impact_assessment` (read-only).
The whole Change Control page + its measures already light up from authored CRs. New
`_Measures`: Verified CRs, CRs Pending Verification, Decisions Logged (folder Change);
Signed-off Reports, Sign-off Rate (folder Health). New model table `Decision` (consuming
`bi.decision`) + a single-direction relationship to Project.

## Migrations (additive, IF NOT EXISTS, inline psycopg — never the loader)
`db/08` CR external_ref; `db/09` decision external_ref; `db/10` status_report approved_by/at;
`db/11` the bi views. Each appended to the loader DDL tuple.

## Error handling, testing, out of scope
Same airlock: failed items get SyncStatus=Error + message; lost write-backs heal; one bad item
never blocks the batch; exit 1 on any error. Pure logic unit-tested (minting, all validators
incl. coherence/cross-axis/date-order, builders, `_trail_states`); I/O verified live in T4–T6
+ the T9 e2e. Out of scope for 2b: per-department impact-assessment authoring, the parent-child
List pattern, baselines, phase gates, RACI, e-signature (all 2c+); hard role-based approval
enforcement (soft warning only).
