"""Tests for tools/build_admin_map.py (pure helpers + registry integrity)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_admin_map as am  # noqa: E402


# --- list_keys / coverage ----------------------------------------------------
def test_list_keys_picks_intake_and_list_ids():
    cfg = {"site_id": "x", "list_id": "a", "list_name": "n",
           "risk_list_id": "b", "report_access_list_id": "c"}
    assert set(am.list_keys(cfg)) == {"list_id", "risk_list_id", "report_access_list_id"}
    assert "site_id" not in am.list_keys(cfg)
    assert "list_name" not in am.list_keys(cfg)  # not an id reference


def test_coverage_clean_when_surfaces_match_config():
    cfg = {k: "id" for k in (s["list_key"] for s in am.SURFACES)}
    cfg["site_id"] = "x"
    unmapped, extra = am.coverage(am.SURFACES, cfg)
    assert unmapped == [] and extra == []


def test_coverage_flags_unmapped_config_list():
    cfg = {k: "id" for k in (s["list_key"] for s in am.SURFACES)}
    cfg["new_widget_list_id"] = "id"  # a List added to config but not the map
    unmapped, extra = am.coverage(am.SURFACES, cfg)
    assert unmapped == ["new_widget_list_id"] and extra == []


def test_coverage_flags_extra_surface():
    surfaces = am.SURFACES + [{"list_key": "ghost_list_id"}]
    cfg = {k: "id" for k in (s["list_key"] for s in am.SURFACES)}
    unmapped, extra = am.coverage(surfaces, cfg)
    assert extra == ["ghost_list_id"] and unmapped == []


# --- link rendering ----------------------------------------------------------
def test_surface_link_uses_live_graph_values():
    s = {"list_key": "risk_list_id", "label": "Project Risks"}
    resolved = {"risk_list_id": ("Project Risks", "https://x/Lists/Project%20Risks")}
    assert am.surface_link(s, resolved) == "[Project Risks](https://x/Lists/Project%20Risks)"


def test_surface_link_falls_back_when_graph_absent():
    s = {"list_key": "risk_list_id", "label": "Project Risks"}
    link = am.surface_link(s, {})  # no live data
    assert link == f"[Project Risks]({am.SITE_BASE}/Lists/Project%20Risks)"


def test_md_escapes_pipes_and_newlines():
    assert am._md("a|b\nc") == "a\\|b c"
    assert am._md(None) == ""


# --- registry integrity ------------------------------------------------------
REQUIRED = {"list_key", "label", "phase", "columns", "process", "db_table",
            "bi_view", "model_table", "measures", "audit"}


def test_every_surface_has_all_fields():
    for s in am.SURFACES:
        assert REQUIRED <= set(s), f"{s.get('list_key')} missing {REQUIRED - set(s)}"


def test_no_duplicate_list_keys():
    keys = [s["list_key"] for s in am.SURFACES]
    assert len(keys) == len(set(keys))


def test_render_smoke():
    md = am.render(am.SURFACES, {}, "> header")
    assert "Admin & Operations Map" in md
    assert "Authoring surfaces" in md
    # every surface's DB table appears
    for s in am.SURFACES:
        assert s["db_table"].split()[0] in md
