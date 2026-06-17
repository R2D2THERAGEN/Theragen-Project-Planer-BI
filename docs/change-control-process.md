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
7. **Change-control reminder.** A **warn-only** pre-commit hook (`tools/check_change_control.py`, wired via `.githooks/pre-commit`) reminds you to add a `CHANGELOG.md` entry when a commit touches the semantic model / a migration / a List / the sync code. It never blocks. Enable once per clone: `git config core.hooksPath .githooks`.

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
| `\Theragen\SyncDirectory` | **05:20** daily | `tools\run_directory_sync.cmd` → `sync_directory.py` | Org-directory sync (sub-stage D): Entra roster → `doc_mgmt.person` + Staff Directory List seed + department read-back. Runs first so person resolution is fresh for the later syncs. |
| `\Theragen\SyncIntake` | **05:30** daily | `tools\run_intake_sync.cmd` | Intake-submission sync (Phase 1) |
| `\Theragen\SyncArtifacts` | **05:40** daily | `tools\run_artifact_sync.cmd` → `sync_artifacts.py` | Artifact sync (projects, risks, schedule, governance — all Phase-2 Lists) |
| Power BI **dataset refresh** | ~hourly / morning (Service-side) | Power BI Service scheduled refresh (and/or `tools/service_refresh.py`) | **Data-only** refresh of the published model |
| **Republish** (manual) | as needed | Power BI Desktop → Publish | Surfaces **new** tables / columns / measures / descriptions / roles |

**Critical distinctions:**
- The dataset **refresh is data-only** and is a **Power BI Service** control surface, **not** a Windows task. It cannot surface schema/model changes.
- A **republish** is a **manual** Desktop step and is the only way model/security/description changes go live.
- **Runtime copy = canonical repo (resolved 2026-06-14):** the repo lives at **`D:\GitHub\Theragen-Project-Planer-BI`** (off OneDrive), and both scheduled tasks run their wrappers **from that same path** — so the runtime copy *is* the git working tree. A code/automation change is therefore deployed simply by committing to that working tree (no separate copy to keep in sync). _Incident history:_ the tasks previously pointed at a `C:\…\OneDrive\…\Theragen-Project-Planer-BI` copy that OneDrive dehydration **wiped on 2026-06-13**, silently failing the 05:30/05:40 syncs (`0x1`) until they were repointed to D: on 2026-06-14. **Rule: never host the runtime repo inside a OneDrive-synced folder.**

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

## 7. Electronic signatures (21 CFR Part 11) — documented control statement

**Approvals and attestations recorded in this system are governance attestations, *not* 21 CFR Part 11 electronic signatures.** Every sign-off surface — document approvals (`document_approval`), status-report sign-offs, CR / governance-CR decisions, phase-gate approvals, baseline attestations — is a management/governance record. Document approvals are server-computed attestations (a SHA-256 over the signed facts; no signer IP), labelled **"Attestation (non-§11)"** in the model, the `bi.document_approval` view, and §T of the artifact-entry guide.

Where a record legally requires a **21 CFR Part 11** signature (a GxP / QSR predicate-rule record), that signature is executed in the **validated QMS**; this system holds the corresponding management attestation. **No Part 11 signature is created, stored, or implied here.**

**Status (2026-06-15): Path 1 selected** — see [`2026-06-14-part11-determination-request.md`](superpowers/specs/2026-06-14-part11-determination-request.md). The PMO is evaluating a potential QMS integration; if it proceeds, the QMS remains the system of record for §11 signatures and this statement stands. Quality/Regulatory confirms the per-record applicability; if any record is ever determined to require §11 *here*, Path 2 (validated provider) in `…-part11-esign-design.md` is built and this statement revised.

---

## 8. Round 2 — dogfood the change control (BUILT 2026-06-15, v2.7)

The honor-system register was promoted into the platform itself, reusing the proven List→sync→`bi`→audit machinery:
- **"Platform Changes" List → `pmbok.platform_change`** (`db/23`) — every platform change is an authored, audited row, surfaced in BI (the `Platform Change` table + Platform measures) and as the generated [`docs/platform-change-log.md`](platform-change-log.md).
- The change-control SOP / glossary / data dictionary / README are **registered as `doc_mgmt` controlled documents** (new `REF` type → `THG-OPS-SOP-001`, `THG-OPS-REF-001`, `THG-IT-REF-001/002`) with v2.7 versions + non-§11 attestations.
- Automated enforcement: the **warn-only change-control reminder** (principle 7).
