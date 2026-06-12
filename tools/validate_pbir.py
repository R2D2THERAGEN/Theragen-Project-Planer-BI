"""Validate every PBIP JSON file (Report + SemanticModel + .pbip) against its
declared $schema (fetched from developer.microsoft.com, cached locally).
Files without a Microsoft $schema are flagged: Desktop's project loader rejects
sidecar JSONs in unversioned formats (e.g. .pbi/editorSettings.json)."""
import json
import os
import sys
import urllib.request

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = [os.path.join(ROOT, "Theragen Project Planner.Report"),
        os.path.join(ROOT, "Theragen Project Planner.SemanticModel"),
        os.path.join(ROOT, "Theragen Project Planner.pbip")]
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".schema_cache")
os.makedirs(CACHE, exist_ok=True)

schemas = {}


def get_schema(url):
    if url in schemas:
        return schemas[url]
    fname = os.path.join(CACHE, url.replace("https://", "").replace("/", "_"))
    if os.path.exists(fname):
        with open(fname, encoding="utf-8") as f:
            schemas[url] = json.load(f)
    else:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read().decode("utf-8")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(data)
        schemas[url] = json.loads(data)
    return schemas[url]


def iter_targets():
    for target in SCAN:
        if os.path.isfile(target):
            yield target
            continue
        for dirpath, dirnames, filenames in os.walk(target):
            # .pbi folders hold Desktop-managed local state (localSettings,
            # cache) - gitignored and not part of the published definition.
            dirnames[:] = [d for d in dirnames if d != ".pbi"]
            for fn in filenames:
                if fn.endswith((".json", ".pbir", ".pbism", ".pbip", ".platform")):
                    yield os.path.join(dirpath, fn)


errors = 0
files = 0
for path in iter_targets():
    rel = os.path.relpath(path, ROOT)
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    url = doc.get("$schema")
    if not url or "developer.microsoft.com" not in url:
        # StaticResources hold arbitrary registered files (themes, images) that
        # Desktop reads by resource type, not by versioned definition schema.
        if f"{os.sep}StaticResources{os.sep}" in path:
            continue
        errors += 1
        print(f"FAIL {rel}: no Microsoft $schema declared - Desktop rejects unversioned sidecar JSONs")
        continue
    files += 1
    try:
        schema = get_schema(url)
    except Exception as e:
        errors += 1
        print(f"FAIL (schema fetch failed): {rel} -> {e}")
        continue
    v = jsonschema.validators.validator_for(schema)(schema)
    errs = list(v.iter_errors(doc))
    if errs:
        errors += len(errs)
        print(f"FAIL {rel}")
        for e in errs[:5]:
            loc = "/".join(str(p) for p in e.absolute_path)
            print(f"  at {loc}: {e.message[:200]}")

print(f"\n{files} files checked, {errors} problems")
sys.exit(1 if errors else 0)
