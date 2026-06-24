from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("full_gpu", PROJECT_ROOT / "scripts" / "full_gpu.py")
assert SPEC and SPEC.loader
full_gpu = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = full_gpu
SPEC.loader.exec_module(full_gpu)


def test_pack_rows_keeps_only_valid_observed_coordinates() -> None:
    frame = pd.DataFrame({
        "tracer": ["BGS", "QSO", "UNKNOWN", "LRG"],
        "x_mpc": [1.0, 2.0, float("nan"), 4.0],
        "y_mpc": [5.0, 6.0, 7.0, 8.0],
        "z_mpc": [9.0, 10.0, 11.0, 12.0],
        "redshift": [0.1, 2.1, 0.4, -0.1],
    })
    packed, tracers = full_gpu.pack_rows(frame)
    assert packed.shape == (2, 5)
    assert packed.dtype.str == "<f4"
    assert packed[:, 4].tolist() == [1.0, 4.0]
    assert tracers == {"BGS": 1, "QSO": 1}
