from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "assess_desi_browser_sample.py"
SPEC = importlib.util.spec_from_file_location("desi_browser_fidelity", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_fidelity_runner_exposes_declared_entry_points() -> None:
    assert callable(module.build_samples)
    assert callable(module.metrics_for_sample)
    assert callable(module.main)
