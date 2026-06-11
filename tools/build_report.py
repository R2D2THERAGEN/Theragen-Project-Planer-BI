"""Emit the Theragen Project Planner PBIR report definition.

Eight pages mirroring the PMBOK template set. Visual JSON uses the PBIR
enhanced report format (GA). Re-run to rebuild definition/pages from scratch.
"""
import json
import os
import shutil
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "Theragen Project Planner"
RPT = os.path.join(ROOT, f"{NAME}.Report")
PAGES = os.path.join(RPT, "definition", "pages")
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

MEAS = "_Measures"


def vid(*parts):
    return uuid.uuid5(NS, "thg-rpt/" + "/".join(parts)).hex[:20]


def w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": f"'{v}'"}}}


def col(table, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": prop}}


def mea(prop, table=MEAS):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": prop}}


def proj(field, table_prop):
    return {"field": field, "queryRef": table_prop}


def title(text):
    return {"title": [{"properties": {"show": lit(True), "text": lit(text)}}]}


def visual(name, vtype, pos, query_state, *, vtitle=None, objects=None, sort=None):
    v = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.0.0/schema.json",
        "name": name,
        "position": pos,
        "visual": {
            "visualType": vtype,
            "query": {"queryState": query_state},
            "drillFilterOtherVisuals": True,
        },
    }
    if sort:
        v["visual"]["query"]["sortDefinition"] = sort
    if objects:
        v["visual"]["objects"] = objects
    if vtitle is not None:
        v["visual"]["visualContainerObjects"] = title(vtitle)
    return v


def pos(x, y, wd, ht, z=1000):
    return {"x": x, "y": y, "z": z, "width": wd, "height": ht}


def card(page, key, measure, x, y, wd=200, ht=100, label=None):
    qs = {"Values": {"projections": [proj(mea(measure), f"{MEAS}.{measure}")]}}
    objects = {"labels": [{"properties": {"fontSize": lit(20)}}]}
    return visual(vid(page, key), "card", pos(x, y, wd, ht), qs,
                  vtitle=label or measure, objects=objects)


def chart(page, key, vtype, cat_field, cat_ref, y_measures, x, y, wd, ht,
          series=None, vtitle="", sort_desc_by=None):
    qs = {
        "Category": {"projections": [proj(cat_field, cat_ref)]},
        "Y": {"projections": [proj(mea(m), f"{MEAS}.{m}") for m in y_measures]},
    }
    if series:
        qs["Series"] = {"projections": [proj(series[0], series[1])]}
    sort = None
    if sort_desc_by:
        sort = {"sort": [{"field": mea(sort_desc_by), "direction": "Descending"}], "isDefaultSort": True}
    return visual(vid(page, key), vtype, pos(x, y, wd, ht), qs, vtitle=vtitle, sort=sort)


def table_vis(page, key, fields, x, y, wd, ht, vtitle="", sort=None):
    qs = {"Values": {"projections": [proj(f, r) for f, r in fields]}}
    return visual(vid(page, key), "tableEx", pos(x, y, wd, ht), qs, vtitle=vtitle, sort=sort)


def matrix(page, key, rows, cols, vals, x, y, wd, ht, vtitle=""):
    qs = {
        "Rows": {"projections": [proj(f, r) for f, r in rows]},
        "Values": {"projections": [proj(f, r) for f, r in vals]},
    }
    if cols:
        qs["Columns"] = {"projections": [proj(f, r) for f, r in cols]}
    return visual(vid(page, key), "pivotTable", pos(x, y, wd, ht), qs, vtitle=vtitle)


def slicer(page, key, field, ref, x, y, wd=250, ht=140, vtitle=""):
    qs = {"Values": {"projections": [proj(field, ref)]}}
    return visual(vid(page, key), "slicer", pos(x, y, wd, ht), qs, vtitle=vtitle)


# ---------------------------------------------------------------------------
PAGE_DEFS = []  # (name, displayName, [visuals])

