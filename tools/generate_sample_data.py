"""Generate seeded sample data for the Theragen Project Planner BI model.

Tables and columns follow THG-ENT-DBS-001 Database Schema Specification v1.0
(PMBOK schema, PostgreSQL naming). Output: CSV files under SampleData/.
"Today" for status derivation is 2026-06-11 (matching the project timeline).
"""
import csv
import os
import random
import uuid
from datetime import date, timedelta

random.seed(42)
TODAY = date(2026, 6, 11)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SampleData")
os.makedirs(OUT, exist_ok=True)

NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def uid(kind, key):
    return str(uuid.uuid5(NS, f"thg/{kind}/{key}"))


def d(iso):
    return date.fromisoformat(iso)


def wd(start, days):
    """start + n working days (approx: skip weekends)."""
    cur, n = start, 0
    while n < days:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            n += 1
    return cur


def write(name, rows, cols):
    path = os.path.join(OUT, f"{name}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{name}.csv: {len(rows)} rows")


# ---------------------------------------------------------------- departments
DEPTS = [
    ("CLN", "Clinical / Medical Affairs"),
    ("REG", "Regulatory / Quality"),
    ("RND", "R&D / Engineering"),
    ("OPS", "Operations / PMO"),
    ("FIN", "Finance / Procurement"),
    ("COM", "Commercial / Marketing"),
    ("IT", "IT / Data / Security"),
    ("HR", "HR / People"),
]
dept_rows = [
    {"department_id": uid("dept", c), "code": c, "name": n, "active": "TRUE"}
    for c, n in DEPTS
]
write("department", dept_rows, ["department_id", "code", "name", "active"])

# --------------------------------------------------------------------- people
PEOPLE = [
    ("Maya Patel", "CLN", "Medical Director"),
    ("Daniel Okafor", "CLN", "Clinical Operations Lead"),
    ("Sofia Reyes", "CLN", "Clinical Research Associate"),
    ("James Whitfield", "REG", "Quality / Regulatory Director"),
    ("Anna Lindqvist", "REG", "Regulatory Affairs Specialist"),
    ("Priya Nair", "REG", "Quality Engineer"),
    ("Ethan Brooks", "RND", "VP Engineering"),
    ("Lena Hoffmann", "RND", "Firmware Lead"),
    ("Marcus Chen", "RND", "Systems Engineer"),
    ("Aiko Tanaka", "RND", "Test Engineer"),
    ("Robert Hale", "OPS", "PMO Director"),
    ("Grace Mwangi", "OPS", "Senior Project Manager"),
    ("Tom Becker", "OPS", "Project Manager"),
    ("Isabel Fonseca", "OPS", "Project Coordinator"),
    ("Victor Osei", "FIN", "Finance Lead"),
    ("Hannah Kim", "FIN", "Procurement Manager"),
    ("Olivia Marsh", "COM", "Commercial Director"),
    ("Lucas Romero", "COM", "Product Marketing Manager"),
    ("Nadia Hassan", "IT", "Information Security Officer"),
    ("Sam Delgado", "IT", "Data Platform Lead"),
    ("Chloe Barnett", "IT", "BI Developer"),
    ("Peter Novak", "HR", "HR Director"),
    ("Ruth Adler", "HR", "Training & Competency Lead"),
    ("Omar Sinclair", "OPS", "Chief Operating Officer"),
]
person_rows = []
for i, (name, dc, role) in enumerate(PEOPLE, 1):
    first = name.split()[0].lower()[0]
    last = name.split()[-1].lower()
    person_rows.append({
        "person_id": uid("person", name),
        "employee_number": f"EMP-{400 + i:05d}",
        "email": f"{first}.{last}@theragen.com",
        "display_name": name,
        "department_code": dict(DEPTS)[dc] if False else dc,
        "department_name": dict(DEPTS)[dc],
        "role_title": role,
        "employment_type": "Employee",
        "active": "TRUE",
        "start_date": "2024-01-15",
    })
write("person", person_rows, ["person_id", "employee_number", "email", "display_name",
                              "department_code", "department_name", "role_title",
                              "employment_type", "active", "start_date"])
P = {r["display_name"]: r["person_id"] for r in person_rows}

