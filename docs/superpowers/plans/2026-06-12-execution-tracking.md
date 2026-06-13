# Project Execution Tracking Implementation Plan

Spec: `docs/superpowers/specs/2026-06-12-execution-tracking-design.md`
Process: subagent-driven, fresh subagent per task, two-stage review per task.
Hard riders (apply to every task):

- NEVER run `tools/load_postgres.py` or any reseed. DB DDL changes go through
  inline psycopg, data writes only through the syncs and explicitly listed
  probe cleanups.
- Never commit `db/.pg.local.json`, `db/.m365.local.json`,
  `db/.graph_token_cache.json`.
- `python -m pytest tests/ -q` must be green at every commit.
- The intake pipeline is LIVE (5:30 AM task). Any touch to
  `tools/sync_intake.py` or `tools/graph_client.py` must keep
  `python tools/sync_intake.py --dry-run` output byte-identical (capture
  before/after).
- Graph identity: richard.allen@theragen.com (cached token). Site/list ids in
  `db/.m365.local.json`.

---

### Task 1: Artifact external_ref migration

**Files:**
- Create: `db/06_artifact_external_ref.sql`
- Modify: `tools/load_postgres.py` (DDL tuple only)

- [ ] **Step 1: Write the migration**

```sql
-- db/06_artifact_external_ref.sql
-- Idempotency anchors for M365-authored execution artifacts: each synced table
-- remembers its SharePoint List item id. One List per table, so the bare item
-- id is unique per table. status_report_area needs none - its rows are keyed
-- deterministically through their parent report.
ALTER TABLE pmbok.risk          ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
ALTER TABLE pmbok.milestone     ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
ALTER TABLE pmbok.status_report ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
```

- [ ] **Step 2: Add to the loader's DDL tuple** in `tools/load_postgres.py`
  (the `for f in (...)` tuple): append `"06_artifact_external_ref.sql"` after
  `"05_intake_external_ref.sql"`. No other loader changes.

- [ ] **Step 3: Apply live** (inline psycopg, NOT the loader):

```bash
python - <<'EOF'
import json, os, psycopg
cfg = json.load(open("db/.pg.local.json"))
sql = open("db/06_artifact_external_ref.sql", encoding="utf-8").read()
with psycopg.connect(host=cfg["server"], dbname=cfg["database"], user=cfg["user"],
                     password=cfg["password"], sslmode="require") as conn:
    conn.execute(sql)
    rows = conn.execute(
        "SELECT table_name FROM information_schema.columns "
        "WHERE table_schema='pmbok' AND column_name='external_ref' "
        "ORDER BY table_name").fetchall()
    print(rows)
EOF
```

Expect `[('milestone',), ('risk',), ('status_report',)]`.

- [ ] **Step 4: Verify + commit**

```bash
python -m pytest tests/ -q     # 12 passed (current count)
git add db/06_artifact_external_ref.sql tools/load_postgres.py
git commit -m "Add artifact external_ref migration (risk, milestone, status_report)"
```

---

### Task 2: Pure artifact logic with tests (TDD)

**Files:**
- Create: `tests/test_artifact_lib.py` (write FIRST, watch it fail)
- Create: `tools/artifact_lib.py`

- [ ] **Step 1: Write the tests**

```python
# tests/test_artifact_lib.py
import datetime
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))
import artifact_lib as al


def _risk(**over):
    base = {"item_id": "7", "Title": "Vendor slip", "ProjectCode": "THG-IT-001",
            "Category": "Vendor", "Description": "Vendor may slip the date.",
            "Trigger": None, "Likelihood": "4", "Impact": "3",
            "ResponseType": "Mitigate", "RiskOwnerEmail": "a@theragen.com",
            "DueDate": "2026-07-01", "RiskStatus": "Open",
            "ResidualScore": None, "ComplianceFlag": "None",
            "RiskCode": "", "SyncStatus": "Pending"}
    base.update(over)
    return base


def _milestone(**over):
    base = {"item_id": "3", "Title": "Go-live", "ProjectCode": "THG-IT-001",
            "BaselineDate": "2026-08-01", "ForecastDate": None,
            "ActualDate": None, "MilestoneStatus": "On track",
            "OwnerRole": "Project Manager", "SyncStatus": "Pending"}
    base.update(over)
    return base


def _report(**over):
    base = {"item_id": "9", "Title": "wk24", "ProjectCode": "THG-IT-001",
            "PeriodStart": "2026-06-08", "PeriodEnd": "2026-06-12",
            "OverallStatus": "Green", "Trend": "Steady",
            "ExecutiveSummary": "On plan.", "DecisionsNeeded": None,
            "SubmittedByEmail": "a@theragen.com", "CreatedByEmail": "",
            "CreatedAt": "2026-06-12T22:00:00Z",
            "Health": {ka: "Green" for ka in al.KNOWLEDGE_AREAS},
            "SyncStatus": "Pending"}
    base.update(over)
    return base


def test_next_risk_code_sequences_and_widens():
    assert al.next_risk_code([]) == "R-001"
    assert al.next_risk_code(["R-001", "R-007", None, "x"]) == "R-008"
    assert al.next_risk_code(["R-999"]) == "R-1000"  # widens, never truncates


def test_risk_score_bounds():
    assert al.risk_score("4", "3") == 12
    assert al.risk_score(5, 5) == 25
    assert al.risk_score(0, 3) is None
    assert al.risk_score("6", 3) is None
    assert al.risk_score(None, 3) is None
    assert al.risk_score("x", 3) is None


def test_validate_risk_happy_and_missing():
    assert al.validate_risk(_risk()) == []
    errs = al.validate_risk(_risk(ProjectCode="", Description="  ",
                                  Likelihood=None, RiskOwnerEmail=""))
    assert any("ProjectCode" in e for e in errs)
    assert any("Description" in e for e in errs)
    assert any("Likelihood" in e for e in errs)
    assert any("RiskOwner" in e for e in errs)


def test_validate_risk_residual_and_membership():
    assert any("Residual" in e for e in al.validate_risk(_risk(ResidualScore=26)))
    assert al.validate_risk(_risk(ResidualScore=25)) == []
    assert any("Category" in e for e in al.validate_risk(_risk(Category="Weather")))


def test_validate_milestone_achieved_needs_actual_date():
    assert al.validate_milestone(_milestone()) == []
    errs = al.validate_milestone(_milestone(MilestoneStatus="Achieved"))
    assert any("ActualDate" in e for e in errs)
    assert al.validate_milestone(_milestone(MilestoneStatus="Achieved",
                                            ActualDate="2026-06-10")) == []


def test_validate_milestone_required():
    errs = al.validate_milestone(_milestone(Title="", BaselineDate=None))
    assert any("Title" in e for e in errs)
    assert any("BaselineDate" in e for e in errs)


def test_validate_status_report_periods_and_membership():
    assert al.validate_status_report(_report()) == []
    errs = al.validate_status_report(_report(PeriodEnd="2026-06-01"))
    assert any("PeriodEnd" in e for e in errs)
    errs = al.validate_status_report(_report(Trend="Sideways"))
    assert any("Trend" in e for e in errs)
    bad_health = {ka: "Green" for ka in al.KNOWLEDGE_AREAS}
    bad_health["Cost"] = "Purple"
    errs = al.validate_status_report(_report(Health=bad_health))
    assert any("Cost" in e for e in errs)


def test_validate_status_report_submitter_fallback():
    # empty picker but createdBy known -> no error
    assert al.validate_status_report(
        _report(SubmittedByEmail="", CreatedByEmail="pm@theragen.com")) == []
    errs = al.validate_status_report(_report(SubmittedByEmail="", CreatedByEmail=""))
    assert any("SubmittedBy" in e for e in errs)


def test_build_area_rows_complete_and_ordered():
    health = {ka: "Green" for ka in al.KNOWLEDGE_AREAS}
    health["Schedule"] = "Red"
    rows = al.build_area_rows(_report(Health=health))
    assert [r["knowledge_area"] for r in rows] == al.KNOWLEDGE_AREAS  # 9, in order
    assert {r["knowledge_area"]: r["status"] for r in rows}["Schedule"] == "Red"


def test_row_changed_normalizes_types():
    cur = {"due_date": datetime.date(2026, 7, 1), "residual_score": Decimal("12"),
           "description": "x", "trigger": None}
    assert not al.row_changed(cur, {"due_date": "2026-07-01",
                                    "residual_score": 12,
                                    "description": "x", "trigger": ""})
    assert al.row_changed(cur, {"due_date": "2026-07-02"})
```

