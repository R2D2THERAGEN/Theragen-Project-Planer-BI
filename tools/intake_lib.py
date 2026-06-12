# tools/intake_lib.py
"""Pure logic for the M365 -> PostgreSQL intake sync. No I/O here."""
import re

ENVELOPES = [(25_000, "$0-25k"), (250_000, "$25-250k"), (1_000_000, "$250k-1M")]

TRIAGE_TO_STATUS = {
    "Submitted": "Proposed",
    "Approved": "Active",
    "Rejected": "Cancelled",
    "On Hold": "Paused",
}

REQUIRED = [
    ("Title", "Title"),
    ("RequestType", "Request Type"),
    ("Department", "Department"),
    ("BusinessProblem", "Business Problem"),
    ("DesiredOutcome", "Desired Outcome"),
    ("SponsorEmail", "Sponsor (person could not be resolved)"),
    ("ProjectManagerEmail", "Project Manager (person could not be resolved)"),
]


def derive_envelope(amount):
    if amount is None:
        return "Unknown"
    for limit, label in ENVELOPES:
        if amount < limit:
            return label
    return ">$1M"


def next_intake_id(existing, year):
    pat = re.compile(rf"INT-{year}-(\d{{4}})$")
    nums = [int(m.group(1)) for s in existing if (m := pat.match(s))]
    return f"INT-{year}-{(max(nums) + 1 if nums else 1):04d}"


def next_project_code(dept_code, existing):
    pat = re.compile(rf"THG-{re.escape(dept_code)}-(\d{{3}})$")
    nums = [int(m.group(1)) for s in existing if (m := pat.match(s))]
    return f"THG-{dept_code}-{(max(nums) + 1 if nums else 1):03d}"


def triage_to_status(triage):
    return TRIAGE_TO_STATUS.get(triage)


def validate_item(fields):
    errors = []
    for key, label in REQUIRED:
        if not (fields.get(key) or "").strip():
            errors.append(f"Missing: {label}")
    return errors
