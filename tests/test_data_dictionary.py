"""Tests for the data-dictionary generator (tools/build_data_dictionary.py).

Pure parsing/rendering functions are tested against small synthetic TMDL
fixtures (spaces for indentation; the parser is whitespace-agnostic so the same
code handles the real tab-indented model), plus a smoke test over the live model.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bdd", ROOT / "tools" / "build_data_dictionary.py")
bdd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bdd)

TABLE_FIXTURE = """\
/// A fact table for demo.
table Demo
    lineageTag: abc

    /// The surrogate key.
    column 'Demo ID'
        dataType: string
        isHidden
        summarizeBy: none
        sourceColumn: Demo ID

    column Amount
        dataType: double
        formatString: #,##0
        summarizeBy: sum
        sourceColumn: Amount

    partition Demo = m
        mode: import
        source =
                let
                    Source = PostgreSQL.Database(PgServer, PgDatabase),
                    Data = Source{[Schema = "bi", Item = "demo"]}[Data]
                in
                    Data

    annotation PBI_ResultType = Table
"""

MEASURE_FIXTURE = """\
/// Measure home.
table _Measures
    lineageTag: m

    /// Count of widgets.
    measure Widgets = COUNTROWS('Widget')
        formatString: #,0
        displayFolder: Core
        lineageTag: x

    measure 'Undoc Measure' = 1 + 1
        formatString: 0

    column Value
        dataType: string
        isHidden
        sourceColumn: Value
"""

REL_FIXTURE = """\
relationship 111
    fromColumn: 'Schedule Activity'.'WBS ID'
    toColumn: 'WBS Element'.'WBS ID'

relationship 222
    fromColumn: Risk.'Project ID'
    toColumn: Project.'Project ID'
"""

ROLE_FIXTURE = """\
/// Read-only scoped role.
role 'Scoped Viewer'
    modelPermission: read
    lineageTag: r
    tablePermission Project = 1 = 1
"""


def test_parse_table_name_description_source():
    t = bdd.parse_table(TABLE_FIXTURE)
    assert t["name"] == "Demo"
    assert t["description"] == "A fact table for demo."
    assert t["source"] == "demo"


def test_parse_table_columns():
    cols = {c["name"]: c for c in bdd.parse_table(TABLE_FIXTURE)["columns"]}
    assert list(cols) == ["Demo ID", "Amount"]
    assert cols["Demo ID"]["data_type"] == "string"
    assert cols["Demo ID"]["hidden"] is True
    assert cols["Demo ID"]["description"] == "The surrogate key."
    assert cols["Amount"]["hidden"] is False
    assert cols["Amount"]["format"] == "#,##0"
    assert cols["Amount"]["description"] is None


def test_parse_measures():
    t = bdd.parse_table(MEASURE_FIXTURE)
    ms = {m["name"]: m for m in t["measures"]}
    assert set(ms) == {"Widgets", "Undoc Measure"}
    assert ms["Widgets"]["description"] == "Count of widgets."
    assert ms["Widgets"]["expression"] == "COUNTROWS('Widget')"
    assert ms["Widgets"]["format"] == "#,0"
    assert ms["Widgets"]["folder"] == "Core"
    assert ms["Undoc Measure"]["description"] is None
    assert [c["name"] for c in t["columns"]] == ["Value"]


def test_parse_relationships():
    rels = bdd.parse_relationships(REL_FIXTURE)
    assert len(rels) == 2
    assert (rels[0]["from_table"], rels[0]["from_column"]) == ("Schedule Activity", "WBS ID")
    assert (rels[0]["to_table"], rels[0]["to_column"]) == ("WBS Element", "WBS ID")
    assert (rels[1]["from_table"], rels[1]["to_table"]) == ("Risk", "Project")


def test_parse_role():
    r = bdd.parse_role(ROLE_FIXTURE)
    assert r["name"] == "Scoped Viewer"
    assert r["description"] == "Read-only scoped role."
    assert r["permission"] == "read"


def test_audit_flags_only_undocumented():
    items = bdd.audit([bdd.parse_table(TABLE_FIXTURE)], [])
    assert any("[Amount]" in x for x in items)          # undocumented column flagged
    assert all("Demo ID" not in x for x in items)        # documented column not flagged
    assert all(not x.startswith("table ") for x in items)  # documented table not flagged


def test_provenance_header_contains_fields():
    h = bdd.provenance_header("abc123", "2026-06-14", "2.6",
                              {"tables": 3, "columns": 10, "measures": 5, "relationships": 4, "roles": 2})
    for token in ("abc123", "2026-06-14", "2.6", "3 tables", "5 measures", "2 roles"):
        assert token in h


def test_real_model_smoke():
    model = bdd.load_model()
    assert len(model["tables"]) >= 30
    assert len(model["relationships"]) >= 20
    names = {t["name"] for t in model["tables"]}
    assert "Decision" in names and "_Measures" in names
    md = bdd.render(model["tables"], model["relationships"], model["roles"], "> stamp")
    assert "Data Dictionary" in md and "Decision" in md
    measures = next(t for t in model["tables"] if t["name"] == "_Measures")["measures"]
    assert measures and all(m["description"] for m in measures)  # measures already documented