Run `python -m pytest tests/test_artifact_lib.py -q` → fails (no module).

- [ ] **Step 2: Write the library**

```python
# tools/artifact_lib.py
"""Pure logic for the execution-artifact sync (no I/O - unit-testable).

Companion to intake_lib.py: domain constants, code minting, validators and
row/fan-out builders for the three artifact Lists. Choice strings are the
de-facto contract shared by the Lists, the DB rows, and the report DAX
(e.g. Health Score SWITCHes on Green/Yellow/Red; Recent Accomplishment
filters Milestone Status = "Achieved").
"""
import datetime
import numbers
import re

RISK_CATEGORIES = ["Technical", "Schedule", "Cost", "Regulatory", "Vendor",
                   "People", "Safety", "Reputational"]
RESPONSE_TYPES = ["Mitigate", "Accept", "Avoid", "Transfer"]
RISK_STATUSES = ["Open", "Mitigating", "Monitoring", "Closed", "Realized"]
COMPLIANCE_FLAGS = ["None", "HIPAA", "GxP", "FDA 21 CFR Part 11"]
MILESTONE_STATUSES = ["On track", "At risk", "Achieved", "Slipped"]
RAG = ["Green", "Yellow", "Red"]
TRENDS = ["Improving", "Steady", "Worsening"]
# Exact strings and order of bi.knowledge_area (db/03_bi_views.sql).
KNOWLEDGE_AREAS = ["Scope", "Schedule", "Cost", "Quality", "Risk",
                   "Stakeholders", "Compliance", "Procurement", "Communications"]

_RISK_CODE = re.compile(r"^R-(\d{3,})$")


def next_risk_code(existing):
    """Next R-NNN within one project. Overflow widens rather than truncates."""
    nums = [int(m.group(1)) for s in existing
            if s and (m := _RISK_CODE.match(s))]
    return f"R-{(max(nums) + 1 if nums else 1):03d}"


def risk_score(likelihood, impact):
    """likelihood x impact, both 1-5. None when either is missing/invalid."""
    try:
        lk, im = int(likelihood), int(impact)
    except (TypeError, ValueError):
        return None
    if not (1 <= lk <= 5 and 1 <= im <= 5):
        return None
    return lk * im


def _blank(v):
    return not str(v or "").strip()


def validate_risk(it):
    errs = [f"Missing: {k}" for k in
            ("ProjectCode", "Category", "Description", "ResponseType")
            if _blank(it.get(k))]
    if _blank(it.get("RiskOwnerEmail")):
        errs.append("Missing: RiskOwner")
    if it.get("Likelihood") is None:
        errs.append("Missing: Likelihood")
    if it.get("Impact") is None:
        errs.append("Missing: Impact")
    if (it.get("Likelihood") is not None and it.get("Impact") is not None
            and risk_score(it["Likelihood"], it["Impact"]) is None):
        errs.append("Likelihood/Impact must be 1-5")
    if not _blank(it.get("Category")) and it["Category"] not in RISK_CATEGORIES:
        errs.append(f"Category not recognized: {it['Category']}")
    if not _blank(it.get("ResponseType")) and it["ResponseType"] not in RESPONSE_TYPES:
        errs.append(f"ResponseType not recognized: {it['ResponseType']}")
    if it.get("RiskStatus") and it["RiskStatus"] not in RISK_STATUSES:
        errs.append(f"RiskStatus not recognized: {it['RiskStatus']}")
    rs = it.get("ResidualScore")
    if rs is not None and not (1 <= int(rs) <= 25):
        errs.append("ResidualScore must be 1-25")
    return errs


def validate_milestone(it):
    errs = [f"Missing: {k}" for k in ("Title", "ProjectCode", "BaselineDate",
                                      "OwnerRole") if _blank(it.get(k))]
    if it.get("MilestoneStatus") not in MILESTONE_STATUSES:
        errs.append(f"MilestoneStatus not recognized: {it.get('MilestoneStatus')}")
    # The report's Recent Accomplishment DAX filters Achieved AND non-blank
    # Actual Date - an Achieved milestone without a date silently disappears.
    if it.get("MilestoneStatus") == "Achieved" and _blank(it.get("ActualDate")):
        errs.append("Achieved requires ActualDate (report hides it otherwise)")
    return errs


def validate_status_report(it):
    errs = [f"Missing: {k}" for k in ("ProjectCode", "PeriodStart", "PeriodEnd",
                                      "ExecutiveSummary") if _blank(it.get(k))]
    if (not _blank(it.get("PeriodStart")) and not _blank(it.get("PeriodEnd"))
            and it["PeriodEnd"] < it["PeriodStart"]):
        errs.append("PeriodEnd must be on/after PeriodStart")
    if it.get("OverallStatus") not in RAG:
        errs.append(f"OverallStatus not recognized: {it.get('OverallStatus')}")
    if it.get("Trend") not in TRENDS:
        errs.append(f"Trend not recognized: {it.get('Trend')}")
    for ka in KNOWLEDGE_AREAS:
        if it["Health"].get(ka) not in RAG:
            errs.append(f"{ka} health not recognized: {it['Health'].get(ka)}")
    if _blank(it.get("SubmittedByEmail")) and _blank(it.get("CreatedByEmail")):
        errs.append("Missing: SubmittedBy (picker empty and item author unknown)")
    return errs


def build_risk_row(it, project_id, department, owner_person_id, risk_code):
    return {
        "project_id": project_id,
        "risk_code": risk_code,
        "category": it["Category"],
        "description": it["Description"],
        "trigger": it["Trigger"],
        "likelihood": int(it["Likelihood"]),
        "impact": int(it["Impact"]),
        "score": risk_score(it["Likelihood"], it["Impact"]),
        "response_type": it["ResponseType"],
        "owner_person_id": owner_person_id,
        "department": department,
        "due_date": it["DueDate"],
        "status": it["RiskStatus"],
        "residual_score": int(it["ResidualScore"]) if it["ResidualScore"] is not None else None,
        "compliance_flag": it["ComplianceFlag"],
    }


def build_milestone_row(it, project_id):
    return {
        "project_id": project_id,
        "name": it["Title"][:200],
        "baseline_date": it["BaselineDate"],
        "forecast_date": it["ForecastDate"],
        "actual_date": it["ActualDate"],
        "status": it["MilestoneStatus"],
        "owner_role": it["OwnerRole"][:100],
    }


def build_report_row(it, project_id, submitted_by_person_id):
    return {
        "project_id": project_id,
        "period_start": it["PeriodStart"],
        "period_end": it["PeriodEnd"],
        "overall_status": it["OverallStatus"],
        "trend": it["Trend"],
        "executive_summary": it["ExecutiveSummary"],
        "decisions_needed": it["DecisionsNeeded"],
        "submitted_by_person_id": submitted_by_person_id,
    }


def build_area_rows(it):
    """One row per knowledge area, in bi.knowledge_area order."""
    return [{"knowledge_area": ka, "status": it["Health"][ka]}
            for ka in KNOWLEDGE_AREAS]


def _norm(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return v
    if isinstance(v, numbers.Number):
        return float(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()[:10]
    return str(v).strip()


def row_changed(current, desired):
    """True if any desired column differs from current, normalizing types
    (date vs ISO string, Decimal vs int, None vs '')."""
    return any(_norm(current.get(k)) != _norm(desired[k]) for k in desired)
```

