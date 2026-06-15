"""Generate docs/platform-change-log.md from the pmbok.platform_change register.

The register (authored via the "Platform Changes" List, surfaced in
bi.platform_change) is the **source of truth for the platform change log**. This
generated doc complements the curated CHANGELOG.md release notes — see
docs/change-control-process.md. Read-only on the DB; never edited by hand.

Usage:  python tools/build_changelog.py
"""
import json
import re
import sys
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "docs" / "platform-change-log.md"
SELECT = ("SELECT version, category, summary, status, approved_by_name, git_sha, changed_at"
          " FROM bi.platform_change")
_COLS = ["version", "category", "summary", "status", "approved_by_name", "git_sha", "changed_at"]


# --- pure helpers ------------------------------------------------------------
def _vkey(v):
    """Sort key for a MAJOR.MINOR version string; unparseable sorts last."""
    m = re.match(r"^(\d+)\.(\d+)", str(v or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (-1, -1)


def sort_rows(rows):
    """Newest first: by version desc, then changed_at desc."""
    return sorted(rows, key=lambda r: (_vkey(r.get("version")), str(r.get("changed_at") or "")),
                  reverse=True)


def _md(s):
    if s is None:
        return ""
    return str(s).replace("|", "\\|").replace("\n", " ")


def render(rows, stamp):
    out = ["# Theragen Project Planner — Platform Change Log", ""]
    out.append("_Generated from the `pmbok.platform_change` register by "
               "`tools/build_changelog.py` — **do not edit by hand**. The register "
               "(authored via the Platform Changes List) is the source of truth for the "
               "platform change log; this complements the curated "
               "[CHANGELOG.md](../CHANGELOG.md) release notes (see the "
               "[change-control process](change-control-process.md))._")
    out.append("")
    out.append(stamp)
    out.append("")
    out.append("| Version | Date | Category | Status | Change | Approver | Commit |")
    out.append("|---|---|---|---|---|---|---|")
    for r in sort_rows(rows):
        out.append(f"| {_md(r.get('version'))} | {_md(r.get('changed_at'))} "
                   f"| {_md(r.get('category'))} | {_md(r.get('status'))} | {_md(r.get('summary'))} "
                   f"| {_md(r.get('approved_by_name'))} | {_md(r.get('git_sha'))} |")
    out.append("")
    return "\n".join(out)


# --- I/O ---------------------------------------------------------------------
def load_rows():
    cfg = json.load(open(REPO_ROOT / "db" / ".pg.local.json", encoding="utf-8"))
    with psycopg.connect(host=cfg["server"], dbname=cfg["database"], user=cfg["user"],
                         password=cfg["password"], sslmode="require", autocommit=True) as c:
        return [dict(zip(_COLS, row)) for row in c.execute(SELECT).fetchall()]


def main(argv):
    rows = load_rows()
    stamp = f"> {len(rows)} platform change(s) logged; latest version v{sort_rows(rows)[0]['version'] if rows else '—'}."
    OUT.write_text(render(rows, stamp) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({len(rows)} changes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