# ------------------------------------------------------------------- projects
# business_value mirrors project_charter.business_case (THG-ENT-DBS-001 P02).
PROJECTS = [
    dict(code="THG-CLN-014", intake="INT-2026-0042", name="Cardio Device Feasibility Study",
         desc="Feasibility study for the next-generation cardio stimulation device across three trial sites.",
         value="De-risk the next-generation cardio platform by validating clinical feasibility early, "
               "protecting the FY27 launch window and strengthening the regulatory submission package.",
         sponsor="Maya Patel", pm="Grace Mwangi", dept="Clinical / Medical Affairs",
         approach="predictive", phase="Executing", status="Active",
         ps="2026-01-05", pf="2026-12-18", as_="2026-01-12", af="",
         budget=725000.00, obj="FY26-O2"),
    dict(code="THG-RND-007", intake="INT-2025-0117", name="Pulse Firmware v3 Platform",
         desc="Re-architecture of the ActaStim pulse firmware platform for modular therapy programs.",
         value="Cut therapy-program release cycles from quarters to weeks with a modular firmware "
               "platform, enabling faster clinical iteration and reduced verification cost per release.",
         sponsor="Ethan Brooks", pm="Lena Hoffmann", dept="R&D / Engineering",
         approach="agile", phase="Executing", status="Active",
         ps="2025-09-01", pf="2026-08-28", as_="2025-09-08", af="",
         budget=480000.00, obj="FY26-O1"),
    dict(code="THG-IT-003", intake="INT-2026-0011", name="HIPAA Data Lake Migration",
         desc="Migration of PHI-bearing analytics workloads to the HIPAA-controlled data lake.",
         value="Consolidate PHI analytics into a HIPAA-controlled platform, eliminating audit findings "
               "exposure, enabling self-service insights, and reducing legacy infrastructure spend.",
         sponsor="Nadia Hassan", pm="Sam Delgado", dept="IT / Data / Security",
         approach="hybrid", phase="Planning", status="Active",
         ps="2026-04-01", pf="2027-01-29", as_="2026-04-06", af="",
         budget=390000.00, obj="FY26-O4"),
    dict(code="THG-OPS-009", intake="INT-2026-0027", name="PMBOK Rollout & Training",
         desc="Deployment of the integrated PMBOK documentation system and training across all departments.",
         value="Standardize project delivery and document control across all eight departments, giving "
               "leadership a single trusted view of project health and audit-ready evidence on demand.",
         sponsor="Omar Sinclair", pm="Tom Becker", dept="Operations / PMO",
         approach="predictive", phase="Monitoring", status="Active",
         ps="2026-02-02", pf="2026-09-30", as_="2026-02-02", af="",
         budget=150000.00, obj="FY26-O3"),
    dict(code="THG-REG-005", intake="INT-2025-0089", name="ISO 13485 Recertification",
         desc="Recertification audit preparation and execution for ISO 13485:2016 quality management.",
         value="Maintain ISO 13485 certification — a prerequisite for market access and key customer "
               "contracts — while closing audit findings that carry regulatory and commercial risk.",
         sponsor="James Whitfield", pm="Priya Nair", dept="Regulatory / Quality",
         approach="predictive", phase="Closing", status="Active",
         ps="2025-07-07", pf="2026-06-30", as_="2025-07-07", af="",
         budget=210000.00, obj="FY26-O5"),
    dict(code="THG-COM-002", intake="INT-2026-0063", name="EU Market Expansion Launch",
         desc="Commercial launch readiness for EU expansion of the ActaStim product family.",
         value="Open the EU market for the ActaStim family, diversifying revenue beyond North America "
               "and establishing distributor relationships ahead of competitor entry.",
         sponsor="Olivia Marsh", pm="Isabel Fonseca", dept="Commercial / Marketing",
         approach="hybrid", phase="Initiating", status="Proposed",
         ps="2026-08-03", pf="2027-05-28", as_="", af="",
         budget=560000.00, obj="FY27-O1"),
]
proj_rows = []
for p in PROJECTS:
    proj_rows.append({
        "project_id": uid("project", p["code"]),
        "project_code": p["code"],
        "intake_id": p["intake"],
        "name": p["name"],
        "description": p["desc"],
        "business_value": p["value"],
        "sponsor_person_id": P[p["sponsor"]],
        "sponsor_name": p["sponsor"],
        "project_manager_id": P[p["pm"]],
        "project_manager_name": p["pm"],
        "primary_department": p["dept"],
        "approach": p["approach"],
        "lifecycle_phase": p["phase"],
        "status": p["status"],
        "planned_start": p["ps"],
        "planned_finish": p["pf"],
        "actual_start": p["as_"],
        "actual_finish": p["af"],
        "budget_total": f"{p['budget']:.2f}",
        "strategic_objective_ref": p["obj"],
    })
write("project", proj_rows, list(proj_rows[0].keys()))
PR = {p["code"]: uid("project", p["code"]) for p in PROJECTS}

