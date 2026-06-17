"""Tests for tools/sync_directory.py — pure decision logic (no DB/Graph/config)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import sync_directory as sd  # noqa: E402  (import is side-effect-free; config loads in main())


def test_domain_of():
    assert sd.domain_of("A.User@Theragen.COM") == "theragen.com"
    assert sd.domain_of("") == ""
    assert sd.domain_of(None) == ""
    assert sd.domain_of("noatsign") == ""


def test_filter_staff_by_domain():
    roster = [
        {"userPrincipalName": "a@theragen.com", "mail": "a@theragen.com"},
        {"userPrincipalName": "svc@neurotech.us"},
        {"mail": "b@actastim.com", "userPrincipalName": "b@neurotechus.onmicrosoft.com"},  # mail wins
        {"userPrincipalName": "c@onmicrosoft.com"},
    ]
    staff = sd.filter_staff(roster, ["theragen.com", "actastim.com"])
    got = [(u.get("mail") or u.get("userPrincipalName")) for u in staff]
    assert got == ["a@theragen.com", "b@actastim.com"]


def test_classify_persons_insert_enrich_deactivate():
    staff = [
        {"userPrincipalName": "new@theragen.com"},
        {"mail": "Existing@theragen.com", "userPrincipalName": "existing@theragen.com"},
    ]
    existing = {
        "existing@theragen.com": {"person_id": "p1", "source": "sharepoint"},
        "gone@theragen.com": {"person_id": "p2", "source": "entra"},        # left roster -> deactivate
        "sp_only@theragen.com": {"person_id": "p3", "source": "sharepoint"},  # not entra -> untouched
    }
    to_insert, to_enrich, to_deactivate = sd.classify_persons(staff, existing)
    assert [u["userPrincipalName"] for u in to_insert] == ["new@theragen.com"]
    assert to_enrich == [(staff[1], "p1")]
    assert to_deactivate == ["p2"]  # only the entra-sourced absentee


def test_classify_skips_users_without_email():
    to_insert, to_enrich, to_deactivate = sd.classify_persons([{"id": "x"}], {})
    assert to_insert == [] and to_enrich == [] and to_deactivate == []


def test_person_id_for_is_deterministic_and_prefers_object_id():
    assert sd.person_id_for({"id": "obj-1", "userPrincipalName": "x@theragen.com"}) \
        == sd.person_id_for({"id": "obj-1"})                       # keyed on Entra id
    assert sd.person_id_for({"userPrincipalName": "X@Theragen.com"}) \
        == sd.person_id_for({"mail": "x@theragen.com"})            # no id -> normalized-email key


def test_dedupe_by_email_keeps_first_and_drops_blank():
    users = [
        {"id": "a", "mail": "Ryan.Bell@theragen.com"},
        {"id": "b", "userPrincipalName": "ryan.bell@theragen.com"},  # same mailbox, 2nd account -> dropped
        {"id": "c", "mail": "other@theragen.com"},
        {"id": "d"},                                                 # no email -> dropped
    ]
    out = sd.dedupe_by_email(users)
    assert [u["id"] for u in out] == ["a", "c"]
