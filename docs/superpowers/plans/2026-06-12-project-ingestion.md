# Project Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** New Theragen projects enter PostgreSQL from a Microsoft Form → SharePoint List pipeline via a once-daily sync, appearing in both Power BI reports as Proposed and advancing with PMO triage.

**Architecture:** A Microsoft Form feeds a SharePoint List (built programmatically via Graph) through a 3-step Power Automate flow. `tools/sync_intake.py` runs daily at 5:30 AM on Allen's PC: it reads un-synced/changed List items with a delegated Graph token (MSAL device-code, cached), validates them with pure functions in `tools/intake_lib.py`, writes intake + Proposed project + charter to PostgreSQL in per-item transactions, and writes assigned IDs or errors back onto the List row. PostgreSQL stays the system of record; the List is the triage surface.

**Tech Stack:** Python 3.14, `msal` + `requests` (Graph), `psycopg[binary]` (PostgreSQL), `pytest` (tests), Windows Task Scheduler. Spec: `docs/superpowers/specs/2026-06-12-project-ingestion-design.md`.

**File structure:**

| File | Responsibility |
|---|---|
| `db/05_intake_external_ref.sql` | Migration: `external_ref` column for idempotency |
| `tools/load_postgres.py` (modify) | `--reseed` + type-db-name guard; run migration 05 |
| `tools/graph_client.py` | Graph auth (MSAL device code, cached) + GET/POST/PATCH helpers |
| `tools/intake_lib.py` | Pure logic: sequences, envelope, triage map, validation, row builders |
| `tools/create_intake_list.py` | One-time: create the "Project Intake" List with typed columns |
| `tools/sync_intake.py` | Daily sync: read List → validate → write PG → write back |
| `tests/test_intake_lib.py` | Unit tests for all pure logic |
| `db/.m365.local.json` (gitignored) | site id, list id, token cache path |
| `docs/intake-setup.md` | Form field spec, Flow recipe, scheduler setup |

Config note: connection values come from the existing `db/.pg.local.json`. All secrets/caches stay gitignored.

---

### Task 1: Migration + seeder guard

**Files:**
- Create: `db/05_intake_external_ref.sql`
- Modify: `tools/load_postgres.py` (top of `main()`, and the DDL file list)
- Modify: `.gitignore`

- [ ] **Step 1: Write the migration**

```sql
-- db/05_intake_external_ref.sql
-- Idempotency anchor for M365-ingested intakes: the SharePoint List item id.
ALTER TABLE doc_mgmt.intake_submission
    ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
```

- [ ] **Step 2: Add the migration to the loader's DDL list**

In `tools/load_postgres.py` find:

```python
    for f in ("01_dm.sql", "02_pmbok.sql", "03_bi_views.sql", "04_foreign_keys.sql"):
```

Replace with:

```python
    for f in ("01_dm.sql", "02_pmbok.sql", "03_bi_views.sql", "04_foreign_keys.sql",
              "05_intake_external_ref.sql"):
```

- [ ] **Step 3: Add the destructive-run guard**

In `tools/load_postgres.py`, at the very top of `main()` (before `conn = psycopg.connect(...)`), insert:

```python
    # This loader DROPS and recreates all three schemas. Once real intakes
    # exist, an accidental run is data loss - require explicit intent.
    if "--reseed" not in sys.argv:
        sys.exit("Refusing to run: this is a destructive reseed. "
                 "Pass --reseed and confirm interactively.")
    typed = input(f"Type the database name ({CFG['database']}) to confirm wipe: ")
    if typed.strip() != CFG["database"]:
        sys.exit("Confirmation mismatch - aborting.")
```

- [ ] **Step 4: Apply the migration to the live database (without reseeding)**

```bash
cd "C:\Users\Allen\OneDrive - Neurotech NA\Documents\GitHub\Theragen-Project-Planer-BI"
python - <<'EOF'
import json, psycopg
cfg = json.load(open("db/.pg.local.json"))
c = psycopg.connect(host=cfg["server"], dbname=cfg["database"], user=cfg["user"],
                    password=cfg["password"], sslmode="require")
c.execute(open("db/05_intake_external_ref.sql", encoding="utf-8").read())
c.commit()
cur = c.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='doc_mgmt' AND table_name='intake_submission' "
                "AND column_name='external_ref'")
print("external_ref present:", cur.fetchone() is not None)
c.close()
EOF
```