# ----------------------------------------------------------------------- WBS
# Per project: level-1 deliverables, each with level-2 work packages.
WBS_PLAN = {
    "THG-CLN-014": [
        ("Study Design & Protocol", "Clinical / Medical Affairs",
         ["Protocol development", "IRB submissions"]),
        ("Site Activation", "Clinical / Medical Affairs",
         ["Site selection", "Site contracts", "Site training"]),
        ("Enrollment & Data Collection", "Clinical / Medical Affairs",
         ["Patient recruitment", "Device deployment", "Data monitoring"]),
        ("Regulatory & Compliance", "Regulatory / Quality",
         ["Part 11 evidence", "Safety reporting"]),
        ("Analysis & Reporting", "R&D / Engineering",
         ["Interim analysis", "Final study report"]),
    ],
    "THG-RND-007": [
        ("Architecture & Design", "R&D / Engineering",
         ["Platform architecture", "Therapy module API"]),
        ("Core Firmware Build", "R&D / Engineering",
         ["Scheduler rewrite", "Driver layer", "Telemetry stack"]),
        ("Verification", "R&D / Engineering",
         ["Unit test harness", "HIL test rig"]),
        ("Design Controls", "Regulatory / Quality",
         ["Design history file", "Risk file (ISO 14971)"]),
    ],
    "THG-IT-003": [
        ("Landing Zone", "IT / Data / Security",
         ["Network & security baseline", "Encryption & key mgmt"]),
        ("Data Migration", "IT / Data / Security",
         ["Source inventory", "Pipeline build", "PHI validation"]),
        ("Access & Audit", "IT / Data / Security",
         ["RBAC model", "Audit trail integration"]),
        ("Cutover & Training", "Operations / PMO",
         ["Parallel run", "Analyst training"]),
    ],
    "THG-OPS-009": [
        ("System Configuration", "Operations / PMO",
         ["Template library setup", "Intake workflow"]),
        ("Department Onboarding", "Operations / PMO",
         ["Pilot departments", "Remaining departments"]),
        ("Training & Competency", "HR / People",
         ["Curriculum build", "Attestation rollout"]),
        ("Adoption & Audit", "Regulatory / Quality",
         ["Usage audits", "Compliance evidence"]),
    ],
    "THG-REG-005": [
        ("Gap Assessment", "Regulatory / Quality",
         ["Internal audit", "Gap remediation plan"]),
        ("Remediation", "Regulatory / Quality",
         ["Document control fixes", "Training records cleanup"]),
        ("Certification Audit", "Regulatory / Quality",
         ["Stage 1 audit", "Stage 2 audit"]),
        ("Closeout", "Operations / PMO",
         ["Findings closure", "Lessons learned"]),
    ],
    "THG-COM-002": [
        ("Market Analysis", "Commercial / Marketing",
         ["Country prioritization", "Pricing study"]),
        ("Regulatory Pathway", "Regulatory / Quality",
         ["CE marking assessment", "Distributor licensing"]),
        ("Launch Readiness", "Commercial / Marketing",
         ["Channel partnerships", "Launch collateral"]),
    ],
}
OWNER_BY_DEPT = {
    "Clinical / Medical Affairs": ["Daniel Okafor", "Sofia Reyes", "Maya Patel"],
    "Regulatory / Quality": ["Anna Lindqvist", "Priya Nair", "James Whitfield"],
    "R&D / Engineering": ["Marcus Chen", "Aiko Tanaka", "Lena Hoffmann"],
    "Operations / PMO": ["Isabel Fonseca", "Tom Becker", "Grace Mwangi"],
    "Finance / Procurement": ["Victor Osei", "Hannah Kim"],
    "Commercial / Marketing": ["Lucas Romero", "Olivia Marsh"],
    "IT / Data / Security": ["Sam Delgado", "Chloe Barnett", "Nadia Hassan"],
    "HR / People": ["Ruth Adler", "Peter Novak"],
}

