# Change-Control Round 2 — Dogfood the Platform's Own Governance

Round 1 (sub-stage G) gave the platform a change-control SOP, a backfilled `CHANGELOG.md`, a `VERSION`, and a generated data dictionary — an **honor-system** register. Round 2 promotes that into the platform itself, reusing the proven List→sync→`bi`→audit machinery and the existing controlled-document lifecycle, so **the platform governs its own changes and documents through the very system it is**.

Two independent capabilities.

---

## R2-A — "Platform Change" register (the changelog as live, governed data)

Every platform change becomes an **authored, approved, audited** row — queryable, in BI, with an audit trail — alongside the human-readable `CHANGELOG.md`.

### Migration — `db/23_platform_change.sql` (additive, inline psycopg, append to loader; never reseed)
`CREATE TABLE pmbok.platform_change (change_id UUID PK, category VARCHAR NOT NULL, summary TEXT NOT NULL, version VARCHAR, status VARCHAR NOT NULL DEFAULT 'Proposed', requested_by_person_id UUID, approved_by_person_id UUID, git_sha VARCHAR(40), changed_at DATE, external_ref VARCHAR(64) UNIQUE)` — **project-less** (the `report_access` precedent), app-resolved persons (the db/10 convention, no DB FKs). `CREATE OR REPLACE VIEW bi.platform_change` (joins `doc_mgmt.person` for requested/approved names; exposes category/summary/version/status/git_sha/changed_at).

### "Platform Changes" List → `pmbok.platform_change` (creator)
`Category` (choice = the 6 SOP categories: Lists & schema / Sync + automation code / Semantic model / DB migration / Security & RLS / Documentation), `Summary` (ml), `Version` (text, e.g. `2.7`), `Status` (choice **Proposed / Approved / Deployed**, default Proposed), `RequestedBy` (person, author-fallback), `ApprovedBy` (person), `GitSHA` (text), `ChangedDate` (date, default `createdDateTime`) + bookkeeping. `platform_change_list_id` → `db/.m365.local.json`.

### Pure logic (`artifact_lib.py` + tests-first)
`PLATFORM_CHANGE_CATEGORIES` (the 6), `PLATFORM_CHANGE_STATUSES = ["Proposed","Approved","Deployed"]`; `validate_platform_change(it)` (required Category∈domain, Summary; Status∈domain; ApprovedBy resolvable when Status≠Proposed); `build_platform_change_row(it, requested_by_id, approved_by_id)`. `change_id = uuid5(NS, "thg/artifact/platformchange/{item_id}")`; `external_ref = item_id`.

### Sync (`sync_artifacts.py`)
`process_platform_change` mirrors **`process_decision`** (authored content; create / `row_changed` update / heal) **+ audit**: `write_trail` inside the per-item txn — `PLATFORM_CHANGE_CREATE` on insert, `PLATFORM_CHANGE_APPROVE` on a Status→Approved transition, `PLATFORM_CHANGE_DEPLOY` on Status→Deployed. Actor = ApprovedBy (or RequestedBy). Registry entry near `decision` (project-less, order-independent). Live-verify a couple of rows + the approve-transition audit; **keep other artifacts' dry-run byte-identical**.

### Model (TMDL) + measures
New `Platform Change.tmdl` over `bi.platform_change` (mirror `Decision.tmdl`; disconnected — no relationship to Project, it's platform-wide). Measures (folder **Platform**): `Platform Changes`, `Changes by Category` (use the Category column in a matrix), `Changes Pending Approval` (`Status="Proposed"`), `Changes Deployed`. **Republish** required to surface (the standing rule).

### Deferred capstone (note, do not build now)
A generator that emits `CHANGELOG.md` *from* the register (register = source of truth). Skipped to avoid divergence with the hand-maintained + drift-guarded `CHANGELOG.md`; the register and the markdown coexist for now.

### R2-A tasks
T1 db/23 + bi view (live) · T2 artifact_lib + tests · T3 List + sync write path (live) · T4 TMDL table + measures + docs.

---

## R2-B — platform docs as controlled documents (dogfood the doc-control machinery)

**No new code** — uses the *existing* Controlled Documents / Document Versions / Document Approvals Lists (2c-3/2c-5). The platform's own governance docs become `doc_mgmt.document` rows with a version + an attestation, demonstrating the controlled-document lifecycle on real documents.

- **One additive lookup:** add a **`REF` (Reference)** document type to `tools/seed_doc_lookups.py` (idempotent `ON CONFLICT DO NOTHING`; + the loader parity block) — the glossary/dictionary/README are reference docs with no fit among the existing 8 types. The SOP is a true `SOP`.
- **Author (via the existing Lists, live):**
  | Document | Type | Dept | Minted DocID |
  |---|---|---|---|
  | `docs/change-control-process.md` | SOP | Operations / PMO | THG-OPS-SOP-NNN |
  | `docs/glossary.md` | REF | Operations / PMO | THG-OPS-REF-NNN |
  | `docs/data-dictionary.md` | REF | IT / Data / Security | THG-IT-REF-NNN |
  | `README.md` | REF | IT / Data / Security | THG-IT-REF-NNN |
  Owner = PMO; `storage_path` = the git path. Then a **Document Version** (e.g. `2.6`) + a **Document Approval** (attestation, non-§11) for each.
- Verify the rows surface in `bi.document` / `bi.document_version` / `bi.document_approval`; the platform docs now carry the same review/version/attestation lifecycle as any controlled document.

### R2-B tasks
T5 add REF doc type to the seeder (live, idempotent) · T6 author the 4 platform docs as controlled documents + versions + attestations (live) + verify.

---

## Verification (Round 2)
- Unit: `validate_platform_change` + `build_platform_change_row`.
- Live: a Platform Change row create + Status→Approved audit (`PLATFORM_CHANGE_*`); the 4 platform docs as `doc_mgmt.document` rows with a version + attestation each.
- Model: `validate_pbir` clean; `build_data_dictionary --audit` 0 (the new Platform Change table's columns get `///` descriptions); republish note.
- `pytest` green at every commit; final review; push.

## Out of scope / deferred
- The CHANGELOG-from-register generator (capstone).
- Automated enforcement (pre-commit / CI gate that a model/List change has a matching Platform Change row) — a future hardening.
- Linking each Document Version to a git commit SHA automatically (manual version authoring for now).
