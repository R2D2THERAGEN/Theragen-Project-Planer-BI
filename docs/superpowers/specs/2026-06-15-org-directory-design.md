# Sub-stage D — Org Directory (Entra roster + PMO-curated department layer)

**Status (2026-06-15): SCOPED — ready to build.** Decisions locked with the user below.

## Why

RLS provisioning (and person resolution generally) needs a **canonical Theragen directory**: who works here, are they active, and which of the 8 departments are they in. Today `doc_mgmt.person` is populated **on demand** — a person row appears only when someone is referenced as an owner/approver/etc. in a SharePoint person field. There is no authoritative roster, so RLS grants can't be validated and "grant the Clinical team" isn't expressible.

## Ground truth (Entra probe, 2026-06-15, read-only)

`GET /users` (richard.allen delegated, first page of ~200+):
- **169 enabled · 141 members · 59 guests**, across multiple domains (`@theragen.com`, `@neurotech.us`, service accounts).
- **`department` is 87% blank** (175/200); the 25 populated are inconsistent/garbage — `Sales`, `SALES`, `Ops`, `Operations`, `Quality`, `Management`, `OCT`, `x509`, `x091`.

**Conclusion:** Entra is a good source for the **roster** (UPN, display name, enabled, member-vs-guest, job title) but **not** for **department** — the org structure isn't maintained there. So the directory = **Entra roster + a PMO-curated department layer**.

## Decisions (locked)

| Decision | Choice |
|---|---|
| **Department source** | **PMO-curated layer** — a "Staff Directory" SharePoint List (synced like every other List) is the source of truth for each person's department. |
| **Roster scope** | **All enabled members** (`accountEnabled = true AND userType = Member`), any domain. Excludes the 59 B2B guests; service accounts are weeded out via the curated layer (left unassigned / marked non-staff). |
| **Storage** | **Extend `doc_mgmt.person`** — single source of truth for people; existing owner/approver resolution keeps working and gets enriched. |

## Architecture

```
Entra (/users, enabled members)  ──►  sync_directory.py  ──►  doc_mgmt.person   (roster: upn, entra id, job title, is_active, source='entra')
                                            │  seeds (create-if-absent)
                                            ▼
                              "Staff Directory" List (PMO fills Department)
                                            │  reads back Department
                                            ▼
                                   doc_mgmt.person.department_id  ──►  bi.org_directory  ──►  model "Directory" + RLS validation
```

- **Roster pull** (Entra → person): paged `GET /users` `$select=id,displayName,userPrincipalName,mail,accountEnabled,userType,jobTitle`; keep `accountEnabled && userType=='Member'`. Upsert `person` by lower-cased email/UPN; enrich `upn`, `entra_object_id`, `job_title`, `is_active=true`, `source='entra'`. People previously `source='entra'` and absent from the current pull → `is_active=false` (deactivation; never hard-deleted). **Never touches SharePoint-resolved (`source='sharepoint'`) rows' active flag.**
- **Curated department layer** ("Staff Directory" List): the sync **seeds** one item per enabled member (`UPN`, `DisplayName` pre-filled, `Department` blank choice of the 8, `Active`) — create-if-absent, **never overwrites the PMO's Department choice**. The PMO fills the `Department` dropdown over time (incremental; access-needing people first). The sync **reads back** `Department` → resolves the 8-name → `person.department_id`. Unassigned → `department_id` stays NULL (flagged, not an error).
- **Work attributes only** — UPN, display name, job title, active, department. No personal data; guests excluded; the personal contact CSVs are explicitly **not** a source.

## RLS payoff

- `process_report_access` gains a **soft check**: if `UserEmail` isn't an active directory UPN, still sync but note it in `SyncMessage` (the airlock/audit precedent — warn, don't block).
- `governance_health.py` gains a check: **grants to non-directory or inactive users** → exceptions digest.
- Future (separate): Entra **security-group → role** provisioning so RLS is managed by group membership in Entra.

## Migration (additive, `IF NOT EXISTS`, inline psycopg — never the loader; append to loader tuple)

`db/24_person_directory.sql`: `ALTER TABLE doc_mgmt.person ADD COLUMN IF NOT EXISTS upn VARCHAR, entra_object_id VARCHAR UNIQUE, job_title VARCHAR, is_active BOOLEAN NOT NULL DEFAULT TRUE, source VARCHAR NOT NULL DEFAULT 'sharepoint', department_id UUID` (department_id only if absent — verify first; app-resolved, the db/10 convention). `CREATE OR REPLACE VIEW bi.org_directory` exposing `person_id, display_name, email, upn, job_title, is_active, source, dep.name AS department, dep.code AS department_code, (EXISTS active report_access grant) AS has_report_access`.

## Tasks (subagent-driven, two-stage review each — the proven cadence)

- **D-T1** — `db/24` (extend person + `bi.org_directory`) + loader tuple; live-apply; `information_schema` verify.
- **D-T2** — `artifact_lib`: `is_enabled_member`, `normalize_upn`/email lower-casing, `STAFF_DIRECTORY` validators, `build_person_directory_row`, department-name→canonical resolution (reuse `DEPARTMENTS`); **tests first**.
- **D-T3** — `tools/graph_directory.py`: paged `GET /users` (handle `@odata.nextLink`), filter enabled members, return the normalized roster; unit-test the filter/normalize purely (mock page payloads).
- **D-T4** — "Staff Directory" List in `create_artifact_lists.py` (UPN, DisplayName, Department[8 choices], Active, JobTitle) + `staff_directory_list_id` in config.
- **D-T5** — `tools/sync_directory.py`: Entra pull → upsert `person` (roster + is_active + source, deactivation) → **seed** Staff Directory List items (create-if-absent, preserve Department) → **read back** Department → set `person.department_id`. Dry-run first; live on the tenant; idempotent re-run = no-ops. Keep the other syncs' behavior untouched.
- **D-T6** — Scheduled job `\Theragen\SyncDirectory` (05:20, before the 05:30/05:40 syncs so resolution is fresh) → `tools/run_directory_sync.cmd`; update the automation inventory (SOP §5 + regenerate `docs/admin-map.md`).
- **D-T7** — TMDL `Directory` table over `bi.org_directory` + measures (Headcount, Headcount by Department, Active Staff, Unassigned-Department count, Staff with Report Access) + a light **People / Admin** report page; **RLS integration** (soft `report_access` UserEmail validation + `governance_health` grant-to-non-directory check).
- **D-T8** — Docs (`artifact-entry-setup.md` §Staff Directory; README; regenerate `admin-map.md` + `data-dictionary.md`); **e2e** (pull roster → assign a few departments in the List → sync → verify `person.department_id` + `bi.org_directory` + the RLS soft-check) + final whole-stage review + push.

## Risks / notes

- **Graph permission:** listing all org users needs `User.Read.All` / `Directory.Read.All` on the sync's app/delegated token. The probe succeeded under richard.allen, so the consent exists; confirm it holds for the scheduled (headless) run in D-T3/D-T5 (may need an app-permission + admin consent for unattended runs).
- **Two-source person rows:** the `source` discriminator + email-keyed upsert keep Entra-sourced and SharePoint-resolved persons from clobbering each other; deactivation only applies to `source='entra'`.
- **Service accounts** (`AccountsPayable@…`) come in under "all enabled members" → left unassigned / markable non-staff in the curated layer; not an error.
- **Bidirectional List:** the sync both creates List items (seed) and reads them (department) — a new pattern; create-if-absent must never overwrite the PMO's `Department` edits (the orphan-keep/heal discipline applies).
- Schema additions need an Allen **republish** to surface the Directory table/measures/page.