Expected output: `external_ref present: True`

- [ ] **Step 5: Verify the guard refuses without --reseed**

Run: `python tools/load_postgres.py`
Expected: exits with `Refusing to run: this is a destructive reseed...` and a non-zero code. Do NOT complete a reseed run.

- [ ] **Step 6: Add gitignore entries**

Append to `.gitignore`:

```
db/.m365.local.json
db/.graph_token_cache.json
```

- [ ] **Step 7: Commit**

```bash
git add db/05_intake_external_ref.sql tools/load_postgres.py .gitignore
git commit -m "Add intake external_ref migration and destructive-reseed guard"
```

---

### Task 2: Pure intake logic with tests

**Files:**
- Create: `tools/intake_lib.py`
- Test: `tests/test_intake_lib.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_intake_lib.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import intake_lib as il


def test_derive_envelope_buckets():
    assert il.derive_envelope(None) == "Unknown"
    assert il.derive_envelope(10_000) == "$0-25k"
    assert il.derive_envelope(25_000) == "$25-250k"
    assert il.derive_envelope(249_999) == "$25-250k"
    assert il.derive_envelope(600_000) == "$250k-1M"
    assert il.derive_envelope(2_000_000) == ">$1M"


def test_next_intake_id_first_of_year():
    assert il.next_intake_id(["INT-2025-0117"], 2026) == "INT-2026-0001"


def test_next_intake_id_increments_within_year():
    existing = ["INT-2026-0042", "INT-2026-0063", "INT-2025-0117"]
    assert il.next_intake_id(existing, 2026) == "INT-2026-0064"


def test_next_project_code_per_department():
    existing = ["THG-CLN-014", "THG-RND-007", "THG-CLN-002"]
    assert il.next_project_code("CLN", existing) == "THG-CLN-015"
    assert il.next_project_code("OPS", existing) == "THG-OPS-001"


def test_triage_to_status_mapping():
    assert il.triage_to_status("Submitted") == "Proposed"
    assert il.triage_to_status("Approved") == "Active"
    assert il.triage_to_status("Rejected") == "Cancelled"
    assert il.triage_to_status("On Hold") == "Paused"
    assert il.triage_to_status("Garbage") is None


def test_validate_item_passes_complete():
    fields = {
        "Title": "New PHI dashboard", "RequestType": "Project / Initiative",
        "Department": "IT / Data / Security",
        "BusinessProblem": "x", "DesiredOutcome": "y",
        "SponsorEmail": "n.hassan@theragen.com",
        "ProjectManagerEmail": "s.delgado@theragen.com",
    }
    assert il.validate_item(fields) == []


def test_validate_item_flags_missing_people_and_title():
    errs = il.validate_item({"RequestType": "Other", "Department": "HR / People",
                             "BusinessProblem": "x", "DesiredOutcome": "y"})
    joined = " | ".join(errs)
    assert "Title" in joined
    assert "Sponsor" in joined
    assert "Project Manager" in joined
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_intake_lib.py -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'intake_lib'`

- [ ] **Step 3: Implement intake_lib**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_intake_lib.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add tools/intake_lib.py tests/test_intake_lib.py
git commit -m "Add pure intake logic: sequences, envelope, triage map, validation"
```

---

### Task 3: Graph client (device-code auth + helpers)

**Files:**
- Create: `tools/graph_client.py`

No unit tests (thin I/O wrapper); verified live in Step 3.

- [ ] **Step 1: Install msal**

Run: `pip install -q msal requests`
Expected: silent success.

- [ ] **Step 2: Implement the client**

```python
# tools/graph_client.py
"""Delegated Microsoft Graph access for the intake sync.

Auth: MSAL device-code flow with the public Microsoft Graph CLI client id,
token cache persisted next to the DB credentials (both gitignored). First run
prints a device-code prompt once; subsequent runs are silent.
"""
import atexit
import json
import os

import msal
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "db", ".graph_token_cache.json")
CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph CLI (public)
AUTHORITY = "https://login.microsoftonline.com/organizations"
SCOPES = ["Sites.ReadWrite.All", "User.Read"]
BASE = "https://graph.microsoft.com/v1.0"


