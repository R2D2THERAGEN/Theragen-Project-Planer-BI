"""Idempotent one-time seed of the doc_mgmt lookup catalogs.

Populates doc_mgmt.document_type (8 controlled-document type codes) and
doc_mgmt.compliance_frame (7 regulatory/methodological frames) via
INSERT ... ON CONFLICT (code) DO NOTHING. Safe to re-run; NEVER drops anything
(this is NOT load_postgres.py). load_postgres.py imports DOC_TYPE_COLS/FRAME_COLS
+ doc_type_rows()/frame_rows() so a from-scratch rebuild seeds the same rows.

Connection from db/.pg.local.json (gitignored). uuid5-keyed ids (same NS as the
loader) make the ids stable across runs and between the two scripts.
"""
import json
import os
import uuid

import psycopg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def uid(kind, key):
    return str(uuid.uuid5(NS, f"thg/{kind}/{key}"))


# Controlled-document type catalog. lifecycle_phase is one of the doc lifecycle
# phases; default_review_cycle is one of the review cycles. These define the
# {TYPE} segment of a doc_id (THG-{DEPT}-{TYPE}-NNN).
DOCUMENT_TYPES = [
    {"code": "CHR", "name": "Project Charter", "lifecycle_phase": "Initiating",
     "default_review_cycle": "On Major Revision", "requires_approval": True},
    {"code": "SOP", "name": "Standard Operating Procedure", "lifecycle_phase": "Cross-Lifecycle",
     "default_review_cycle": "Annual", "requires_approval": True},
    {"code": "PLN", "name": "Plan", "lifecycle_phase": "Planning",
     "default_review_cycle": "On Major Revision", "requires_approval": True},
    {"code": "SCP", "name": "Scope Statement", "lifecycle_phase": "Planning",
     "default_review_cycle": "On Major Revision", "requires_approval": True},
    {"code": "RPT", "name": "Report", "lifecycle_phase": "Monitoring",
     "default_review_cycle": "On Major Revision", "requires_approval": False},
    {"code": "POL", "name": "Policy", "lifecycle_phase": "Governance",
     "default_review_cycle": "Annual", "requires_approval": True},
    {"code": "WI", "name": "Work Instruction", "lifecycle_phase": "Executing",
     "default_review_cycle": "Annual", "requires_approval": True},
    {"code": "FRM", "name": "Form", "lifecycle_phase": "Reference",
     "default_review_cycle": "On Major Revision", "requires_approval": False},
]

COMPLIANCE_FRAMES = [
    {"code": "21CFR11", "name": "FDA 21 CFR Part 11", "authority": "FDA",
     "applies_to": "Electronic records and electronic signatures in FDA-regulated work.",
     "reference_url": "https://www.ecfr.gov/current/title-21/part-11"},
    {"code": "HIPAA", "name": "Health Insurance Portability and Accountability Act",
     "authority": "HHS", "applies_to": "Protected health information (PHI) handling.",
     "reference_url": "https://www.hhs.gov/hipaa"},
    {"code": "PMBOK7", "name": "PMBOK Guide 7th Edition", "authority": "PMI",
     "applies_to": "Project management principles and performance domains.",
     "reference_url": "https://www.pmi.org"},
    {"code": "ISO13485", "name": "ISO 13485", "authority": "ISO",
     "applies_to": "Medical device quality management systems.",
     "reference_url": "https://www.iso.org/standard/59752.html"},
    {"code": "GxP", "name": "Good Practice Quality Guidelines", "authority": "Various",
     "applies_to": "Good manufacturing, clinical, and laboratory practice.",
     "reference_url": None},
    {"code": "SOC2", "name": "SOC 2", "authority": "AICPA",
     "applies_to": "Service organization security and availability controls.",
     "reference_url": "https://www.aicpa.org"},
    {"code": "ISO9001", "name": "ISO 9001", "authority": "ISO",
     "applies_to": "Quality management systems.",
     "reference_url": "https://www.iso.org/standard/62085.html"},
]

DOC_TYPE_COLS = ["document_type_id", "code", "name", "lifecycle_phase",
                 "default_review_cycle", "requires_approval"]
FRAME_COLS = ["frame_id", "code", "name", "authority", "applies_to", "reference_url"]


def doc_type_rows():
    return [{"document_type_id": uid("doctype", t["code"]), **t} for t in DOCUMENT_TYPES]


def frame_rows():
    return [{"frame_id": uid("frame", f["code"]), **f} for f in COMPLIANCE_FRAMES]


def _upsert(cur, table, cols, data):
    ph = ", ".join(["%s"] * len(cols))
    collist = ", ".join(cols)
    cur.executemany(
        f"INSERT INTO {table} ({collist}) VALUES ({ph}) ON CONFLICT (code) DO NOTHING",
        [[row[c] for c in cols] for row in data])


def main():
    cfg = json.load(open(os.path.join(ROOT, "db", ".pg.local.json")))
    with psycopg.connect(host=cfg["server"], dbname=cfg["database"], user=cfg["user"],
                         password=cfg["password"], sslmode="require") as conn:
        with conn.cursor() as cur:
            _upsert(cur, "doc_mgmt.document_type", DOC_TYPE_COLS, doc_type_rows())
            _upsert(cur, "doc_mgmt.compliance_frame", FRAME_COLS, frame_rows())
        conn.commit()
        dt = conn.execute("SELECT count(*) FROM doc_mgmt.document_type").fetchone()[0]
        cf = conn.execute("SELECT count(*) FROM doc_mgmt.compliance_frame").fetchone()[0]
        print(f"doc_mgmt.document_type rows: {dt}")
        print(f"doc_mgmt.compliance_frame rows: {cf}")


if __name__ == "__main__":
    main()
