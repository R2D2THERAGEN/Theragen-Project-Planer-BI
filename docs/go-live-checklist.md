# Go-Live Checklist — Tooltips (CL-6) & Row-Level Security (CL-7)

**Status: 2026-06-17.** Both features are **code-complete in the repo**; what remains is Desktop/Service
work that only the report owner (Allen) can perform under an interactive identity. This runbook is the
single place that tracks those steps. The deeper RLS reference lives in
[`artifact-entry-setup.md` §Z](artifact-entry-setup.md) ("Turning RLS on"); this file is the short,
checkable go-live list.

> Every step below assumes the standing prerequisite: **republish the `.pbip` from Power BI Desktop**.
> A data-only Service refresh will *not* surface new model tables, roles, or tooltip-page bindings.

---

## CL-6 — Activate report-page tooltips

**Code-complete:** all three tooltip pages carry the page-level `type: "Tooltip"` marker (the real
"allow use as tooltip" flag), and two are wired to a visual via a `visualTooltip` block
(`type: Canvas`, `section: <page>`, `show: true`):

| Tooltip page | Bound to | State |
|---|---|---|
| `tooltipProjectKpi` | **Portfolio** page → project table | ✅ wired |
| `tooltipRisk` | **Risk** page → risk register table | ✅ wired |
| `tooltipDocGovernance` | *(nothing yet)* | ⚠️ **built but unbound** |

**⚠️ Open gap — `tooltipDocGovernance`:** the page exists and is marked, but no visual references it, so
it will never pop. To activate it, add a `visualTooltip` block (`section: 'tooltipDocGovernance'`) to a
Controlled-Document visual. **Decision required:** wire it, or accept it as a defined-but-unused page
(harmless — it simply never triggers).

**Verify in Desktop after republish:**

- [ ] **Portfolio** → hover a project-table row → the *Project KPI* card pops (CPI, SPI, % complete,
      open CRs, signed-off?, days in current phase).
- [ ] **Risk** → hover a risk-register row → the *Risk* card pops (exposure, response status, overdue?).
- [ ] Resolve `tooltipDocGovernance` (wire it to a Controlled-Document visual, or leave it unbound).

> Note: `validate_pbir` checks `1.0.0` visuals but **skips** the `2.10.0` ones, so the tooltip
> rendering itself is only confirmable by eye in Desktop/Service — hence the hover checks above.

---

## CL-7 — Turn on Row-Level Security

**Code-complete:** the `Scoped Viewer` and `All Access` roles exist
(`definition/roles/*.tmdl`) and are referenced in `model.tmdl`. Default-deny: with RLS on, a user with
**no** active grant sees **nothing**; a user sees the **union** of their active grants. The visibility
rule is authored data — the **Report Access** List → `pmbok.report_access` → `bi.report_access` →
the `Scoped Viewer` role reads it via `USERPRINCIPALNAME()`.

**Current live grants (2026-06-17):** 1 active **All** grant — `richard.allen@theragen.com` — and 1
active **Project** grant. The All grant means Allen will not lock himself out.

**Steps:**

- [ ] **Test first in Desktop** — *Modeling → View as → Scoped Viewer*, enter a sample UPN, and confirm:
  - a **Project** grant → sees only that project;
  - a **Department** grant → sees only that department's projects;
  - an **All** grant → sees everything;
  - an **ungranted** UPN → sees nothing.
- [ ] **Seed PMO/admin `All` grants *before* sharing** — default-deny means anyone unconfigured opens a
      blank report. Add an `All` grant (via the Report Access List) for each PMO/admin needing full
      visibility. *(Only `richard.allen` has one today.)*
- [ ] **Publish**, then in the Service assign users / Entra groups to **Scoped Viewer** (admins to
      **All Access**) under the dataset's **Security** settings.
- [ ] **Validate with a non-admin account** — RLS is **inert for the refresh identity**; it only applies
      when a user opens the report under *their own* identity.

**⚠️ Caveat — the Distributor subject area is not access-scoped.** RLS filters the `Project` table; the
new **Distributor** model table is *standalone* (no relationship to `Project`), so a `Scoped Viewer`
sees **all distributors regardless of grant**. If distributor data should also be access-scoped, that's
a follow-up (the Sales & Distribution page would need its own grant dimension / role filter). Flag it if
it matters; otherwise the distributor network is treated as non-restricted reference data.

---

## After both are live

- Update [`CHANGELOG.md`](../CHANGELOG.md) per the change-control SOP (category `security` for the RLS
  go-live; `model` for the tooltip activation).
- Tick CL-6 / CL-7 closed.
