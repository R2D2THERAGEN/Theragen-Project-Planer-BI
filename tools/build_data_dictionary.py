"""Generate docs/data-dictionary.md from the semantic-model TMDL.

Read-only: parses the model's .tmdl files and emits a Markdown data dictionary
(model index, per-table columns + measures, relationships) with a provenance
header derived from the model's own git state. Never writes TMDL.

Usage:
    python tools/build_data_dictionary.py            # regenerate docs/data-dictionary.md
    python tools/build_data_dictionary.py --audit    # list objects missing a /// description; exit 1 if any

See docs/change-control-process.md (the provenance-stamp + --audit gate are part
of the change-control process) and docs/glossary.md (business definitions).
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "Theragen Project Planner.SemanticModel"
MODEL_DIR = REPO_ROOT / MODEL_NAME
DEF_DIR = MODEL_DIR / "definition"
TABLES_DIR = DEF_DIR / "tables"
ROLES_DIR = DEF_DIR / "roles"
REL_FILE = DEF_DIR / "relationships.tmdl"
OUT_FILE = REPO_ROOT / "docs" / "data-dictionary.md"

# --- regexes -----------------------------------------------------------------
_DESC = re.compile(r"^\s*///\s?(.*)$")
_TABLE = re.compile(r"^table\s+(.+?)\s*$")
_ROLE = re.compile(r"^role\s+(.+?)\s*$")
_COLUMN = re.compile(r"^\s+column\s+(.+?)\s*$")
_MEASURE = re.compile(r"^\s+measure\s+('[^']*'|[^=\s]+)\s*=\s*(.*)$")
_PARTITION = re.compile(r"^\s+partition\b")
_PROP = re.compile(r"^\s+([A-Za-z]+):\s*(.*)$")
_FLAG = re.compile(r"^\s+(isHidden)\s*$")
_ITEM = re.compile(r'Item\s*=\s*"([^"]+)"')
_FROM = re.compile(r"^\s+fromColumn:\s*(.+)$")
_TO = re.compile(r"^\s+toColumn:\s*(.+)$")
_XFILTER = re.compile(r"^\s+crossFilteringBehavior:\s*(.+)$")
_INACTIVE = re.compile(r"^\s+isActive:\s*false\b")
_MODELPERM = re.compile(r"^\s+modelPermission:\s*(.+)$")


def _strip_q(s):
    s = s.strip()
    return s[1:-1] if len(s) >= 2 and s[0] == "'" and s[-1] == "'" else s


def _split_ref(ref):
    """'Table'.'Column' / Table.'Column' / Table.Column -> (table, column)."""
    ref = ref.strip()
    if ref.startswith("'"):
        end = ref.index("'", 1)
        table = ref[1:end]
        rest = ref[end + 1:]
        col = rest[1:] if rest.startswith(".") else rest
    else:
        dot = ref.index(".")
        table, col = ref[:dot], ref[dot + 1:]
    return table.strip(), _strip_q(col)


# --- parsers (pure) ----------------------------------------------------------
def parse_table(text):
    """Parse one table .tmdl -> {name, description, source, columns[], measures[]}."""
    tbl = {"name": None, "description": None, "source": None, "columns": [], "measures": []}
    m = _ITEM.search(text)
    if m:
        tbl["source"] = m.group(1)
    pending, current = [], None
    for line in text.splitlines():
        if not line.strip():
            pending = []
            continue
        d = _DESC.match(line)
        if d:
            pending.append(d.group(1).rstrip())
            continue
        mt = _TABLE.match(line)
        if mt and tbl["name"] is None:
            tbl["name"] = _strip_q(mt.group(1))
            tbl["description"] = " ".join(pending).strip() or None
            pending, current = [], None
            continue
        mc = _COLUMN.match(line)
        if mc:
            current = {"name": _strip_q(mc.group(1)), "data_type": None, "hidden": False,
                       "format": None, "description": " ".join(pending).strip() or None}
            tbl["columns"].append(current)
            pending = []
            continue
        mm = _MEASURE.match(line)
        if mm:
            current = {"name": _strip_q(mm.group(1)), "expression": mm.group(2).strip(),
                       "format": None, "folder": None, "description": " ".join(pending).strip() or None}
            tbl["measures"].append(current)
            pending = []
            continue
        if _PARTITION.match(line):
            current, pending = None, []
            continue
        if _FLAG.match(line):
            if current is not None:
                current["hidden"] = True
            continue
        p = _PROP.match(line)
        if p and current is not None:
            k, v = p.group(1), p.group(2).strip()
            if k == "dataType":
                current["data_type"] = v
            elif k == "formatString":
                current["format"] = v
            elif k == "displayFolder":
                current["folder"] = v
    return tbl


def parse_relationships(text):
    """Parse relationships.tmdl -> [{from_table, from_column, to_table, to_column, cross_filter, active}]."""
    rels, cur = [], None
    for line in text.splitlines():
        if re.match(r"^relationship\s+", line):
            cur = {"from_table": None, "from_column": None, "to_table": None,
                   "to_column": None, "cross_filter": "single", "active": True}
            rels.append(cur)
            continue
        if cur is None:
            continue
        mf = _FROM.match(line)
        if mf:
            cur["from_table"], cur["from_column"] = _split_ref(mf.group(1))
            continue
        mto = _TO.match(line)
        if mto:
            cur["to_table"], cur["to_column"] = _split_ref(mto.group(1))
            continue
        mx = _XFILTER.match(line)
        if mx:
            cur["cross_filter"] = mx.group(1).strip()
            continue
        if _INACTIVE.match(line):
            cur["active"] = False
    return rels


def parse_role(text):
    """Parse one role .tmdl -> {name, description, permission}."""
    r = {"name": None, "description": None, "permission": None}
    pending = []
    for line in text.splitlines():
        if not line.strip():
            pending = []
            continue
        d = _DESC.match(line)
        if d:
            pending.append(d.group(1).rstrip())
            continue
        mr = _ROLE.match(line)
        if mr and r["name"] is None:
            r["name"] = _strip_q(mr.group(1))
            r["description"] = " ".join(pending).strip() or None
            pending = []
            continue
        mp = _MODELPERM.match(line)
        if mp:
            r["permission"] = mp.group(1).strip()
    return r


def audit(tables, roles):
    """List objects with no /// description (tables, columns, measures, roles)."""
    missing = []
    for t in tables:
        if not t["description"]:
            missing.append(f"table '{t['name']}'")
        for c in t["columns"]:
            if not c["description"]:
                missing.append(f"'{t['name']}'[{c['name']}]")
        for m in t["measures"]:
            if not m["description"]:
                missing.append(f"[{m['name']}]")
    for r in roles:
        if not r["description"]:
            missing.append(f"role '{r['name']}'")
    return missing


