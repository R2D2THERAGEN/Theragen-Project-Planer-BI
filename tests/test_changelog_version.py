"""Drift guard for the change-control process (docs/change-control-process.md).

The root VERSION file is authoritative for the current platform version; the top
entry of CHANGELOG.md must match it. The SOP requires bumping both in the same
commit -- this test fails if they drift.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _version():
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _changelog_top_version():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^##\s*(\d+\.\d+)\b", text, re.MULTILINE)
    assert m, "no '## <MAJOR.MINOR>' version header found in CHANGELOG.md"
    return m.group(1)


def test_version_file_is_major_minor():
    v = _version()
    assert re.fullmatch(r"\d+\.\d+", v), f"VERSION must be MAJOR.MINOR, got {v!r}"


def test_version_matches_changelog_top():
    v, top = _version(), _changelog_top_version()
    assert v == top, (
        f"VERSION ({v}) != CHANGELOG top ({top}); bump both together "
        "per docs/change-control-process.md"
    )
