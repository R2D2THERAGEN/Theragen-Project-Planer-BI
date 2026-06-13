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
