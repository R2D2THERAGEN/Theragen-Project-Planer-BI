# Power BI Report Translation Playbook

## Overview

Complete pipeline for translating a Power BI report from English to a target locale (e.g., sv-SE). Covers BOTH the semantic model (via MCP tools) AND the report layer (via JSON file editing). Designed to be executed in ONE pass with ZERO babysitting.

### What Gets Translated

| Layer | Method | Covers |
|-------|--------|--------|
| **Semantic Model** | MCP tools (Phases 0-9) | Table/column/measure names (captions), data values, DAX expressions, date tables |
| **Report Definition** | JSON file editing (Phase 10) | Visual titles, text boxes, button labels, page names, bookmarks, axis labels |

### Two Translation Mechanisms

1. **Captions** (sv-SE culture translations) — Power BI shows these when the user's locale is sv-SE. The physical object names stay English. This is the standard multi-language approach.
2. **Data/expression changes** — Physical changes to table data and DAX expressions. These show regardless of locale.
3. **Report JSON changes** — Direct edits to the report definition files. These show regardless of locale.

---

## Pre-Flight

### Step 0: Inventory the Model

Before touching anything, build a complete map of the model.

- [ ] **0.1** List all tables with row counts and partition source types (M vs Calculated vs DirectQuery)
  ```
  Query INFO.TABLES() for names, IDs
  Query COUNTROWS() for each table
  Get partition sourceType for each table
  ```
- [ ] **0.2** Classify tables into buckets:
  - **Calculated (DAX)**: Can translate and refresh immediately
  - **M/Power Query with static data** (Base64, Table.FromRows): Can translate and refresh immediately
  - **M/Power Query from source**: Need source connection OR rebuild as static if small enough (<100 rows)
  - **M/Power Query from source (large)**: Use List.Generate/List.Dates for programmatic rebuild, or add Table.TransformColumns steps (requires credentials for refresh)
- [ ] **0.3** List all measures with expressions
- [ ] **0.4** List all calculated columns with expressions
- [ ] **0.5** Check existing translations (culture, property types already set)
- [ ] **0.6** Document the connection name and model details
- [ ] **0.7** Inventory report JSON files — list all pages, visual titles, text boxes

**Output**: Full inventory. Know exactly what you're dealing with across BOTH layers.

---

## Phase 1: Model Metadata Translations (Captions)

This translates the NAMES of tables, columns, and measures as they appear in field lists and visual headers (when viewed in sv-SE locale).

- [ ] **1.1** Create culture if not exists (e.g., sv-SE)
- [ ] **1.2** Translate ALL table captions
- [ ] **1.3** Translate ALL column captions (every column in every table)
  - SK/surrogate key columns: keep original name as caption (e.g., `CostCenter_SK` → `CostCenter_SK`)
  - Hierarchy group columns: translate (e.g., `Company Group (groups)` → `Företagsgrupp (grupper)`)
  - Data columns: translate (e.g., `LegalEntity` → `Juridisk person`)
- [ ] **1.4** Translate ALL measure captions
  - Use `INFO.MEASURES()` with `TableID` → `INFO.TABLES()` lookup to find actual table names. Measures may live in unexpected tables (e.g., DynamicColumns, not _Measures).
- [ ] **1.5** Verify: Query translation counts match total object counts
  ```
  Total tables = translated table captions
  Total columns = translated column captions
  Total measures = translated measure captions
  ```

**Gate**: 100% caption coverage before proceeding.

---

## Phase 2: Calculated Table Data Values

These are tables defined with DAX DATATABLE/ROW expressions. The data is hardcoded English text.

- [ ] **2.1** List all Calculated partitions
- [ ] **2.2** For each: query the data, identify English text values
- [ ] **2.3** Translate the DAX expression (DATATABLE values)
  - NAMEOF() references are safe — they reference physical column names, not captions
- [ ] **2.4** Refresh each with Calculate type
- [ ] **2.5** Verify: query each table, confirm all values are translated

