# Field-Sales / Distributor Org — subject-area scope (sub-stage F)

**Status (2026-06-17): SCOPED, not built.** Surfaced from the BuildMoc workbook — Theragen's real go-to-market structure is a device-sales **distributor network**, a dimension entirely separate from the internal staff directory + the 8 departments.

## The structure (from `Master DIst` / `Sales Footprint` / `Mktg Rep to OC Team`)

```
Region (SE / MW / SW / NE)  ->  RSM (Regional Sales Manager)  ->  Marketing Rep  ->  Distributor
                                                                         |
                                                    + OCT Pod / Lead OCS-IAS (order-conversion team)
```

**Ground truth (probe):** 606 rows · **329 distinct distributors** · 4 regions (SE 110 / MW 100 / SW 98 / NE 75; 218 blank) · ~4 core RSMs (Jeff Williams, Tom Milroy, Ryan Davis, Scott Hannon) · Sales Type = Distributor (528) / Direct (77). **The data is messy** — `Status` is free-text (`Do Not Pay`, `Terminated 2023`, `Gone`, `PENDING INVENTORY`, `BGS`…), many blanks (Region/RSM ~⅓ blank), and RSM typos (`Tom Milory` vs `Tom Milroy`). A large share are historical/terminated.

## Proposed model

- **`sales.distributor`** (one row per distributor): `distributor_id`, `name`, `sales_type` (Distributor/Direct), `region`, `rsm` (canonicalized), `status_raw`, `status` (normalized: Active / Terminated / Inactive / Pending), `active` (bool), `products`, `email`, `external_ref`.
- Region + RSM as **denormalized columns** on the distributor (v1) — a `sales.rsm` / region dim only if cross-filtering needs it.
- **`bi.distributor`** view → a **Distributor** model table + measures: `Distributors`, `Active Distributors`, `Distributors by Region`, `Distributors by RSM`, `Terminated Distributors`, `Direct vs Distributor`.

## Data quality (the real work)

1. **Normalize `Status`** → a small controlled set (Active / Terminated / Inactive-"Do Not Pay" / Pending). The raw free-text is preserved in `status_raw`.
2. **Canonicalize RSM** (fix `Tom Milory`→`Tom Milroy`; map to the 4 core RSMs) + region blanks.
3. **Dedup** — 329 distinct distributors across 606 rows (multiple reps/products per distributor) → decide the grain (distributor dim vs distributor-rep assignment fact).

## Ingestion — the open decision

The data lives in **Excel maintained by sales ops**, not SharePoint. Two paths:
- **A — Periodic Excel import** (mirror `backfill_directory_from_ease.py`): a tool reads the `Master DIst` sheet, normalizes, upserts `sales.distributor`. Pragmatic for v1; re-run on each export.
- **B — SharePoint "Distributors" List** (the platform's authoring pattern) → daily sync. Ongoing authoring + airlock + audit, but someone must migrate 329 rows into the List first.

## Tasks (sub-stage F, when approved)

- **F-T1** `db/26` `sales` schema + `sales.distributor` + `bi.distributor`.
- **F-T2** `artifact_lib`: `normalize_distributor_status`, `canonical_rsm`, `normalize_region` + tests.
- **F-T3** the ingestion (import tool *or* List per the decision above) + dedup/grain.
- **F-T4** `Distributor` model table + measures + a Sales/Distributor report page.
- **F-T5** docs + e2e + push.

## Open decisions (for the build kickoff)

1. **Same model or separate?** The field-sales org is unrelated to the PMBOK project data. Add it as a new subject area in the same `.pbip`, or stand up its own model/report? (Cross-analysis with projects is the only reason to combine — likely none, so *lean separate subject area in the same model, no relationships to Project*.)
2. **Ingestion A (Excel import) vs B (List).** Lean **A** for v1 (the data is Excel-native + messy + mostly historical).
3. **Grain:** distributor dim (329) vs distributor-rep-product assignment fact (606).
4. **Scope:** distributors only, or also model the rep / OCT-pod / order-conversion structure (the `Mktg Rep to OC Team` sheet)?

## Out of scope (v1)

Linking distributors to orders/revenue (a CRM/ERP integration); the OCT-pod order-conversion workflow detail; the full rep roster as people (they overlap the staff directory only partially).
