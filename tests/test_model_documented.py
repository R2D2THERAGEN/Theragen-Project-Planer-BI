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
