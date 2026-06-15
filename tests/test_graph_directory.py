"""Tests for tools/graph_directory.py — pure paging + member filtering (no live Graph)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import graph_directory as gd  # noqa: E402


def test_collect_members_filters_across_pages():
    pages = [
        {"value": [
            {"userPrincipalName": "a@theragen.com", "accountEnabled": True, "userType": "Member"},
            {"userPrincipalName": "guest#EXT#", "accountEnabled": True, "userType": "Guest"},
        ], "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=X"},
        {"value": [
            {"userPrincipalName": "b@theragen.com", "accountEnabled": True},   # userType defaults Member
            {"userPrincipalName": "off@theragen.com", "accountEnabled": False, "userType": "Member"},
        ]},
    ]
    upns = [u["userPrincipalName"] for u in gd.collect_members(pages)]
    assert upns == ["a@theragen.com", "b@theragen.com"]  # guest + disabled dropped


def test_collect_members_empty():
    assert gd.collect_members([]) == []
    assert gd.collect_members([{"value": []}]) == []


def test_iter_user_pages_follows_nextlink_and_strips_base():
    calls = []

    class FakeGraph:
        def __init__(self):
            self.n = 0

        def get(self, path, **params):
            calls.append((path, params))
            if self.n == 0:
                self.n += 1
                return {"value": [{"userPrincipalName": "a@theragen.com",
                                   "accountEnabled": True, "userType": "Member"}],
                        "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=ABC"}
            return {"value": [{"userPrincipalName": "b@theragen.com",
                               "accountEnabled": True, "userType": "Member"}]}

    pages = list(gd.iter_user_pages(FakeGraph(), page_size=50))
    assert len(pages) == 2
    # first call: /users with select + top
    assert calls[0][0] == "/users"
    assert calls[0][1]["$top"] == "50"
    assert "id,displayName" in calls[0][1]["$select"]
    # second call: the BASE-stripped relative nextLink, no params (encoded in the link)
    assert calls[1][0] == "/users?$skiptoken=ABC"
    assert calls[1][1] == {}


def test_pull_roster_end_to_end_with_fake_graph():
    class FakeGraph:
        def get(self, path, **params):
            return {"value": [
                {"userPrincipalName": "m@theragen.com", "accountEnabled": True, "userType": "Member"},
                {"userPrincipalName": "g#EXT#", "accountEnabled": True, "userType": "Guest"},
            ]}
    roster = gd.pull_roster(FakeGraph())
    assert [u["userPrincipalName"] for u in roster] == ["m@theragen.com"]