- [ ] **Step 3: Green + commit**

```bash
python -m pytest tests/ -q     # all green (12 existing + 11 new)
git add tools/artifact_lib.py tests/test_artifact_lib.py
git commit -m "Add pure artifact logic: domains, minting, validators, builders, diff"
```

---

### Task 3: Extract SitePeople into graph_client; refactor sync_intake

**Files:**
- Modify: `tools/graph_client.py` (add `coerce_bool` + `SitePeople`)
- Modify: `tools/sync_intake.py` (consume them; delete the moved code)

- [ ] **Step 1: capture the baseline**: `python tools/sync_intake.py --dry-run > /tmp/intake_before.txt 2>&1`

- [ ] **Step 2: add to graph_client.py** (below the `Graph` class; move the
  docstrings/comments with the code — they document live behavior):

```python
def coerce_bool(v):
    """Graph booleans are JSON true/false; non-UI writers may send strings."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() not in ("", "0", "false", "no")
    return bool(v)


class SitePeople:
    """LookupId -> e-mail resolution via a site's hidden User Information List.

    Graph person fields arrive as display-name strings when requested by
    column name, but the companion <Name>LookupId field gives the numeric
    site-user id; the UIL maps that id to the user's e-mail. The UIL is not
    returned by the default /lists endpoint - it needs an explicit $filter.
    Cache is per-instance, loaded lazily once.
    """

    def __init__(self, g, site_id):
        self.g, self.site_id = g, site_id
        self._cache = None

    def _load(self):
        if self._cache is not None:
            return
        self._cache = {}
        lists = self.g.get(f"/sites/{self.site_id}/lists",
                           **{"$filter": "displayName eq 'User Information List'",
                              "$select": "id,displayName"})
        uil_id = next((l["id"] for l in lists.get("value", [])), None)
        if not uil_id:
            print("WARNING: User Information List not found - person fields "
                  "will be empty", file=sys.stderr)
            return
        url = f"/sites/{self.site_id}/lists/{uil_id}/items"
        params = {"$expand": "fields($select=Id,EMail,UserName)", "$top": "500"}
        while url:
            page = self.g.get(url, **params)
            for item in page.get("value", []):
                f = item.get("fields", {})
                lid = str(f.get("Id") or item.get("id") or "").strip()
                email = (f.get("EMail") or f.get("UserName") or "").lower().strip()
                if lid and email:
                    self._cache[lid] = email
            url = page.get("@odata.nextLink", "")
            if url:
                url = url.replace("https://graph.microsoft.com/v1.0", "")
                params = {}

    def email(self, lookup_id_str):
        lid = str(lookup_id_str or "").strip()
        if not lid:
            return ""
        self._load()
        return self._cache.get(lid, "")
```