wbs_rows, act_rows = [], []
for p in PROJECTS:
    code = p["code"]
    pstart, pfinish = d(p["ps"]), d(p["pf"])
    total_days = (pfinish - pstart).days
    n_l1 = len(WBS_PLAN[code])
    for i, (l1name, dept, children) in enumerate(WBS_PLAN[code], 1):
        l1_code = str(i)
        l1_id = uid("wbs", f"{code}/{l1_code}")
        wbs_rows.append({
            "wbs_element_id": l1_id, "project_id": PR[code], "project_code": code,
            "wbs_code": l1_code, "parent_wbs_element_id": "", "level": 1,
            "name": l1name, "owning_department": dept,
            "owner_role": "Workstream Lead",
            "estimated_effort_hrs": "", "estimated_cost": "",
        })
        # time window for this deliverable (sequential-ish with overlap)
        w_start = pstart + timedelta(days=int(total_days * (i - 1) / n_l1 * 0.85))
        w_len = int(total_days / n_l1 * 1.3)
        for j, wpname in enumerate(children, 1):
            wp_code = f"{i}.{j}"
            wp_id = uid("wbs", f"{code}/{wp_code}")
            effort = random.choice([80, 120, 160, 240, 320])
            cost = effort * random.choice([150, 175, 200])
            wbs_rows.append({
                "wbs_element_id": wp_id, "project_id": PR[code], "project_code": code,
                "wbs_code": wp_code, "parent_wbs_element_id": l1_id, "level": 2,
                "name": wpname, "owning_department": dept,
                "owner_role": "Work Package Owner",
                "estimated_effort_hrs": effort, "estimated_cost": f"{cost:.2f}",
            })
            # 2 activities per work package
            for k in range(1, 3):
                a_start = w_start + timedelta(days=int(w_len * (j - 1 + (k - 1) * 0.5) / (len(children) + 1)))
                dur = random.choice([10, 15, 20, 25, 30])
                a_finish = wd(a_start, dur)
                owner = random.choice(OWNER_BY_DEPT[dept])
                # status vs TODAY
                if a_finish < TODAY and p["status"] != "Proposed":
                    if random.random() < 0.82:
                        st, pct = "Done", 100
                        sa, fa = a_start + timedelta(days=random.randint(-2, 3)), a_finish + timedelta(days=random.randint(-3, 6))
                    else:
                        st, pct = "At risk", random.choice([60, 70, 80])
                        sa, fa = a_start + timedelta(days=random.randint(0, 5)), None
                elif a_start <= TODAY <= a_finish and p["status"] != "Proposed":
                    st = "In progress" if random.random() < 0.75 else "At risk"
                    elapsed = (TODAY - a_start).days / max((a_finish - a_start).days, 1)
                    pct = min(95, max(5, int(elapsed * 100) + random.randint(-15, 10)))
                    sa, fa = a_start + timedelta(days=random.randint(-1, 4)), None
                else:
                    st, pct, sa, fa = "Not started", 0, None, None
                act_rows.append({
                    "activity_id": uid("act", f"{code}/{wp_code}-A{k}"),
                    "wbs_element_id": wp_id, "project_id": PR[code], "project_code": code,
                    "activity_code": f"{wp_code}-A{k}",
                    "name": f"{wpname} — {'plan & prepare' if k == 1 else 'execute & verify'}",
                    "start_planned": a_start.isoformat(), "finish_planned": a_finish.isoformat(),
                    "start_actual": sa.isoformat() if sa else "",
                    "finish_actual": fa.isoformat() if fa else "",
                    "duration_days": dur,
                    "owner_person_id": P[owner], "owner_name": owner,
                    "department": dept, "status": st, "pct_complete": pct,
                })
write("wbs_element", wbs_rows, list(wbs_rows[0].keys()))
write("schedule_activity", act_rows, list(act_rows[0].keys()))

