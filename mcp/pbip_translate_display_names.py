"""
Reusable Power BI .pbip nativeQueryRef → displayName translator.

Usage:
  python pbip_translate_display_names.py <report_pages_dir> <translation_map.json> [--dry-run]

Arguments:
  report_pages_dir   Path to the report's definition/pages folder
  translation_map    JSON file with {"nativeQueryRef": "displayName"} mappings
  --dry-run          Show what would change without writing files

The translation map JSON should have two keys:
  "translations": {"English Value": "Swedish Value", ...}
  "skip": ["AlreadySwedish", "InternalMeasure", ...]

To generate a starter map from a report, use --scan mode:
  python pbip_translate_display_names.py <report_pages_dir> --scan > starter_map.json
"""

import json
import os
import sys
import glob
import argparse


def scan_report(pages_dir: str) -> dict:
    """Scan report and return all unique nativeQueryRef values with counts."""
    refs = {}
    pattern = os.path.join(pages_dir, "**", "visual.json")
    for file_path in glob.glob(pattern, recursive=True):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        query_state = data.get("visual", {}).get("query", {}).get("queryState", {})
        for bucket in query_state.values():
            if isinstance(bucket, dict) and "projections" in bucket:
                for proj in bucket["projections"]:
                    nqr = proj.get("nativeQueryRef")
                    if nqr:
                        has_dn = "displayName" in proj
                        if nqr not in refs:
                            refs[nqr] = {"count": 0, "has_displayName": 0}
                        refs[nqr]["count"] += 1
                        if has_dn:
                            refs[nqr]["has_displayName"] += 1

    # Build starter map
    starter = {
        "translations": {},
        "skip": []
    }
    for nqr, info in sorted(refs.items()):
        starter["translations"][nqr] = f"TODO: {nqr} (appears {info['count']}x, {info['has_displayName']} already have displayName)"

    return starter


def process_projections(projections, translations, skip_set, file_path, stats):
    """Add displayName to projections that need translation."""
    modified = False
    for proj in projections:
        nqr = proj.get("nativeQueryRef")
        if not nqr:
            continue

        if "displayName" in proj:
            # Also fix existing English displayName values
            existing_dn = proj["displayName"]
            if existing_dn in translations:
                translation = translations[existing_dn]
                if translation != existing_dn and not translation.startswith("TODO:"):
                    proj["displayName"] = translation
                    stats["translated"] += 1
                    visual_id = os.path.basename(os.path.dirname(file_path))
                    stats["details"].append(f"  displayName fix: {existing_dn} -> {translation}  [{visual_id}]")
                    modified = True
                    continue
            stats["already_has_displayName"] += 1
            continue

        if nqr in skip_set:
            stats["skipped"] += 1
            continue

        if nqr in translations:
            translation = translations[nqr]
            if translation == nqr or translation.startswith("TODO:"):
                stats["skipped"] += 1
                continue
            proj["displayName"] = translation
            stats["translated"] += 1
            visual_id = os.path.basename(os.path.dirname(file_path))
            stats["details"].append(f"  {nqr} -> {translation}  [{visual_id}]")
            modified = True
        else:
            stats["unmapped"].add(nqr)

    return modified


def translate_report(pages_dir: str, translations: dict, skip_set: set, dry_run: bool = False):
    """Walk all visual.json files and inject displayName translations."""
    stats = {
        "files_scanned": 0,
        "files_modified": 0,
        "translated": 0,
        "already_has_displayName": 0,
        "skipped": 0,
        "unmapped": set(),
        "errors": [],
        "details": [],
    }

    pattern = os.path.join(pages_dir, "**", "visual.json")
    files = glob.glob(pattern, recursive=True)
    print(f"Found {len(files)} visual.json files")

    for file_path in sorted(files):
        stats["files_scanned"] += 1
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            stats["errors"].append(f"Error reading {file_path}: {e}")
            continue

        query_state = data.get("visual", {}).get("query", {}).get("queryState", {})
        if not query_state:
            continue

        modified = False
        for bucket in query_state.values():
            if isinstance(bucket, dict) and "projections" in bucket:
                if process_projections(bucket["projections"], translations, skip_set, file_path, stats):
                    modified = True

        if modified and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write('\n')
            stats["files_modified"] += 1
        elif modified:
            stats["files_modified"] += 1

    return stats


def print_stats(stats):
    """Print translation results."""
    print(f"\n=== RESULTS ===")
    print(f"Files scanned: {stats['files_scanned']}")
    print(f"Files modified: {stats['files_modified']}")
    print(f"Translations added: {stats['translated']}")
    print(f"Already had displayName: {stats['already_has_displayName']}")
    print(f"Skipped: {stats['skipped']}")

    if stats["unmapped"]:
        print(f"\nUNMAPPED values ({len(stats['unmapped'])}):")
        for val in sorted(stats["unmapped"]):
            print(f"  - {val}")

    if stats["errors"]:
        print(f"\nERRORS ({len(stats['errors'])}):")
        for err in stats["errors"]:
            print(f"  {err}")


def main():
    parser = argparse.ArgumentParser(description="Translate Power BI report nativeQueryRef to displayName")
    parser.add_argument("pages_dir", help="Path to report's definition/pages folder")
    parser.add_argument("translation_map", nargs="?", help="JSON file with translation mappings")
    parser.add_argument("--scan", action="store_true", help="Scan mode: output starter translation map")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")

    args = parser.parse_args()

    if not os.path.isdir(args.pages_dir):
        print(f"Error: {args.pages_dir} is not a directory")
        sys.exit(1)

    if args.scan:
        starter = scan_report(args.pages_dir)
        print(json.dumps(starter, indent=2, ensure_ascii=False))
        return

    if not args.translation_map:
        print("Error: translation_map required (or use --scan)")
        sys.exit(1)

    with open(args.translation_map, 'r', encoding='utf-8') as f:
        map_data = json.load(f)

    translations = map_data.get("translations", {})
    skip_set = set(map_data.get("skip", []))

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"Mode: {mode}")
    print(f"Translations loaded: {len(translations)}")
    print(f"Skip list: {len(skip_set)} entries")

    stats = translate_report(args.pages_dir, translations, skip_set, args.dry_run)
    print_stats(stats)


if __name__ == "__main__":
    main()
