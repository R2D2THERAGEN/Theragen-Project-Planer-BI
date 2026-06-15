"""Tests for the change-control reminder (tools/check_change_control.py)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cc", ROOT / "tools" / "check_change_control.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)


def test_model_change_without_changelog_triggers():
    # git quotes space-containing paths; the reminder strips the quotes.
    out = cc.changelog_reminder(
        ['"Theragen Project Planner.SemanticModel/definition/tables/Risk.tmdl"', "README.md"])
    assert any("Risk.tmdl" in p for p in out)


def test_changelog_present_suppresses_reminder():
    assert cc.changelog_reminder(["db/24_foo.sql", "CHANGELOG.md"]) == []


def test_unrelated_changes_no_reminder():
    assert cc.changelog_reminder(
        ["docs/glossary.md", "README.md", "tools/build_data_dictionary.py"]) == []


def test_migration_list_and_sync_trigger():
    assert cc.changelog_reminder(["db/24_x.sql"]) == ["db/24_x.sql"]
    assert cc.changelog_reminder(["tools/create_artifact_lists.py"]) == ["tools/create_artifact_lists.py"]
    assert cc.changelog_reminder(["tools/sync_artifacts.py"]) == ["tools/sync_artifacts.py"]
    assert cc.changelog_reminder(["tools/artifact_lib.py"]) == ["tools/artifact_lib.py"]