**Common tables**: Selector tables, parameter tables, waterfall steps, KPI lists, graph selectors

---

## Phase 3: M/Power Query Static Data Tables

Tables with M expressions containing Base64-encoded data or Table.FromRows with hardcoded values.

- [ ] **3.1** Identify M partitions with Base64 or hardcoded data (look for `Binary.FromText`, `Table.FromRows` with literal values)
- [ ] **3.2** Query current data to see English values
- [ ] **3.3** Rewrite M expression with translated data (replace Base64 with explicit Table.FromRows using Swedish values)
- [ ] **3.4** Refresh each with Full type
- [ ] **3.5** Verify: query each table, confirm translation

---

## Phase 4: Cascading Breakage Scan (CRITICAL)

**This is the step that gets missed.** After changing data values in Phase 2-3, any DAX that matched on those old English values is NOW BROKEN.

- [ ] **4.1** Search ALL measures for ALL changed values in ONE query:
  ```
  -- Build one compound FILTER instead of N separate queries
  EVALUATE
  FILTER(
    INFO.MEASURES(),
    CONTAINSSTRING([Expression], "old_value_1") ||
    CONTAINSSTRING([Expression], "old_value_2") || ...
  )
  ```
- [ ] **4.2** Same compound query for ALL calculated columns in one pass:
  ```
  EVALUATE FILTER(INFO.COLUMNS(), [Expression] <> BLANK() &&
    (CONTAINSSTRING([Expression], "old_value_1") || ...))
  ```
- [ ] **4.3** Update every found measure/column to use the new Swedish value
  - Include color/conditional formatting measures — they often compare against data values
- [ ] **4.4** Verify: no measures contain any of the old English values

**Common patterns that break**:
- SWITCH statements matching on selector values ("Display Budget" → "Visa budget")
- IF/CONTAINSSTRING checks on parameter names ("LY" → "FÅ")
- Filter expressions on status values (dPatient[status] = "active")
- Comparison labels ("vs LY" → "mot FÅ")
- Error/fallback messages ("No LY Data Available")
- Color measures comparing DynamicColumns[Category] ("Year-Month" → "År-Månad")

---

## Phase 5: Measure Display Text

Measures that RETURN English text visible to users.

- [ ] **5.1** Search ALL measure expressions for quoted strings:
  ```
  Patterns to search:
  - Common English words: "Country", "Clinic", "Revenue", "Budget", "Total",
    "Year", "Month", "Week", "Selected", "Display", "Active", "Current",
    "Average", "Filter", "Show", "All", "None", "Other", "Yes", "No",
    "N/A", "Error", "Warning", "vs ", "per ", "Forecast", "Actuals",
    "Churn", "Outcome", "Invoiced", "Customer", "Ledger", "Profit",
    "Board", "Multiple", "Last Updated"
  - Label patterns: "Label", "Title", "Header", "Text"
  - Fallback values: "No data", "Not available", "N/A"
  ```
