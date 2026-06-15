# Changelog

All notable changes to the **Theragen Project Planner** platform are recorded here, per the
[change-control process](docs/change-control-process.md). The version at the top is the current
platform version and **must equal** the root [`VERSION`](VERSION) file (a test enforces this).
Versioning is `MAJOR.MINOR`, aligned to delivery phases (see the SOP's version scheme).

Change categories: `lists` · `code` · `model` · `migration` · `security` · `docs`.
Each entry: the version, date, category tags, a summary, the approver role, and a representative commit.

A **data-sourced companion** — generated from the `pmbok.platform_change` register by
`tools/build_changelog.py` — is at [docs/platform-change-log.md](docs/platform-change-log.md). This file is the
curated release notes; that one is the register's queryable change log.

---

## 2.7 — 2026-06-14 · `model` `migration` `code` `lists`
**Change-control Round 2 — dogfood.**
- **Platform Change register:** `pmbok.platform_change` (`db/23`) + "Platform Changes" List + `process_platform_change` (audited) + the disconnected `Platform Change` model table + Platform measures — platform changes become authored, approved, audited rows.
- **Docs as controlled documents:** the change-control SOP, glossary, data dictionary, and README registered in `doc_mgmt.document` (new `REF` type) as `THG-OPS-SOP-001` / `THG-OPS-REF-001` / `THG-IT-REF-001` / `THG-IT-REF-002` — the controlled-document machinery applied to the platform's own docs.
- _Approver:_ PMO · _commits:_ `233776c` →

## 2.6 — 2026-06-14 · `docs` `model`
**Model documentation & change control.**
- Business glossary (`docs/glossary.md`); generated data dictionary (`docs/data-dictionary.md` + `tools/build_data_dictionary.py`); this change-control SOP, `CHANGELOG.md`, and `VERSION`.
- `///` descriptions across all model objects (field tooltips) + rich tooltip report pages.
- _Approver:_ PMO / Doc owner · _commits:_ `1afee45` →

## 2.5 — 2026-06-14 · `security` `model` `migration`
**Data-driven access control & row-level security.**
- `pmbok.report_access` (`db/22`) + "Report Access" List; `Scoped Viewer` / `All Access` RLS roles (default-deny, union-of-grants); grant/revoke/change audit; Entra B2B-guest matching by real email.
- _Approver:_ Security / PMO · _commit:_ `e314b11`

## 2.4 — 2026-06-14 · `code` `security`
**Compliance hardening.**
- Optional hard authority enforcement (`enforce_decision_authority` config toggle, soft-warn by default); true §11 e-signing design/scoping spec (decision-gated, not built).
- _Approver:_ Security / PMO · _commit:_ `ecddf11`

## 2.3 — 2026-06-14 · `model` `migration` `lists` `code`
**Earned Value Management.**
- `pmbok.cost_actual` (`db/21`) + "Cost Actuals" List (child-by-WBS); EVM measures AC / CV / CPI / EAC / VAC / TCPI.
- _Approver:_ BI owner · _commit:_ `bb331c2`

## 2.2 — 2026-06-14 · `model` `migration` `lists` `code`
**Risk responses.**
- `pmbok.risk_response` (`db/20`) + "Risk Responses" List (child-by-code); Risk Action measures (Risk Actions / Open / Overdue).
- _Approver:_ Data owner · _commit:_ `69c573c`

## 2.1 — 2026-06-14 · `docs` `code`
**Governance reporting & operationalize.**
- Four paginated RDL reports (Governance Dossier, CR Register, Document Register, Baseline & Phase-Gate Register) + shared `paginated_lib`; `governance_health.py` exceptions digest + wrapper.
- _Approver:_ BI owner · _commit:_ `5ecf559`

## 2.0 — 2026-06-14 · `model` `migration` `lists` `code`
**Phase 2 platform — schedule + governance.**
- Schedule activities + auto-WBS (2a); change requests + decisions + status-report sign-off + audit trail (2b); baselines + phase gates (2c-1); change-impact assessments (2c-2); controlled documents (2c-3); document RACI (2c-4); document versions + e-sig attestations (2c-5); governance change requests + assessments + LinkedCR (2c-6). Migrations `db/07`–`db/19`.
- _Approver:_ PMO · _commit:_ `141fd50`

## 1.0 — earlier · `code` `migration` `lists` `model`
**Phase 1 platform — intake + execution tracking (baseline).**
- SharePoint Lists → daily Python sync → Azure PostgreSQL → `bi.*` views → Power BI; projects, risks, milestones, status reports; the per-project status page. The foundation all later phases extend.
- _Approver:_ PMO · _commit:_ `f5cda55`