# ----------------------------------------------------------------- milestones
MILES = {
    "THG-CLN-014": [("Protocol approved", "2026-03-13", "Achieved"),
                    ("All sites activated", "2026-06-05", "Achieved"),
                    ("First Patient In", "2026-09-01", "At risk"),
                    ("Enrollment complete", "2026-10-30", "On track"),
                    ("Final report issued", "2026-12-11", "On track")],
    "THG-RND-007": [("Architecture baselined", "2025-11-14", "Achieved"),
                    ("Core firmware feature-complete", "2026-04-24", "Slipped"),
                    ("HIL verification complete", "2026-07-17", "At risk"),
                    ("Design freeze", "2026-08-21", "On track")],
    "THG-IT-003": [("Landing zone accepted", "2026-06-26", "On track"),
                   ("Pipeline MVP", "2026-09-04", "On track"),
                   ("PHI validation sign-off", "2026-11-20", "On track"),
                   ("Cutover complete", "2027-01-15", "On track")],
    "THG-OPS-009": [("Templates published", "2026-03-06", "Achieved"),
                    ("Pilot departments live", "2026-05-01", "Achieved"),
                    ("All departments onboarded", "2026-07-31", "At risk"),
                    ("Adoption audit passed", "2026-09-18", "On track")],
    "THG-REG-005": [("Gap assessment complete", "2025-10-03", "Achieved"),
                    ("Remediation complete", "2026-02-27", "Achieved"),
                    ("Stage 2 audit passed", "2026-05-15", "Achieved"),
                    ("Certificate issued", "2026-06-26", "On track")],
    "THG-COM-002": [("Market analysis approved", "2026-10-02", "On track"),
                    ("CE pathway confirmed", "2026-12-18", "On track"),
                    ("Launch go/no-go", "2027-03-26", "On track")],
}
mile_rows = []
for code, items in MILES.items():
    for name, base, st in items:
        bdate = d(base)
        fdate, adate = bdate, ""
        if st == "Achieved":
            slip = random.randint(-2, 4)
            adate = (bdate + timedelta(days=slip)).isoformat()
            fdate = bdate + timedelta(days=slip)
        elif st == "Slipped":
            fdate = bdate + timedelta(days=random.randint(14, 28))
        elif st == "At risk":
            fdate = bdate + timedelta(days=random.randint(5, 12))
        mile_rows.append({
            "milestone_id": uid("mile", f"{code}/{name}"),
            "project_id": PR[code], "project_code": code, "name": name,
            "baseline_date": base, "forecast_date": fdate.isoformat(),
            "actual_date": adate, "status": st, "owner_role": "Project Manager",
        })
write("milestone", mile_rows, list(mile_rows[0].keys()))

# ---------------------------------------------------------------- budget lines
bud_rows = []
CATS = ["Labor", "Materials", "Vendor", "Other"]
for p in PROJECTS:
    code = p["code"]
    l1s = [w for w in wbs_rows if w["project_code"] == code and w["level"] == 1]
    weights = [random.uniform(0.6, 1.4) for _ in l1s]
    wsum = sum(weights)
    target = p["budget"] / 1.10  # totals include 10% contingency
    for w1, wt in zip(l1s, weights):
        alloc = target * wt / wsum
        labor = alloc * random.uniform(0.45, 0.7)
        mats = alloc * random.uniform(0.05, 0.2)
        vend = alloc * random.uniform(0.1, 0.35)
        other = max(alloc - labor - mats - vend, 0)
        subtotal = labor + mats + vend + other
        cont = 10.0
        bud_rows.append({
            "budget_line_id": uid("bud", f"{code}/{w1['wbs_code']}"),
            "wbs_element_id": w1["wbs_element_id"],
            "project_id": PR[code], "project_code": code,
            "wbs_code": w1["wbs_code"], "wbs_name": w1["name"],
            "category": "Labor" if labor >= max(mats, vend, other) else "Vendor",
            "labor_amount": f"{labor:.2f}", "materials_amount": f"{mats:.2f}",
            "vendor_amount": f"{vend:.2f}", "other_amount": f"{other:.2f}",
            "subtotal": f"{subtotal:.2f}", "contingency_pct": f"{cont:.2f}",
            "total": f"{subtotal * (1 + cont / 100):.2f}",
            "funding_source": random.choice(["OpEx", "OpEx", "CapEx", "Grant"]),
        })
write("budget_line_item", bud_rows, list(bud_rows[0].keys()))

