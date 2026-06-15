# Theragen Project Planner — Platform Change Log

_Generated from the `pmbok.platform_change` register by `tools/build_changelog.py` — **do not edit by hand**. The register (authored via the Platform Changes List) is the source of truth for the platform change log; this complements the curated [CHANGELOG.md](../CHANGELOG.md) release notes (see the [change-control process](change-control-process.md))._

> 9 platform change(s) logged; latest version v2.7.

| Version | Date | Category | Status | Change | Approver | Commit |
|---|---|---|---|---|---|---|
| 2.7 | 2026-06-15 | Documentation | Proposed | Round 2 dogfood: platform change register (db/23 + Platform Changes List + process_platform_change sync wiring). |  |  |
| 2.6 | 2026-06-14 | Documentation | Deployed | Model documentation & change control - glossary, generated data dictionary, /// field tooltips, tooltip pages, change-control SOP/CHANGELOG/VERSION. |  | 7a11e5e |
| 2.5 | 2026-06-14 | Security & RLS | Deployed | Data-driven access control & RLS - report_access (db/22) + Scoped Viewer/All Access roles + Entra B2B-guest matching. |  | e314b11 |
| 2.4 | 2026-06-14 | Security & RLS | Deployed | Compliance hardening - enforce_decision_authority toggle + 21 CFR Part 11 design. |  | ecddf11 |
| 2.3 | 2026-06-14 | Lists & schema | Deployed | EVM - pmbok.cost_actual (db/21) + Cost Actuals List + AC/CV/CPI/EAC/VAC/TCPI measures. |  | bb331c2 |
| 2.2 | 2026-06-14 | Lists & schema | Deployed | Risk responses - pmbok.risk_response (db/20) + List + Risk Action measures. |  | 69c573c |
| 2.1 | 2026-06-14 | Documentation | Deployed | Governance reporting & operationalize - four paginated RDLs + governance_health digest. |  | 5ecf559 |
| 2.0 | 2026-06-14 | Semantic model | Deployed | Phase 2 platform - schedule+WBS, change & approval + audit trail, baselines/phase-gates, controlled documents/RACI/versions/attestations, governance CRs (2a-2c-6). |  | 141fd50 |
| 1.0 | 2026-06-13 | Sync + automation code | Deployed | Phase 1 - intake + execution tracking baseline (projects, risks, milestones, status reports; SharePoint -> Python sync -> Azure PostgreSQL -> bi views -> Power BI). |  | f5cda55 |

