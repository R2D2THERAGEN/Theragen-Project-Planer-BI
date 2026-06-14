import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import governance_health as gh


def test_all_clear_digest():
    sections = [("Docs overdue", ["doc_id"], []), ("CRs stuck", ["cr_code"], [])]
    out = gh.format_digest(sections)
    assert "0 item(s) need attention across 2 checks." in out
    assert "[ OK ] Docs overdue: none" in out
    assert "[ OK ] CRs stuck: none" in out


def test_populated_section_counts_and_table():
    sections = [("Docs overdue", ["doc_id", "title"],
                 [("THG-X-1", "Charter"), ("THG-X-2", "SOP")])]
    out = gh.format_digest(sections)
    assert "2 item(s) need attention across 1 checks." in out
    assert "[   2 ] Docs overdue" in out
    assert "THG-X-1" in out and "Charter" in out
    assert "doc_id" in out and "title" in out


def test_total_counts_across_sections():
    sections = [("A", ["x"], [("1",), ("2",)]), ("B", ["y"], []),
                ("C", ["z"], [("3",)])]
    assert "3 item(s) need attention across 3 checks." in gh.format_digest(sections)


def test_row_cap_overflow_note():
    rows = [(f"r{i}",) for i in range(gh.MAX_ROWS + 5)]
    out = gh.format_digest([("Many", ["id"], rows)])
    assert "... and 5 more" in out
    # exactly MAX_ROWS data rows rendered (each value starts with r); header
    # "id" and separator lines do not start with "  r".
    assert out.count("\n  r") == gh.MAX_ROWS


def test_stamp_in_header():
    assert "2026-06-14 15:49" in gh.format_digest([], stamp="2026-06-14 15:49")


def test_table_aligns_to_widest_cell():
    out = gh._table(["id", "name"], [("x", "short"), ("yy", "a-longer-name")])
    # the id column pads to width 2 ("yy"); both data rows present
    assert "x  | short" in out
    assert "yy | a-longer-name" in out