# ---------------------------------------------------------------------- risks
RISK_BANK = [
    ("Regulatory", "Regulatory submission rejected or delayed by FDA feedback cycle", "FDA 21 CFR Part 11"),
    ("Schedule", "Key resource availability conflicts with parallel programs", ""),
    ("Technical", "Integration defects discovered late in verification", ""),
    ("Vendor", "Vendor deliverable slips beyond contractual window", ""),
    ("Cost", "Material costs exceed estimate due to supplier price increases", ""),
    ("People", "Attrition of specialized engineering talent mid-project", ""),
    ("Safety", "Adverse event reporting threshold reached during study", "GxP"),
    ("Regulatory", "HIPAA audit finding on access controls", "HIPAA"),
    ("Technical", "Data migration validation uncovers PHI mapping errors", "HIPAA"),
    ("Schedule", "Site activation slower than planned in two regions", ""),
    ("Reputational", "Negative trial publicity affects enrollment", ""),
    ("Cost", "Currency exposure on EU vendor contracts", ""),
]
risk_rows, resp_rows = [], []
rk = 0
for p in PROJECTS:
    code = p["code"]
    n = {"Initiating": 4, "Planning": 6, "Executing": 7, "Monitoring": 5, "Closing": 4}[p["phase"]]
    picks = random.sample(RISK_BANK, n)
    for idx, (cat, desc, frame) in enumerate(picks, 1):
        rk += 1
        L = random.randint(1, 5)
        I = random.randint(2, 5)
        score = L * I
        status = random.choices(
            ["Open", "Mitigating", "Monitoring", "Closed", "Realized"],
            weights=[25, 30, 20, 20, 5])[0]
        if p["phase"] == "Closing":
            status = random.choices(["Closed", "Monitoring"], weights=[70, 30])[0]
        resid = max(1, score - random.randint(2, 10)) if status in ("Mitigating", "Monitoring", "Closed") else ""
        dept = random.choice([p["dept"], p["dept"], "Regulatory / Quality", "Operations / PMO"])
        owner = random.choice(OWNER_BY_DEPT[dept])
        due = TODAY + timedelta(days=random.randint(-40, 90)) if status in ("Open", "Mitigating") else ""
        risk_rows.append({
            "risk_id": uid("risk", f"{code}/R{idx:03d}"),
            "project_id": PR[code], "project_code": code,
            "risk_code": f"R-{idx:03d}", "category": cat, "description": desc,
            "trigger": "", "likelihood": L, "impact": I, "score": score,
            "response_type": random.choice(["Mitigate", "Mitigate", "Avoid", "Transfer", "Accept"]),
            "owner_person_id": P[owner], "owner_name": owner, "department": dept,
            "due_date": due.isoformat() if due else "", "status": status,
            "residual_score": resid,
            "compliance_flag": frame if frame else "None",
        })
        if status in ("Open", "Mitigating", "Monitoring"):
            for ai in range(1, random.randint(2, 3)):
                ast = random.choices(["Open", "In progress", "Done", "Blocked"],
                                     weights=[30, 40, 25, 5])[0]
                resp_rows.append({
                    "response_id": uid("resp", f"{code}/R{idx:03d}/{ai}"),
                    "risk_id": uid("risk", f"{code}/R{idx:03d}"),
                    "project_code": code, "risk_code": f"R-{idx:03d}",
                    "action_type": random.choice(["Mitigation", "Mitigation", "Transfer", "Avoidance"]),
                    "description": f"Mitigation action {ai} for {cat.lower()} risk",
                    "owner_person_id": P[owner], "owner_name": owner,
                    "due_date": (TODAY + timedelta(days=random.randint(-20, 75))).isoformat(),
                    "status": ast,
                })
write("risk", risk_rows, list(risk_rows[0].keys()))
write("risk_response", resp_rows, list(resp_rows[0].keys()))

# -------------------------------------------------------------- change requests
CR_BANK = [
    ("Scope", "Add third-party device telemetry export to deliverable set", "Sponsor request following payer feedback"),
    ("Schedule", "Extend verification window for additional HIL cycles", "Defect burn-down slower than planned"),
    ("Cost", "Additional vendor budget for accelerated site contracts", "Site activation delays"),
    ("Quality", "Adopt revised risk file template per ISO 14971:2019", "Audit readiness"),
    ("Compliance", "Add Part 11 audit trail export to reporting module", "Regulatory pre-screen finding"),
    ("Scope", "Defer secondary endpoint analytics to Phase 2", "Budget pressure"),
]
cr_rows = []
crn = 0
for p in PROJECTS:
    code = p["code"]
    n = {"Initiating": 1, "Planning": 2, "Executing": 4, "Monitoring": 3, "Closing": 2}[p["phase"]]
    pstart = d(p["ps"])
    for idx in range(1, n + 1):
        crn += 1
        ctype, desc, reason = random.choice(CR_BANK)
        req_at = pstart + timedelta(days=random.randint(30, max(35, (min(TODAY, d(p["pf"])) - pstart).days - 10)))
        decision = random.choices(["Approved", "Rejected", "Deferred", "Pending"],
                                  weights=[55, 15, 10, 20])[0]
        cycle = random.randint(5, 35)
        dec_at = req_at + timedelta(days=cycle) if decision != "Pending" else None
        if dec_at and dec_at > TODAY:
            decision, dec_at = "Pending", None
        status = {"Approved": random.choice(["Implementing", "Verified", "Closed"]),
                  "Rejected": "Rejected", "Deferred": "Open",
                  "Pending": random.choice(["Open", "In Assessment"])}[decision]
        cost_imp = random.choice([0, 0, 8000, 12000, 15000, 25000, -10000]) if ctype in ("Scope", "Cost", "Schedule") else 0
        sched_imp = random.choice([0, 0, 5, 10, 15, -5]) if ctype in ("Scope", "Schedule") else 0
        requester = random.choice(list(P.keys()))
        cr_rows.append({
            "cr_id": uid("cr", f"{code}/C{idx:03d}"),
            "project_id": PR[code], "project_code": code,
            "cr_code": f"C-{idx:03d}",
            "intake_id": p["intake"],
            "requested_at": req_at.isoformat(),
            "requested_by_person_id": P[requester], "requested_by_name": requester,
            "cr_class": random.choices(["A - Minor", "B - Substantive", "C - Controlling", "Emergency / Safety"],
                                       weights=[35, 45, 15, 5])[0],
            "change_types": ctype,
            "description": desc, "reason": reason,
            "impact_schedule_days": sched_imp,
            "impact_cost": f"{cost_imp:.2f}",
            "decision": decision,
            "decided_at": dec_at.isoformat() if dec_at else "",
            "cycle_time_days": cycle if dec_at else "",
            "status": status,
        })
