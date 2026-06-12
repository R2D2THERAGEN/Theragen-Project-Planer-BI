"""Bind PostgreSQL credentials to the published semantic model, run a live
service refresh, and enable the nightly schedule. Uses the signed-in Azure CLI
identity; credentials come from db/.pg.local.json (never printed).

Usage: python tools/service_refresh.py
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "db", ".pg.local.json")))
GROUP = "8a1d65df-8123-4f92-8a5c-a5a40e03355c"  # Playground
DATASET = "e3e1f151-0f7d-4bbe-8428-d74dcfa640d4"  # Theragen Project Planner
BASE = "https://api.powerbi.com/v1.0/myorg"

token = subprocess.run(
    ["az", "account", "get-access-token", "--resource",
     "https://analysis.windows.net/powerbi/api", "--query", "accessToken", "-o", "tsv"],
    capture_output=True, text=True, shell=True).stdout.strip()


def call(method, path, body=None, ok=(200, 202)):
    req = urllib.request.Request(
        f"{BASE}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            data = r.read().decode()
            return r.status, json.loads(data) if data else {}
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


# 1. Locate the PostgreSQL datasource on the dataset.
st, ds = call("GET", f"/groups/{GROUP}/datasets/{DATASET}/datasources")
if st != 200:
    sys.exit(f"datasources lookup failed: {st} {ds}")
pg = next((d for d in ds["value"]
           if d.get("datasourceType", "").lower().startswith("postgre")), None)
if not pg:
    sys.exit(f"no PostgreSQL datasource found - got: "
             f"{[(d.get('datasourceType'), d.get('connectionDetails')) for d in ds['value']]}")
print(f"datasource: {pg['datasourceType']} -> {pg['connectionDetails']}")

# 2. Bind Basic credentials (HTTPS transport; encryption handled by TLS).
cred = {
    "credentialDetails": {
        "credentialType": "Basic",
        "credentials": json.dumps({"credentialData": [
            {"name": "username", "value": CFG["user"]},
            {"name": "password", "value": CFG["password"]}]}),
        "encryptedConnection": "Encrypted",
        "encryptionAlgorithm": "None",
        "privacyLevel": "Organizational",
    }
}
st, body = call("PATCH",
                f"/gateways/{pg['gatewayId']}/datasources/{pg['datasourceId']}", cred)
print(f"credential bind: HTTP {st} {body if st >= 300 else ''}")
if st >= 300:
    sys.exit(1)

# 3. Trigger a refresh and poll to completion.
st, body = call("POST", f"/groups/{GROUP}/datasets/{DATASET}/refreshes",
                {"notifyOption": "NoNotification"})
print(f"refresh trigger: HTTP {st}")
for _ in range(40):
    time.sleep(15)
    st, hist = call("GET", f"/groups/{GROUP}/datasets/{DATASET}/refreshes?$top=1")
    run = hist["value"][0]
    if run["status"] not in ("Unknown", "InProgress"):
        print(f"refresh: {run['status']} "
              f"({run.get('startTime', '?')} -> {run.get('endTime', '?')})")
        if run["status"] != "Completed":
            print(run.get("serviceExceptionJson", ""))
            sys.exit(1)
        break
    print("  refreshing...")
else:
    sys.exit("refresh did not finish in 10 minutes")

# 4. Nightly schedule: 06:00 Eastern, every day, mail on failure.
sched = {"value": {
    "enabled": True,
    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"],
    "times": ["06:00"],
    "localTimeZoneId": "Eastern Standard Time",
    "notifyOption": "MailOnFailure",
}}
st, body = call("PATCH", f"/groups/{GROUP}/datasets/{DATASET}/refreshSchedule", sched)
print(f"schedule: HTTP {st} {body if st >= 300 else '(daily 06:00 ET, mail on failure)'}")
sys.exit(0 if st < 300 else 1)