- [ ] **Step 3: refactor sync_intake.py**: delete `_user_cache`,
  `_load_user_cache`, `_coerce_bool`, `person_email`; import
  `from graph_client import Graph, SitePeople, coerce_bool`; `normalize(item, g)`
  becomes `normalize(item, people)` using `people.email(f.get("SponsorLookupId"))`
  and `coerce_bool`; in `main()` create `people = SitePeople(g, M365["site_id"])`
  once and pass it. The FIELDS constant and everything else stays untouched.

- [ ] **Step 4: prove identical**: `python tools/sync_intake.py --dry-run >
  /tmp/intake_after.txt 2>&1` then `diff /tmp/intake_before.txt /tmp/intake_after.txt`
  (empty). `python -m pytest tests/ -q` green.

- [ ] **Step 5: commit**: `git add tools/graph_client.py tools/sync_intake.py &&
  git commit -m "Extract SitePeople person resolution for reuse by the artifact sync"`

---

### Task 4: Create the three artifact Lists

**Files:**
- Create: `tools/create_artifact_lists.py`

- [ ] **Step 1: write the creator** (idempotent; MERGES into
  `db/.m365.local.json` — must not drop the intake keys):

```python
# tools/create_artifact_lists.py
"""One-time: create the three execution-artifact Lists on the root site and
merge their ids into db/.m365.local.json (preserving the intake keys)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_lib as al
from graph_client import Graph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "db", ".m365.local.json")


def choice(name, choices, default=None, allow_text=False):
    col = {"name": name, "choice": {"allowTextEntry": allow_text,
                                    "choices": choices,
                                    "displayAs": "dropDownMenu"}}
    if default:
        col["defaultValue"] = {"value": default}
    return col


def text(name, multiline=False):
    return {"name": name, "text": ({"allowMultipleLines": True} if multiline else {})}


def date_only(name):
    return {"name": name, "dateTime": {"format": "dateOnly"}}


BOOKKEEPING = [
    choice("SyncStatus", ["Pending", "Synced", "Error"], default="Pending"),
    text("SyncMessage", multiline=True),
]

LISTS = {
    "risk_list_id": ("Project Risks", [
        text("ProjectCode"),
        choice("Category", al.RISK_CATEGORIES),
        text("Description", multiline=True),
        text("Trigger", multiline=True),
        choice("Likelihood", ["1", "2", "3", "4", "5"]),
        choice("Impact", ["1", "2", "3", "4", "5"]),
        choice("ResponseType", al.RESPONSE_TYPES),
        {"name": "RiskOwner", "personOrGroup": {"allowMultipleSelection": False}},
        date_only("DueDate"),
        choice("RiskStatus", al.RISK_STATUSES, default="Open"),
        {"name": "ResidualScore", "number": {"decimalPlaces": "none"}},
        choice("ComplianceFlag", al.COMPLIANCE_FLAGS, default="None"),
        text("RiskCode"),
    ] + BOOKKEEPING),
    "milestone_list_id": ("Project Milestones", [
        text("ProjectCode"),
        date_only("BaselineDate"),
        date_only("ForecastDate"),
        date_only("ActualDate"),
        choice("MilestoneStatus", al.MILESTONE_STATUSES, default="On track"),
        choice("OwnerRole", ["Project Manager", "Sponsor", "Workstream Lead",
                             "Work Package Owner"],
               default="Project Manager", allow_text=True),
    ] + BOOKKEEPING),
    "status_report_list_id": ("Project Status Reports", [
        text("ProjectCode"),
        date_only("PeriodStart"),
        date_only("PeriodEnd"),
        choice("OverallStatus", al.RAG, default="Green"),
        choice("Trend", al.TRENDS, default="Steady"),
        text("ExecutiveSummary", multiline=True),
        text("DecisionsNeeded", multiline=True),
        {"name": "SubmittedBy", "personOrGroup": {"allowMultipleSelection": False}},
    ] + [choice(f"{ka}Health", al.RAG, default="Green")
         for ka in al.KNOWLEDGE_AREAS] + BOOKKEEPING),
}


def main():
    g = Graph()
    cfg = json.load(open(CFG_PATH, encoding="utf-8"))
    site_id = cfg["site_id"]
    for key, (name, columns) in LISTS.items():
        existing = g.get(f"/sites/{site_id}/lists",
                         **{"$filter": f"displayName eq '{name}'"})
        if existing.get("value"):
            lst = existing["value"][0]
            print(f"{name}: already exists ({lst['id']})")
        else:
            lst = g.post(f"/sites/{site_id}/lists", {
                "displayName": name,
                "description": f"Theragen {name.lower()} - synced to PostgreSQL daily.",
                "columns": columns,
                "list": {"template": "genericList"},
            })
            print(f"{name}: created ({lst['id']})")
        cfg[key] = lst["id"]
        cols = g.get(f"/sites/{site_id}/lists/{lst['id']}/columns")
        names = {c["name"] for c in cols["value"]}
        missing = [c["name"] for c in columns if c["name"] not in names]
        print(f"  columns: {'OK all present' if not missing else f'MISSING {missing}'}")
    json.dump(cfg, open(CFG_PATH, "w", encoding="utf-8"), indent=2)
    print(f"config merged: {CFG_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: run it** — expect three "created" lines each with
  "OK all present", and `db/.m365.local.json` now holding 6+ keys (intake keys
  intact — verify by printing the JSON keys).

- [ ] **Step 3: re-run** — idempotent ("already exists" x3).

- [ ] **Step 4: commit** (script only): `git add tools/create_artifact_lists.py
  && git commit -m "Add one-time creator for the three artifact Lists"`

---

### Task 5: sync_artifacts.py — read, normalize, validate, dry-run

**Files:**
- Create: `tools/sync_artifacts.py` (engine + normalizers + STUB processors)

The full file below ships in this task with `process_*` stubs that perform
validation + project/person resolution and return `DRY`/`ERROR` strings only —
no DB writes, no write-backs (write-backs land in T6).

```python
# tools/sync_artifacts.py
"""Daily M365 -> PostgreSQL execution-artifact sync
(spec: 2026-06-12-execution-tracking).

Reads the Project Risks / Project Milestones / Project Status Reports Lists,
inserts new artifacts (status reports fan out to 9 knowledge-area rows),
re-applies PM edits via full-row compare, heals lost write-backs, and surfaces
errors on each List row. Idempotent via <table>.external_ref = List item id.
PostgreSQL is the system of record; the Lists are the authoring surface and
win on conflict. --dry-run prints intent only.
"""
import argparse
import json
import os
import sys
import uuid