def get_token():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE):
        cache.deserialize(open(CACHE, encoding="utf-8").read())
    atexit.register(lambda: open(CACHE, "w", encoding="utf-8").write(cache.serialize())
                    if cache.has_state_changed else None)
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY,
                                       token_cache=cache)
    accounts = app.get_accounts()
    result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        print(flow["message"])  # user completes sign-in once
        result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise SystemExit(f"Graph auth failed: {result.get('error_description')}")
    return result["access_token"]


class Graph:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {get_token()}"

    def get(self, path, **params):
        r = self.s.get(f"{BASE}{path}", params=params or None, timeout=30)
        r.raise_for_status()
        return r.json()

    def post(self, path, body):
        r = self.s.post(f"{BASE}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def patch(self, path, body):
        r = self.s.patch(f"{BASE}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json() if r.text else {}
```

- [ ] **Step 3: Live verification**

```bash
python - <<'EOF'
import sys; sys.path.insert(0, "tools")
from graph_client import Graph
g = Graph()
me = g.get("/me")
site = g.get("/sites/root")
print("signed in as:", me.get("userPrincipalName"))
print("root site:", site.get("displayName"), site.get("id"))
EOF
```

Expected: a one-time device-code prompt, then the signed-in UPN and the Theragen root SharePoint site name + id. **If `Sites.ReadWrite.All` is refused by tenant policy**, stop and surface the error — fallback is an admin-consented app registration (out of v1 scope, requires Allen's tenant admin).

- [ ] **Step 4: Commit**

```bash
git add tools/graph_client.py
git commit -m "Add delegated Graph client with cached device-code auth"
```

---

### Task 4: Create the Project Intake List

**Files:**
- Create: `tools/create_intake_list.py`
- Create (runtime, gitignored): `db/.m365.local.json`

- [ ] **Step 1: Implement the creator**

```python
# tools/create_intake_list.py
"""One-time: create the 'Project Intake' SharePoint List on the root site with
typed columns, and persist site/list ids to db/.m365.local.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graph_client import Graph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "db", ".m365.local.json")
LIST_NAME = "Project Intake"

DEPARTMENTS = ["Clinical / Medical Affairs", "Regulatory / Quality",
               "R&D / Engineering", "Operations / PMO", "Finance / Procurement",
               "Commercial / Marketing", "IT / Data / Security", "HR / People"]
REQUEST_TYPES = ["Project / Initiative", "Clinical or study request",
                 "Cross-dept work request", "System change",
                 "Vendor / procurement", "Other"]
EFFORTS = ["Small (<4 wk)", "Medium (1-3 mo)", "Large (3-12 mo)", "Program (>12 mo)"]
TRIAGE = ["Submitted", "Approved", "Rejected", "On Hold"]
SYNC = ["Pending", "Synced", "Error"]


def choice(name, choices, default=None):
    col = {"name": name, "choice": {"allowTextEntry": False, "choices": choices,
                                    "displayAs": "dropDownMenu"}}
    if default:
        col["defaultValue"] = {"value": default}
    return col


COLUMNS = [
    choice("RequestType", REQUEST_TYPES),
    choice("Department", DEPARTMENTS),
    {"name": "BusinessProblem", "text": {"allowMultipleLines": True}},
    {"name": "DesiredOutcome", "text": {"allowMultipleLines": True}},
    {"name": "Sponsor", "personOrGroup": {"allowMultipleSelection": False}},
    {"name": "ProjectManager", "personOrGroup": {"allowMultipleSelection": False}},
    {"name": "PlannedStart", "dateTime": {"format": "dateOnly"}},
    {"name": "PlannedFinish", "dateTime": {"format": "dateOnly"}},
    {"name": "EstimatedBudget", "number": {"decimalPlaces": "two"}},
    choice("EffortBucket", EFFORTS),
    {"name": "PHIFlag", "boolean": {}},
    {"name": "CFR11Flag", "boolean": {}},
    {"name": "ClinicalFlag", "boolean": {}},
    {"name": "VendorFlag", "boolean": {}},
    {"name": "DataSharingFlag", "boolean": {}},
    {"name": "StrategicObjective", "text": {}},
    choice("TriageStatus", TRIAGE, default="Submitted"),
    {"name": "IntakeID", "text": {}},
    {"name": "ProjectCode", "text": {}},
    choice("SyncStatus", SYNC, default="Pending"),
    {"name": "SyncMessage", "text": {"allowMultipleLines": True}},
]


def main():
    g = Graph()
    site = g.get("/sites/root")
    site_id = site["id"]
    existing = g.get(f"/sites/{site_id}/lists", **{"$filter": f"displayName eq '{LIST_NAME}'"})
    if existing.get("value"):
        lst = existing["value"][0]
        print(f"List already exists: {lst['id']}")
    else:
        lst = g.post(f"/sites/{site_id}/lists", {
            "displayName": LIST_NAME,
            "description": "Theragen project intake (SOP-002). Synced to PostgreSQL daily.",
            "columns": COLUMNS,
            "list": {"template": "genericList"},
        })
        print(f"List created: {lst['id']}")
    json.dump({"site_id": site_id, "list_id": lst["id"], "list_name": LIST_NAME},
              open(CFG_PATH, "w", encoding="utf-8"), indent=2)
    print(f"config written: {CFG_PATH}")
    cols = g.get(f"/sites/{site_id}/lists/{lst['id']}/columns")
    names = {c["name"] for c in cols["value"]}
    missing = [c["name"] for c in COLUMNS if c["name"] not in names]
    print("column check:", "OK all present" if not missing else f"MISSING {missing}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `python tools/create_intake_list.py`
Expected:
```
List created: <guid>
config written: ...db\.m365.local.json
column check: OK all present
```

- [ ] **Step 3: Eyeball the List in the browser**

Open the root SharePoint site → Site contents → **Project Intake**. Confirm the columns render, TriageStatus defaults to Submitted, Sponsor/ProjectManager are people pickers.

- [ ] **Step 4: Commit**

```bash
git add tools/create_intake_list.py
git commit -m "Add one-time creator for the Project Intake SharePoint List"
```

---

### Task 5: The sync — read, validate, dry-run

**Files:**
- Create: `tools/sync_intake.py`

- [ ] **Step 1: Implement read + transform + dry-run skeleton**

```python
# tools/sync_intake.py
"""Daily M365 -> PostgreSQL intake sync (spec: 2026-06-12-project-ingestion).

Reads Project Intake List items, creates intake + Proposed project + charter
rows for new submissions, applies triage status transitions for existing ones,
and writes results back onto the List. Idempotent via
intake_submission.external_ref = List item id. --dry-run prints intent only.
"""
import argparse
import datetime
import json
import os
import sys
import uuid

import psycopg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intake_lib as il
from graph_client import Graph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PG = json.load(open(os.path.join(ROOT, "db", ".pg.local.json")))
M365 = json.load(open(os.path.join(ROOT, "db", ".m365.local.json")))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

FIELDS = ("Title,RequestType,Department,BusinessProblem,DesiredOutcome,"
          "Sponsor,ProjectManager,PlannedStart,PlannedFinish,EstimatedBudget,"
          "EffortBucket,PHIFlag,CFR11Flag,ClinicalFlag,VendorFlag,"
          "DataSharingFlag,StrategicObjective,TriageStatus,IntakeID,"
          "ProjectCode,SyncStatus,SyncMessage")


def person_email(field_value):
    """Graph person fields arrive as {LookupId, LookupValue, Email}."""
    if isinstance(field_value, dict):
        return (field_value.get("Email") or "").lower()
    return ""


def fetch_items(g):
    site, lst = M365["site_id"], M365["list_id"]
    url = f"/sites/{site}/lists/{lst}/items"
    out, params = [], {"expand": f"fields($select={FIELDS})", "$top": "200"}
    while url:
        page = g.get(url, **params)
        out += page.get("value", [])
        url = page.get("@odata.nextLink", "")
        if url:
            url = url.replace("https://graph.microsoft.com/v1.0", "")
            params = {}
    return out


def normalize(item):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "RequestType": f.get("RequestType") or "",
        "Department": f.get("Department") or "",
        "BusinessProblem": f.get("BusinessProblem") or "",
        "DesiredOutcome": f.get("DesiredOutcome") or "",
        "SponsorEmail": person_email(f.get("Sponsor")),
        "ProjectManagerEmail": person_email(f.get("ProjectManager")),
        "PlannedStart": (f.get("PlannedStart") or "")[:10] or None,
        "PlannedFinish": (f.get("PlannedFinish") or "")[:10] or None,
        "EstimatedBudget": f.get("EstimatedBudget"),
        "EffortBucket": f.get("EffortBucket") or "Large (3-12 mo)",
        "Flags": {k: bool(f.get(k)) for k in
                  ("PHIFlag", "CFR11Flag", "ClinicalFlag", "VendorFlag",
                   "DataSharingFlag")},
        "StrategicObjective": f.get("StrategicObjective") or None,
        "TriageStatus": f.get("TriageStatus") or "Submitted",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = Graph()
    conn = psycopg.connect(host=PG["server"], dbname=PG["database"],
                           user=PG["user"], password=PG["password"],
                           sslmode="require")
    items = [normalize(i) for i in fetch_items(g)]
    print(f"{len(items)} list item(s) fetched")

    synced = dict(conn.execute(
        "SELECT external_ref, intake_id FROM doc_mgmt.intake_submission "
        "WHERE external_ref IS NOT NULL").fetchall())

    results = []
    for it in items:
        if it["item_id"] not in synced:
            results.append(process_new(conn, g, it, args.dry_run))
        else:
            results.append(process_triage(conn, g, it, args.dry_run))
    conn.close()
    for r in results:
        print(" ", r)
    bad = [r for r in results if r.startswith("ERROR")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
```

(`process_new` / `process_triage` arrive in Task 6 — for this task add stubs so the dry run executes:)

```python
def process_new(conn, g, it, dry):
    errs = il.validate_item(it)
    if errs:
        return f"ERROR item {it['item_id']}: " + "; ".join(errs)
    return f"DRY new item {it['item_id']}: would create intake+project ({it['Title']})"


def process_triage(conn, g, it, dry):
    return f"DRY triage item {it['item_id']}: status {it['TriageStatus']}"
```

- [ ] **Step 2: Dry-run against the (empty) List**

Run: `python tools/sync_intake.py --dry-run`
Expected: `0 list item(s) fetched`, exit 0.

- [ ] **Step 3: Create one test item directly in the List UI**

In the browser: Project Intake → New → fill Title `TEST sync probe`, Request Type, Department `IT / Data / Security`, problem/outcome text, pick yourself as Sponsor and ProjectManager. Save.

- [ ] **Step 4: Dry-run shows the item, validated**

Run: `python tools/sync_intake.py --dry-run`
Expected: `1 list item(s) fetched` and `DRY new item ...: would create intake+project (TEST sync probe)` — no ERROR (people resolved to emails).

- [ ] **Step 5: Commit**

```bash
git add tools/sync_intake.py
git commit -m "Add intake sync: Graph read, normalization, validation, dry-run"
```

---

### Task 6: The sync — write path, write-back, triage

**Files:**
- Modify: `tools/sync_intake.py` (replace the two stubs)

- [ ] **Step 1: Replace the stubs with the real write path**

```python
def writeback(g, item_id, fields):
    g.patch(f"/sites/{M365['site_id']}/lists/{M365['list_id']}/items/{item_id}/fields",
            fields)


def person_id_by_email(conn, email):
    row = conn.execute("SELECT person_id FROM doc_mgmt.person WHERE lower(email)=%s",
                       (email,)).fetchone()
    return row[0] if row else None


def process_new(conn, g, it, dry):
    errs = il.validate_item(it)
    sponsor = person_id_by_email(conn, it["SponsorEmail"]) if it["SponsorEmail"] else None
    pm = person_id_by_email(conn, it["ProjectManagerEmail"]) if it["ProjectManagerEmail"] else None
    if it["SponsorEmail"] and not sponsor:
        errs.append(f"Sponsor {it['SponsorEmail']} not in person directory")
    if it["ProjectManagerEmail"] and not pm:
        errs.append(f"PM {it['ProjectManagerEmail']} not in person directory")
    if errs:
        msg = "; ".join(errs)
        if not dry:
            writeback(g, it["item_id"], {"SyncStatus": "Error", "SyncMessage": msg})
        return f"ERROR item {it['item_id']}: {msg}"

    year = datetime.date.today().year
    existing_intakes = [r[0] for r in conn.execute(
        "SELECT intake_id FROM doc_mgmt.intake_submission").fetchall()]
    intake_id = il.next_intake_id(existing_intakes, year)
    dept = conn.execute("SELECT department_id, code FROM doc_mgmt.department "
                        "WHERE name=%s", (it["Department"],)).fetchone()
    if not dept:
        return f"ERROR item {it['item_id']}: unknown department {it['Department']}"
    dept_id, dept_code = dept
    existing_codes = [r[0] for r in conn.execute(
        "SELECT project_code FROM pmbok.project").fetchall()]
    project_code = il.next_project_code(dept_code, existing_codes)
    project_id = str(uuid.uuid5(NS, f"thg/project/{project_code}"))

    if dry:
        return (f"DRY item {it['item_id']}: would create {intake_id} / "
                f"{project_code} ({it['Title']})")

    with conn.transaction():
        conn.execute(
            "INSERT INTO doc_mgmt.intake_submission (intake_submission_id, intake_id,"
            " submitted_at, requester_person_id, requesting_department_id,"
            " request_title, request_type, business_problem, desired_outcome,"
            " effort, budget_envelope, phi_flag, cfr11_flag, clinical_flag,"
            " vendor_flag, data_sharing_flag, external_ref)"
            " VALUES (%s,%s,now(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(uuid.uuid5(NS, f"thg/intake/{intake_id}")), intake_id, sponsor,
             dept_id, it["Title"][:200], it["RequestType"], it["BusinessProblem"],
             it["DesiredOutcome"], it["EffortBucket"],
             il.derive_envelope(it["EstimatedBudget"]),
             it["Flags"]["PHIFlag"], it["Flags"]["CFR11Flag"],
             it["Flags"]["ClinicalFlag"], it["Flags"]["VendorFlag"],
             it["Flags"]["DataSharingFlag"], it["item_id"]))
        conn.execute(
            "INSERT INTO pmbok.project (project_id, project_code, intake_id, name,"
            " description, sponsor_person_id, project_manager_id,"
            " primary_department, approach, lifecycle_phase, status,"
            " planned_start, planned_finish, budget_total, strategic_objective_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'predictive','Initiating','Proposed',"
            " %s,%s,%s,%s)",
            (project_id, project_code, intake_id, it["Title"][:200],
             it["BusinessProblem"], sponsor, pm, it["Department"],
             it["PlannedStart"], it["PlannedFinish"], it["EstimatedBudget"],
             it["StrategicObjective"]))
        conn.execute(
            "INSERT INTO pmbok.project_charter (charter_id, project_id, doc_id,"
            " business_case, high_level_in_scope, pm_authority_text)"
            " VALUES (%s,%s,%s,%s,'Per approved scope baseline.',"
            " 'Authority per the Theragen project charter standard.')",
            (str(uuid.uuid5(NS, f"thg/charter/{project_code}")), project_id,
             "THG-CHR-" + project_code[4:], it["DesiredOutcome"]))
    writeback(g, it["item_id"], {"SyncStatus": "Synced", "SyncMessage": "",
                                 "IntakeID": intake_id, "ProjectCode": project_code})
    return f"OK new {intake_id} / {project_code} ({it['Title']})"


def process_triage(conn, g, it, dry):
    target = il.triage_to_status(it["TriageStatus"])
    if target is None:
        return f"ERROR item {it['item_id']}: unknown TriageStatus {it['TriageStatus']}"
    row = conn.execute(
        "SELECT p.project_id, p.status FROM pmbok.project p"
        " JOIN doc_mgmt.intake_submission i ON i.intake_id = p.intake_id"
        " WHERE i.external_ref = %s", (it["item_id"],)).fetchone()
    if not row:
        return f"ERROR item {it['item_id']}: synced intake has no project row"
    project_id, current = row
    if current == target:
        return f"OK item {it['item_id']}: status already {current}"
    if dry:
        return f"DRY item {it['item_id']}: would move {current} -> {target}"
    with conn.transaction():
        conn.execute(
            "UPDATE pmbok.project SET status=%s,"
            " actual_start = CASE WHEN %s='Active' AND actual_start IS NULL"
            " THEN CURRENT_DATE ELSE actual_start END WHERE project_id=%s",
            (target, target, project_id))
    writeback(g, it["item_id"], {"SyncStatus": "Synced",
                                 "SyncMessage": f"Status -> {target}"})
    return f"OK triage item {it['item_id']}: {current} -> {target}"
```

- [ ] **Step 2: Dry-run shows intended creation with minted ids**

Run: `python tools/sync_intake.py --dry-run`
Expected: `DRY item ...: would create INT-2026-0007 / THG-IT-004 (TEST sync probe)` (numbers = next after the seeded data; 6 seeded intakes → 0007; IT has 1 seeded project → 004... verify plausibility, exact numbers depend on seed).

- [ ] **Step 3: Real run creates the rows and writes back**

Run: `python tools/sync_intake.py`
Expected: `OK new INT-2026-#### / THG-IT-### (TEST sync probe)`, exit 0.
Verify in the List UI: the row shows IntakeID, ProjectCode, SyncStatus = Synced.
Verify in the DB:

```bash
python - <<'EOF'
import json, psycopg
cfg = json.load(open("db/.pg.local.json"))
c = psycopg.connect(host=cfg["server"], dbname=cfg["database"], user=cfg["user"],
                    password=cfg["password"], sslmode="require")
print(c.execute("SELECT project_code, name, status FROM bi.project "
                "WHERE name LIKE 'TEST sync%'").fetchall())
c.close()
EOF
```

Expected: `[('THG-IT-###', 'TEST sync probe', 'Proposed')]`

- [ ] **Step 4: Idempotency — re-run is a no-op**

Run: `python tools/sync_intake.py`
Expected: `OK item ...: status already Proposed` — no duplicate rows (verify count unchanged with the Step 3 query).

- [ ] **Step 5: Triage transition end-to-end**

In the List UI set the test row's TriageStatus to **Approved**, then:
Run: `python tools/sync_intake.py`
Expected: `OK triage item ...: Proposed -> Active`; Step-3 query now shows `Active`.

- [ ] **Step 6: Clean up the probe and commit**

Delete the test List row, then remove the probe rows:

```bash
python - <<'EOF'
import json, psycopg
cfg = json.load(open("db/.pg.local.json"))
c = psycopg.connect(host=cfg["server"], dbname=cfg["database"], user=cfg["user"],
                    password=cfg["password"], sslmode="require")
c.execute("DELETE FROM pmbok.project_charter WHERE project_id IN "
          "(SELECT project_id FROM pmbok.project WHERE name LIKE 'TEST sync%')")
c.execute("DELETE FROM pmbok.project WHERE name LIKE 'TEST sync%'")
c.execute("DELETE FROM doc_mgmt.intake_submission WHERE request_title LIKE 'TEST sync%'")
c.commit(); c.close(); print("probe removed")
EOF
git add tools/sync_intake.py
git commit -m "Intake sync: write path, idempotency, triage transitions, write-back"
```

---

### Task 7: Form + Flow recipe and scheduling docs

**Files:**
- Create: `docs/intake-setup.md`

- [ ] **Step 1: Write the setup doc**

```markdown
# Intake Setup — Form, Flow, Schedule

## A. Microsoft Form (forms.office.com, ~10 min)

New form **"Theragen Project Intake"**, org-only (Settings → Only people in my
organization, Record name ON). Questions, in order — names must match the Flow
mapping below:

1. Request title (Text)
2. Request type (Choice): Project / Initiative · Clinical or study request ·
   Cross-dept work request · System change · Vendor / procurement · Other
3. Requesting department (Choice): the 8 Theragen departments
4. Business problem (Text, long)
5. Desired outcome / business value (Text, long)
6. Sponsor — full name (Text)
7. Project manager — full name (Text)
8. Planned start (Date) · 9. Planned finish (Date)
10. Estimated budget USD (Number)
11. Effort (Choice): Small (<4 wk) · Medium (1-3 mo) · Large (3-12 mo) · Program (>12 mo)
12-16. PHI involved? · 21 CFR Part 11? · Clinical/study? · Vendor involved? ·
   External data sharing? (each Choice: Yes/No)
17. Strategic objective ref (Text, optional)

## B. Power Automate flow (make.powerautomate.com, ~10 min)

Automated cloud flow, trigger **When a new response is submitted** (the form).

1. **Get response details** (form, response id from trigger)
2. **Office 365 Users – Search for users (V2)**: search = Sponsor answer, top 1
   → same again for Project manager
3. **SharePoint – Create item**: site = root Theragen site, list =
   **Project Intake**; map: Title ← request title; RequestType, Department,
   BusinessProblem, DesiredOutcome, PlannedStart, PlannedFinish,
   EstimatedBudget, EffortBucket, StrategicObjective ← form answers;
   Sponsor Claims ← `first(body('Search_sponsor')?['value'])?['UserPrincipalName']`;
   ProjectManager Claims ← same pattern for PM; the five flags ←
   `equals(<answer>,'Yes')`; leave TriageStatus/SyncStatus at their defaults.

If a people search returns nothing the person column stays empty — the sync
flags the row as Error with a clear message and the PMO fixes the picker by
hand. That is the intended data-quality gate.

## C. Daily schedule (run as Allen, PC on at 5:30 AM)

    schtasks /Create /TN "Theragen Intake Sync" /SC DAILY /ST 05:30 ^
      /TR "\"C:\Python314\python.exe\" \"C:\Users\Allen\OneDrive - Neurotech NA\Documents\GitHub\Theragen-Project-Planer-BI\tools\sync_intake.py\"" ^
      /F /RL LIMITED
    schtasks /Change /TN "Theragen Intake Sync" /ENABLE

In Task Scheduler GUI, open the task → Settings → check **"Run task as soon as
possible after a scheduled start is missed"**.

Pipeline timing: 5:30 sync → 6:00 model refresh → reports current each morning.

## D. End-to-end smoke

Submit the form for a real-ish project → confirm List row appears with people
resolved → `python tools/sync_intake.py --dry-run` shows it → real run → row
shows IntakeID/ProjectCode/Synced → next morning (or `python
tools/service_refresh.py`) it appears in Portfolio Overview as Proposed.
```

- [ ] **Step 2: Commit**

```bash
git add docs/intake-setup.md
git commit -m "Document Form/Flow recipe and daily sync scheduling"
```

---

### Task 8: Schedule + end-to-end smoke

**Files:** none new (operational task)

- [ ] **Step 1: Allen builds the Form and Flow** per `docs/intake-setup.md` A+B (manual, ~20 min).

- [ ] **Step 2: Register the scheduled task**

Run the `schtasks` commands from `docs/intake-setup.md` §C.
Verify: `schtasks /Query /TN "Theragen Intake Sync"` shows Ready, Next Run 5:30 AM.

- [ ] **Step 3: Full e2e smoke** per §D with one real test submission; finish with `python tools/service_refresh.py` and confirm the project shows as **Proposed** in Portfolio Overview.

- [ ] **Step 4: Final commit + update project docs**

Add an "Ingestion" paragraph to `README.md` pointing at `docs/intake-setup.md` and the spec; commit:

```bash
git add README.md
git commit -m "Document the live intake pipeline in the README"
```

---

## Self-review

- **Spec coverage:** migration+guard (T1), pure logic+tests (T2), Graph auth (T3), List schema incl. people pickers/triage/bookkeeping (T4), sync read/validate/dry-run (T5), write path/idempotency/triage/write-back/per-item errors (T6), Form+Flow recipe & person-resolution airlock (T7), daily 5:30 schedule + missed-start + e2e (T8). Out-of-scope items from the spec are not implemented anywhere. ✓
- **Placeholders:** none — every code step carries full code; expected outputs stated. ✓
- **Type consistency:** `intake_lib` function names/signatures match between tests (T2), stubs (T5), and write path (T6: `validate_item`, `next_intake_id`, `next_project_code`, `derive_envelope`, `triage_to_status`); `Graph.get/post/patch` used as defined in T3; `M365`/`PG` config keys consistent. ✓
```