def provenance_header(sha, date, version, counts):
    return (f"> Generated from model `{sha}` ({date}) · platform **v{version}**  \n"
            f"> {counts['tables']} tables · {counts['columns']} columns · {counts['measures']} measures "
            f"· {counts['relationships']} relationships · {counts['roles']} roles")


# --- rendering ---------------------------------------------------------------
def _md(s):
    """Escape a value for a Markdown table cell."""
    if s is None:
        return ""
    return str(s).replace("|", "\\|").replace("\n", " ")


def _anchor(name):
    return re.sub(r"[^a-z0-9_]+", "-", name.lower()).strip("-")


def render(tables, relationships, roles, header):
    tables = sorted(tables, key=lambda t: t["name"].lower())
    out = ["# Theragen Project Planner — Data Dictionary", ""]
    out.append("_Generated from the semantic-model TMDL by `tools/build_data_dictionary.py` — "
               "**do not edit by hand**; regenerate after model changes "
               "(see [change-control process](change-control-process.md)). "
               "Business definitions live in the [glossary](glossary.md)._")
    out.append("")
    out.append(header)
    out.append("")
    # model index
    out.append("## Model index")
    out.append("")
    out.append("| Table | Source | Cols | Measures | Description |")
    out.append("|---|---|---|---|---|")
    for t in tables:
        src = f"`bi.{t['source']}`" if t["source"] else "—"
        out.append(f"| [{t['name']}](#{_anchor(t['name'])}) | {src} | {len(t['columns'])} "
                   f"| {len(t['measures'])} | {_md(t['description'])} |")
    out.append("")
    if roles:
        out.append("**Roles (RLS):** " + " · ".join(
            f"`{r['name']}` ({r['permission']})" + (f" — {_md(r['description'])}" if r['description'] else "")
            for r in roles))
        out.append("")
    # per-table detail
    for t in tables:
        out.append(f'<a id="{_anchor(t["name"])}"></a>')
        out.append(f"## {t['name']}")
        out.append("")
        if t["description"]:
            out.append(_md(t["description"]))
            out.append("")
        if t["source"]:
            out.append(f"**Source:** `bi.{t['source']}`")
            out.append("")
        if t["columns"]:
            out.append("**Columns**")
            out.append("")
            out.append("| Column | Type | Hidden | Format | Description |")
            out.append("|---|---|---|---|---|")
            for c in t["columns"]:
                out.append(f"| {_md(c['name'])} | {_md(c['data_type'])} | {'yes' if c['hidden'] else ''} "
                           f"| {_md(c['format'])} | {_md(c['description'])} |")
            out.append("")
        if t["measures"]:
            out.append("**Measures**")
            out.append("")
            out.append("| Measure | Format | Folder | Description | DAX |")
            out.append("|---|---|---|---|---|")
            for m in sorted(t["measures"], key=lambda x: (x["folder"] or "", x["name"])):
                out.append(f"| {_md(m['name'])} | {_md(m['format'])} | {_md(m['folder'])} "
                           f"| {_md(m['description'])} | `{_md(m['expression'])}` |")
            out.append("")
    # relationships
    out.append("## Relationships")
    out.append("")
    out.append("| From | To | Cross-filter | Active |")
    out.append("|---|---|---|---|")
    for r in sorted(relationships, key=lambda x: (x["from_table"] or "", x["from_column"] or "")):
        out.append(f"| `{_md(r['from_table'])}`[{_md(r['from_column'])}] "
                   f"| `{_md(r['to_table'])}`[{_md(r['to_column'])}] | {_md(r['cross_filter'])} "
                   f"| {'yes' if r['active'] else 'no'} |")
    out.append("")
    return "\n".join(out)


