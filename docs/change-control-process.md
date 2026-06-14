# Change & Configuration Management Process (SOP)

| | |
|---|---|
| **Document** | Change & Configuration Management Process |
| **Applies to** | The Theragen Project Planner platform (sync code, database, semantic model, reports, Lists, docs) |
| **Current platform version** | see [`VERSION`](../VERSION) and the top of [`CHANGELOG.md`](../CHANGELOG.md) |
| **Owner** | PMO / Operations |
| **Related** | [Glossary](glossary.md) · [Data dictionary](data-dictionary.md) · [Artifact entry setup](artifact-entry-setup.md) |

This SOP is the single written rule for **how the platform is allowed to change**. It is itself a controlled
document: changes to it follow the **Documentation** row below.

> **Scope boundary.** This governs changes to the **system** (its code, schema, model, reports, Lists, docs).
> It does **not** govern the business **data** authored day-to-day through the SharePoint Lists — that flows
> through the validation/airlock/audit rules described in [artifact-entry-setup.md](artifact-entry-setup.md).

---

## 1. Principles

1. **Additive & idempotent.** Schema changes are additive (`ALTER … ADD COLUMN IF NOT EXISTS`, new tables/views), applied via inline migrations and appended to the loader for from-scratch rebuilds. **The loader is never re-run against the live database, and the database is never reseeded.**
2. **Audit by default.** Every governance state change writes an append-only `doc_mgmt.audit_trail_entry` row inside the same transaction as the change.
3. **Single source of truth.** A fact is authored once and propagated: a model object's `///` description *is* its tooltip *and* its data-dictionary entry; the root `VERSION` *is* the platform version cited by the changelog and the dictionary stamp.
4. **Default-deny security.** RLS shows a user nothing until an explicit grant exists; access grants are airlocked and audited.
5. **Dry-run byte-identical.** A change to one sync artifact must not alter the dry-run output of any other artifact (the two morning syncs are live).
6. **Green at every commit.** `pytest` passes, `tools/validate_pbir.py` is clean, and `build_data_dictionary --audit` exits zero on every commit.

---

## 2. Change taxonomy & controls

Every platform change falls into one of six categories. For each, these five controls apply.

| Category | Examples | Versioned by | Review / Approval | Test / Validate gate | Deploy / Automation | Recorded |
|---|---|---|---|---|---|---|
| **Lists & schema** | SharePoint authoring Lists — new column / new List — via `tools/create_artifact_lists.py` | git SHA + List column-set note | Data owner / PMO | sync **airlock** + `validate_*` | idempotent creator re-run; the **05:40 `SyncArtifacts`** job picks it up next morning | CHANGELOG + sync `SyncMessage` |
| **Sync + automation code** | `tools/sync_artifacts.py`, `tools/artifact_lib.py`, the scheduled tasks / `.cmd` wrappers | git SHA | Eng lead (two-stage review) | `pytest` green **+ dry-run byte-identical** for untouched artifacts | commit → **update the runtime copy** (see §5) → Task Scheduler runs it | CHANGELOG |
| **Semantic model** | TMDL tables / columns / measures / roles / descriptions | git SHA + **model `vMAJOR.MINOR`** | BI owner | Tabular Editor BPA + `validate_pbir` + `build_data_dictionary --audit` | **Allen republishes** the `.pbip` from Power BI Desktop | CHANGELOG + dictionary **provenance stamp** |
| **DB migration** | `db/NN_*.sql` — additive, `IF NOT EXISTS` | the **`db/NN` sequence number** | Data owner | `information_schema` verify post-apply | inline `psycopg` against live; appended to the loader tuple (**never reseed**) | CHANGELOG |
| **Security / RLS / access** | RLS roles, `report_access` grants, `enforce_decision_authority` | git SHA + grant audit | Security / PMO | Desktop **View-as-role** + `pytest` | republish + assign users/groups to roles in the Service | `audit_trail_entry` (`ACCESS_*`) + CHANGELOG |
| **Documentation** | glossary, data dictionary, this SOP, README | doc-header / `VERSION` + changelog | Doc owner | `--audit` (for the dictionary); regenerate | git only | CHANGELOG |

---

## 3. Change lifecycle

```
propose  →  review  →  approve  →  test / validate  →  deploy / republish  →  record
```

1. **Propose** — a brief description + the category it falls under.
2. **Review** — the category's reviewer (§4) examines it; code changes get a two-stage (build + quality) review.
3. **Approve** — the category's approver signs off (recorded in the CHANGELOG entry's _Approver_).
4. **Test / validate** — run the category's gate (the *Test / Validate* column). Nothing merges red.
5. **Deploy / republish** — run the category's deploy path. **Model/security changes require an Allen republish** to surface; a data-only refresh cannot.
6. **Record** — add a `CHANGELOG.md` entry and, when the model or platform version moves, bump `VERSION` **in the same commit**.