# ---- Page 1: Portfolio Overview -------------------------------------------
pg = "portfolio"
vis = []
cards = ["Active Projects", "Portfolio Charter Budget", "SPI", "High Risks",
         "Open CRs", "Milestones At Risk"]
for i, m in enumerate(cards):
    vis.append(card(pg, f"c{i}", m, 8 + i * 212, 8))
vis.append(table_vis(pg, "health", [
    (col("Project", "Project Code"), "Project.Project Code"),
    (col("Project", "Project Name"), "Project.Project Name"),
    (col("Project", "Project Manager"), "Project.Project Manager"),
    (col("Project", "Lifecycle Phase"), "Project.Lifecycle Phase"),
    (mea("Latest Overall Status"), f"{MEAS}.Latest Overall Status"),
    (mea("SPI"), f"{MEAS}.SPI"),
    (mea("Budget Total"), f"{MEAS}.Budget Total"),
    (mea("Open Risks"), f"{MEAS}.Open Risks"),
], 8, 120, 700, 280, vtitle="Project portfolio health"))
vis.append(chart(pg, "bud_dept", "clusteredBarChart",
                 col("Project", "Primary Department"), "Project.Primary Department",
                 ["Budget Total"], 716, 120, 556, 280,
                 vtitle="Funded budget by department", sort_desc_by="Budget Total"))
vis.append(chart(pg, "phase", "clusteredColumnChart",
                 col("Project", "Lifecycle Phase"), "Project.Lifecycle Phase",
                 ["Projects"], 8, 408, 420, 300, vtitle="Projects by lifecycle phase"))
vis.append(chart(pg, "bud_cat", "donutChart",
                 col("Budget Line", "Cost Category"), "Budget Line.Cost Category",
                 ["Budget Total"], 436, 408, 420, 300, vtitle="Budget mix by cost category"))
vis.append(chart(pg, "risk_cat", "clusteredBarChart",
                 col("Risk", "Risk Category"), "Risk.Risk Category",
                 ["Open Risks"], 864, 408, 408, 300,
                 vtitle="Open risks by category", sort_desc_by="Open Risks"))
PAGE_DEFS.append((pg, "Portfolio Overview", vis))

# ---- Page 2: Project Status ------------------------------------------------
pg = "status"
vis = [slicer(pg, "slc", col("Project", "Project Name"), "Project.Project Name",
              8, 8, 250, 220, vtitle="Project")]
for i, (m, lbl) in enumerate([("Latest Overall Status", "Overall status"),
                              ("Latest Trend", "Trend"),
                              ("Health Score", "Health score (3=green)"),
                              ("Latest Report Date", "Latest report")]):
    vis.append(card(pg, f"c{i}", m, 270 + i * 252, 8, wd=244, ht=100, label=lbl))
vis.append(chart(pg, "trend", "stackedColumnChart",
                 col("Status Report", "Period End"), "Status Report.Period End",
                 ["Area Entries"], 270, 116, 1002, 250,
                 series=(col("Status Report Area", "Area Status"), "Status Report Area.Area Status"),
                 vtitle="Knowledge-area health over reporting periods"))
vis.append(table_vis(pg, "ka", [
    (col("Knowledge Area", "Knowledge Area"), "Knowledge Area.Knowledge Area"),
    (mea("Green Areas"), f"{MEAS}.Green Areas"),
    (mea("Yellow Areas"), f"{MEAS}.Yellow Areas"),
    (mea("Red Areas"), f"{MEAS}.Red Areas"),
    (mea("Health Score"), f"{MEAS}.Health Score"),
], 8, 236, 504, 240, vtitle="Health by knowledge area"))
vis.append(table_vis(pg, "reports", [
    (col("Status Report", "Period End"), "Status Report.Period End"),
    (col("Status Report", "Overall Status"), "Status Report.Overall Status"),
    (col("Status Report", "Trend"), "Status Report.Trend"),
    (col("Status Report", "Executive Summary"), "Status Report.Executive Summary"),
    (col("Status Report", "Decisions Needed"), "Status Report.Decisions Needed"),
], 8, 484, 1264, 224, vtitle="Status reports - executive summary and decisions needed",
    sort={"sort": [{"field": col("Status Report", "Period End"),
                    "direction": "Descending"}], "isDefaultSort": True}))