import psycopg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_lib as al
from graph_client import Graph, SitePeople

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PG = json.load(open(os.path.join(ROOT, "db", ".pg.local.json")))
M365 = json.load(open(os.path.join(ROOT, "db", ".m365.local.json")))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

HEALTH_FIELDS = ",".join(f"{ka}Health" for ka in al.KNOWLEDGE_AREAS)
RISK_FIELDS = ("Title,ProjectCode,Category,Description,Trigger,Likelihood,"
               "Impact,ResponseType,RiskOwner,RiskOwnerLookupId,DueDate,"
               "RiskStatus,ResidualScore,ComplianceFlag,RiskCode,"
               "SyncStatus,SyncMessage")
MILESTONE_FIELDS = ("Title,ProjectCode,BaselineDate,ForecastDate,ActualDate,"
                    "MilestoneStatus,OwnerRole,SyncStatus,SyncMessage")
REPORT_FIELDS = ("Title,ProjectCode,PeriodStart,PeriodEnd,OverallStatus,Trend,"
                 "ExecutiveSummary,DecisionsNeeded,SubmittedBy,"
                 "SubmittedByLookupId," + HEALTH_FIELDS + ",SyncStatus,SyncMessage")


def _date(v):
    return (v or "")[:10] or None


def fetch_items(g, list_id, fields):
    site = M365["site_id"]
    url = f"/sites/{site}/lists/{list_id}/items"
    out, params = [], {"$expand": f"fields($select={fields})", "$top": "200"}
    while url:
        page = g.get(url, **params)
        out += page.get("value", [])
        url = page.get("@odata.nextLink", "")
        if url:
            url = url.replace("https://graph.microsoft.com/v1.0", "")
            params = {}
    return out