---

## 4. Approval matrix

| Role | Owns sign-off for | Current holder |
|---|---|---|
| **Data owner** | Lists & schema, DB migrations, Risk/Cost data shapes | PMO (Allen) |
| **Eng lead** | Sync + automation code | Allen |
| **BI owner** | Semantic model, measures, reports | Allen |
| **Security / PMO** | RLS, access grants, authority enforcement, §11 posture | PMO (Allen) |
| **Doc owner** | Glossary, data dictionary, this SOP, README | PMO (Allen) |

> Theragen runs a **single maintainer** today, so all roles currently resolve to Allen / PMO. The matrix exists so
> the roles can be **separated as the team grows** without re-deriving who owns what. Cross-checks (the audit
> trail, two-stage code review, the automated gates) are the compensating control while roles overlap.

---

## 5. Automation inventory

Confirmed from Windows Task Scheduler (2026-06-14):

| Job | Schedule | Runs | Purpose |
|---|---|---|---|
| `\Theragen\SyncIntake` | **05:30** daily | `tools\run_intake_sync.cmd` | Intake-submission sync (Phase 1) |
| `\Theragen\SyncArtifacts` | **05:40** daily | `tools\run_artifact_sync.cmd` → `sync_artifacts.py` | Artifact sync (projects, risks, schedule, governance — all Phase-2 Lists) |
| Power BI **dataset refresh** | ~hourly / morning (Service-side) | Power BI Service scheduled refresh (and/or `tools/service_refresh.py`) | **Data-only** refresh of the published model |
| **Republish** (manual) | as needed | Power BI Desktop → Publish | Surfaces **new** tables / columns / measures / descriptions / roles |

**Critical distinctions:**
- The dataset **refresh is data-only** and is a **Power BI Service** control surface, **not** a Windows task. It cannot surface schema/model changes.
- A **republish** is a **manual** Desktop step and is the only way model/security/description changes go live.
- **Runtime-copy note (open item):** the two scheduled tasks execute from `C:\Users\Allen\OneDrive\…\Theragen-Project-Planer-BI`, while the canonical git repo is the relocated **D:** archive. A code/automation change is therefore **not deployed by `git commit` alone** — the runtime C: copy must reflect the committed change (via a `git pull` in that clone, or whatever sync keeps C: current). **TODO: confirm and document the C:↔D: relationship** and the exact step that propagates a commit to the runtime copy.

---

## 6. Versioning & provenance

**Version scheme.** The platform version is `MAJOR.MINOR`, held in the root [`VERSION`](../VERSION) file:
- **MINOR** bumps for each shipped capability/sub-stage (the normal case).
- **MAJOR** bumps for a phase-level milestone or a breaking change to the model/schema contract.
- Other artifacts carry their own native version: **code** = git SHA; **migrations** = the `db/NN` sequence; **model** = `VERSION` + git SHA; **reports** = git SHA.

**The CHANGELOG is authoritative for history; `VERSION` is authoritative for the current number.** They must agree: bumping `VERSION` and adding the matching top `CHANGELOG.md` entry happen in the **same commit**. `tests/test_changelog_version.py` fails if they drift.

**Data-dictionary provenance stamp** (the contract `tools/build_data_dictionary.py` implements in G-T3). The generated `docs/data-dictionary.md` opens with a header derived from the **model's own git state**, so regenerating against an unchanged model reproduces it byte-for-byte (no timestamp churn):

```
> Generated from model <short SHA> (<commit date>) · platform v<VERSION>
> N tables · N columns · N measures · N relationships · N roles
```

- `<short SHA>` / `<commit date>` = the **last commit that touched the `*.SemanticModel` directory** (`git log -1 -- "<model dir>"`), **not** `HEAD`/now.
- `v<VERSION>` = the root `VERSION` file.
- counts = computed by the parser. Git unavailable → SHA/date degrade to `unknown` (the doc still generates).

---

## 7. Round 2 — dogfood the change control (planned, not yet built)

Promote this honor-system register into the platform itself, reusing the proven List→sync→`bi`→audit machinery:
- A **"Platform Change" List → `pmbok.platform_change`** register (category, summary, version, status, requested/approved-by, git SHA) — every platform change becomes an **authored, approved, audited** row.
- **Register the glossary / data dictionary / this SOP as controlled documents** in `doc_mgmt.document` + `document_version` + `document_approval`, so the documentation is versioned + attested **through the very system it documents**.
- Optional automated enforcement: a `governance_health`-style check for changes lacking a version/approval/doc-update, and/or a pre-commit hook.

Gated on Round-1 landing + a go-ahead (per the locked "both, phased" + "documented + existing gates" decisions).
