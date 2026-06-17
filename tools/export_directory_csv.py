"""Export bi.org_directory to a clean CSV for grounding the Staff Directory agent.

A stopgap until the agent is re-grounded on the published Power BI **Directory**
model: this hands it the FULL directory with only the real fields (no empty
SharePoint "Title" column to misread), so it stops hallucinating blank names and
can see every person. The output is *data* -- gitignored, regenerate as needed.

Connection from db/.pg.local.json (psycopg imported lazily so tests stay light).

    python tools/export_directory_csv.py              # -> staff-directory-export.csv
    python tools/export_directory_csv.py --out X.csv
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = ["UPN", "DisplayName", "Email", "Department", "JobTitle", "Active"]


def directory_csv_rows(records):
    """Pure: bi.org_directory dict rows -> list-of-lists in HEADER order (header first)."""
    rows = [list(HEADER)]
    for r in records:
        rows.append([
            r.get("upn") or "",
            r.get("display_name") or "",
            r.get("email") or "",
            r.get("department") or "",
            r.get("job_title") or "",
            "Yes" if r.get("active") else "No",
        ])
    return rows


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "staff-directory-export.csv"))
    args = ap.parse_args(argv)
    import psycopg
    cfg = json.load(open(os.path.join(ROOT, "db", ".pg.local.json"), encoding="utf-8"))
    with psycopg.connect(host=cfg["server"], dbname=cfg["database"], user=cfg["user"],
                         password=cfg["password"], sslmode="require", autocommit=True,
                         connect_timeout=20) as conn:
        cur = conn.execute(
            "SELECT upn, display_name, email, department, job_title, active"
            " FROM bi.org_directory ORDER BY display_name")
        cols = [c.name for c in cur.description]
        records = [dict(zip(cols, row)) for row in cur.fetchall()]
    rows = directory_csv_rows(records)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"wrote {args.out} -- {len(rows) - 1} people")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