- [ ] **5.2** For each found measure, determine if the string is:
  - **User-facing display text** → TRANSLATE
  - **Internal filter/logic value** → check if data it matches was also translated
  - **Source column name reference** → DO NOT translate (these are DAX identifiers)
  - **Comment** → ignore
  - **Pre-existing broken measure** → document and skip (can't update measures referencing deleted tables/columns)
- [ ] **5.3** Update all user-facing text to Swedish
- [ ] **5.4** Update all internal filter values to match their translated data sources
- [ ] **5.5** Verify: re-scan, confirm no remaining English display text

---

## Phase 6: Source Table Data Values

Dimension/fact tables loaded from external sources (Fabric, SQL, etc.) that contain English text visible in slicers, axes, tooltips.

- [ ] **6.1** For EACH source table, query distinct values of ALL text columns
- [ ] **6.2** Identify which text columns contain user-visible English values
- [ ] **6.3** Skip columns that are system identifiers, proper nouns, or universal codes
- [ ] **6.4** For each table needing translation, check row count:
  - **< 100 rows**: Rebuild as static M table (#table constructor)
  - **100-500 rows**: Consider static rebuild or `List.Generate` for programmatic data
  - **> 500 rows**: Use `List.Generate`/`List.Dates` for programmatic rebuild, or add `Table.TransformColumns` step (requires source credentials)
- [ ] **6.5** For static rebuilds: query ALL data, construct M expression, update partition, refresh
- [ ] **6.6** After each table change, run Phase 4 scan for that table's old values
- [ ] **6.7** Refresh dependent tables that reference the changed table

**Priority source tables** (commonly have English):
- Date tables (month names, weekday names, quarter labels) → ALWAYS check
- Version/forecast tables (status labels, type names) → ALWAYS check
- Dimension tables (roles, categories, types, statuses) → ALWAYS check
- Dynamic column/pivot tables (category labels, comparison headers) → ALWAYS check

---

## Phase 7: Date Table Special Handling

Date tables deserve their own step because they ALWAYS have English and affect EVERY page.

- [ ] **7.1** Check for English in: MonthName, Weekday/DayName, Month_Short, Quarter labels, PastOrFuture, WeekName
- [ ] **7.2** Best approach: rebuild as self-contained M expression using:
  - `Date.ToText(date, "MMMM", "sv-SE")` for month names
  - `Date.DayOfWeekName(date, "sv-SE")` for day names
  - NOT `Text.From()` with format parameter (doesn't work in M)
- [ ] **7.3** Preserve all computed columns (69+ columns typical). Compute everything from the date value.
- [ ] **7.4** Verify date range matches original
- [ ] **7.5** Refresh ALL dependent tables:
  - `_Date_Prev`, `_DateComparison`, `_DateComparison2`, etc.
  - Strip `DBConn` references from dependent M expressions first if needed

---

## Phase 8: Relationship Integrity Check

Translated values must match across related tables.

- [ ] **8.1** List all relationships in the model
- [ ] **8.2** For each relationship where the key column contains translated text:
  - Query distinct values from BOTH sides
  - Confirm they match exactly
- [ ] **8.3** Note: most relationships use numeric SK/ID/Date keys — these are safe. Quick scan usually sufficient.

---

## Phase 9: Full Verification Sweep (Skip if phases 1-8 were clean)

**Skip this phase if all previous phases completed with zero errors.** The Audit Phase runs the same checks via the translation audit MCP server — Phase 9 is redundant when the earlier work was clean.

Only run Phase 9 if earlier phases had failures, partial results, or skipped items:

- [ ] **9.1** Query tables that had errors or were skipped. Look for remaining English.
- [ ] **9.2** Query measures that failed to update. Search for quoted English strings.
- [ ] **9.3** Document what's left untranslated and WHY:
  - Source system identifiers (expected)
  - Large tables awaiting source refresh (documented)
  - Pre-existing broken measures (documented)

---

## Phase 10: Report Layer Translation (JSON File Editing)

**This phase requires the report saved as a Power BI Project (.pbip).** The `.pbip` format unpacks the report into editable JSON files.

**IMPORTANT: Power BI Desktop does NOT hot-reload .pbip files.** After editing JSON on disk, you MUST close and reopen the project to see changes.

### Target files
```
<project>/
├── <ReportName>.Report/
│   ├── report.json              # Report-level settings
│   └── definition/
│       ├── pages/
│       │   ├── <page-id>/
│       │   │   ├── page.json    # Page name, display name
│       │   │   └── visuals/
│       │   │       ├── <visual-id>/
│       │   │       │   └── visual.json  # Visual title, subtitle, field labels
│       ├── bookmarks/           # Bookmark names
│       └── ...
```

### Four Categories of Translatable Content

1. **Visual titles** — in `visualContainerObjects.title[].properties.text.expr.Literal.Value`
   - Banner titles (shape visuals with font size 40)
   - Chart titles (lineChart, clusteredColumnChart, comboChart, pivotTable)
   - Subtitles in `visualContainerObjects.subTitle`
   - Hidden titles (`show: false`) — translate for completeness

2. **nativeQueryRef overrides (displayName)** — in `query.queryState.*.projections[]`
   - **CRITICAL**: `nativeQueryRef` IS the visible field label in charts, tables, slicers, and matrices when no `displayName` is set. Captions do NOT override nativeQueryRef.
   - You must ADD a `"displayName": "Swedish Value"` property to every projection with an English `nativeQueryRef`
   - Do NOT change the `nativeQueryRef` value itself — that breaks the query engine
   - Also check and FIX any existing `displayName` values that are already English

3. **Existing displayName fields** — some visuals already have `displayName` set (from manual field renaming in Power BI Desktop). These may be in English and need translating too.

4. **Text content** — in text boxes, cards, buttons
   - `content` properties in shape/textbox visuals
   - Button labels

### What NOT to Translate

- `nativeQueryRef` value itself — changing it breaks the query. Instead ADD `displayName` next to it
- `queryRef` — query engine reference, never visible
- `selector.data[].scopeId.Comparison.Right.Literal.Value` — conditional formatting selectors. Changing these BREAKS color/formatting logic silently
- `Entity` / `Property` values — model object references (DAX identifiers)
- Color codes, font names, format strings, alignment values (`'center'`, `'Basic'`, `'Dropdown'`)
- Matrix expansion state identity values (e.g., "Assets", "Equity and liabilities")
- Company/entity proper names (e.g., "MSP 35 CPS Cloud Center")
- Internal measures used for formatting: `Color PnL Background`, `VAR IsExpandable`, `FontColorCode`, `HeaderIsInScope`, etc.

### Steps

- [ ] **10.1** Page names: Scan all `page.json` files for `displayName` — translate any English page names

- [ ] **10.2** Visual titles: BROAD scan across ALL pages:
  ```
  Grep all visual.json for title text:
  Pattern: visualContainerObjects → title → text → Literal → Value

  Common English to search for:
  "Invoiced", "Customer", "Churn", "Accumulated", "Actuals",
  "Budget", "Forecast", "Comparison", "Overview", "Revenue",
  "Profit", "Balance", "Development", "Top ", "by ", "vs ",
  "Chosen", "Selected", "Full Year", "YTD", "Month", "Year",
  "Financial KPIs", "Ledger"
  ```
  IMPORTANT: A targeted scan of just a few pages will miss 80%+. Scan ALL pages every time.

- [ ] **10.3** nativeQueryRef displayName injection (BULK — use script):
  ```bash
  # Step 1: Scan report to discover all nativeQueryRef values
  python pbip_translate_display_names.py <pages_dir> --scan > starter_map.json

  # Step 2: Build translation map
  # Start from translation_map_sv-SE.json as base for Swedish reports
  # Add new terms, move already-Swedish values to "skip" list
  # Mark any uncertain terms with "TODO:" prefix (script will skip them)

  # Step 3: Dry run
  python pbip_translate_display_names.py <pages_dir> translation_map.json --dry-run

  # Step 4: Execute
  python pbip_translate_display_names.py <pages_dir> translation_map.json
  ```
  The script does three things:
  - Adds `displayName` where missing (nativeQueryRef is English, no override exists)
  - Fixes existing `displayName` where English (someone manually set an English label)
  - Skips values in the "skip" list (already Swedish, abbreviations, internal measures)

  **The sv-SE translation map (`translation_map_sv-SE.json`) includes 109 financial reporting terms. For reports in the same domain, most terms are already covered — only delta additions needed.**

- [ ] **10.4** Fix auto-generated visual titles:
  ```bash
  python pbip_fix_visual_titles.py <pages_dir> <translation_map> --scan
  python pbip_fix_visual_titles.py <pages_dir> <translation_map> --dry-run
  python pbip_fix_visual_titles.py <pages_dir> <translation_map> --execute
  ```
  Visuals with `title.show=true` (or default) but no custom `text` get auto-generated English titles from model property names. This script injects Swedish titles based on projection displayName values. **Run AFTER `pbip_translate_display_names.py`** — the title script uses displayName values from projections to generate Swedish titles.

- [ ] **10.5** Translate slicer headers — scan for `objects.header[].properties.text` with English values. The `pbip_fix_visual_titles.py` script also handles slicer headers in the same pass.

- [ ] **10.6** Scan for text boxes (`visualType: "textbox"`) and buttons (`visualType: "actionButton"`) with English content

- [ ] **10.7** Scan for bookmark display names

- [ ] **10.8** Scan for tooltip page titles

- [ ] **10.9** Final validation — comprehensive English audit:
  ```bash
  # Extract all unique displayName values
  python -c "
  import json, glob, os
  vals = set()
  for fp in glob.glob('pages/**/visual.json', recursive=True):
      data = json.load(open(fp, encoding='utf-8'))
      qs = data.get('visual',{}).get('query',{}).get('queryState',{})
      for b in qs.values():
          if isinstance(b,dict) and 'projections' in b:
              for p in b['projections']:
                  dn = p.get('displayName')
                  if dn: vals.add(dn)
  for v in sorted(vals): print(v)
  "

  # Extract all unique title text values
  python -c "
  import json, glob
  titles = set()
  for fp in glob.glob('pages/**/visual.json', recursive=True):
      data = json.load(open(fp, encoding='utf-8'))
      vco = data.get('visual',{}).get('visualContainerObjects',{})
      for t in vco.get('title',[]):
          v = t.get('properties',{}).get('text',{}).get('expr',{}).get('Literal',{}).get('Value')
          if v and v.startswith(\"'\") and v.endswith(\"'\"):
              titles.add(v[1:-1])
  for t in sorted(titles): print(t)
  "
  ```
  Eyeball both lists. Every value should be Swedish (or a domain abbreviation like FC, BU, ACT).

- [ ] **10.10** Close Power BI Desktop, reopen .pbip, visually verify all pages. Save project.

### Tools Reference

| File | Purpose |
|------|---------|
| `pbip_translate_display_names.py` | Reusable script: scan, dry-run, or execute nativeQueryRef → displayName translation |
| `pbip_fix_visual_titles.py` | Fix auto-generated visual titles and slicer headers. Run AFTER `pbip_translate_display_names.py`. |
| `translation_map_sv-SE.json` | Swedish translation dictionary (109 terms + 60 skip entries). Financial reporting domain. |

**Rules for Phase 10:**
- DO NOT change `nativeQueryRef` or `queryRef` values — ADD `displayName` next to them instead
- DO NOT translate conditional formatting selectors (`scopeId.Comparison.Right.Literal.Value`)
- DO NOT translate `Entity` / `Property` values (DAX identifiers)
- DO translate: titles, displayName overrides, text box content, button labels, page names
- Preserve JSON structure exactly — only change/add string values
- Some visual.json files are 600KB+. Use grep/offset to find translatable content.
- Pages can be near-duplicates (e.g., Kundfakturering/Leverantörsfakturering share identical structures). Always scan ALL pages.
- After editing JSON, MUST close and reopen Power BI Desktop to see changes.

---

## Execution Order Summary

```
 SETUP: User saves .pbix as .pbip project in workspace
     ↓
 0.  Inventory          → Know what you have (model + report files)
 1.  Captions           → Translate metadata names (MCP) — batch ALL tables+columns+measures in one call
 2.  Calculated tables  → Translate hardcoded DAX data (MCP)  ─┐ independent per table,
 3.  Static M tables    → Translate hardcoded M data (MCP)     ─┘ process all tables before moving on
 4.  BREAKAGE SCAN      → ONE compound query for all changed values (MCP)
 5.  Measure text       → Translate display strings in DAX (MCP)
 6.  Source tables      → Translate dimension data values (MCP) — batch all tables
 7.  Date table         → Special handling for dates (MCP)
 8.  Relationships      → Verify cross-table consistency (MCP)
 9.  Full sweep         → SKIP if phases 1-8 were clean (audit phase covers this)
10.  Report layer       → Translate visual titles, text boxes, etc. (JSON editing — scripts handle bulk)
     ↓
 AUDIT: validate_translation_coverage → PASS ends workflow
 DONE: User saves, publishes translated report
```

---

## Key Lessons Learned

### Model Layer
1. **ALWAYS do the breakage scan after changing data values.** SWITCH/IF statements silently return BLANK when they can't match.
2. **Date tables are always English.** Budget time for them.
3. **Source tables can't refresh without credentials.** Plan for static rebuild or deferred refresh.
4. **Overlapping categories exist.** Don't assume simple 1:1 age/category mappings. Query the actual data.
5. **Base64-encoded M data hides English.** Always decode/query to check.
6. **Batch measure updates work better** than individual updates (avoids table name mismatch bugs).
7. **"N/A", "Yes"/"No", "Other"** are easy to miss. Search for ALL short common English words.
8. **Comments in DAX** contain "active" etc. — don't translate comments, only active code strings.
9. **Column rename steps in M** change the physical column name. Don't translate those unless you update ALL DAX references.
10. **Test with actual data queries**, not just expression inspection. A measure might look right but return wrong values.
11. **Measures live in unexpected tables.** Use `INFO.MEASURES()` with `TableID` → `INFO.TABLES()` lookup to find the actual table name.
12. **Pre-existing broken measures can't be updated.** Document and skip.
13. **Large source tables can be rebuilt programmatically.** Use `List.Generate` or `List.Dates` in M instead of embedding 500+ literal rows.
14. **Date table self-contained M rebuild.** Use `Date.ToText(date, "MMMM", "sv-SE")` and `Date.DayOfWeekName(date, "sv-SE")`. `Text.From()` does NOT accept format parameters.
15. **Dependent tables chain-refresh.** After rebuilding `_Date`, refresh `_Date_Prev`, `_DateComparison`, etc. Strip `DBConn` references first.
16. **Color/conditional formatting measures reference data values.** Search for category/filter value comparisons in ALL measures.
17. **Calculated table NAMEOF() references are safe.** They reference physical column names, not translated captions.
18. **INFO.MEASURES() uses [Name] not [ExplicitName].** Use `CONTAINSSTRING()` not `SEARCH()` for filtering.
19. **Relationship keys are almost always numeric SK/ID/Date columns.** Quick scan saves time.
20. **"Budget" is the same in Swedish.** Don't over-translate — some financial terms (Budget, SEK, N/A, pp) are identical.

### Report Layer
21. **Captions only show in matching locale.** If user views in English locale, they see physical English names. Report JSON changes are locale-independent.
22. **Some pages use dynamic titles (measures), others use static titles (report JSON).** This causes inconsistency — some pages appear translated while others don't. Always check both.
23. **Visual field label overrides in JSON take precedence over captions.** If someone manually renamed a field in a visual, the caption is ignored for that visual.
24. **The .pbip format is required for report JSON editing.** A .pbix is a compressed binary — save as project first.
25. **Initial targeted scans miss 80%+ of English.** A quick scan of "obvious" pages found 6 items. A broad scan of ALL pages found 50+. Always do the broad scan.
26. **`displayName` on query projections = visible column headers.** These override captions and show regardless of locale. Always translate.
27. **Conditional formatting selectors MUST NOT be translated.** Values in `scopeId.Comparison.Right.Literal.Value` paths control color/formatting logic. Changing them breaks visuals silently (colors disappear, formatting reverts to default).
28. **Pages can be near-duplicates.** Example: Kundfakturering and Leverantörsfakturering had identical "Invoiced" visual structures. Never assume a page is unique — scan ALL pages.
29. **Hidden titles (show: false) should still be translated.** They may become visible if someone toggles the setting later.
30. **Abbreviations need translating.** "Comp" → "Jmf", "YTD" → "ÅTD". These are easy to miss because they look like codes.
31. **Some visual.json files are 600KB+.** Large matrix visuals with many conditional formatting rules. Use grep/offset to find translatable content instead of reading the whole file.
32. **Business terms need domain-specific Swedish.** "Upsell" → "Merförsäljning", "Downsell" → "Nedförsäljning", "Churn" → "Avhopp". Don't guess — use established Swedish business terminology.
33. **Matrix expansion state identity values are NOT display text.** "Assets", "Equity and liabilities" in expansion state paths are internal identifiers. Do not translate.

### nativeQueryRef & Script Lessons
34. **nativeQueryRef IS the visible field label.** This is the #1 gotcha. When no `displayName` is set on a projection, Power BI shows the `nativeQueryRef` value as the column header / legend / axis label. Captions set via MCP (Phase 1) do NOT override this in the report layer. You MUST add `displayName` to every projection with an English nativeQueryRef.
35. **Do NOT change nativeQueryRef itself.** It's the query engine's internal reference. Changing it breaks the visual. Instead, add a sibling `displayName` property.
36. **Existing English displayName values get skipped by naive scripts.** A script that only adds `displayName` where missing will skip projections that already have an English `displayName` (set by someone who manually renamed a field in Power BI Desktop). The script must also CHECK and FIX existing displayName values.
37. **Use `pbip_translate_display_names.py` for bulk nativeQueryRef work.** Manual editing of 400+ projections is not feasible. The script scans all visual.json files, finds every projection, and injects Swedish displayName from a translation map. Use `--scan` to discover terms, `--dry-run` to preview, then execute.
38. **The translation map is domain-specific but reusable within domain.** `translation_map_sv-SE.json` covers financial reporting terms (invoicing, P&L, balance sheet, forecasting). Reports in the same domain reuse 90%+ of the map. Only delta additions needed per project.
39. **Power BI Desktop does NOT hot-reload .pbip files.** After editing JSON on disk, you must close Desktop and reopen the .pbip project. Changes are invisible until you do this.
40. **Abbreviations that stay the same in Swedish context:** FC (Forecast), BU (Budget), ACT (Actuals), PY (Previous Year), VTB/VTC (Variance To Budget/Comparison), Var%, Δ YoY. These are standard financial abbreviations used in Swedish reporting too. Don't translate them.
41. **Internal/formatting measures should be skipped.** Values like `Color PnL Background`, `VAR IsAnyChild`, `FontColorCode`, `HeaderIsInScope`, `EnableExpansion` — these are internal measures used for conditional formatting, never visible to users. Put them in the skip list.
42. **Always do a final displayName + title audit.** After all edits, extract every unique displayName and title text value. Eyeball the sorted list. Anything English sticks out immediately in a wall of Swedish text.
43. **Auto-generated visual titles use English model property names.** When `visualContainerObjects.title` has `show=true` (or default) but no `text` property, PBI generates the title from nativeQueryRef/property names. Must inject explicit `text` with Swedish title. The `pbip_fix_visual_titles.py` script handles this.
44. **Slicer headers have their own text property.** Path: `visual.objects.header[].properties.text.expr.Literal.Value`. Not covered by displayName injection. Must be translated separately.
45. **The audit server must check for MISSING title text, not just English title text.** A visible title with no text property = auto-generated English. This was the #1 false-PASS cause.
46. **Run `pbip_fix_visual_titles.py` AFTER `pbip_translate_display_names.py`.** The title script uses displayName values from projections to generate Swedish titles. If displayNames aren't set yet, the generated titles will be English.
47. **Single English words like "CareTaker" escape keyword detection.** Expand the keyword list aggressively. Better to have false positives than false negatives.
