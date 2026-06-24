from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


helpers = load_module("fidelity_helpers", "fidelity_helpers.py")
grid = load_module("fidelity_grid", "fidelity_grid.py")


def test_scalar_metrics_are_zero_for_identical_arrays() -> None:
    values = np.array([0.01, 0.02, 0.03, 0.04])
    metrics = helpers.scalar_metrics(values, values, bins=np.linspace(0.0, 0.05, 6))
    assert metrics["ks_distance"] == 0.0
    assert metrics["wasserstein_distance"] == 0.0
    assert metrics["jensen_shannon_divergence_bits"] == 0.0


def test_categorical_table_reports_fraction_residuals() -> None:
    table = helpers.categorical_table(
        pd.Series(["BGS", "BGS", "LRG", "QSO"]),
        pd.Series(["BGS", "LRG"]),
        name="tracer",
    )
    assert table.loc[table["tracer"] == "QSO", "fraction_residual"].item() == -0.25


def test_equal_area_sky_cells_handles_ra_wrap() -> None:
    cells = grid.equal_area_sky_cells(
        [0.0, 360.0, 180.0],
        [0.0, 0.0, 90.0],
        ra_bins=4,
        sin_dec_bins=4,
    )
    assert cells.iloc[0] == cells.iloc[1]
    assert cells.nunique() == 2


def test_occupancy_metrics_are_exact_for_full_sample() -> None:
    cells = pd.Series(["a", "a", "b", "c"], dtype="string")
    metrics = grid.occupancy_metrics(cells, cells, sampling_fraction=1.0)
    assert metrics["occupied_cell_recall"] == 1.0
    assert metrics["occupancy_correlation"] == 1.0
    assert metrics["occupancy_nrmse"] == 0.0


def test_cartesian_voxel_cells_are_stable() -> None:
    frame = pd.DataFrame(
        {
            "x_mpc": [0.0, 49.9, 50.0],
            "y_mpc": [0.0, 0.0, 0.0],
            "z_mpc": [0.0, 0.0, 0.0],
        }
    )
    cells = grid.cartesian_voxel_cells(frame, cell_size_mpc=50.0)
    assert cells.iloc[0] == cells.iloc[1]
    assert cells.iloc[0] != cells.iloc[2]
