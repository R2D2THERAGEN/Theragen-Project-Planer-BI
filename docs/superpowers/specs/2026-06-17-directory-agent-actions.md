# Staff Directory agent — governed actions (E-T3 routing)

**Status (2026-06-17): design + runbook.** The backend is already built — this describes how the agent takes *actions* through the existing airlock + audit, and the Copilot Studio wiring to do it.

## Principle — the agent never writes the database

Every agent action is a **write to a SharePoint List item**, never a direct DB write. The existing daily sync then **validates (airlock), audits, and applies** it. The agent therefore inherits all governance for free: default-deny RLS, `audit_trail_entry`, the controlled department choices, person resolution. No new backend, no bypass.

```
Agent (Copilot Studio)  ->  Power Automate (SharePoint connector)  ->  List item write
                                                                            |
                          existing sync (airlock + audit)  <---------------+
                                   |
                          Azure PostgreSQL  ->  bi.* views  ->  model / RLS
```

## Action 1 — Assign a department

- **Agent intent:** "Put Jane Doe in Clinical."
- **Write:** Power Automate **Update item** on the **Staff Directory** list — set `Department` = `Clinical / Medical Affairs` on the row whose `UPN` = jane.doe@theragen.com.
- **Applied by:** the **05:20 `SyncDirectory`** read-back → `person.department_id` → `bi.org_directory` → the Directory model + Report-Access Department-scope logic.
- **Reversible:** change or blank the `Department` (blank → Unassigned).
- **Constraint:** the agent must only ever choose from the 8 controlled department names (+ Unassigned). It already knows them.

## Action 2 — Grant / revoke report access

- **Agent intent:** "Give Jane access to the HIPAA project" / "Give Jane access to Clinical's projects."
- **Write:** Power Automate **Create item** on the **Report Access** list — `UserEmail`, `ScopeType` (Project / Department / All), `ScopeValue` (a project code or department name; blank for All), `Active` = Yes, `GrantedBy`.
- **Applied by:** the **05:40 `SyncArtifacts`** run — which **airlocks** the scope value (must resolve to a real project / department), writes an **`ACCESS_GRANT`** audit row, and lands the grant in `bi.report_access` → the `Scoped Viewer` RLS role.
- **Revoke:** set that row's `Active` = No → `ACCESS_REVOKE` audit; the grant stops applying.
- **Read-back for the agent:** ground a "who has access to X?" answer on **`bi.report_access`** (already exposes all grants + `granted_by_name`).

## Human-in-the-loop + safety (required)

- The agent must **state the exact change and confirm** before writing ("I'll grant jane.doe@theragen.com Department access to *Clinical / Medical Affairs*, granted by you — confirm?"). No silent writes.
- Every action is **auditable** (`audit_trail_entry`) and **reversible** (revoke / reassign). Default-deny RLS means a bad grant only ever *adds* visibility for one user, never removes governance.
- The agent should **never grant beyond the requester's own authority** — see *harden later*.

## Latency

Writes apply at the **next scheduled sync** (05:20 for department, 05:40 for access), or immediately if someone runs `python tools/sync_directory.py` / `tools/sync_artifacts.py`. *Harden later:* an on-demand HTTP-triggered sync so agent actions apply in seconds.

## Copilot Studio wiring

1. Build two **Power Automate flows** (cloud flows) in the tenant:
   - `Directory - Assign Department` (inputs: UPN, Department) → SharePoint *Get items* (filter UPN) → *Update item* (Department).
   - `Directory - Grant Access` (inputs: UserEmail, ScopeType, ScopeValue) → SharePoint *Create item* on Report Access (Active = Yes, GrantedBy = the flow caller).
2. In the agent → **Actions/Tools**, add each flow; describe its inputs so the model fills them.
3. In the **agent instructions**, add: "To assign a department or grant access, call the matching action; first confirm the exact change with the user; only use the controlled department names; never grant access a user is not entitled to request."

## Harden later (explicitly deferred)

- **On-demand sync** trigger so actions apply immediately (today: next scheduled run).
- **Authority enforcement** — check that the requester is allowed to grant the access they're asking for (today: human confirmation + audit are the controls; reuse the `enforce_decision_authority` pattern).
- **Agent reads current state** from `bi.report_access` / `bi.org_directory` before acting (avoid duplicate grants).
- **Structured confirmation / approval** for sensitive grants (route through the change-control approval flow).