write("change_request", cr_rows, list(cr_rows[0].keys()))

# -------------------------------------------------------------- status reports
KAS = ["Scope", "Schedule", "Cost", "Quality", "Risk", "Stakeholders", "Compliance",
       "Procurement", "Communications"]
sr_rows, sra_rows = [], []
for p in PROJECTS:
    if p["status"] == "Proposed":
        continue
    code = p["code"]
    start = d(p["as_"] or p["ps"])
    end = min(TODAY, d(p["pf"]))
    period = start
    rn = 0
    while period + timedelta(days=27) <= end:
        rn += 1
        p_end = period + timedelta(days=27)
        # health degrades for projects with slipped milestones
        bias = {"THG-RND-007": 1.0, "THG-CLN-014": 0.5, "THG-OPS-009": 0.6}.get(code, 0.25)
        statuses = []
        for ka in KAS:
            r = random.random() + (bias * 0.35 if ka in ("Schedule", "Risk", "Cost") else 0)
            ka_st = "Red" if r > 1.12 else ("Yellow" if r > 0.78 else "Green")
            statuses.append((ka, ka_st))
        worst = "Red" if any(s == "Red" for _, s in statuses) else (
            "Yellow" if sum(1 for _, s in statuses if s == "Yellow") >= 2 else "Green")
        overall = worst
        trend = random.choices(["Improving", "Steady", "Worsening"], weights=[30, 50, 20])[0]
        rid = uid("sr", f"{code}/{rn}")
        sr_rows.append({
            "report_id": rid, "project_id": PR[code], "project_code": code,
            "report_number": rn,
            "period_start": period.isoformat(), "period_end": p_end.isoformat(),
            "overall_status": overall, "trend": trend,
            "executive_summary": f"Period {rn}: execution {'on plan' if overall == 'Green' else 'with attention areas'} for {p['name']}.",
            "decisions_needed": "" if random.random() < 0.6 else "Steering decision required on pending change request",
            "submitted_by_person_id": P[p["pm"]], "submitted_by_name": p["pm"],
            "submitted_at": (p_end + timedelta(days=2)).isoformat(),
        })
        for ka, ka_st in statuses:
            sra_rows.append({
                "area_id": uid("sra", f"{code}/{rn}/{ka}"),
                "report_id": rid, "project_code": code,
                "knowledge_area": ka, "status": ka_st,
                "commentary": "",
            })
        period = p_end + timedelta(days=1)
write("status_report", sr_rows, list(sr_rows[0].keys()))
write("status_report_area", sra_rows, list(sra_rows[0].keys()))

# ---------------------------------------------------------------- stakeholders
stk_rows = []
for p in PROJECTS:
    code = p["code"]
    n = random.randint(5, 8)
    people = random.sample(list(P.keys()), n)
    for i, person in enumerate(people, 1):
        pd = next(r for r in person_rows if r["display_name"] == person)
        eng = random.choices(["R", "A", "C", "I"], weights=[25, 10, 30, 35])[0]
        stk_rows.append({
            "stakeholder_id": uid("stk", f"{code}/{i}"),
            "project_id": PR[code], "project_code": code,
            "stk_code": f"S-{i:03d}",
            "person_id": pd["person_id"], "stakeholder_name": person,
            "role": pd["role_title"],
            "department": pd["department_name"],
            "engagement": eng,
            "interest": random.choices(["High", "Medium", "Low"], weights=[40, 40, 20])[0],
            "influence": random.choices(["High", "Medium", "Low"], weights=[35, 40, 25])[0],
            "communication_preference": random.choice(["Email", "Teams", "Meeting", "Dashboard"]),
        })
write("stakeholder", stk_rows, list(stk_rows[0].keys()))

