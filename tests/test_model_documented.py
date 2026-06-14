"""Coverage guard: every model object must carry a /// description.

Part of the change-control process (docs/change-control-process.md) — the
"everything documented" bar. Turns the build_data_dictionary --audit gate into a
pytest guard, so any future model change that adds an undescribed table, column,
measure, or role fails CI.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bdd", ROOT / "tools" / "build_data_dictionary.py")
bdd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bdd)


def test_every_model_object_has_a_description():
    model = bdd.load_model()
    missing = bdd.audit(model["tables"], model["roles"])
    assert missing == [], (
        f"{len(missing)} model object(s) lack a /// description (run "
        "`python tools/build_data_dictionary.py --audit`): " + ", ".join(missing[:20])
    )


def test_roles_have_no_lineage_tag():
    """TMDL roles do not support a lineageTag property - Power BI Desktop rejects
    the model with 'lineageTag is not a supported property in the current context'.
    Regression guard for the load failure fixed 2026-06-14."""
    roles_dir = ROOT / "Theragen Project Planner.SemanticModel" / "definition" / "roles"
    offenders = []
    for f in sorted(roles_dir.glob("*.tmdl")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("lineageTag"):
                offenders.append(f"{f.name}:{i}")
    assert not offenders, (
        "TMDL roles must not contain lineageTag (unsupported in the role context; "
        "Desktop won't load the model): " + ", ".join(offenders)
    )
