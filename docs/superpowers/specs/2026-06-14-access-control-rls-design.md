# Data-Driven Access Control + Row-Level Security — Design

Status: design (2026-06-14). Compliance-hardening track, part of "harden compliance" (post-2c). This
is a **design spec / development process**, not yet built — it defines how report visibility becomes
**authored data** (a form → List) consumed by Power BI Row-Level Security (RLS), so who-sees-what can
change without a model edit.

## Problem

Today every viewer of the published model sees every project. Hardcoding an RLS rule (e.g. "by
department") in DAX is brittle: each policy change is a model edit + republish, and exceptions
(a cross-department PMO lead, a contractor scoped to one project) can't be expressed. The business
needs to **maintain access itself**, on the same SharePoint-List→sync→PostgreSQL→bi pattern as every
other artifact, with the model's RLS simply **reading the authored grants**.

## Decisions

- **Access is authored, not coded.** A new **"Report Access"** List is the form; each row is a grant.
  The RLS DAX filter reads the resulting `bi.report_access` view via `USERPRINCIPALNAME()` — no model
  change is needed to alter who sees what.
- **Flexible grant grain** (one List handles every case): a grant is `(UserEmail, ScopeType,
  ScopeValue)` where `ScopeType ∈ {Project, Department, All}`:
  - `Project` + a `ProjectCode` → that one project.
  - `Department` + a department name → every project in that department.
  - `All` (blank value) → the whole portfolio (PMO / executives).
  A user with several rows gets the **union** of their grants.
- **Email is the join key.** `person.email` is already UPN-shaped (`first.last@theragen.com`), so the
  RLS filter matches `USERPRINCIPALNAME()` directly — no separate identity mapping table.
- **Default-deny.** With RLS enabled and no grant, a user sees nothing. A bootstrap grant for the PMO
  (`ScopeType = All`) must exist before the report is shared, or admins lock themselves out.
- **RLS only bites under per-user identity.** It has no effect for the shared `richard.allen` refresh
  account; it applies when the report is shared and opened by individual Entra users. This is a
  Service-config step (assign users/groups to the role), separate from the model build.

## The "Report Access" List → `pmbok.report_access`

New table `pmbok.report_access` (additive migration, app-resolved, the pmbok convention):

| Column | Notes |
|--------|-------|
| `access_id UUID PK` | uuid5 of the item id |
| `user_email VARCHAR NOT NULL` | the grantee's UPN/email (matches `person.email`) |
| `scope_type VARCHAR NOT NULL` | `Project` / `Department` / `All` |
| `scope_value VARCHAR` | project_code or department name; NULL for `All` |
| `granted_by_person_id UUID` | who authored the grant (author-fallback) |
| `active BOOLEAN NOT NULL DEFAULT TRUE` | soft-disable a grant without deleting the record |
| `granted_at TIMESTAMPTZ DEFAULT now()` | |
| `external_ref VARCHAR(64) UNIQUE` | idempotency anchor |

List columns: `UserEmail` (text, or a person picker resolved to email), `ScopeType` (choice),
`ScopeValue` (text — a ProjectCode or Department; blank for All), `Active` (choice Yes/No, default
Yes), `GrantedBy` (person, author-fallback), + `SyncStatus`/`SyncMessage`. `bi.report_access` exposes
the grants (active only) joined to a friendly name. Validation: `ScopeType` in domain; `ScopeValue`
required unless `ScopeType = All`; `ScopeValue` resolves to a real project/department when set
(airlock); `UserEmail` non-blank. **No audit beyond `granted_by`/`granted_at`** in v1 (a future
hardening item — see below).

## The sync (the proven pattern)

A `report_access` registry entry: `ACCESS_FIELDS` / `normalize_access` / `ACCESS_SELECT`;
`process_report_access` mirrors `process_decision` (authored content; create / `row_changed` update /
heal; no parent-child). `access_id = uuid5(NS, "thg/artifact/access/{item_id}")`. Editable in place
(toggle `Active`, change scope). Runs on the same 5:40 AM job.

## RLS in the model (TMDL `role` objects)

One **"Scoped Viewer"** role with a table-permission filter on `Project` (it propagates to every
related fact via the existing single-direction relationships):

```
'Project' filter (pseudo-DAX):
VAR me = USERPRINCIPALNAME()
RETURN
    CALCULATETABLE(             -- the user is granted this project directly,
        'Report Access',         -- its department, or All
        'Report Access'[User Email] = me,
        'Report Access'[Active] = TRUE(),
        OR( 'Report Access'[Scope Type] = "All",
            OR( 'Report Access'[Scope Type] = "Project" && 'Report Access'[Scope Value] = 'Project'[Project Code],
                'Report Access'[Scope Type] = "Department" && 'Report Access'[Scope Value] = 'Project'[Department] )))
    <> {}   -- expressed as a boolean filter on Project rows
```

(Concretely: a boolean column/measure `[Is Visible To Me]` evaluated per project row, used as the role's
`Project` filter expression. `Report Access` is a **disconnected** table — no relationship to Project —
queried inside the filter so it doesn't itself get filtered.) A separate **"All Access"** role with no
filter is optional convenience for admins (equivalent to an `All` grant).

## Build plan (when approved — a normal sub-stage)

1. **T1** `db/22_report_access.sql`: `pmbok.report_access` + `bi.report_access` (active grants, name
   resolution) + loader tuple. Apply live.
2. **T2** `artifact_lib`: `ACCESS_SCOPE_TYPES`, `validate_access`, `build_access_row` + tests.
3. **T3** "Report Access" List in the creator; sync wiring + `process_report_access`; live verify.
4. **T4** TMDL: a disconnected `Report Access` table + the `Scoped Viewer` RLS role (+ optional
   `All Access` role) + a `[Is Visible To Me]` helper; validate with Tabular Editor; **test the role**
   in Desktop's "View as role" with a sample UPN. Docs §Z Report Access. Republish.
5. **Service**: enable the report for the org; assign users/Entra groups to the `Scoped Viewer` role;
   seed the PMO `All` grants first.

## Open questions / future hardening (the "development process")

- **Entra group grants** — allow `ScopeType = Group` mapping to an Entra security group, so access
  follows group membership (less per-user churn). Needs a group→members resolution in the sync.
- **Access-change audit** — write `report_access` grants/revocations to `doc_mgmt.audit_trail_entry`
  (an `ACCESS_GRANT` / `ACCESS_REVOKE` action) so the access history is itself auditable. Recommended
  for a 21 CFR-adjacent system.
- **Object-level security** (hide whole tables/measures from some roles) — separate from RLS.
- **Periodic access review** — a `governance_health` check for grants to inactive persons or stale
  `All` grants.
- **Least-privilege default** — confirm "default-deny" is acceptable operationally (vs default-read).

## Verification (when built)

Unit: validators + builders. Live: grant/scope resolution + heal/idempotency (T3). Model: Tabular
Editor "View as role" for a `Project` grant, a `Department` grant, and an `All` grant, confirming each
sees exactly the expected projects; an ungranted user sees none. Service: a non-admin test account sees
only its granted projects in the published report.
