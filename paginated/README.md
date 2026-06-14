# Theragen Status Report — Paginated (.rdl)

Pixel-perfect, constant-layout version of the leadership one-pager (letter
landscape). Same sections as the interactive **Project Status Report** page and
the Sync 3.0 status deck: project header, MAIN STATUS traffic light, Project
Description, Business Value, Health Check, RAID, Key Project Areas,
Accomplishments, Next Steps, key legend.

All seven datasets are **DAX queries against the published semantic model** —
every number reuses the model's measures, so the paginated and interactive
reports can never disagree.

## One-time setup

1. **Publish the semantic model**: open `Theragen Project Planner.pbip` in
   Power BI Desktop → Publish → choose your workspace.
2. Install the free [Power BI Report Builder](https://aka.ms/pbireportbuilder).
3. Open `Theragen Status Report.rdl` in Report Builder.
4. In the Report Data pane, double-click the **TheragenModel** data source and
   repoint it at the published semantic model (Build permission required) —
   the placeholder connect string contains `YOUR_WORKSPACE`.
5. Run (F5): pick a project in the **Project** dropdown → constant one-pager.
6. Publish (File → Publish) to the **same workspace** as the model.

## Notes

- License: same as regular reports — Pro/PPU publishes to shared workspaces;
  no Premium capacity required.
- Layout is fixed: tables grow and paginate (a 30-row RAID list prints all 30
  rows), unlike the interactive page where long tables scroll.
- Export to PDF / schedule email subscriptions from the service for the
  Strategic Projects meeting cadence.
- One project per render via the `ProjectCode` parameter. The service can't
  burst multiple parameter values into a single PDF (and paginated reports
  don't support subreports), so a full portfolio packet = one export per
  project, or a Power Automate flow looping the parameter.
- Regenerate from source after layout changes: `python tools/build_paginated.py`
  (then re-apply the data source connection in Report Builder).

---

# Governance & document reports (.rdl)

Four print / PDF / archive-ready **records** for the governance + controlled-document
data (the audit-oriented counterpart to the interactive **Governance & Documents**
page). All bind to the same published semantic model via DAX as the Status Report —
one source of truth — so the registers and the page can never disagree.

| Report | Parameter | Contents |
|--------|-----------|----------|
| **Theragen Governance Dossier.rdl** | `@DocID` | One printable packet per controlled document: metadata header + RACI matrix + version history + **approval attestations (non-§11)** + the governance change requests (CHG-NNN) that target it. The audit dossier. |
| **Theragen Governance CR Register.rdl** | none | Every governance change request with class / decision / decider / status, plus the per-department impact assessments. |
| **Theragen Controlled Document Register.rdl** | none | The org-wide controlled-document portfolio (type / department / owner / status / version / next-review-due). |
| **Theragen Baseline & Phase Gate Register.rdl** | `@ProjectCode` | Project baselines (schedule / budget / scope, versioned, immutable) + the phase-gate transition log. |

## Setup (same as the Status Report)

1. **Republish the semantic model first** — these DAX datasets reference the
   governance tables (`Governance Change Request`, `Document Version[Linked CR]`,
   etc.), which only exist in the published model after a republish from Desktop.
2. Open each `.rdl` in Power BI Report Builder → repoint the **TheragenModel**
   data source at the published model (Build permission) → Run (F5) → Publish to
   the **Playground** workspace.

## Notes

- The approval section labels every row **"Attestation (non-§11)"** (sourced from
  the model's `Attestation Kind`) — never represent these as 21 CFR Part 11
  signatures.
- Tables grow and paginate (a 40-version history prints all 40 rows).
- Regenerate all four after edits: `python tools/build_paginated_governance.py`
  (shared RDL helpers live in `tools/paginated_lib.py`; then re-apply the data
  source connection in Report Builder). The Status Report generator
  (`build_paginated.py`) is independent and unchanged.

---

# Subscriptions — scheduled PDF delivery

Once a report is published to the workspace, schedule it from the **Power BI
service** (no code; Pro/PPU is enough for shared workspaces):

1. Workspace → the published paginated report → **⋯ → Subscribe to report** (or
   **Manage subscriptions → New subscription**).
2. Set the recipients, the **frequency** (e.g. weekly for the Strategic Projects
   cadence), the time, and **attach full report as PDF**.
3. For a parameterized report (Dossier `@DocID`, Baseline `@ProjectCode`), the
   subscription captures the **current parameter value** — one subscription per
   document/project. To burst every document into one run, drive the `@DocID`
   parameter from a **Power Automate** flow (loop the doc list, render each to
   PDF) — paginated reports don't support multi-value bursting natively.
4. Pair with the **governance health digest** (`tools/governance_health.py`, see
   `docs/artifact-entry-setup.md`) for the exception side: the registers/dossier
   give the full picture on a cadence; the digest flags only what needs action.