for i, (m, lbl) in enumerate([("Open Risks", None), ("Open CRs", None),
                              ("Activities Overdue", None), ("Closure Complete Pct", "Closure complete")]):
    vis.append(card(pg, f"k{i}", m, 520 + i * 190, 374, wd=182, ht=100, label=lbl))
PAGE_DEFS.append((pg, "Project Status", vis))

# ---- Page 3: Schedule & Milestones -----------------------------------------
pg = "schedule"
vis = [slicer(pg, "slc", col("Project", "Project Name"), "Project.Project Name",
              8, 8, 250, 220, vtitle="Project")]
for i, (m, lbl) in enumerate([("Pct Complete (Duration Weighted)", "% complete"),
                              ("SPI", None), ("Activities Overdue", None),
                              ("On-Time Completion Pct", "On-time completion")]):
    vis.append(card(pg, f"c{i}", m, 270 + i * 252, 8, wd=244, ht=100, label=lbl))
vis.append(chart(pg, "wbs", "clusteredBarChart",
                 col("WBS Element", "Deliverable"), "WBS Element.Deliverable",
                 ["Pct Complete (Duration Weighted)"], 270, 116, 500, 280,
                 vtitle="% complete by deliverable"))
vis.append(chart(pg, "dept", "stackedBarChart",
                 col("Department", "Department"), "Department.Department",
                 ["Activities"], 778, 116, 494, 280,
                 series=(col("Schedule Activity", "Activity Status"), "Schedule Activity.Activity Status"),
                 vtitle="Activities by department and status"))
vis.append(table_vis(pg, "acts", [
    (col("Schedule Activity", "Activity Code"), "Schedule Activity.Activity Code"),
    (col("Schedule Activity", "Activity Name"), "Schedule Activity.Activity Name"),
    (col("Schedule Activity", "Owner"), "Schedule Activity.Owner"),
    (col("Schedule Activity", "Planned Finish"), "Schedule Activity.Planned Finish"),
    (col("Schedule Activity", "Activity Status"), "Schedule Activity.Activity Status"),
    (col("Schedule Activity", "Pct Complete"), "Schedule Activity.Pct Complete"),
], 8, 404, 700, 304, vtitle="Activity register (sorted by planned finish)",
    sort={"sort": [{"field": col("Schedule Activity", "Planned Finish"),
                    "direction": "Ascending"}], "isDefaultSort": True}))
vis.append(table_vis(pg, "miles", [
    (col("Milestone", "Milestone"), "Milestone.Milestone"),
    (col("Milestone", "Baseline Date"), "Milestone.Baseline Date"),
    (col("Milestone", "Forecast Date"), "Milestone.Forecast Date"),
    (col("Milestone", "Milestone Status"), "Milestone.Milestone Status"),
    (col("Milestone", "Slip Days"), "Milestone.Slip Days"),
], 716, 404, 556, 304, vtitle="Milestones - baseline vs forecast",
    sort={"sort": [{"field": col("Milestone", "Baseline Date"),
                    "direction": "Ascending"}], "isDefaultSort": True}))
PAGE_DEFS.append((pg, "Schedule & Milestones", vis))

# ---- Page 4: Cost & Budget --------------------------------------------------
pg = "cost"
vis = []
for i, (m, lbl) in enumerate([("Budget Total", "Funded budget"),
                              ("Contingency Amount", None),
                              ("Approved CR Cost Impact", "Approved CR impact"),
                              ("Working Budget", None),
                              ("Earned Value", None), ("Planned Value", None)]):
    vis.append(card(pg, f"c{i}", m, 8 + i * 212, 8, label=lbl))
vis.append(chart(pg, "cat", "clusteredBarChart",
                 col("Budget Line", "Cost Category"), "Budget Line.Cost Category",
                 ["Budget Total"], 8, 116, 420, 280,
                 vtitle="Budget by cost category", sort_desc_by="Budget Total"))