def normalize_risk(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "Category": f.get("Category") or "",
        "Description": f.get("Description") or "",
        "Trigger": f.get("Trigger") or None,
        "Likelihood": f.get("Likelihood"),
        "Impact": f.get("Impact"),
        "ResponseType": f.get("ResponseType") or "",
        "RiskOwnerEmail": people.email(f.get("RiskOwnerLookupId")),
        "DueDate": _date(f.get("DueDate")),
        "RiskStatus": f.get("RiskStatus") or "Open",
        "ResidualScore": f.get("ResidualScore"),
        "ComplianceFlag": f.get("ComplianceFlag") or "None",
        "RiskCode": f.get("RiskCode") or "",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_milestone(item, people):
    f = item.get("fields", {})
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "BaselineDate": _date(f.get("BaselineDate")),
        "ForecastDate": _date(f.get("ForecastDate")),
        "ActualDate": _date(f.get("ActualDate")),
        "MilestoneStatus": f.get("MilestoneStatus") or "On track",
        "OwnerRole": f.get("OwnerRole") or "Project Manager",
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def normalize_report(item, people):
    f = item.get("fields", {})
    created_by = (((item.get("createdBy") or {}).get("user") or {})
                  .get("email") or "").lower()
    return {
        "item_id": item["id"],
        "Title": f.get("Title") or "",
        "ProjectCode": (f.get("ProjectCode") or "").strip(),
        "PeriodStart": _date(f.get("PeriodStart")),
        "PeriodEnd": _date(f.get("PeriodEnd")),
        "OverallStatus": f.get("OverallStatus") or "Green",
        "Trend": f.get("Trend") or "Steady",
        "ExecutiveSummary": f.get("ExecutiveSummary") or "",
        "DecisionsNeeded": f.get("DecisionsNeeded") or None,
        "SubmittedByEmail": people.email(f.get("SubmittedByLookupId")),
        "CreatedByEmail": created_by,
        "CreatedAt": item.get("createdDateTime"),
        "Health": {ka: f.get(f"{ka}Health") or "Green"
                   for ka in al.KNOWLEDGE_AREAS},
        "SyncStatus": f.get("SyncStatus") or "Pending",
    }


def writeback(g, list_id, item_id, fields):
    g.patch(f"/sites/{M365['site_id']}/lists/{list_id}/items/{item_id}/fields",
            fields)


def person_id_by_email(conn, email):
    row = conn.execute("SELECT person_id FROM doc_mgmt.person WHERE lower(email)=%s",
                       (email,)).fetchone()
    return row[0] if row else None


def project_by_code(conn, code):
    return conn.execute(
        "SELECT project_id, primary_department FROM pmbok.project "
        "WHERE project_code=%s", (code,)).fetchone()


def _error(g, list_id, it, errs, dry, kind):
    msg = "; ".join(errs)
    if not dry:
        writeback(g, list_id, it["item_id"],
                  {"SyncStatus": "Error", "SyncMessage": msg})
    return f"ERROR {kind} item {it['item_id']}: {msg}"


def synced_map(conn, table, select_sql):
    """external_ref -> current-row dict for one artifact table."""
    out = {}
    cur = conn.execute(select_sql)
    cols = [d.name for d in cur.description]
    for row in cur.fetchall():
        rec = dict(zip(cols, row))
        out[rec.pop("external_ref")] = rec
    return out


RISK_SELECT = ('SELECT external_ref, risk_id, project_id, risk_code, category,'
               ' description, "trigger", likelihood, impact, score,'
               ' response_type, owner_person_id, department, due_date, status,'
               ' residual_score, compliance_flag'
               ' FROM pmbok.risk WHERE external_ref IS NOT NULL')
MILESTONE_SELECT = ('SELECT external_ref, milestone_id, project_id, name,'
                    ' baseline_date, forecast_date, actual_date, status,'
                    ' owner_role'
                    ' FROM pmbok.milestone WHERE external_ref IS NOT NULL')
REPORT_SELECT = ('SELECT external_ref, report_id, project_id, period_start,'
                 ' period_end, overall_status, trend, executive_summary,'
                 ' decisions_needed, submitted_by_person_id'
                 ' FROM pmbok.status_report WHERE external_ref IS NOT NULL')


# ---- processors (T5: stubs - validate/resolve and report intent only) -------

def process_risk(conn, g, it, dry, current):
    errs = al.validate_risk(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    owner = (person_id_by_email(conn, it["RiskOwnerEmail"])
             if it["RiskOwnerEmail"] else None)
    if it["RiskOwnerEmail"] and not owner:
        errs.append(f"RiskOwner {it['RiskOwnerEmail']} not in person directory")
    if errs:
        return _error(g, M365["risk_list_id"], it, errs, dry, "risk")
    if current:
        return f"DRY risk item {it['item_id']}: existing (update path lands in T6/T7)"
    return f"DRY risk item {it['item_id']}: would create (project {it['ProjectCode']})"
    # TODO(T6): insert + write-back; TODO(T7): compare/update/heal


def process_milestone(conn, g, it, dry, current):
    errs = al.validate_milestone(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    if errs:
        return _error(g, M365["milestone_list_id"], it, errs, dry, "milestone")
    if current:
        return f"DRY milestone item {it['item_id']}: existing (update path lands in T6/T7)"
    return f"DRY milestone item {it['item_id']}: would create ({it['Title']})"
    # TODO(T6)/TODO(T7) as above


def process_report(conn, g, it, dry, current):
    errs = al.validate_status_report(it)
    proj = project_by_code(conn, it["ProjectCode"]) if it["ProjectCode"] else None
    if it["ProjectCode"] and not proj:
        errs.append(f"Unknown ProjectCode: {it['ProjectCode']}")
    submitter = (person_id_by_email(conn, it["SubmittedByEmail"])
                 or person_id_by_email(conn, it["CreatedByEmail"]))
    if not errs and not submitter:
        errs.append("SubmittedBy not in person directory")
    if errs:
        return _error(g, M365["status_report_list_id"], it, errs, dry, "report")
    if current:
        return f"DRY report item {it['item_id']}: existing (update path lands in T6/T7)"
    return (f"DRY report item {it['item_id']}: would create report + "
            f"{len(al.KNOWLEDGE_AREAS)} areas ({it['ProjectCode']} "
            f"{it['PeriodStart']}..{it['PeriodEnd']})")
    # TODO(T6)/TODO(T7) as above


ARTIFACTS = [
    {"kind": "risk", "list_key": "risk_list_id", "fields": RISK_FIELDS,
     "normalize": normalize_risk, "process": process_risk,
     "select": RISK_SELECT},
    {"kind": "milestone", "list_key": "milestone_list_id",
     "fields": MILESTONE_FIELDS, "normalize": normalize_milestone,
     "process": process_milestone, "select": MILESTONE_SELECT},
    {"kind": "report", "list_key": "status_report_list_id",
     "fields": REPORT_FIELDS, "normalize": normalize_report,
     "process": process_report, "select": REPORT_SELECT},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = Graph()
    people = SitePeople(g, M365["site_id"])
    results, orphans = [], []
    with psycopg.connect(host=PG["server"], dbname=PG["database"],
                         user=PG["user"], password=PG["password"],
                         sslmode="require") as conn:
        for art in ARTIFACTS:
            raw = fetch_items(g, M365[art["list_key"]], art["fields"])
            print(f"{art['kind']}: {len(raw)} list item(s) fetched")
            items = [art["normalize"](i, people) for i in raw]
            synced = synced_map(conn, art["kind"], art["select"])
            seen = set()
            for it in items:
                seen.add(it["item_id"])
                try:
                    results.append(art["process"](conn, g, it, args.dry_run,
                                                  synced.get(it["item_id"])))
                except Exception as e:  # one item must not kill the batch
                    results.append(f"ERROR {art['kind']} item {it['item_id']}: "
                                   f"{type(e).__name__}: {e}")
            for ref in sorted(set(synced) - seen, key=str):
                orphans.append(f"INFO orphaned external_ref {art['kind']}/{ref}: "
                               "List row deleted; DB row kept (system of record)")
    for r in results:
        print(" ", r)
    for o in orphans:
        print(" ", o)
    bad = [r for r in results if r.startswith("ERROR")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Steps to verify (live, read-only):** hand-enter ONE row per List in the
  browser-less way — create probe items via Graph POST (Title "TEST artifact
  probe", valid ProjectCode of a real project, RiskOwner/SubmittedBy via
  `{"RiskOwnerLookupId": "485"}` pattern, Likelihood "4" / Impact "3",
  BaselineDate, PeriodStart/End). Then:
  - `python tools/sync_artifacts.py --dry-run` → three "fetched" lines, one
    `DRY ... would create` per List, exit 0.
  - Break one probe (PATCH ProjectCode to "THG-XX-999") → dry-run shows
    `ERROR ... Unknown ProjectCode` and exit 1; fix it back.
  - Leave the three probes in place for T6.
- [ ] **Commit:** `git add tools/sync_artifacts.py && git commit -m "Artifact sync: read, normalize, validate, dry-run"`

---

### Task 6: Write path — inserts, fan-out, minting, write-backs

**Files:**
- Modify: `tools/sync_artifacts.py` (replace the three stubs' create branches)

Replace each `return f"DRY ... would create ..."` (and the trailing TODO
comments) with real writes; the `current:` branches keep returning a
placeholder until T7. Exact code:

**process_risk** create branch:

```python
    project_id, department = proj
    if current:
        return f"OK risk item {it['item_id']}: existing (update path lands in T7)"
    existing_codes = [r[0] for r in conn.execute(
        "SELECT risk_code FROM pmbok.risk WHERE project_id=%s",
        (project_id,)).fetchall()]
    risk_code = al.next_risk_code(existing_codes)
    if dry:
        return f"DRY risk item {it['item_id']}: would create {risk_code} ({it['ProjectCode']})"
    row = al.build_risk_row(it, project_id, department, owner, risk_code)
    with conn.transaction():
        conn.execute(
            'INSERT INTO pmbok.risk (risk_id, project_id, risk_code, category,'
            ' description, "trigger", likelihood, impact, score, response_type,'
            ' owner_person_id, department, due_date, status, residual_score,'
            ' compliance_flag, external_ref)'
            ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (str(uuid.uuid5(NS, f"thg/artifact/risk/{it['item_id']}")),
             row["project_id"], row["risk_code"], row["category"],
             row["description"], row["trigger"], row["likelihood"],
             row["impact"], row["score"], row["response_type"],
             row["owner_person_id"], row["department"], row["due_date"],
             row["status"], row["residual_score"], row["compliance_flag"],
             it["item_id"]))
    writeback(g, M365["risk_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": "", "RiskCode": risk_code})
    return f"OK new risk {risk_code} ({it['ProjectCode']}, item {it['item_id']})"
```

**process_milestone** create branch:

```python
    project_id, _dept = proj
    if current:
        return f"OK milestone item {it['item_id']}: existing (update path lands in T7)"
    if dry:
        return f"DRY milestone item {it['item_id']}: would create ({it['Title']})"
    row = al.build_milestone_row(it, project_id)
    with conn.transaction():
        conn.execute(
            "INSERT INTO pmbok.milestone (milestone_id, project_id, name,"
            " baseline_date, forecast_date, actual_date, status, owner_role,"
            " external_ref) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(uuid.uuid5(NS, f"thg/artifact/milestone/{it['item_id']}")),
             row["project_id"], row["name"], row["baseline_date"],
             row["forecast_date"], row["actual_date"], row["status"],
             row["owner_role"], it["item_id"]))
    writeback(g, M365["milestone_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": ""})
    return f"OK new milestone ({it['Title']}, item {it['item_id']})"
```

**process_report** create branch (duplicate-period guard + 1+9 atomic):

```python
    project_id, _dept = proj
    if current:
        return f"OK report item {it['item_id']}: existing (update path lands in T7)"
    dup = conn.execute(
        "SELECT 1 FROM pmbok.status_report WHERE project_id=%s AND"
        " period_start=%s AND (external_ref IS NULL OR external_ref<>%s)",
        (project_id, it["PeriodStart"], it["item_id"])).fetchone()
    if dup:
        return _error(g, M365["status_report_list_id"], it,
                      [f"Duplicate report period for {it['ProjectCode']}: "
                       f"{it['PeriodStart']}"], dry, "report")
    if dry:
        return (f"DRY report item {it['item_id']}: would create report + 9 areas"
                f" ({it['ProjectCode']} {it['PeriodStart']}..{it['PeriodEnd']})")
    report_id = str(uuid.uuid5(NS, f"thg/artifact/report/{it['item_id']}"))
    row = al.build_report_row(it, project_id, submitter)
    with conn.transaction():
        conn.execute(
            "INSERT INTO pmbok.status_report (report_id, project_id,"
            " period_start, period_end, overall_status, trend,"
            " executive_summary, decisions_needed, submitted_by_person_id,"
            " submitted_at, external_ref)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (report_id, row["project_id"], row["period_start"],
             row["period_end"], row["overall_status"], row["trend"],
             row["executive_summary"], row["decisions_needed"],
             row["submitted_by_person_id"], it["CreatedAt"], it["item_id"]))
        for area in al.build_area_rows(it):
            conn.execute(
                "INSERT INTO pmbok.status_report_area (area_id, report_id,"
                " knowledge_area, status) VALUES (%s,%s,%s,%s)",
                (str(uuid.uuid5(NS, f"thg/sra/{it['item_id']}/{area['knowledge_area']}")),
                 report_id, area["knowledge_area"], area["status"]))
    writeback(g, M365["status_report_list_id"], it["item_id"],
              {"SyncStatus": "Synced", "SyncMessage": ""})
    return f"OK new report + 9 areas ({it['ProjectCode']} {it['PeriodStart']}, item {it['item_id']})"
```

(The duplicate-period guard runs before `dry` so dry-run surfaces it too.)

- [ ] **Verify live** with the three T5 probes: dry-run shows minted `R-NNN`;
  real run prints three `OK new ...`; Graph GETs show Synced (+RiskCode); DB
  probes: `SELECT ... FROM bi.risk WHERE project_code=...`, `bi.milestone`,
  `bi.status_report` (+ `SELECT COUNT(*) FROM bi.status_report_area WHERE
  report_id=...` = 9). Immediate re-run → three `OK ... existing` lines, no
  new rows (counts unchanged).
- [ ] **Commit:** `git commit -m "Artifact sync: insert paths, report fan-out, code minting, write-backs"`

---

### Task 7: Update path, healing, orphan handling

**Files:**
- Modify: `tools/sync_artifacts.py` (replace the three `current:` placeholders)

Pattern per processor (risk shown; milestone/report analogous):

```python
    if current:
        if str(current["project_id"]) != str(project_id):
            return _error(g, M365["risk_list_id"], it,
                          ["ProjectCode changed after sync - create a new row"
                           " instead"], dry, "risk")
        desired = al.build_risk_row(it, current["project_id"], department,
                                    owner, current["risk_code"])
        if al.row_changed(current, desired):
            if dry:
                return f"DRY risk item {it['item_id']}: would update {current['risk_code']}"
            with conn.transaction():
                conn.execute(
                    'UPDATE pmbok.risk SET category=%s, description=%s,'
                    ' "trigger"=%s, likelihood=%s, impact=%s, score=%s,'
                    ' response_type=%s, owner_person_id=%s, department=%s,'
                    ' due_date=%s, status=%s, residual_score=%s,'
                    ' compliance_flag=%s WHERE external_ref=%s',
                    (desired["category"], desired["description"],
                     desired["trigger"], desired["likelihood"],
                     desired["impact"], desired["score"],
                     desired["response_type"], desired["owner_person_id"],
                     desired["department"], desired["due_date"],
                     desired["status"], desired["residual_score"],
                     desired["compliance_flag"], it["item_id"]))
            writeback(g, M365["risk_list_id"], it["item_id"],
                      {"SyncStatus": "Synced", "SyncMessage": "",
                       "RiskCode": current["risk_code"]})
            return f"OK risk item {it['item_id']}: updated {current['risk_code']}"
        if it["SyncStatus"] != "Synced" or it["RiskCode"] != current["risk_code"]:
            if not dry:
                writeback(g, M365["risk_list_id"], it["item_id"],
                          {"SyncStatus": "Synced", "SyncMessage": "",
                           "RiskCode": current["risk_code"]})
            return f"OK risk item {it['item_id']}: healed write-back"
        return f"OK risk item {it['item_id']}: no change"
```

Notes that the implementer must honor:
- `build_risk_row` is called with `current["project_id"]` (not the resolved
  one) so `row_changed` never trips on the protected key; the explicit guard
  above handles re-parenting attempts.
- Milestone heal condition: `it["SyncStatus"] != "Synced"` only (no minted code).
- Report update: desired = `build_report_row(it, current["project_id"],
  current["submitted_by_person_id"])` — submitter and submitted_at are
  immutable after creation. Compare parent via `row_changed` AND compare the 9
  area statuses against a second per-run map
  `SELECT r.external_ref, a.knowledge_area, a.status FROM pmbok.status_report_area a
  JOIN pmbok.status_report r ON r.report_id=a.report_id WHERE r.external_ref IS NOT NULL`
  (loaded once in `main` and passed via the registry entry or a closure).
  On change: one transaction updating the parent row (when changed) and
  `UPDATE pmbok.status_report_area SET status=%s WHERE report_id=%s AND
  knowledge_area=%s` per differing area. The duplicate-period guard from T6
  also applies on update (a PM may edit PeriodStart into a collision).
- Orphan handling already landed in T5's `main()` — confirm it prints for a
  deleted row and exits 0.

- [ ] **Verify live (probes from T6):**
  1. PATCH the risk probe's Likelihood to "5" → run → `OK risk ... updated R-NNN`;
     `bi.risk` shows score 15; re-run → `no change`.
  2. PATCH the report probe's ScheduleHealth to "Red" → run → report updated;
     `bi.status_report_area` shows Schedule=Red, other 8 untouched.
  3. PATCH the milestone probe `{"SyncStatus": "Pending"}` → run →
     `healed write-back`; List shows Synced again.
  4. PATCH the risk probe's ProjectCode to a different real project → run →
     `ERROR ... create a new row instead`; PATCH back → run → `no change`
     (after an Error the heal path restores Synced).
  5. DELETE the milestone probe List item → run → `INFO orphaned external_ref
     milestone/<id>` + exit 0 + DB row intact.
  6. Cleanup: DELETE the remaining two probe List items; targeted DB deletes
     (areas → report; risk; milestone) for the probe rows by external_ref;
     verify zero probe rows remain in all four tables.
- [ ] **Commit:** `git commit -m "Artifact sync: update path, write-back healing, orphan reporting"`

---

### Task 8: Wrapper, 5:40 AM schedule, PM docs

**Files:**
- Create: `tools/run_artifact_sync.cmd` (clone of `tools/run_intake_sync.cmd`,
  pointing at `sync_artifacts.py` and `logs\artifact_sync.log`)
- Create: `docs/artifact-entry-setup.md`
- Modify: `README.md` (one paragraph under "Project ingestion")

- [ ] **Step 1: wrapper** — copy `run_intake_sync.cmd`, swap the script and log
  names. Nothing else changes (it self-creates `logs\`).
- [ ] **Step 2: register the task** (cmd.exe semantics; the wrapper-path
  pattern from `docs/intake-setup.md` §C):

```cmd
schtasks /Create /TN "Theragen\SyncArtifacts" /TR "\"<REPO>\tools\run_artifact_sync.cmd\"" /SC DAILY /ST 05:40 /RL LIMITED /F
```

  then StartWhenAvailable + battery tolerance via the PowerShell snippet from
  §C (TaskName "SyncArtifacts"). Trigger one manual run (`schtasks /Run`) —
  empty Lists → "0 list item(s) fetched" x3, exit 0 in `logs\artifact_sync.log`.
- [ ] **Step 3: docs/artifact-entry-setup.md** — PM-facing how-to: the three
  Lists and what each column means (exact choice strings), the
  Error → fix row → next-run-heals loop, write-back columns are read-only,
  Achieved-requires-ActualDate and the 35-day accomplishment window,
  delete policy (deleting a List row does NOT delete history; close/reject
  via status instead), duplicate-period rule, pipeline timing
  (5:30 intake → 5:40 artifacts → 6:00 refresh), morning health check
  (`findstr "ERROR" logs\artifact_sync.log`), and the hard rule **never run
  load_postgres.py --reseed after go-live** (it destroys live intakes and
  artifacts).
- [ ] **Step 4: README** — extend the ingestion section with one "Execution
  tracking" paragraph linking the new doc.
- [ ] **Commit:** `git add tools/run_artifact_sync.cmd docs/artifact-entry-setup.md README.md && git commit -m "Schedule artifact sync (5:40 AM) and document PM artifact entry"`

---

### Task 9: End-to-end smoke + final review (needs Allen)

- [ ] For one real project (e.g. the next genuine intake, or a seeded demo
  project): file 2 risks, 3 milestones (one Achieved with ActualDate within
  35 days), 1 status report (one area non-Green) — in the Lists UI.
- [ ] `python tools/sync_artifacts.py --dry-run` → expected intents; real run →
  all OK; `python tools/service_refresh.py` → Project Status Report page for
  that project shows: traffic light + trend, 9-cell health check with the
  non-Green cell, RAID rows with minted R-codes, risk gauge with a real
  average, the Achieved milestone under Accomplishments and a future one
  under Next Steps.
- [ ] Next morning: `logs\intake_sync.log` and `logs\artifact_sync.log` both
  show exit 0 unattended runs; report current.
- [ ] Whole-implementation review (most capable model) across the T1–T8 range;
  fix loop; final commit.

---

## Self-review

- **Spec coverage:** migration (T1), pure logic+tests (T2), shared person
  resolution (T3), Lists incl. 9 health columns (T4), engine
  read/validate/dry-run + orphans (T5), insert paths + fan-out + minting +
  write-backs + duplicate guard (T6), updates + healing + re-parent protection
  (T7), schedule + PM docs (T8), e2e (T9). Out-of-scope items deferred match
  the spec. ✓
- **Type consistency:** `artifact_lib` signatures match tests (T2) and call
  sites (T5–T7): `validate_*(it)->list`, `build_*_row(...)->dict`,
  `build_area_rows(it)->list[9]`, `row_changed(current, desired)->bool`,
  `next_risk_code(list)->str`, `risk_score(l,i)->int|None`. `SitePeople.email`
  matches both syncs; `M365` keys (`risk_list_id`, `milestone_list_id`,
  `status_report_list_id`) written by T4 and read by T5. ✓
- **Placeholders:** every step carries full code or an exact recipe; expected
  outputs stated for each live verification. ✓
