"""Change-control reminder (CL-3) — per docs/change-control-process.md.

WARNS (never blocks) when staged changes touch a change-controlled surface — the
semantic model, a DB migration, the authoring Lists, or the sync code — but
CHANGELOG.md is not also staged. Wired via .githooks/pre-commit; the pure logic
is unit-tested.

Enable the hook once:  git config core.hooksPath .githooks
"""
import re
import subprocess
import sys

# Surfaces that the change-control process says should carry a CHANGELOG entry.
_TRIGGERS = [re.compile(p) for p in (
    r"\.SemanticModel/",            # semantic model TMDL
    r"(^|/)db/[^/]*\.sql$",         # DB migration
    r"create_artifact_lists\.py$",  # authoring Lists
    r"sync_artifacts\.py$",         # sync code
    r"artifact_lib\.py$",           # sync logic
)]


def changelog_reminder(paths):
    """Return the change-controlled paths that should prompt a CHANGELOG.md entry.
    Empty if CHANGELOG.md is among the changes, or nothing change-controlled changed."""
    norm = [p.strip().strip('"') for p in paths]
    if any(p == "CHANGELOG.md" for p in norm):
        return []
    return [p for p in norm if any(t.search(p) for t in _TRIGGERS)]


def _staged():
    out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                         capture_output=True, text=True)
    return [p for p in out.stdout.splitlines() if p.strip()]


def main(argv):
    triggered = changelog_reminder(_staged())
    if triggered:
        print("change-control reminder (warn only — commit proceeds):")
        print("  change-controlled files are staged without a CHANGELOG.md update:")
        for p in triggered[:10]:
            print(f"    - {p}")
        print("  consider adding a CHANGELOG.md entry (docs/change-control-process.md).")
    return 0  # warn mode: never blocks


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