vis.append(chart(pg, "fund", "donutChart",
                 col("Budget Line", "Funding Source"), "Budget Line.Funding Source",
                 ["Budget Total"], 436, 116, 360, 280, vtitle="Budget by funding source"))
vis.append(chart(pg, "proj", "clusteredColumnChart",
                 col("Project", "Project Code"), "Project.Project Code",
                 ["Budget Total", "Working Budget"], 804, 116, 468, 280,
                 vtitle="Funded vs working budget by project"))
vis.append(matrix(pg, "wbsmx",
                  [(col("Project", "Project Code"), "Project.Project Code"),
                   (col("WBS Element", "Deliverable"), "WBS Element.Deliverable")],
                  [],
                  [(mea("Labor Amount"), f"{MEAS}.Labor Amount"),
                   (mea("Materials Amount"), f"{MEAS}.Materials Amount"),
                   (mea("Vendor Amount"), f"{MEAS}.Vendor Amount"),
                   (mea("Other Amount"), f"{MEAS}.Other Amount"),
                   (mea("Budget Total"), f"{MEAS}.Budget Total")],
                  8, 404, 836, 304, vtitle="Cost breakdown by project and deliverable"))
vis.append(table_vis(pg, "evm", [
    (col("Project", "Project Code"), "Project.Project Code"),
    (mea("BAC (WBS Estimates)"), f"{MEAS}.BAC (WBS Estimates)"),
    (mea("Planned Value"), f"{MEAS}.Planned Value"),
    (mea("Earned Value"), f"{MEAS}.Earned Value"),
    (mea("Schedule Variance (SV)"), f"{MEAS}.Schedule Variance (SV)"),
    (mea("SPI"), f"{MEAS}.SPI"),
], 852, 404, 420, 304, vtitle="Earned value by project"))
PAGE_DEFS.append((pg, "Cost & Budget", vis))

# ---- Page 5: Risk Management ------------------------------------------------
pg = "risk"
vis = []
for i, (m, lbl) in enumerate([("Open Risks", None), ("High Risks", None),
                              ("Critical Risks", None), ("Risks Past Due", None),
                              ("Risk Reduction Pct", "Mitigation effect"),
                              ("Open Response Actions", "Open actions")]):
    vis.append(card(pg, f"c{i}", m, 8 + i * 212, 8, label=lbl))
vis.append(matrix(pg, "heat",
                  [(col("Risk", "Likelihood"), "Risk.Likelihood")],
                  [(col("Risk", "Impact"), "Risk.Impact")],
                  [(mea("Risks"), f"{MEAS}.Risks")],
                  8, 116, 420, 280, vtitle="5x5 heat map - likelihood x impact"))
vis.append(chart(pg, "cat", "stackedBarChart",
                 col("Risk", "Risk Category"), "Risk.Risk Category",
                 ["Open Risks"], 436, 116, 420, 280,
                 series=(col("Risk", "Severity"), "Risk.Severity"),
                 vtitle="Open risks by category and severity", sort_desc_by="Open Risks"))
vis.append(chart(pg, "resp", "clusteredColumnChart",
                 col("Risk Response", "Action Status"), "Risk Response.Action Status",
                 ["Response Actions"], 864, 116, 408, 280,
                 vtitle="Response actions by status"))
vis.append(table_vis(pg, "top", [
    (col("Risk", "Risk Code"), "Risk.Risk Code"),
    (col("Risk", "Project Code"), "Risk.Project Code"),
    (col("Risk", "Risk Description"), "Risk.Risk Description"),
    (col("Risk", "Severity"), "Risk.Severity"),
    (col("Risk", "Risk Score"), "Risk.Risk Score"),
    (col("Risk", "Risk Status"), "Risk.Risk Status"),
    (col("Risk", "Owner"), "Risk.Owner"),
    (col("Risk", "Due Date"), "Risk.Due Date"),
], 8, 404, 1264, 304, vtitle="Risk register (sorted by score)",
    sort={"sort": [{"field": col("Risk", "Risk Score"),
                    "direction": "Descending"}], "isDefaultSort": True}))
