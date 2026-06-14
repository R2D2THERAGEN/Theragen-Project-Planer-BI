"""Governance health digest - a read-only exceptions report over the bi views.

Surfaces the governance items that need human action so the framework drives
work, not just records it: documents overdue for review, documents missing an
Accountable, baselined versions with no sign-off attestation, change requests
stuck mid-workflow, and unsigned status reports.

Read-only (SELECTs only) - safe to run any time. Prints a digest to stdout;
schedule it (tools/run_governance_health.cmd) to log a daily snapshot, or pipe
it into an e-mail. Exit code is always 0 (it is a report, not a failure); the
digest itself shows what needs attention.

    python tools/governance_health.py
"""
import json
import os

import psycopg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Aging thresholds (days) before an in-flight item is flagged.
PENDING_CR_DAYS = 14      # a Pending decision sitting this long
APPROVED_UNVERIFIED_DAYS = 30  # Approved but implementation not verified
RECENT_REPORT_DAYS = 90   # only flag unsigned reports for recent periods (not
                          # the historical backlog nobody will retro-sign)
MAX_ROWS = 25             # cap rows shown per check so no backlog floods the digest

# Each check: (key, title, sql). Every SQL returns rows whose column names are
# the digest's table headers; an empty result means "all clear" for that check.
CHECKS = [
    ("docs_overdue", "Documents overdue for review",
     "SELECT doc_id, title, owner_name,"
     " to_char(next_review_due,'YYYY-MM-DD') AS next_review_due,"
     " (CURRENT_DATE - next_review_due) AS days_overdue"
     " FROM bi.document"
     " WHERE status <> 'RETIRED' AND next_review_due IS NOT NULL"
     "   AND next_review_due < CURRENT_DATE"
     " ORDER BY next_review_due"),
    ("docs_no_accountable", "Documents with no Accountable (RACI gap)",
     "SELECT d.doc_id, d.title, d.owner_name"
     " FROM bi.document d"
     " WHERE d.status <> 'RETIRED'"
     "   AND NOT EXISTS (SELECT 1 FROM bi.raci_assignment r"
     "      WHERE r.document_id = d.document_id AND r.role = 'A'"
     "        AND (r.valid_to IS NULL OR r.valid_to >= CURRENT_DATE))"
     " ORDER BY d.doc_id"),
    ("baseline_unsigned", "Baselined versions with no sign-off attestation",
     "SELECT v.doc_id, v.version, v.author_name,"
     " to_char(v.created_at,'YYYY-MM-DD') AS baselined"
     " FROM bi.document_version v"
     " WHERE v.status = 'BASELINE'"
     "   AND NOT EXISTS (SELECT 1 FROM bi.document_approval a"
     "      WHERE a.version_id = v.version_id)"
     " ORDER BY v.doc_id, v.version"),
    ("govcr_stuck", "Governance CRs approved but not verified",
     "SELECT cr_code, doc_id, status, decided_by_name,"
     " to_char(decided_at,'YYYY-MM-DD') AS decided,"
     " (CURRENT_DATE - decided_at) AS days_since"
     " FROM bi.change_request_gov"
     " WHERE decision = 'Approved' AND implementation_verified = FALSE"
     "   AND status NOT IN ('Verified','Closed','Rejected')"
     "   AND (decided_at IS NULL OR decided_at <= CURRENT_DATE - %s)"
     " ORDER BY decided_at",
     (APPROVED_UNVERIFIED_DAYS,)),
    ("govcr_pending", "Governance CRs pending a decision too long",
     "SELECT cr_code, doc_id, requested_by_name,"
     " to_char(requested_at,'YYYY-MM-DD') AS requested,"
     " (CURRENT_DATE - requested_at) AS days_pending"
     " FROM bi.change_request_gov"
     " WHERE decision = 'Pending'"
     "   AND requested_at <= CURRENT_DATE - %s"
     " ORDER BY requested_at",
     (PENDING_CR_DAYS,)),
    ("projcr_stuck", "Project CRs approved but not verified",
     "SELECT cr_code, project_code, status, decided_by_name,"
     " to_char(decided_at,'YYYY-MM-DD') AS decided"
     " FROM bi.change_request"
     " WHERE decision = 'Approved' AND implementation_verified = FALSE"
     "   AND status NOT IN ('Verified','Closed','Rejected')"
     " ORDER BY decided_at"),
    ("reports_unsigned", "Status reports for a recent closed period, unsigned",
     "SELECT project_code, report_number,"
     " to_char(period_end,'YYYY-MM-DD') AS period_end, submitted_by_name"
     " FROM bi.status_report"
     " WHERE is_signed_off = FALSE AND period_end < CURRENT_DATE"
     "   AND period_end >= CURRENT_DATE - %s"
     " ORDER BY period_end DESC",
     (RECENT_REPORT_DAYS,)),
]


def run_checks(conn):
    """Execute every check -> list of (title, headers, rows). I/O only."""
    sections = []
    for check in CHECKS:
        key, title, sql = check[0], check[1], check[2]
        params = check[3] if len(check) > 3 else None
        cur = conn.execute(sql, params) if params else conn.execute(sql)
        headers = [d.name for d in cur.description]
        rows = [tuple("" if v is None else str(v) for v in r) for r in cur.fetchall()]
        sections.append((title, headers, rows))
    return sections


def _table(headers, rows):
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    line = lambda cells: "  " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells))
    out = [line(headers), "  " + "-+-".join("-" * w for w in widths)]
    out += [line(r) for r in rows]
    return "\n".join(out)


def format_digest(sections, *, stamp=""):
    """Pure: render the sections to a text digest. Empty checks render as a
    one-line 'clear'; populated checks render a count + a table."""
    total = sum(len(rows) for _, _, rows in sections)
    head = "GOVERNANCE HEALTH DIGEST"
    if stamp:
        head += f"  -  {stamp}"
    lines = [head, "=" * len(head), "",
             f"{total} item(s) need attention across {len(sections)} checks.", ""]
    for title, headers, rows in sections:
        if not rows:
            lines.append(f"[ OK ] {title}: none")
            continue
        lines.append(f"[ {len(rows):>3} ] {title}")
        shown, overflow = rows[:MAX_ROWS], len(rows) - MAX_ROWS
        lines.append(_table(headers, shown))
        if overflow > 0:
            lines.append(f"  ... and {overflow} more")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    cfg = json.load(open(os.path.join(ROOT, "db", ".pg.local.json"), encoding="utf-8"))
    with psycopg.connect(host=cfg["server"], dbname=cfg["database"], user=cfg["user"],
                         password=cfg["password"], sslmode="require",
                         autocommit=True) as conn:
        stamp = conn.execute("SELECT to_char(now(),'YYYY-MM-DD HH24:MI')").fetchone()[0]
        sections = run_checks(conn)
    print(format_digest(sections, stamp=stamp))


if __name__ == "__main__":
    main()
