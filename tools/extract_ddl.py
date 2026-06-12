"""Reconstruct runnable PostgreSQL DDL from the THG-ENT-DBS-001 extracts.

The workbook's DDL sheets carry two export defects:
  1. String DEFAULTs lost their quotes (DEFAULT Not started).
  2. In the DM sheet, DEFAULT values were replaced by the column description
     (DEFAULT Active flag.).
Both are repaired from the authoritative *_Fields sheets (Default column).
Also reroutes FK targets that the PMBOK sheet wrongly schema-qualified as
pmbok.* when the table lives in doc_mgmt (person, intake_submission, document).

Output: db/01_dm.sql, db/02_pmbok.sql
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_source_extracts")
OUT = os.path.join(ROOT, "db")

FUNC_DEFAULTS = {"now()", "gen_random_uuid()", "CURRENT_TIMESTAMP"}


def load_tables(entities_tsv):
    names = set()
    with open(os.path.join(SRC, entities_tsv), encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) >= 2 and re.match(r"^[PD]\d\d$", row[0]):
                names.add(row[1])
    return names


def load_fields(entities_tsv, fields_tsv):
    """(table_name, column) -> default literal from the Fields sheet."""
    ent = {}
    with open(os.path.join(SRC, entities_tsv), encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) >= 2 and re.match(r"^[PD]\d\d$", row[0]):
                ent[row[0]] = row[1]
    defaults = {}
    with open(os.path.join(SRC, fields_tsv), encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) >= 6 and re.match(r"^[PD]\d\d$", row[0]):
                table = ent.get(row[0])
                if not table:
                    continue
                row = row + [""] * (11 - len(row))
                field, key, fkref, dflt = row[1], row[5].strip(), row[6].strip(), row[7].strip()
                # Some DM rows are shifted one cell left (Default sits in the
                # FK-reference column, description in Default). A real default
                # never ends with '.'; a real FK ref always contains '.'.
                def plausible(v):
                    return v and not v.endswith((".", "?")) and "?" not in v
                default = ""
                if plausible(dflt):
                    default = dflt
                elif key != "FK" and "." not in fkref and plausible(fkref):
                    default = fkref
                if default:
                    defaults[(table, field)] = default
    return defaults


def sql_literal(value, line):
    if value in FUNC_DEFAULTS:
        return value
    if value.upper() in ("TRUE", "FALSE"):
        return value.upper()
    if re.fullmatch(r"-?\d+(\.\d+)?", value):
        return value
    return "'" + value.replace("'", "''") + "'"


def rebuild(ddl_tsv, defaults, out_path, home_schema, dm_tables, pm_tables):
    with open(os.path.join(SRC, ddl_tsv), encoding="utf-8") as f:
        lines = f.read().splitlines()
    lines = lines[3:]  # banner

    out, table, qualified, fks = [], None, None, []
    for line in lines:
        m = re.match(r"CREATE TABLE (\w+)\.(\w+) \(", line)
        if m:
            table = m.group(2)
            qualified = f"{m.group(1)}.{m.group(2)}"
        cm = re.match(r"^(\s*)(\w+)\s+.*\bDEFAULT\b", line)
        if cm and table:
            col = cm.group(2)
            key = (table, col)
            # split off trailing comment
            body, sep, comment = line.partition("  --")
            default = defaults.get(key)
            if default is not None and "BOOLEAN" in body and default.upper() not in ("TRUE", "FALSE"):
                default = None
            # Detach trailing comma and constraint keywords so the DEFAULT
            # rewrite can't swallow them (e.g. "... PRIMARY KEY,").
            core = body.rstrip()
            comma = core.endswith(",")
            if comma:
                core = core[:-1].rstrip()
            suffix = ""
            changed = True
            while changed:
                changed = False
                for kw in (" PRIMARY KEY", " UNIQUE"):
                    if core.endswith(kw):
                        suffix = kw + suffix
                        core = core[: -len(kw)].rstrip()
                        changed = True
            if default is not None:
                core = re.sub(r"DEFAULT\s+.*$",
                              f"DEFAULT {sql_literal(default, line)}", core)
            else:
                # DDL claims a default the spec doesn't define - drop the clause
                core = re.sub(r"\s+DEFAULT\s+.*$", "", core)
            body = core + suffix + ("," if comma else "")
            line = body + (sep + comment if sep else "")
        # Both sheets qualify every FK target with their own schema, even when
        # the table lives across the bridge. Re-home each reference by where
        # the table is actually defined (DM-only -> doc_mgmt, PMBOK-only ->
        # pmbok; tables in both keep the home schema of the current file).
        def rehome(m):
            tbl = m.group(1)
            if tbl in dm_tables and tbl not in pm_tables:
                schema = "doc_mgmt"
            elif tbl in pm_tables and tbl not in dm_tables:
                schema = "pmbok"
            else:
                schema = home_schema
            return f"REFERENCES {schema}.{tbl}("
        line = re.sub(r"REFERENCES \w+\.(\w+)\(", rehome, line)
        # 'trigger' is reserved in PostgreSQL - quote the risk column.
        line = re.sub(r"^(\s*)trigger TEXT", r'\1"trigger" TEXT', line)
        # cr_code is C-NNN *per project* (like wbs_code); the sheet's global
        # UNIQUE is over-strict - replaced by a composite below.
        if table == "change_request" and re.match(r"\s*cr_code ", line):
            line = line.replace(" UNIQUE", "")
        # The workbook orders tables by entity id, producing forward FK
        # references (department -> person). Hoist every FK into ALTER TABLE
        # statements applied after both schemas exist.
        fk = re.match(r"\s*CONSTRAINT (\w+) FOREIGN KEY (.+?),?\s*$", line)
        if fk and qualified:
            fks.append(f"ALTER TABLE {qualified} ADD CONSTRAINT {fk.group(1)} "
                       f"FOREIGN KEY {fk.group(2)};")
            continue
        out.append(line)

    # The workbook export leaves dangling commas on the last column before
    # the closing ");" - strip them (comment-aware).
    for i, line in enumerate(out):
        if line.strip() == ");":
            j = i - 1
            while j >= 0 and (not out[j].strip() or out[j].lstrip().startswith("--")):
                j -= 1
            if j >= 0:
                body, sep, comment = out[j].partition("  --")
                if body.rstrip().endswith(","):
                    out[j] = body.rstrip()[:-1] + (sep + comment if sep else "")

    os.makedirs(OUT, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    n_def = sum(1 for ln in out if "DEFAULT" in ln)
    print(f"{os.path.relpath(out_path, ROOT)}: {len(out)} lines, "
          f"{n_def} DEFAULT clauses, {len(fks)} FKs hoisted")
    return fks


def main():
    dm_tables = load_tables("DM_Entities.tsv")
    pm_tables = load_tables("PMBOK_Entities.tsv")
    dm_defaults = load_fields("DM_Entities.tsv", "DM_Fields.tsv")
    pm_defaults = load_fields("PMBOK_Entities.tsv", "PMBOK_Fields.tsv")
    fks = rebuild("DM_DDL.tsv", dm_defaults, os.path.join(OUT, "01_dm.sql"),
                  "doc_mgmt", dm_tables, pm_tables)
    fks += rebuild("PMBOK_DDL.tsv", pm_defaults, os.path.join(OUT, "02_pmbok.sql"),
                   "pmbok", dm_tables, pm_tables)
    fks.append("ALTER TABLE pmbok.change_request ADD CONSTRAINT "
               "uq_change_request_project_cr UNIQUE (project_id, cr_code);")
    with open(os.path.join(OUT, "04_foreign_keys.sql"), "w", encoding="utf-8") as f:
        f.write("-- Foreign keys for both schemas, applied after all tables exist.\n"
                + "\n".join(fks) + "\n")
    print(f"db\\04_foreign_keys.sql: {len(fks)} constraints")


if __name__ == "__main__":
    main()
