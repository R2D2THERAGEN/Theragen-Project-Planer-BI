#!/usr/bin/env python3
"""
Fix auto-generated visual titles and slicer headers in Power BI .pbip reports.

When a visual has title.show=true (or default) but no custom text,
Power BI auto-generates the title from English model property names.
This script injects translated titles based on the projection displayName values.

Also fixes slicer header text (objects.header[].properties.text).

Usage:
    python pbip_fix_visual_titles.py <pages_dir> <translation_map> --scan
    python pbip_fix_visual_titles.py <pages_dir> <translation_map> --dry-run
    python pbip_fix_visual_titles.py <pages_dir> <translation_map> --execute
"""
import json
import sys
import os
import glob
import argparse
from pathlib import Path


def load_translation_map(map_path: str) -> dict:
    """Load translation map from JSON file."""
    with open(map_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("translations", {})


def get_title_status(visual_data: dict) -> tuple:
    """
    Check if visual needs a title fix.

    Returns: (needs_fix: bool, reason: str, title_props: dict_or_None)
    """
    vco = visual_data.get("visual", {}).get("visualContainerObjects", {})
    title_list = vco.get("title", [])

    if not title_list:
        # No title section at all -> PBI shows auto-generated title
        return True, "no_title_section", None

    props = title_list[0].get("properties", {})

    # Check if title is hidden
    show = props.get("show", {})
    show_val = show.get("expr", {}).get("Literal", {}).get("Value", None)
    if show_val == "false":
        return False, "hidden", props

    # Check if custom text already exists
    if "text" in props:
        text_val = props["text"].get("expr", {}).get("Literal", {}).get("Value", "")
        return False, f"has_text: {text_val}", props

    # Title is visible (show=true or not set) but no text
    if show_val == "true":
        return True, "show_true_no_text", props
    else:
        # show property not set -> defaults to visible
        return True, "no_show_property", props


def get_visual_fields(visual_data: dict) -> dict:
    """Extract field info from projections. Returns dict of role -> list of {name, displayName}."""
    query_state = visual_data.get("visual", {}).get("query", {}).get("queryState", {})
    fields = {}

    for role, role_data in query_state.items():
        projections = role_data.get("projections", [])
        field_list = []
        for proj in projections:
            native = proj.get("nativeQueryRef", "")
            display = proj.get("displayName", native)
            field_list.append({"native": native, "display": display})
        if field_list:
            fields[role] = field_list

    return fields


def generate_swedish_title(visual_type: str, fields: dict, translations: dict) -> str | None:
    """Generate a Swedish title based on visual type and fields."""
    value_names = []
    axis_names = []
    row_names = []
    column_names = []

    for role, field_list in fields.items():
        for f in field_list:
            name = f["display"]
            # Translate if still English
            if name in translations:
                name = translations[name]

            if role == "Values":
                value_names.append(name)
            elif role in ("Category", "X", "Series", "Axis"):
                axis_names.append(name)
            elif role == "Rows":
                row_names.append(name)
            elif role == "Columns":
                column_names.append(name)
            else:
                value_names.append(name)

    if visual_type in ("card", "multiRowCard", "kpi"):
        return " och ".join(value_names) if value_names else None

    elif visual_type in ("barChart", "columnChart", "lineChart", "clusteredBarChart",
                          "clusteredColumnChart", "stackedBarChart", "stackedColumnChart",
                          "lineStackedColumnComboChart", "lineClusteredColumnComboChart",
                          "areaChart", "stackedAreaChart", "waterfallChart", "funnel",
                          "hundredPercentStackedBarChart", "hundredPercentStackedColumnChart"):
        val = " och ".join(value_names) if value_names else ""
        ax = " och ".join(axis_names) if axis_names else ""
        if val and ax:
            return f"{val} per {ax}"
        return val or ax or None

    elif visual_type in ("pivotTable",):
        parts = []
        if value_names:
            parts.append(", ".join(value_names))
        if row_names:
            parts.append("per " + " och ".join(row_names))
        if column_names:
            parts.append("och " + " och ".join(column_names))
        return " ".join(parts) if parts else None

    elif visual_type in ("tableEx",):
        all_names = value_names + row_names + column_names + axis_names
        return ", ".join(all_names) if all_names else None

    elif visual_type in ("slicer",):
        all_names = value_names + axis_names + row_names + column_names
        return " och ".join(all_names) if all_names else None

    elif visual_type in ("donutChart", "pieChart", "treemap"):
        val = " och ".join(value_names) if value_names else ""
        ax = " och ".join(axis_names) if axis_names else ""
        if val and ax:
            return f"{val} per {ax}"
        return val or ax or None

    elif visual_type in ("scatterChart",):
        return " och ".join(value_names) if value_names else None

    else:
        all_names = value_names + axis_names + row_names + column_names
        return ", ".join(all_names) if all_names else None


def get_slicer_header_issues(visual_data: dict, translations: dict) -> list:
    """
    Check slicer header text for English values.

    Returns list of dicts with 'current_text' and 'translated_text'.
    """
    visual_type = visual_data.get("visual", {}).get("visualType",
                   visual_data.get("visualType", ""))
    if visual_type != "slicer":
        return []

    issues = []
    objects = visual_data.get("visual", {}).get("objects", {})
    for header_obj in objects.get("header", []):
        text_expr = header_obj.get("properties", {}).get("text", {}).get("expr", {}).get("Literal", {}).get("Value")
        if text_expr:
            clean_text = text_expr.strip("'")
            if clean_text in translations:
                issues.append({
                    "current_text": clean_text,
                    "translated_text": translations[clean_text]
                })
    return issues


def fix_slicer_headers(visual_data: dict, translations: dict) -> bool:
    """Fix slicer header text in-place. Returns True if changed."""
    issues = get_slicer_header_issues(visual_data, translations)
    if not issues:
        return False

    objects = visual_data.get("visual", {}).get("objects", {})
    for header_obj in objects.get("header", []):
        text_expr = header_obj.get("properties", {}).get("text", {}).get("expr", {}).get("Literal", {}).get("Value")
        if text_expr:
            clean_text = text_expr.strip("'")
            if clean_text in translations:
                header_obj["properties"]["text"]["expr"]["Literal"]["Value"] = f"'{translations[clean_text]}'"

    return True


def process_visual(visual_path: str, translations: dict, mode: str = "scan") -> tuple:
    """Process a single visual.json file. Returns (changed, info_dict)."""
    with open(visual_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    needs_fix, reason, title_props = get_title_status(data)
    slicer_issues = get_slicer_header_issues(data, translations)

    if not needs_fix and not slicer_issues:
        return False, {"path": visual_path, "reason": reason}

    visual_type = data.get("visual", {}).get("visualType",
                   data.get("visualType", "unknown"))
    fields = get_visual_fields(data)
    title = generate_swedish_title(visual_type, fields, translations) if needs_fix else None

    if not title and not slicer_issues:
        return False, {"path": visual_path, "reason": "no_fields_found", "visual_type": visual_type}

    info = {
        "path": visual_path,
        "reason": reason,
        "visual_type": visual_type,
        "generated_title": title,
        "fields": {role: [f["display"] for f in fl] for role, fl in fields.items()},
        "slicer_header_fixes": slicer_issues,
    }

    if mode == "execute":
        changed = False

        # Fix title
        if needs_fix and title:
            vco = data.get("visual", {}).get("visualContainerObjects", {})

            if reason == "no_title_section":
                if "visualContainerObjects" not in data.get("visual", {}):
                    data["visual"]["visualContainerObjects"] = {}
                data["visual"]["visualContainerObjects"]["title"] = [
                    {
                        "properties": {
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": f"'{title}'"
                                    }
                                }
                            }
                        }
                    }
                ]
            else:
                title_list = vco["title"]
                props = title_list[0].get("properties", {})
                props["text"] = {
                    "expr": {
                        "Literal": {
                            "Value": f"'{title}'"
                        }
                    }
                }
                title_list[0]["properties"] = props
            changed = True

        # Fix slicer headers
        if slicer_issues:
            fix_slicer_headers(data, translations)
            changed = True

        if changed:
            with open(visual_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")

        return True, info

    return True, info


def main():
    parser = argparse.ArgumentParser(
        description="Fix auto-generated visual titles and slicer headers in Power BI .pbip reports"
    )
    parser.add_argument("pages_dir", help="Path to report's definition/pages folder")
    parser.add_argument("translation_map", help="Path to translation map JSON file")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", action="store_true", help="Show what needs fixing")
    group.add_argument("--dry-run", action="store_true", help="Show what would change")
    group.add_argument("--execute", action="store_true", help="Apply changes")
    args = parser.parse_args()

    if not os.path.isdir(args.pages_dir):
        print(f"Error: pages_dir not found: {args.pages_dir}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.translation_map):
        print(f"Error: translation_map not found: {args.translation_map}", file=sys.stderr)
        sys.exit(1)

    translations = load_translation_map(args.translation_map)
    mode = "scan" if args.scan else ("dry-run" if args.dry_run else "execute")

    visual_files = glob.glob(os.path.join(args.pages_dir, "**", "visual.json"), recursive=True)
    print(f"Found {len(visual_files)} visual files")

    needs_fix = []
    already_ok = []
    fixed = []

    for vf in sorted(visual_files):
        changed, info = process_visual(vf, translations, mode)
        if changed:
            needs_fix.append(info)
            if mode == "execute":
                fixed.append(info)
        else:
            already_ok.append(info)

    if args.scan:
        print(f"\n=== NEEDS FIX: {len(needs_fix)} visuals ===")
        for item in needs_fix:
            rel = os.path.relpath(item["path"], args.pages_dir)
            print(f"  {rel}")
            print(f"    Type: {item['visual_type']}, Reason: {item['reason']}")
            if item.get("generated_title"):
                print(f"    Title would be: {item['generated_title']}")
            print(f"    Fields: {item.get('fields', {})}")
            if item.get("slicer_header_fixes"):
                for sh in item["slicer_header_fixes"]:
                    print(f"    Slicer header: '{sh['current_text']}' -> '{sh['translated_text']}'")
            print()

    elif args.dry_run:
        print(f"\n=== WOULD FIX: {len(needs_fix)} visuals ===")
        for item in needs_fix:
            rel = os.path.relpath(item["path"], args.pages_dir)
            print(f"  {rel}")
            print(f"    Type: {item['visual_type']}")
            if item.get("generated_title"):
                print(f"    Title: '{item['generated_title']}'")
            if item.get("slicer_header_fixes"):
                for sh in item["slicer_header_fixes"]:
                    print(f"    Slicer header: '{sh['current_text']}' -> '{sh['translated_text']}'")
            print()

    elif args.execute:
        print(f"\n=== FIXED: {len(fixed)} visuals ===")
        for item in fixed:
            rel = os.path.relpath(item["path"], args.pages_dir)
            parts = []
            if item.get("generated_title"):
                parts.append(f"title='{item['generated_title']}'")
            if item.get("slicer_header_fixes"):
                parts.append(f"{len(item['slicer_header_fixes'])} slicer headers")
            print(f"  {rel}: {', '.join(parts)}")

    print(f"\nSummary: {len(needs_fix)} need fix, {len(already_ok)} already OK")


if __name__ == "__main__":
    main()