# ---------------------------------------------------------------- team members
tm_rows = []
for p in PROJECTS:
    code = p["code"]
    pool = OWNER_BY_DEPT[p["dept"]] + random.sample(list(P.keys()), 4)
    seen = set()
    for person in pool:
        if person in seen or person in (p["pm"],):
            continue
        seen.add(person)
        pd = next(r for r in person_rows if r["display_name"] == person)
        tm_rows.append({
            "team_member_id": uid("tm", f"{code}/{person}"),
            "project_id": PR[code], "project_code": code,
            "person_id": pd["person_id"], "member_name": person,
            "role": pd["role_title"], "department": pd["department_name"],
            "allocation_pct": random.choice([15, 25, 25, 50, 50, 75, 100]),
            "start_date": p["ps"], "end_date": "",
        })
    # the PM at high allocation
    pmd = next(r for r in person_rows if r["display_name"] == p["pm"])
    tm_rows.append({
        "team_member_id": uid("tm", f"{code}/{p['pm']}"),
        "project_id": PR[code], "project_code": code,
        "person_id": pmd["person_id"], "member_name": p["pm"],
        "role": "Project Manager", "department": pmd["department_name"],
        "allocation_pct": 75, "start_date": p["ps"], "end_date": "",
    })
write("project_team_member", tm_rows, list(tm_rows[0].keys()))

# -------------------------------------------------------------------- lessons
LESSON_BANK = [
    ("Process", "Intake triage SLA needs a fast lane for compliance-flagged requests",
     "Compliance pre-screen added 8 days to urgent intake", "Add expedited triage path to SOP-002"),
    ("Tools", "Template version drift caused rework in two departments",
     "Teams used cached older templates", "Enforce template fetch from controlled library"),
    ("Team", "Cross-department RACI clarified late, slowed early decisions",
     "RACI agreed only after phase 1", "Baseline RACI at charter approval"),
    ("Vendor", "Vendor onboarding security review took longer than planned",
     "4-week security review on critical path", "Start vendor reviews at contract signature"),
    ("Regulatory", "Part 11 evidence collection should start at execution, not closing",
     "Evidence assembly compressed at audit", "Collect signatures and audit trail exports monthly"),
    ("Process", "Bi-weekly steering cadence too slow during execution peaks",
     "Decisions queued up to 3 weeks", "Move to weekly steering during execution"),
]
les_rows = []
for p in PROJECTS:
    if p["phase"] in ("Initiating",):
        continue
    code = p["code"]
    n = {"Planning": 1, "Executing": 2, "Monitoring": 3, "Closing": 5}.get(p["phase"], 1)
    for i, (cat, lesson, what, rec) in enumerate(random.sample(LESSON_BANK, n), 1):
        les_rows.append({
            "lesson_id": uid("les", f"{code}/{i}"),
            "project_id": PR[code], "project_code": code,
            "category": cat, "lesson": lesson,
            "what_happened": what, "recommendation": rec,
            "followup_owner_role": "PMO Director",
            "status": random.choices(["Open", "Addressed", "Adopted", "Archived"],
                                     weights=[35, 30, 25, 10])[0],
        })
write("lesson_learned", les_rows, list(les_rows[0].keys()))

# ------------------------------------------------------------- closure items
CLOSURE_BANK = [
    "All deliverables accepted by sponsor", "Final budget reconciliation complete",
    "Vendor contracts closed out", "Project documentation baselined in DM system",
    "Lessons learned captured and filed", "Team members released and reassigned",
    "Audit evidence pack assembled", "Final status report issued",
    "Closure approval signatures obtained", "Records retention schedule applied",
]
cls_rows = []
for p in PROJECTS:
    if p["phase"] not in ("Monitoring", "Closing"):
        continue
    code = p["code"]
    done_rate = 0.85 if p["phase"] == "Closing" else 0.2
    for i, item in enumerate(CLOSURE_BANK, 1):
        done = random.random() < done_rate
        cls_rows.append({
            "closure_item_id": uid("cls", f"{code}/{i}"),
            "project_id": PR[code], "project_code": code,
            "item": item, "owner_role": "Project Manager",
            "done": "TRUE" if done else "FALSE",
            "evidence": "DM document link" if done else "",
        })
write("closure_checklist_item", cls_rows, list(cls_rows[0].keys()))

# -------------------------------------------------------------- knowledge areas
write("knowledge_area", [{"knowledge_area": k, "sort_order": i} for i, k in enumerate(KAS, 1)],
      ["knowledge_area", "sort_order"])

print("\nSample data generated in", OUT)
