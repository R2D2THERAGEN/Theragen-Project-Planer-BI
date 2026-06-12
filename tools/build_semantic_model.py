"""Emit the Theragen Project Planner PBIP semantic model (TMDL format).

Bootstrap generator: writes the .pbip pointer, SemanticModel folder with
database/model/expressions/relationships/cultures and one TMDL file per table.
After generation the TMDL files are the maintained artifacts (open in Power BI
Desktop or Tabular Editor); re-run only to rebuild from scratch.
"""
import os
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "Theragen Project Planner"
SM = os.path.join(ROOT, f"{NAME}.SemanticModel")
DEF = os.path.join(SM, "definition")
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def tag(*parts):
    return str(uuid.uuid5(NS, "thg-bi/" + "/".join(parts)))


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(os.path.relpath(path, ROOT))


# ---------------------------------------------------------------------------
# Column spec: (friendly, source, dtype, opts)
# dtype: string,int64,double,decimal,dateTime,boolean
# opts: h=hidden, money/pct0/date/whole = formatString presets, key=isKey
# ---------------------------------------------------------------------------
FMT = {
    "money": "\\$#,##0;(\\$#,##0);\\$0",
    "money2": "\\$#,##0.00;(\\$#,##0.00);\\$0.00",
    "whole": "#,0",
    "num1": "#,0.0",
    "date": "yyyy-mm-dd",
    "pctraw": "0\\%",
}

TABLES = {}

TABLES["Project"] = dict(
    csv="project",
    desc="Project dimension - one row per project (PMBOK P01 project, charter fields denormalized).",
    cols=[
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Intake ID", "intake_id", "string", ""),
        ("Project Name", "name", "string", ""),
        ("Project Description", "description", "string", ""),
        ("Business Value", "business_value", "string", ""),
        ("Sponsor", "sponsor_name", "string", ""),
        ("Project Manager", "project_manager_name", "string", ""),
        ("Primary Department", "primary_department", "string", ""),
        ("Approach", "approach", "string", ""),
        ("Lifecycle Phase", "lifecycle_phase", "string", ""),
        ("Project Status", "status", "string", ""),
        ("Planned Start", "planned_start", "dateTime", "date"),
        ("Planned Finish", "planned_finish", "dateTime", "date"),
        ("Actual Start", "actual_start", "dateTime", "date"),
        ("Actual Finish", "actual_finish", "dateTime", "date"),
        ("Charter Budget", "budget_total", "decimal", "money"),
        ("Strategic Objective", "strategic_objective_ref", "string", ""),
    ],
)

TABLES["Department"] = dict(
    csv="department",
    desc="Conformed department dimension (DM D01). Filters executing departments on facts.",
    cols=[
        ("Department ID", "department_id", "string", "h"),
        ("Department Code", "code", "string", ""),
        ("Department", "name", "string", ""),
    ],
)

TABLES["Person"] = dict(
    csv="person",
    desc="Person directory (DM D02). Owners, requesters and assignees on facts.",
    cols=[
        ("Person ID", "person_id", "string", "h"),
        ("Person", "display_name", "string", ""),
        ("Email", "email", "string", ""),
        ("Person Department", "department_name", "string", ""),
        ("Role Title", "role_title", "string", ""),
        ("Employee Number", "employee_number", "string", ""),
    ],
)

