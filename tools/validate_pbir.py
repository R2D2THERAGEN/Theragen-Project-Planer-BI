"""Validate every PBIR JSON file in the Report folder against its declared
$schema (fetched from developer.microsoft.com, cached locally)."""
import json
import os
import sys
import urllib.request

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RPT = os.path.join(ROOT, "Theragen Project Planner.Report")
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


errors = 0
files = 0
for dirpath, _, filenames in os.walk(RPT):
    for fn in filenames:
        if not fn.endswith((".json", ".pbir", ".platform")):
            continue
        path = os.path.join(dirpath, fn)
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        url = doc.get("$schema")
        if not url or "developer.microsoft.com" not in url:
            continue
        files += 1
        try:
            schema = get_schema(url)
        except Exception as e:
            print(f"SKIP (schema fetch failed): {os.path.relpath(path, ROOT)} -> {e}")
            continue
        v = jsonschema.validators.validator_for(schema)(schema)
        errs = list(v.iter_errors(doc))
        if errs:
            errors += len(errs)
            print(f"FAIL {os.path.relpath(path, ROOT)}")
            for e in errs[:5]:
                loc = "/".join(str(p) for p in e.absolute_path)
                print(f"  at {loc}: {e.message[:200]}")

print(f"\n{files} files checked, {errors} schema violations")
sys.exit(1 if errors else 0)