PAGE_DEFS.append((pg, "Risk Management", vis))

# ---- Page 6: Change Control --------------------------------------------------
pg = "change"
vis = []
for i, (m, lbl) in enumerate([("Change Requests", None), ("Open CRs", None),
                              ("Pending CRs", None), ("CR Approval Rate", None),
                              ("Avg CR Cycle Days", None),
                              ("Approved CR Cost Impact", "Approved cost impact")]):
    vis.append(card(pg, f"c{i}", m, 8 + i * 212, 8, label=lbl))
vis.append(chart(pg, "pipe", "clusteredColumnChart",
                 col("Change Request", "CR Status"), "Change Request.CR Status",
                 ["Change Requests"], 8, 116, 420, 280, vtitle="CR pipeline by status"))
vis.append(chart(pg, "class", "stackedColumnChart",
                 col("Change Request", "CR Class"), "Change Request.CR Class",
                 ["Change Requests"], 436, 116, 420, 280,
                 series=(col("Change Request", "Decision"), "Change Request.Decision"),
                 vtitle="CRs by class and decision"))
vis.append(chart(pg, "trend", "lineChart",
                 col("Date", "Year Month"), "Date.Year Month",
                 ["Change Requests"], 864, 116, 408, 280, vtitle="CRs raised by month"))
vis.append(table_vis(pg, "log", [
    (col("Change Request", "CR Code"), "Change Request.CR Code"),
    (col("Change Request", "Project Code"), "Change Request.Project Code"),
    (col("Change Request", "Change Type"), "Change Request.Change Type"),
    (col("Change Request", "CR Class"), "Change Request.CR Class"),
    (col("Change Request", "Requested Date"), "Change Request.Requested Date"),
    (col("Change Request", "Decision"), "Change Request.Decision"),
    (col("Change Request", "Cycle Time Days"), "Change Request.Cycle Time Days"),
    (col("Change Request", "Cost Impact"), "Change Request.Cost Impact"),
    (col("Change Request", "Schedule Impact Days"), "Change Request.Schedule Impact Days"),
], 8, 404, 1264, 304, vtitle="Change log",
    sort={"sort": [{"field": col("Change Request", "Requested Date"),
                    "direction": "Descending"}], "isDefaultSort": True}))
PAGE_DEFS.append((pg, "Change Control", vis))

# ---- Page 7: Stakeholders & Team ----------------------------------------------
pg = "people"
vis = [slicer(pg, "slc", col("Project", "Project Name"), "Project.Project Name",
              8, 8, 250, 220, vtitle="Project")]
for i, (m, lbl) in enumerate([("Stakeholders", None), ("Key Players", "Key players (H/H)"),
                              ("Team Members", None), ("Total FTE", None)]):
    vis.append(card(pg, f"c{i}", m, 270 + i * 252, 8, wd=244, ht=100, label=lbl))
vis.append(matrix(pg, "grid",
                  [(col("Stakeholder", "Interest"), "Stakeholder.Interest")],
                  [(col("Stakeholder", "Influence"), "Stakeholder.Influence")],
                  [(mea("Stakeholders"), f"{MEAS}.Stakeholders")],
                  270, 116, 380, 240, vtitle="Interest x influence grid"))
vis.append(chart(pg, "raci", "stackedBarChart",
                 col("Department", "Department"), "Department.Department",
                 ["Stakeholders"], 658, 116, 614, 240,
                 series=(col("Stakeholder", "Engagement"), "Stakeholder.Engagement"),
                 vtitle="RACI engagement by department"))