# --- I/O ---------------------------------------------------------------------
def load_model():
    tables = [parse_table(p.read_text(encoding="utf-8")) for p in sorted(TABLES_DIR.glob("*.tmdl"))]
    relationships = parse_relationships(REL_FILE.read_text(encoding="utf-8")) if REL_FILE.exists() else []
    roles = ([parse_role(p.read_text(encoding="utf-8")) for p in sorted(ROLES_DIR.glob("*.tmdl"))]
             if ROLES_DIR.exists() else [])
    return {"tables": tables, "relationships": relationships, "roles": roles}


def git_model_stamp():
    """(short_sha, date) of the last commit touching the model dir; ('unknown', 'unknown') on failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "-1", "--format=%h\t%cs", "--", MODEL_NAME],
            capture_output=True, text=True, timeout=10)
        line = out.stdout.strip()
        if "\t" in line:
            sha, date = line.split("\t", 1)
            return sha.strip(), date.strip()
    except Exception:
        pass
    return "unknown", "unknown"


def read_version():
    try:
        return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def _counts(model):
    return {
        "tables": len(model["tables"]),
        "columns": sum(len(t["columns"]) for t in model["tables"]),
        "measures": sum(len(t["measures"]) for t in model["tables"]),
        "relationships": len(model["relationships"]),
        "roles": len(model["roles"]),
    }


def main(argv):
    model = load_model()
    if "--audit" in argv:
        missing = audit(model["tables"], model["roles"])
        for x in missing:
            print(x)
        print(f"\n{len(missing)} object(s) missing a /// description.")
        return 1 if missing else 0
    sha, date = git_model_stamp()
    header = provenance_header(sha, date, read_version(), _counts(model))
    md = render(model["tables"], model["relationships"], model["roles"], header)
    OUT_FILE.write_text(md + "\n", encoding="utf-8")
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)} — {_counts(model)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
