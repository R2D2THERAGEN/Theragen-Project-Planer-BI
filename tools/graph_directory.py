# tools/graph_directory.py
"""Entra org-directory roster pull (sub-stage D, D-T3).

Reads enabled **member** users from Microsoft Graph (`/users`, paged) and returns
the Theragen staff roster. The pure paging + filter logic is split from the Graph
I/O so it is unit-testable without a live token. The department is NOT taken from
Entra (it is 87% blank/inconsistent) -- it's curated in the Staff Directory List;
this module only supplies the roster.

Standalone (read-only):
    python tools/graph_directory.py --count   # roster size + a sample
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_lib as al            # noqa: E402
from graph_client import Graph       # noqa: E402

BASE = "https://graph.microsoft.com/v1.0"
USER_SELECT = "id,displayName,userPrincipalName,mail,accountEnabled,userType,jobTitle"


def collect_members(pages):
    """Pure: flatten the `value` arrays across an iterable of Graph page dicts,
    keeping only enabled members (al.is_enabled_member). Returns a list of users."""
    out = []
    for page in pages:
        for u in page.get("value", []):
            if al.is_enabled_member(u):
                out.append(u)
    return out


def iter_user_pages(graph, page_size=200):
    """Yield each Graph /users page, following @odata.nextLink to exhaustion.
    The nextLink is an absolute URL; strip BASE to a relative path (the params are
    already encoded in it, so the follow-up call sends none)."""
    path = "/users"
    params = {"$select": USER_SELECT, "$top": str(page_size)}
    while path:
        page = graph.get(path, **params)
        yield page
        nxt = page.get("@odata.nextLink", "")
        path = nxt.replace(BASE, "") if nxt else ""
        params = {}


def pull_roster(graph=None, page_size=200):
    """The Theragen staff roster: all enabled member users from Entra."""
    graph = graph or Graph()
    return collect_members(iter_user_pages(graph, page_size))


def main(argv):
    if "--count" in argv:
        roster = pull_roster()
        print(f"enabled-member roster: {len(roster)} users")
        for u in roster[:8]:
            print(f"  {u.get('userPrincipalName')} | {u.get('displayName')} | title={u.get('jobTitle')}")
        return 0
    print("usage: python tools/graph_directory.py --count")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