vis.append(table_vis(pg, "stk", [
    (col("Stakeholder", "Stakeholder"), "Stakeholder.Stakeholder"),
    (col("Stakeholder", "Stakeholder Role"), "Stakeholder.Stakeholder Role"),
    (col("Stakeholder", "Department"), "Stakeholder.Department"),
    (col("Stakeholder", "Engagement"), "Stakeholder.Engagement"),
    (col("Stakeholder", "Interest"), "Stakeholder.Interest"),
    (col("Stakeholder", "Influence"), "Stakeholder.Influence"),
], 8, 364, 700, 344, vtitle="Stakeholder register"))
vis.append(chart(pg, "fte", "clusteredBarChart",
                 col("Department", "Department"), "Department.Department",
                 ["Total FTE"], 716, 364, 556, 344,
                 vtitle="Team FTE by department", sort_desc_by="Total FTE"))
PAGE_DEFS.append((pg, "Stakeholders & Team", vis))

# ---- Page 8: Lessons & Closure --------------------------------------------------
pg = "closing"
vis = []
for i, (m, lbl) in enumerate([("Lessons", None), ("Open Lessons", None),
                              ("Adopted Lessons", None), ("Closure Items Done", None),
                              ("Closure Complete Pct", "Closure complete")]):
    vis.append(card(pg, f"c{i}", m, 8 + i * 212, 8, label=lbl))
vis.append(chart(pg, "cat", "clusteredBarChart",
                 col("Lesson Learned", "Lesson Category"), "Lesson Learned.Lesson Category",
                 ["Lessons"], 8, 116, 420, 260,
                 vtitle="Lessons by category", sort_desc_by="Lessons"))
vis.append(chart(pg, "st", "clusteredColumnChart",
                 col("Lesson Learned", "Lesson Status"), "Lesson Learned.Lesson Status",
                 ["Lessons"], 436, 116, 420, 260, vtitle="Lessons by status"))
vis.append(chart(pg, "cls", "stackedBarChart",
                 col("Closure Item", "Project Code"), "Closure Item.Project Code",
                 ["Closure Items"], 864, 116, 408, 260,
                 series=(col("Closure Item", "Done"), "Closure Item.Done"),
                 vtitle="Closure checklist by project"))
vis.append(table_vis(pg, "log", [
    (col("Lesson Learned", "Project Code"), "Lesson Learned.Project Code"),
    (col("Lesson Learned", "Lesson Category"), "Lesson Learned.Lesson Category"),
    (col("Lesson Learned", "Lesson"), "Lesson Learned.Lesson"),
    (col("Lesson Learned", "Recommendation"), "Lesson Learned.Recommendation"),
    (col("Lesson Learned", "Lesson Status"), "Lesson Learned.Lesson Status"),
], 8, 384, 1264, 324, vtitle="Lessons learned register"))
PAGE_DEFS.append((pg, "Lessons & Closure", vis))


# ---------------------------------------------------------------------------
def main():
    # Best-effort clean: OneDrive/Desktop can hold transient locks. Generation is
    # deterministic (same file set every run), so overwriting in place is safe.
    if os.path.isdir(PAGES):
        shutil.rmtree(PAGES, ignore_errors=True)

    w(os.path.join(RPT, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(NS, "thg-bi/platform/report"))},
    })
    w(os.path.join(RPT, "definition.pbir"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    })
    # Required by Desktop's PBIR reader ("Cannot find file 'version.json'" otherwise).
    w(os.path.join(RPT, "definition", "version.json"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })
    w(os.path.join(RPT, "definition", "report.json"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.55",
                                          "type": "SharedResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json",
                                         "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True},
    })
    w(os.path.join(PAGES, "pages.json"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p for p, _, _ in PAGE_DEFS],
        "activePageName": PAGE_DEFS[0][0],
    })
    nvis = 0
    for pname, display, vis in PAGE_DEFS:
        w(os.path.join(PAGES, pname, "page.json"), {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.0.0/schema.json",
            "name": pname,
            "displayName": display,
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
        })
        for v in vis:
            w(os.path.join(PAGES, pname, "visuals", v["name"], "visual.json"), v)
            nvis += 1
    print(f"Report written: {len(PAGE_DEFS)} pages, {nvis} visuals")


if __name__ == "__main__":
    main()
