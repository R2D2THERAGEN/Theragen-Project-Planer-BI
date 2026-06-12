# tools/graph_client.py
"""Delegated Microsoft Graph access for the intake sync.

Auth: MSAL device-code flow with the public Microsoft Graph CLI client id,
token cache persisted next to the DB credentials (both gitignored). First run
prints a device-code prompt once; subsequent runs are silent.
"""
import atexit
import json
import os
import sys

import msal
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "db", ".graph_token_cache.json")
CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph CLI (public)
AUTHORITY = "https://login.microsoftonline.com/organizations"
# Sites.Manage.All is required to CREATE lists/columns (ReadWrite covers items only).
SCOPES = ["Sites.ReadWrite.All", "Sites.Manage.All", "User.Read"]
BASE = "https://graph.microsoft.com/v1.0"


def _raise(r):
    if not r.ok:
        raise requests.HTTPError(f"{r.status_code} {r.reason}: {r.text[:500]}", response=r)


def get_token():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            cache.deserialize(f.read())
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    atexit.register(lambda: open(CACHE, "w", encoding="utf-8").write(cache.serialize())
                    if cache.has_state_changed else None)
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY,
                                       token_cache=cache)
    accounts = app.get_accounts()
    result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
    if not result:
        if not sys.stdin.isatty():
            raise SystemExit(
                "Graph token expired and no console available for device-code "
                "sign-in. Run 'python tools/sync_intake.py --dry-run' once in a "
                "terminal to re-authenticate.")
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
        _raise(r)
        return r.json()

    def post(self, path, body):
        r = self.s.post(f"{BASE}{path}", json=body, timeout=30)
        _raise(r)
        return r.json()

    def patch(self, path, body):
        r = self.s.patch(f"{BASE}{path}", json=body, timeout=30)
        _raise(r)
        return r.json() if r.text else {}
