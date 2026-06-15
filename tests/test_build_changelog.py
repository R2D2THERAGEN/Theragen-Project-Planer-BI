"""Tests for the platform-change-log generator (tools/build_changelog.py).

Pure functions only (sort + render); the DB read is exercised live by the tool.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bc", ROOT / "tools" / "build_changelog.py")
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)


def _r(version, **kw):
    base = {"version": version, "category": "Documentation", "summary": "x",
            "status": "Deployed", "approved_by_name": None, "git_sha": None,
            "changed_at": "2026-06-14"}
    base.update(kw)
    return base


def test_version_sort_newest_first():
    rows = [_r("2.6"), _r("2.10"), _r("2.7"), _r("1.0")]
    assert [r["version"] for r in bc.sort_rows(rows)] == ["2.10", "2.7", "2.6", "1.0"]


def test_unparseable_version_sorts_last():
    rows = [_r("2.0"), _r(None), _r("draft")]
    assert bc.sort_rows(rows)[0]["version"] == "2.0"


def test_render_table_contains_rows_and_escapes_pipes():
    md = bc.render([_r("2.7", summary="Round 2 | dogfood", category="Documentation")], "> stamp")
    assert "Platform Change Log" in md
    assert "do not edit by hand" in md
    assert "| 2.7 |" in md
    assert "Round 2 \\| dogfood" in md  # pipe escaped for the table cell