TABLES["WBS Element"] = dict(
    csv="wbs_element",
    desc="Work breakdown structure dimension (PMBOK P08). Two-level hierarchy: deliverable > work package.",
    cols=[
        ("WBS ID", "wbs_element_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("WBS Code", "wbs_code", "string", ""),
        ("Parent WBS ID", "parent_wbs_element_id", "string", "h"),
        ("WBS Level", "level", "int64", "whole"),
        ("WBS Name", "name", "string", ""),
        ("Owning Department", "owning_department", "string", ""),
        ("Owner Role", "owner_role", "string", ""),
        ("Estimated Effort Hrs", "estimated_effort_hrs", "double", "whole"),
        ("Estimated Cost", "estimated_cost", "decimal", "money"),
    ],
    calc_cols=[
        ("Deliverable",
         "IF('WBS Element'[WBS Level] = 1, 'WBS Element'[WBS Name], "
         "LOOKUPVALUE('WBS Element'[WBS Name], 'WBS Element'[WBS ID], 'WBS Element'[Parent WBS ID]))",
         "string", "Level-1 deliverable this node rolls up to."),
        ("WBS Label",
         "'WBS Element'[WBS Code] & \"  \" & 'WBS Element'[WBS Name]",
         "string", "Code + name for axis labels."),
    ],
)

TABLES["Knowledge Area"] = dict(
    csv="knowledge_area",
    desc="PMBOK knowledge areas (enum knowledge_area) used by status report health entries.",
    cols=[
        ("Knowledge Area", "knowledge_area", "string", ""),
        ("KA Sort", "sort_order", "int64", "h"),
    ],
    sort_by={"Knowledge Area": "KA Sort"},
)

TABLES["Schedule Activity"] = dict(
    csv="schedule_activity",
    desc="Fact - schedule activities (PMBOK P10). One row per activity with planned/actual dates and percent complete.",
    cols=[
        ("Activity ID", "activity_id", "string", "h"),
        ("WBS ID", "wbs_element_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Activity Code", "activity_code", "string", ""),
        ("Activity Name", "name", "string", ""),
        ("Planned Start", "start_planned", "dateTime", "date"),
        ("Planned Finish", "finish_planned", "dateTime", "date"),
        ("Actual Start", "start_actual", "dateTime", "date"),
        ("Actual Finish", "finish_actual", "dateTime", "date"),
        ("Duration Days", "duration_days", "int64", "whole"),
        ("Owner ID", "owner_person_id", "string", "h"),
        ("Owner", "owner_name", "string", ""),
        ("Department", "department", "string", ""),
        ("Activity Status", "status", "string", ""),
        ("Pct Complete", "pct_complete", "double", "pctraw"),
    ],
)

TABLES["Milestone"] = dict(
    csv="milestone",
    desc="Fact - milestones (PMBOK P11). Baseline vs forecast vs actual dates.",
    cols=[
        ("Milestone ID", "milestone_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Milestone", "name", "string", ""),
        ("Baseline Date", "baseline_date", "dateTime", "date"),
        ("Forecast Date", "forecast_date", "dateTime", "date"),
        ("Actual Date", "actual_date", "dateTime", "date"),
        ("Milestone Status", "status", "string", ""),
        ("Owner Role", "owner_role", "string", ""),
    ],
    calc_cols=[
        ("Slip Days",
         "DATEDIFF('Milestone'[Baseline Date], "
         "COALESCE('Milestone'[Actual Date], 'Milestone'[Forecast Date], 'Milestone'[Baseline Date]), DAY)",
         "int64", "Days between baseline and actual (or forecast) date. Positive = slip."),
    ],
)

TABLES["Budget Line"] = dict(
    csv="budget_line_item",
    desc="Fact - cost budget estimate lines (PMBOK P13), one per level-1 deliverable.",
    cols=[
        ("Budget Line ID", "budget_line_id", "string", "h"),
        ("WBS ID", "wbs_element_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Cost Category", "category", "string", ""),
        ("Labor Amount", "labor_amount", "decimal", "money"),
        ("Materials Amount", "materials_amount", "decimal", "money"),
        ("Vendor Amount", "vendor_amount", "decimal", "money"),
        ("Other Amount", "other_amount", "decimal", "money"),
        ("Subtotal", "subtotal", "decimal", "money"),
        ("Contingency Pct", "contingency_pct", "double", "num1"),
        ("Total", "total", "decimal", "money"),
        ("Funding Source", "funding_source", "string", ""),
    ],
)

TABLES["Risk"] = dict(
    csv="risk",
    desc="Fact - risk register (PMBOK P14). 5x5 likelihood x impact scoring.",
    cols=[
        ("Risk ID", "risk_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Risk Code", "risk_code", "string", ""),
        ("Risk Category", "category", "string", ""),
        ("Risk Description", "description", "string", ""),
        ("Likelihood", "likelihood", "int64", "whole"),
        ("Impact", "impact", "int64", "whole"),
        ("Risk Score", "score", "int64", "whole"),
        ("Response Type", "response_type", "string", ""),
        ("Owner ID", "owner_person_id", "string", "h"),
        ("Owner", "owner_name", "string", ""),
        ("Department", "department", "string", ""),
        ("Due Date", "due_date", "dateTime", "date"),
        ("Risk Status", "status", "string", ""),
        ("Residual Score", "residual_score", "int64", "whole"),
        ("Compliance Frame", "compliance_flag", "string", ""),
    ],
    calc_cols=[
        ("Severity",
         "SWITCH(TRUE(), 'Risk'[Risk Score] >= 20, \"Critical\", 'Risk'[Risk Score] >= 12, \"High\", "
         "'Risk'[Risk Score] >= 6, \"Medium\", \"Low\")",
         "string", "Banding of Risk Score on the 5x5 matrix: >=20 Critical, >=12 High, >=6 Medium."),
        ("RAID Type",
         "IF('Risk'[Risk Status] = \"Realized\", \"Issue\", \"Risk\")",
         "string", "RAID classification: a realized risk is reported as an Issue."),
    ],
)

TABLES["Risk Response"] = dict(
    csv="risk_response",
    desc="Fact - risk response actions (PMBOK P15).",
    cols=[
        ("Response ID", "response_id", "string", "h"),
        ("Risk ID", "risk_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Risk Code", "risk_code", "string", ""),
        ("Action Type", "action_type", "string", ""),
        ("Action Description", "description", "string", ""),
        ("Action Owner", "owner_name", "string", ""),
        ("Action Due Date", "due_date", "dateTime", "date"),
        ("Action Status", "status", "string", ""),
    ],
)

TABLES["Change Request"] = dict(
    csv="change_request",
    desc="Fact - project change requests (PMBOK P21) with impact and decision cycle.",
    cols=[
        ("CR ID", "cr_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("CR Code", "cr_code", "string", ""),
        ("Intake ID", "intake_id", "string", ""),
        ("Requested Date", "requested_at", "dateTime", "date"),
        ("Requested By ID", "requested_by_person_id", "string", "h"),
        ("Requested By", "requested_by_name", "string", ""),
        ("CR Class", "cr_class", "string", ""),
        ("Change Type", "change_types", "string", ""),
        ("CR Description", "description", "string", ""),
        ("Reason", "reason", "string", ""),
        ("Schedule Impact Days", "impact_schedule_days", "int64", "whole"),
        ("Cost Impact", "impact_cost", "decimal", "money"),
        ("Decision", "decision", "string", ""),
        ("Decided Date", "decided_at", "dateTime", "date"),
        ("Cycle Time Days", "cycle_time_days", "int64", "whole"),
        ("CR Status", "status", "string", ""),
    ],
)

TABLES["Status Report"] = dict(
    csv="status_report",
    desc="Fact - periodic status reports (PMBOK P23). Overall G/Y/R health and trend per period.",
    cols=[
        ("Report ID", "report_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Report Number", "report_number", "int64", "whole"),
        ("Period Start", "period_start", "dateTime", "date"),
        ("Period End", "period_end", "dateTime", "date"),
        ("Overall Status", "overall_status", "string", ""),
        ("Trend", "trend", "string", ""),
        ("Executive Summary", "executive_summary", "string", ""),
        ("Decisions Needed", "decisions_needed", "string", ""),
        ("Submitted By", "submitted_by_name", "string", ""),
        ("Submitted Date", "submitted_at", "dateTime", "date"),
    ],
)

TABLES["Status Report Area"] = dict(
    csv="status_report_area",
    desc="Fact - per-knowledge-area health entries within each status report (PMBOK P24).",
    cols=[
        ("Area ID", "area_id", "string", "h"),
        ("Report ID", "report_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Knowledge Area", "knowledge_area", "string", ""),
        ("Area Status", "status", "string", ""),
    ],
)

TABLES["Stakeholder"] = dict(
    csv="stakeholder",
    desc="Fact - stakeholder register entries (PMBOK P03) with RACI engagement and interest/influence.",
    cols=[
        ("Stakeholder ID", "stakeholder_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Stk Code", "stk_code", "string", ""),
        ("Person ID", "person_id", "string", "h"),
        ("Stakeholder", "stakeholder_name", "string", ""),
        ("Stakeholder Role", "role", "string", ""),
        ("Department", "department", "string", ""),
        ("Engagement", "engagement", "string", ""),
        ("Interest", "interest", "string", ""),
        ("Influence", "influence", "string", ""),
        ("Comm Preference", "communication_preference", "string", ""),
    ],
)

TABLES["Team Member"] = dict(
    csv="project_team_member",
    desc="Fact - project team assignments (PMBOK P31) with allocation percentage.",
    cols=[
        ("Team Member ID", "team_member_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Person ID", "person_id", "string", "h"),
        ("Member", "member_name", "string", ""),
        ("Team Role", "role", "string", ""),
        ("Department", "department", "string", ""),
        ("Allocation Pct", "allocation_pct", "double", "pctraw"),
        ("Start Date", "start_date", "dateTime", "date"),
        ("End Date", "end_date", "dateTime", "date"),
    ],
)

TABLES["Lesson Learned"] = dict(
    csv="lesson_learned",
    desc="Fact - lessons learned (PMBOK P25).",
    cols=[
        ("Lesson ID", "lesson_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Lesson Category", "category", "string", ""),
        ("Lesson", "lesson", "string", ""),
        ("What Happened", "what_happened", "string", ""),
        ("Recommendation", "recommendation", "string", ""),
        ("Follow-up Owner", "followup_owner_role", "string", ""),
        ("Lesson Status", "status", "string", ""),
    ],
)

TABLES["Closure Item"] = dict(
    csv="closure_checklist_item",
    desc="Fact - project closure checklist items (PMBOK P26).",
    cols=[
        ("Closure Item ID", "closure_item_id", "string", "h"),
        ("Project ID", "project_id", "string", "h"),
        ("Project Code", "project_code", "string", ""),
        ("Closure Item", "item", "string", ""),
        ("Owner Role", "owner_role", "string", ""),
        ("Done", "done", "boolean", ""),
        ("Evidence", "evidence", "string", ""),
    ],
)

TYPE_M = {"string": "type text", "int64": "Int64.Type", "double": "type number",
          "decimal": "Currency.Type", "dateTime": "type date", "boolean": "type logical"}


def m_partition(t):
    cols = t["cols"]
    sel = ", ".join(f'"{src}"' for _, src, _, _ in cols)
    types = ", ".join("{" + f'"{src}", {TYPE_M[dt]}' + "}" for _, src, dt, _ in cols)
    rens = ", ".join("{" + f'"{src}", "{fr}"' + "}" for fr, src, _, _ in cols if src != fr)
    lines = [
        "let",
        f'\tSource = Csv.Document(File.Contents(DataFolder & "\\{t["csv"]}.csv"), '
        "[Delimiter = \",\", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),",
        "\tPromoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f"\tSelected = Table.SelectColumns(Promoted, {{{sel}}}),",
        "\tNulled = Table.ReplaceValue(Selected, \"\", null, Replacer.ReplaceValue, Table.ColumnNames(Selected)),",
        f"\tTyped = Table.TransformColumnTypes(Nulled, {{{types}}}),",
        f"\tRenamed = Table.RenameColumns(Typed, {{{rens}}})",
        "in",
        "\tRenamed",
    ]
    return lines


def emit_table(name, t):
    out = []
    if t.get("desc"):
        out.append(f"/// {t['desc']}")
    out += [f"table '{name}'", f"\tlineageTag: {tag('table', name)}", ""]
    sort_by = t.get("sort_by", {})
    for fr, src, dt, opt in t["cols"]:
        out.append(f"\tcolumn '{fr}'")
        out.append(f"\t\tdataType: {'dateTime' if dt == 'dateTime' else dt}")
        if dt == "dateTime":
            out.append(f"\t\tformatString: {FMT['date']}")
        elif opt in FMT:
            out.append(f"\t\tformatString: {FMT[opt]}")
        if opt == "h":
            out.append("\t\tisHidden")
        out.append(f"\t\tlineageTag: {tag('col', name, fr)}")
        out.append("\t\tsummarizeBy: none")
        if fr in sort_by:
            out.append(f"\t\tsortByColumn: '{sort_by[fr]}'")
        out.append(f"\t\tsourceColumn: {fr}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    for cc in t.get("calc_cols", []):
        cname, expr, cdt, cdesc = cc
        if cdesc:
            out.append(f"\t/// {cdesc}")
        out.append(f"\tcolumn '{cname}' = {expr}")
        out.append(f"\t\tdataType: {cdt}")
        out.append(f"\t\tlineageTag: {tag('calccol', name, cname)}")
        out.append("\t\tsummarizeBy: none")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    part = m_partition(t)
    out.append(f"\tpartition '{name}' = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    for ln in part:
        out.append("\t\t\t\t" + ln.replace("\t", "    "))
    out.append("")
    out.append("\tannotation PBI_ResultType = Table")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------- Date
def emit_date():
    cc = [
        ("Year", "YEAR('Date'[Date])", "int64", "whole", ""),
        ("Quarter", "\"Q\" & QUARTER('Date'[Date])", "string", "", ""),
        ("Month Number", "MONTH('Date'[Date])", "int64", "h", ""),
        ("Month", "FORMAT('Date'[Date], \"MMM\")", "string", "", "Month Number"),
        ("Year Month", "FORMAT('Date'[Date], \"YYYY-MM\")", "string", "", ""),
        ("Week Of", "'Date'[Date] - WEEKDAY('Date'[Date], 2) + 1", "dateTime", "date", ""),
    ]
    out = ["/// Marked date dimension covering 2025-2027.",
           "table 'Date'",
           f"\tlineageTag: {tag('table', 'Date')}",
           "\tdataCategory: Time",
           "",
           "\tcolumn 'Date'",
           "\t\tdataType: dateTime",
           "\t\tisKey",
           f"\t\tformatString: {FMT['date']}",
           f"\t\tlineageTag: {tag('col', 'Date', 'Date')}",
           "\t\tsummarizeBy: none",
           # Calculated-table columns must bind to the DAX-produced column or the
           # AS engine fails with CALCTABLE_COLUMN_MISSING_SOURCECOLUMN.
           "\t\tsourceColumn: [Date]",
           "",
           "\t\tannotation SummarizationSetBy = User",
           ""]
    for cname, expr, cdt, opt, sortby in cc:
        out.append(f"\tcolumn '{cname}' = {expr}")
        out.append(f"\t\tdataType: {cdt}")
        if cdt == "dateTime":
            out.append(f"\t\tformatString: {FMT['date']}")
        elif opt in FMT:
            out.append(f"\t\tformatString: {FMT[opt]}")
        if opt == "h":
            out.append("\t\tisHidden")
        if sortby:
            out.append(f"\t\tsortByColumn: '{sortby}'")
        out.append(f"\t\tlineageTag: {tag('calccol', 'Date', cname)}")
        out.append("\t\tsummarizeBy: none")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    out += ["\tpartition 'Date' = calculated",
            "\t\tmode: import",
            "\t\tsource = CALENDAR(DATE(2025, 1, 1), DATE(2027, 12, 31))",
            "",
            "\tannotation PBI_ResultType = Table",
            ""]
    return "\n".join(out)


# ---------------------------------------------------- calculated leadership tables
# Pre-filtered DAX tables feeding the leadership status page (PPTX sections
# "Accomplishments" and "Next Steps"). Evaluated at refresh; windows are
# relative to TODAY(). Calculated-table columns require sourceColumn: [Name].
CALC_TABLES = {
    "Recent Accomplishment": dict(
        desc="Leadership view - work completed in the last 35 days (done activities + achieved milestones).",
        dax=(
            "UNION("
            "SELECTCOLUMNS(FILTER('Schedule Activity', 'Schedule Activity'[Activity Status] = \"Done\" "
            "&& NOT ISBLANK('Schedule Activity'[Actual Finish]) "
            "&& 'Schedule Activity'[Actual Finish] >= TODAY() - 35), "
            "\"Project ID\", 'Schedule Activity'[Project ID], "
            "\"Accomplishment\", 'Schedule Activity'[Activity Name], "
            "\"Completed Date\", 'Schedule Activity'[Actual Finish], "
            "\"Source\", \"Activity\"), "
            "SELECTCOLUMNS(FILTER('Milestone', 'Milestone'[Milestone Status] = \"Achieved\" "
            "&& NOT ISBLANK('Milestone'[Actual Date]) "
            "&& 'Milestone'[Actual Date] >= TODAY() - 35), "
            "\"Project ID\", 'Milestone'[Project ID], "
            "\"Accomplishment\", 'Milestone'[Milestone], "
            "\"Completed Date\", 'Milestone'[Actual Date], "
            "\"Source\", \"Milestone\"))"
        ),
        cols=[("Project ID", "string", "h"), ("Accomplishment", "string", ""),
              ("Completed Date", "dateTime", "date"), ("Source", "string", "")],
    ),
    "Upcoming Next Step": dict(
        desc="Leadership view - open work targeted in the next 45 days (activities + milestones).",
        dax=(
            "UNION("
            "SELECTCOLUMNS(FILTER('Schedule Activity', "
            "NOT 'Schedule Activity'[Activity Status] IN {\"Done\", \"Cancelled\"} "
            "&& 'Schedule Activity'[Planned Finish] >= TODAY() - 7 "
            "&& 'Schedule Activity'[Planned Finish] <= TODAY() + 45), "
            "\"Project ID\", 'Schedule Activity'[Project ID], "
            "\"Next Step\", 'Schedule Activity'[Activity Name], "
            "\"Target Date\", 'Schedule Activity'[Planned Finish], "
            "\"Owner\", 'Schedule Activity'[Owner], "
            "\"Source\", \"Activity\"), "
            "SELECTCOLUMNS(FILTER('Milestone', "
            "'Milestone'[Milestone Status] IN {\"On track\", \"At risk\", \"Slipped\"} "
            "&& COALESCE('Milestone'[Forecast Date], 'Milestone'[Baseline Date]) >= TODAY() - 7 "
            "&& COALESCE('Milestone'[Forecast Date], 'Milestone'[Baseline Date]) <= TODAY() + 45), "
            "\"Project ID\", 'Milestone'[Project ID], "
            "\"Next Step\", 'Milestone'[Milestone], "
            "\"Target Date\", COALESCE('Milestone'[Forecast Date], 'Milestone'[Baseline Date]), "
            "\"Owner\", 'Milestone'[Owner Role], "
            "\"Source\", \"Milestone\"))"
        ),
        cols=[("Project ID", "string", "h"), ("Next Step", "string", ""),
              ("Target Date", "dateTime", "date"), ("Owner", "string", ""),
              ("Source", "string", "")],
    ),
}


def emit_calc_table(name, t):
    out = [f"/// {t['desc']}", f"table '{name}'", f"\tlineageTag: {tag('table', name)}", ""]
    for cname, cdt, opt in t["cols"]:
        out.append(f"\tcolumn '{cname}'")
        out.append(f"\t\tdataType: {cdt}")
        if cdt == "dateTime":
            out.append(f"\t\tformatString: {FMT['date']}")
        elif opt in FMT:
            out.append(f"\t\tformatString: {FMT[opt]}")
        if opt == "h":
            out.append("\t\tisHidden")
        out.append(f"\t\tlineageTag: {tag('col', name, cname)}")
        out.append("\t\tsummarizeBy: none")
        out.append(f"\t\tsourceColumn: [{cname}]")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    out += [f"\tpartition '{name}' = calculated",
            "\t\tmode: import",
            f"\t\tsource = {t['dax']}",
            "",
            "\tannotation PBI_ResultType = Table",
            ""]
    return "\n".join(out)


# ------------------------------------------------------------------ measures
M = []  # (folder, name, expr, fmt, desc)


def add(folder, name, expr, fmt, desc):
    M.append((folder, name, expr, fmt, desc))


C_WHOLE, C_MONEY, C_PCT, C_NUM2, C_NUM1 = "#,0", "\\$#,##0;(\\$#,##0);\\$0", "0.0%;-0.0%;0.0%", "0.00", "#,0.0"

# Portfolio
add("Portfolio", "Projects", "COUNTROWS('Project')", C_WHOLE, "Count of projects in context.")
add("Portfolio", "Active Projects",
    "CALCULATE([Projects], 'Project'[Project Status] = \"Active\")", C_WHOLE,
    "Projects with status Active.")
add("Portfolio", "Proposed Projects",
    "CALCULATE([Projects], 'Project'[Project Status] = \"Proposed\")", C_WHOLE,
    "Projects with status Proposed.")
add("Portfolio", "Portfolio Charter Budget", "SUM('Project'[Charter Budget])", C_MONEY,
    "Sum of charter-approved budget totals (project.budget_total).")

# Schedule
add("Schedule", "Activities", "COUNTROWS('Schedule Activity')", C_WHOLE, "Count of schedule activities.")
add("Schedule", "Activities Done",
    "CALCULATE([Activities], 'Schedule Activity'[Activity Status] = \"Done\")", C_WHOLE,
    "Activities completed.")
add("Schedule", "Activities In Progress",
    "CALCULATE([Activities], 'Schedule Activity'[Activity Status] = \"In progress\")", C_WHOLE,
    "Activities currently in progress.")
add("Schedule", "Activities At Risk",
    "CALCULATE([Activities], 'Schedule Activity'[Activity Status] = \"At risk\")", C_WHOLE,
    "Activities flagged at risk.")
add("Schedule", "Pct Complete (Duration Weighted)",
    "DIVIDE(SUMX('Schedule Activity', 'Schedule Activity'[Duration Days] * 'Schedule Activity'[Pct Complete]), "
    "SUMX('Schedule Activity', 'Schedule Activity'[Duration Days]) * 100)", C_PCT,
    "Percent complete weighted by activity duration.")
add("Schedule", "Activities Overdue",
    "COUNTROWS(FILTER('Schedule Activity', 'Schedule Activity'[Planned Finish] < TODAY() "
    "&& NOT 'Schedule Activity'[Activity Status] IN {\"Done\", \"Cancelled\"}))", C_WHOLE,
    "Open activities past their planned finish date.")
add("Schedule", "Overdue Pct", "DIVIDE([Activities Overdue], [Activities])", C_PCT,
    "Share of activities overdue.")
add("Schedule", "On-Time Completion Pct",
    "DIVIDE(COUNTROWS(FILTER('Schedule Activity', 'Schedule Activity'[Activity Status] = \"Done\" "
    "&& NOT ISBLANK('Schedule Activity'[Actual Finish]) "
    "&& 'Schedule Activity'[Actual Finish] <= 'Schedule Activity'[Planned Finish])), [Activities Done])", C_PCT,
    "Done activities that finished on or before planned finish.")
add("Schedule", "Avg Duration Days", "AVERAGE('Schedule Activity'[Duration Days])", C_NUM1,
    "Average planned working-day duration.")

# EVM (estimate-based; cost actuals feed is Phase 2)
add("EVM", "BAC (WBS Estimates)",
    "CALCULATE(SUM('WBS Element'[Estimated Cost]), 'WBS Element'[WBS Level] = 2)", C_MONEY,
    "Budget at completion from work-package estimates (wbs_element.estimated_cost). EVM baseline.")
add("EVM", "Earned Value",
    "SUMX(FILTER('WBS Element', 'WBS Element'[WBS Level] = 2), "
    "'WBS Element'[Estimated Cost] * CALCULATE(AVERAGE('Schedule Activity'[Pct Complete])) / 100)", C_MONEY,
    "EV = work-package estimate x mean percent complete of its activities.")
add("EVM", "Planned Value",
    "VAR AsOf = TODAY() RETURN SUMX(FILTER('WBS Element', 'WBS Element'[WBS Level] = 2), "
    "'WBS Element'[Estimated Cost] * CALCULATE(AVERAGEX('Schedule Activity', "
    "VAR s = 'Schedule Activity'[Planned Start] VAR f = 'Schedule Activity'[Planned Finish] "
    "RETURN IF(AsOf >= f, 1, IF(AsOf <= s, 0, DIVIDE(AsOf - s, f - s))))))", C_MONEY,
    "PV = work-package estimate x planned-elapsed fraction of its activities as of today.")
add("EVM", "Schedule Variance (SV)", "[Earned Value] - [Planned Value]", C_MONEY,
    "EV minus PV. Negative = behind schedule.")
add("EVM", "SPI", "DIVIDE([Earned Value], [Planned Value])", C_NUM2,
    "Schedule Performance Index = EV / PV. Below 1.0 = behind schedule. "
    "CPI/EAC require a cost-actuals feed (Phase 2 - not in THG-ENT-DBS-001 v1.0).")

# Milestones
add("Milestones", "Milestones", "COUNTROWS('Milestone')", C_WHOLE, "Count of milestones.")
add("Milestones", "Milestones Achieved",
    "CALCULATE([Milestones], 'Milestone'[Milestone Status] = \"Achieved\")", C_WHOLE, "Milestones achieved.")
add("Milestones", "Milestones At Risk",
    "CALCULATE([Milestones], 'Milestone'[Milestone Status] = \"At risk\")", C_WHOLE, "Milestones at risk.")
add("Milestones", "Milestones Slipped",
    "CALCULATE([Milestones], 'Milestone'[Milestone Status] = \"Slipped\")", C_WHOLE, "Milestones slipped.")
add("Milestones", "Milestone Hit Rate",
    "DIVIDE(COUNTROWS(FILTER('Milestone', 'Milestone'[Milestone Status] = \"Achieved\" "
    "&& NOT ISBLANK('Milestone'[Actual Date]) && 'Milestone'[Actual Date] <= 'Milestone'[Baseline Date])), "
    "[Milestones Achieved])", C_PCT,
    "Achieved milestones that landed on or before baseline.")
add("Milestones", "Avg Milestone Slip Days", "AVERAGE('Milestone'[Slip Days])", C_NUM1,
    "Mean slip days (actual/forecast vs baseline). Positive = late.")

# Cost
add("Cost", "Budget Total", "SUM('Budget Line'[Total])", C_MONEY,
    "Funded budget including contingency (budget_line_item.total).")
add("Cost", "Budget Subtotal", "SUM('Budget Line'[Subtotal])", C_MONEY,
    "Budget before contingency.")
add("Cost", "Contingency Amount", "[Budget Total] - [Budget Subtotal]", C_MONEY,
    "Contingency reserve in the funded budget.")
add("Cost", "Labor Amount", "SUM('Budget Line'[Labor Amount])", C_MONEY, "Labor component.")
add("Cost", "Materials Amount", "SUM('Budget Line'[Materials Amount])", C_MONEY, "Materials component.")
add("Cost", "Vendor Amount", "SUM('Budget Line'[Vendor Amount])", C_MONEY, "Vendor / contractor component.")
add("Cost", "Other Amount", "SUM('Budget Line'[Other Amount])", C_MONEY, "Other cost component.")
add("Cost", "Approved CR Cost Impact",
    "CALCULATE(SUM('Change Request'[Cost Impact]), 'Change Request'[Decision] = \"Approved\")", C_MONEY,
    "Net cost impact of approved change requests.")
add("Cost", "Working Budget", "[Budget Total] + [Approved CR Cost Impact]", C_MONEY,
    "Funded budget adjusted for approved change requests.")
add("Cost", "Budget vs Charter", "[Budget Total] - [Portfolio Charter Budget]", C_MONEY,
    "Detailed budget vs charter-approved total. Positive = over charter.")

# Risk
add("Risk", "Risks", "COUNTROWS('Risk')", C_WHOLE, "Count of risks.")
add("Risk", "Open Risks",
    "CALCULATE([Risks], 'Risk'[Risk Status] IN {\"Open\", \"Mitigating\", \"Monitoring\"})", C_WHOLE,
    "Risks not yet closed or realized.")
add("Risk", "High Risks",
    "CALCULATE([Risks], 'Risk'[Risk Score] >= 12, 'Risk'[Risk Status] IN {\"Open\", \"Mitigating\", \"Monitoring\"})",
    C_WHOLE, "Open risks with score >= 12 on the 5x5 matrix.")
add("Risk", "Critical Risks",
    "CALCULATE([Risks], 'Risk'[Risk Score] >= 20, 'Risk'[Risk Status] IN {\"Open\", \"Mitigating\", \"Monitoring\"})",
    C_WHOLE, "Open risks with score >= 20.")
add("Risk", "Realized Risks",
    "CALCULATE([Risks], 'Risk'[Risk Status] = \"Realized\")", C_WHOLE, "Risks that materialized.")
add("Risk", "Total Risk Exposure",
    "CALCULATE(SUM('Risk'[Risk Score]), 'Risk'[Risk Status] IN {\"Open\", \"Mitigating\", \"Monitoring\"})",
    C_WHOLE, "Sum of L x I scores across open risks.")
add("Risk", "Residual Exposure",
    "CALCULATE(SUM('Risk'[Residual Score]), 'Risk'[Risk Status] IN {\"Open\", \"Mitigating\", \"Monitoring\"})",
    C_WHOLE, "Sum of residual scores across open risks (post-mitigation).")
add("Risk", "Risk Reduction Pct",
    "1 - DIVIDE([Residual Exposure], [Total Risk Exposure])", C_PCT,
    "Exposure reduction achieved by planned mitigations.")
add("Risk", "Risks Past Due",
    "COUNTROWS(FILTER('Risk', NOT ISBLANK('Risk'[Due Date]) && 'Risk'[Due Date] < TODAY() "
    "&& 'Risk'[Risk Status] IN {\"Open\", \"Mitigating\"}))", C_WHOLE,
    "Open risks whose mitigation due date has passed.")
add("Risk", "Avg Risk Score", "AVERAGE('Risk'[Risk Score])", C_NUM1, "Mean risk score.")
add("Risk", "Response Actions", "COUNTROWS('Risk Response')", C_WHOLE,
    "Risk response actions in context.")
add("Risk", "Open Response Actions",
    "CALCULATE(COUNTROWS('Risk Response'), NOT 'Risk Response'[Action Status] IN {\"Done\"})", C_WHOLE,
    "Risk response actions not yet done.")

# Change
add("Change", "Change Requests", "COUNTROWS('Change Request')", C_WHOLE, "Count of CRs.")
add("Change", "Open CRs",
    "CALCULATE([Change Requests], NOT 'Change Request'[CR Status] IN {\"Closed\", \"Rejected\"})", C_WHOLE,
    "CRs still in the pipeline.")
add("Change", "Approved CRs",
    "CALCULATE([Change Requests], 'Change Request'[Decision] = \"Approved\")", C_WHOLE, "CRs approved.")
add("Change", "Rejected CRs",
    "CALCULATE([Change Requests], 'Change Request'[Decision] = \"Rejected\")", C_WHOLE, "CRs rejected.")
add("Change", "Pending CRs",
    "CALCULATE([Change Requests], 'Change Request'[Decision] = \"Pending\")", C_WHOLE,
    "CRs awaiting a decision.")
add("Change", "CR Approval Rate",
    "DIVIDE([Approved CRs], [Approved CRs] + [Rejected CRs])", C_PCT,
    "Approved share of decided CRs.")
add("Change", "Avg CR Cycle Days", "AVERAGE('Change Request'[Cycle Time Days])", C_NUM1,
    "Mean days from request to decision.")
add("Change", "Net Schedule Impact Days",
    "CALCULATE(SUM('Change Request'[Schedule Impact Days]), 'Change Request'[Decision] = \"Approved\")", C_WHOLE,
    "Net schedule delta from approved CRs.")
add("Change", "Emergency CRs",
    "CALCULATE([Change Requests], 'Change Request'[CR Class] = \"Emergency / Safety\")", C_WHOLE,
    "Emergency / safety class CRs.")

# Health
add("Health", "Status Reports", "COUNTROWS('Status Report')", C_WHOLE, "Reports submitted.")
add("Health", "Latest Report Date", "MAX('Status Report'[Period End])", "yyyy-mm-dd",
    "Most recent reporting period end.")
add("Health", "Latest Overall Status",
    "VAR d0 = MAX('Status Report'[Period End]) RETURN "
    "MAXX(FILTER('Status Report', 'Status Report'[Period End] = d0), 'Status Report'[Overall Status])", "",
    "Overall G/Y/R from the most recent report in context.")
add("Health", "Latest Trend",
    "VAR d0 = MAX('Status Report'[Period End]) RETURN "
    "MAXX(FILTER('Status Report', 'Status Report'[Period End] = d0), 'Status Report'[Trend])", "",
    "Trend from the most recent report in context.")
add("Health", "Health Score",
    "AVERAGEX('Status Report Area', SWITCH('Status Report Area'[Area Status], "
    "\"Green\", 3, \"Yellow\", 2, \"Red\", 1))", C_NUM2,
    "Mean knowledge-area health: Green=3, Yellow=2, Red=1.")
add("Health", "Area Entries", "COUNTROWS('Status Report Area')", C_WHOLE,
    "Knowledge-area health entries in context.")
add("Health", "Red Areas",
    "CALCULATE(COUNTROWS('Status Report Area'), 'Status Report Area'[Area Status] = \"Red\")", C_WHOLE,
    "Knowledge-area entries reported Red.")
add("Health", "Yellow Areas",
    "CALCULATE(COUNTROWS('Status Report Area'), 'Status Report Area'[Area Status] = \"Yellow\")", C_WHOLE,
    "Knowledge-area entries reported Yellow.")
add("Health", "Green Areas",
    "CALCULATE(COUNTROWS('Status Report Area'), 'Status Report Area'[Area Status] = \"Green\")", C_WHOLE,
    "Knowledge-area entries reported Green.")

# Status Page (leadership one-pager, mirrors the Theragen Status Report PPTX)
add("Status Page", "Theragen Project Name",
    "SELECTEDVALUE('Project'[Project Name], \"All projects - select one\")", "",
    "Selected project name for the status report header.")
add("Status Page", "Project Manager (Selected)",
    "SELECTEDVALUE('Project'[Project Manager], \"-\")", "",
    "Selected project's PM for the status report header.")
add("Status Page", "Target Date Completion",
    "VAR d = MAX('Project'[Planned Finish]) RETURN IF(ISBLANK(d), \"TBD\", FORMAT(d, \"M/D/YYYY\"))", "",
    "Planned finish of the selected project; TBD when not set.")
add("Status Page", "Current Phase",
    "SELECTEDVALUE('Project'[Lifecycle Phase], \"Multiple\")", "",
    "Current PMI process group of the selected project.")
add("Status Page", "Main Status",
    "SWITCH([Latest Overall Status], \"Green\", \"G\", \"Yellow\", \"Y\", \"Red\", \"R\", BLANK())", "",
    "Traffic-light letter from the latest status report: G / Y / R.")
add("Status Page", "Status Color",
    "SWITCH([Latest Overall Status], \"Green\", \"#00FF00\", \"Yellow\", \"#D6D60D\", "
    "\"Red\", \"#FF0000\", \"#605E5C\")", "",
    "Hex color for the Main Status traffic light. Values match the Theragen "
    "status deck exactly (G #00FF00 / Y #D6D60D / R #FF0000).")
add("Status Page", "Project Description (Selected)",
    "SELECTEDVALUE('Project'[Project Description], \"Select a single project\")", "",
    "Project description text block.")
add("Status Page", "Business Value (Selected)",
    "SELECTEDVALUE('Project'[Business Value], \"Select a single project\")", "",
    "Business value text block (charter business case).")
add("Status Page", "Latest Area Status",
    "VAR d0 = MAX('Status Report'[Period End]) RETURN "
    "CALCULATE(MAX('Status Report Area'[Area Status]), 'Status Report'[Period End] = d0)", "",
    "Health-check status of a knowledge area from the most recent report.")
add("Status Page", "Area Status Color",
    "SWITCH([Latest Area Status], \"Green\", \"#00FF00\", \"Yellow\", \"#D6D60D\", "
    "\"Red\", \"#FF0000\", \"#252423\")", "",
    "Deck-exact font color for the Health Check status column (conditional formatting).")
add("Status Page", "Report Date",
    "VAR d = MAX('Status Report'[Period End]) RETURN IF(ISBLANK(d), \"-\", FORMAT(d, \"M/D/YYYY\"))", "",
    "Date of the latest status report.")
add("Status Page", "Decisions Needed (Latest)",
    "VAR d0 = MAX('Status Report'[Period End]) RETURN "
    "CALCULATE(MAX('Status Report'[Decisions Needed]), 'Status Report'[Period End] = d0)", "",
    "Open decisions called out in the latest status report.")
add("Status Page", "Workstream Start",
    "MIN('Schedule Activity'[Planned Start])", "yyyy-mm-dd",
    "Earliest planned start of activities in context (workstream start date).")
add("Status Page", "Workstream Target",
    "MAX('Schedule Activity'[Planned Finish])", "yyyy-mm-dd",
    "Latest planned finish of activities in context (target implementation date).")
add("Status Page", "Workstream Status",
    "VAR tot = [Activities] VAR done = [Activities Done] "
    "VAR atRisk = [Activities At Risk] + [Activities Overdue] "
    "VAR started = [Activities In Progress] + done "
    "RETURN SWITCH(TRUE(), ISBLANK(tot) || tot = 0, \"-\", done = tot, \"COMPLETED\", "
    "atRisk > 0, \"AT RISK\", started = 0, \"NOT STARTED\", \"ON TRACK\")", "",
    "Roll-up status per workstream: COMPLETED / AT RISK / NOT STARTED / ON TRACK.")
add("Status Page", "Workstream Status Color",
    "SWITCH([Workstream Status], \"ON TRACK\", \"#00FF00\", \"AT RISK\", \"#D6D60D\", "
    "\"#252423\")", "",
    "Deck-exact font color for the Key Project Areas status column (conditional formatting).")
add("Status Page", "Status Key",
    "\"KEY:   G = Green   |   Y = Yellow   |   R = Off Track   |   C = Completed   |   "
    "NS = Not Started   |   H = Hold   |   CN = Cancelled\"", "",
    "Legend for status letters (matches the Theragen status report key).")
add("Status Page", "Phase Key",
    "\"PHASES:   Initiating - Planning - Executing - Monitoring - Closing\"", "",
    "Legend for PMI lifecycle phases used on this report.")

# Stakeholders
add("Stakeholders", "Stakeholders", "COUNTROWS('Stakeholder')", C_WHOLE, "Stakeholder register entries.")
add("Stakeholders", "High Influence Stakeholders",
    "CALCULATE([Stakeholders], 'Stakeholder'[Influence] = \"High\")", C_WHOLE, "Influence = High.")
add("Stakeholders", "Key Players",
    "CALCULATE([Stakeholders], 'Stakeholder'[Influence] = \"High\", 'Stakeholder'[Interest] = \"High\")",
    C_WHOLE, "High interest and high influence (manage closely).")
add("Stakeholders", "Accountable Count",
    "CALCULATE([Stakeholders], 'Stakeholder'[Engagement] = \"A\")", C_WHOLE, "RACI = Accountable.")
add("Stakeholders", "Responsible Count",
    "CALCULATE([Stakeholders], 'Stakeholder'[Engagement] = \"R\")", C_WHOLE, "RACI = Responsible.")

# Team
add("Team", "Team Members", "COUNTROWS('Team Member')", C_WHOLE, "Team assignments.")
add("Team", "Total FTE", "SUM('Team Member'[Allocation Pct]) / 100", C_NUM1,
    "Sum of allocation percentages as full-time equivalents.")
add("Team", "Avg Allocation Pct", "AVERAGE('Team Member'[Allocation Pct]) / 100", C_PCT,
    "Mean allocation per assignment.")

# Closing
add("Closing", "Lessons", "COUNTROWS('Lesson Learned')", C_WHOLE, "Lessons captured.")
add("Closing", "Open Lessons",
    "CALCULATE([Lessons], 'Lesson Learned'[Lesson Status] = \"Open\")", C_WHOLE, "Lessons awaiting action.")
add("Closing", "Adopted Lessons",
    "CALCULATE([Lessons], 'Lesson Learned'[Lesson Status] = \"Adopted\")", C_WHOLE,
    "Lessons adopted into practice.")
add("Closing", "Closure Items", "COUNTROWS('Closure Item')", C_WHOLE, "Closure checklist items.")
add("Closing", "Closure Items Done",
    "CALCULATE([Closure Items], 'Closure Item'[Done] = TRUE())", C_WHOLE, "Checklist items complete.")
add("Closing", "Closure Complete Pct", "DIVIDE([Closure Items Done], [Closure Items])", C_PCT,
    "Closure checklist completion.")


def emit_measures():
    out = ["/// Measure home table. All portfolio analytics measures live here.",
           "table _Measures",
           f"\tlineageTag: {tag('table', '_Measures')}",
           ""]
    for folder, name, expr, fmt, desc in M:
        if desc:
            out.append(f"\t/// {desc}")
        out.append(f"\tmeasure '{name}' = {expr}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append(f"\t\tlineageTag: {tag('measure', name)}")
        out.append("")
    out += ["\tcolumn Value",
            "\t\tdataType: string",
            "\t\tisHidden",
            f"\t\tlineageTag: {tag('col', '_Measures', 'Value')}",
            "\t\tsummarizeBy: none",
            "\t\tsourceColumn: Value",
            "",
            "\t\tannotation SummarizationSetBy = User",
            "",
            "\tpartition _Measures = m",
            "\t\tmode: import",
            "\t\tsource =",
            "\t\t\t\tlet",
            "\t\t\t\t    Source = Table.FromRows({}, {\"Value\"}),",
            "\t\t\t\t    Typed = Table.TransformColumnTypes(Source, {{\"Value\", type text}})",
            "\t\t\t\tin",
            "\t\t\t\t    Typed",
            "",
            "\tannotation PBI_ResultType = Table",
            ""]
    return "\n".join(out)


# ------------------------------------------------------------- relationships
RELS = [
    # fromTable, fromCol, toTable, toCol, active
    ("Schedule Activity", "WBS ID", "WBS Element", "WBS ID", True),
    ("Budget Line", "WBS ID", "WBS Element", "WBS ID", True),
    ("WBS Element", "Project ID", "Project", "Project ID", True),
    ("Milestone", "Project ID", "Project", "Project ID", True),
    ("Risk", "Project ID", "Project", "Project ID", True),
    ("Change Request", "Project ID", "Project", "Project ID", True),
    ("Status Report", "Project ID", "Project", "Project ID", True),
    ("Stakeholder", "Project ID", "Project", "Project ID", True),
    ("Team Member", "Project ID", "Project", "Project ID", True),
    ("Lesson Learned", "Project ID", "Project", "Project ID", True),
    ("Closure Item", "Project ID", "Project", "Project ID", True),
    ("Risk Response", "Risk ID", "Risk", "Risk ID", True),
    ("Status Report Area", "Report ID", "Status Report", "Report ID", True),
    ("Status Report Area", "Knowledge Area", "Knowledge Area", "Knowledge Area", True),
    ("Schedule Activity", "Planned Finish", "Date", "Date", True),
    ("Schedule Activity", "Planned Start", "Date", "Date", False),
    ("Schedule Activity", "Actual Finish", "Date", "Date", False),
    ("Milestone", "Baseline Date", "Date", "Date", True),
    ("Milestone", "Forecast Date", "Date", "Date", False),
    ("Milestone", "Actual Date", "Date", "Date", False),
    ("Risk", "Due Date", "Date", "Date", True),
    ("Change Request", "Requested Date", "Date", "Date", True),
    ("Change Request", "Decided Date", "Date", "Date", False),
    ("Status Report", "Period End", "Date", "Date", True),
    ("Team Member", "Start Date", "Date", "Date", True),
    ("Schedule Activity", "Department", "Department", "Department", True),
    ("Risk", "Department", "Department", "Department", True),
    ("Stakeholder", "Department", "Department", "Department", True),
    ("Team Member", "Department", "Department", "Department", True),
    ("Schedule Activity", "Owner ID", "Person", "Person ID", True),
    ("Risk", "Owner ID", "Person", "Person ID", True),
    ("Change Request", "Requested By ID", "Person", "Person ID", True),
    ("Stakeholder", "Person ID", "Person", "Person ID", True),
    ("Team Member", "Person ID", "Person", "Person ID", True),
    ("Recent Accomplishment", "Project ID", "Project", "Project ID", True),
    ("Upcoming Next Step", "Project ID", "Project", "Project ID", True),
]


def emit_relationships():
    out = []
    for ft, fc, tt, tc, active in RELS:
        rid = tag("rel", ft, fc, tt, tc)
        out.append(f"relationship {rid}")
        if not active:
            out.append("\tisActive: false")
        out.append(f"\tfromColumn: '{ft}'.'{fc}'")
        out.append(f"\ttoColumn: '{tt}'.'{tc}'")
        out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------- model
TABLE_ORDER = ["Project", "Department", "Person", "WBS Element", "Knowledge Area",
               "Schedule Activity", "Milestone", "Budget Line", "Risk", "Risk Response",
               "Change Request", "Status Report", "Status Report Area", "Stakeholder",
               "Team Member", "Lesson Learned", "Closure Item"]


def emit_model():
    qorder = ", ".join(f"\"{t}\"" for t in ["DataFolder"] + TABLE_ORDER + ["_Measures"])
    out = ["model Model",
           "\tculture: en-US",
           "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
           "\tsourceQueryCulture: en-US",
           "\tdataAccessOptions",
           "\t\tlegacyRedirects",
           "\t\treturnErrorValuesAsNull",
           "",
           f"annotation PBI_QueryOrder = [{qorder}]",
           "",
           "annotation __PBI_TimeIntelligenceEnabled = 0",
           ""]
    for t in TABLE_ORDER + ["Date", "Recent Accomplishment", "Upcoming Next Step", "_Measures"]:
        out.append(f"ref table '{t}'" if (" " in t or t == "Date") else f"ref table {t}")
    out.append("")
    out.append("ref cultureInfo en-US")
    out.append("")
    return "\n".join(out)


def emit_expressions():
    folder = os.path.join(ROOT, "SampleData")
    return "\n".join([
        "/// Folder containing the PMBOK sample data CSVs. Repoint when the PostgreSQL source goes live.",
        f'expression DataFolder = "{folder}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
        f"\tlineageTag: {tag('expr', 'DataFolder')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
    ])


def main():
    w(os.path.join(ROOT, f"{NAME}.pbip"), (
        '{\n'
        '  "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",\n'
        '  "version": "1.0",\n'
        '  "artifacts": [\n'
        '    {\n'
        '      "report": {\n'
        f'        "path": "{NAME}.Report"\n'
        '      }\n'
        '    }\n'
        '  ],\n'
        '  "settings": {\n'
        '    "enableAutoRecovery": true\n'
        '  }\n'
        '}\n'))

    w(os.path.join(SM, ".platform"), (
        '{\n'
        '  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",\n'
        '  "metadata": {\n'
        '    "type": "SemanticModel",\n'
        f'    "displayName": "{NAME}"\n'
        '  },\n'
        '  "config": {\n'
        '    "version": "2.0",\n'
        f'    "logicalId": "{tag("platform", "semanticmodel")}"\n'
        '  }\n'
        '}\n'))

    w(os.path.join(SM, "definition.pbism"), (
        '{\n'
        '  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",\n'
        '  "version": "4.0",\n'
        '  "settings": {}\n'
        '}\n'))

    # NOTE: do not emit .pbi/editorSettings.json - Desktop requires a versioned
    # $schema format for it and creates its own on first save (June 2026 builds
    # reject files without $schema/version).
    w(os.path.join(DEF, "database.tmdl"), "database\n\tcompatibilityLevel: 1601\n")
    w(os.path.join(DEF, "model.tmdl"), emit_model())
    w(os.path.join(DEF, "expressions.tmdl"), emit_expressions())
    w(os.path.join(DEF, "relationships.tmdl"), emit_relationships())
    w(os.path.join(DEF, "cultures", "en-US.tmdl"), (
        "cultureInfo en-US\n"
        "\tlinguisticMetadata = {\"Version\": \"1.0.0\", \"Language\": \"en-US\"}\n"
        "\t\tcontentType: json\n"))

    for name in TABLE_ORDER:
        w(os.path.join(DEF, "tables", f"{name}.tmdl"), emit_table(name, TABLES[name]))
    w(os.path.join(DEF, "tables", "Date.tmdl"), emit_date())
    for name, t in CALC_TABLES.items():
        w(os.path.join(DEF, "tables", f"{name}.tmdl"), emit_calc_table(name, t))
    w(os.path.join(DEF, "tables", "_Measures.tmdl"), emit_measures())
    print(f"\nSemantic model written: {len(TABLE_ORDER) + len(CALC_TABLES) + 2} tables, "
          f"{len(M)} measures, {len(RELS)} relationships")


if __name__ == "__main__":
    main()
