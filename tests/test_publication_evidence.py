from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_desi_publication_figures import occupancy_fraction_grid, parse_budgets, validate_gpu_contract


def test_parse_budgets_sorts_and_deduplicates() -> None:
    assert parse_budgets("500000,125000,500000,250000") == [125000, 250000, 500000]


def test_occupancy_fraction_grid_is_normalised() -> None:
    cells = pd.Series([0, 0, 1, 3, 3, 3], dtype="int64")
    grid = occupancy_fraction_grid(cells, ra_bins=2, sin_dec_bins=2)
    assert grid.shape == (2, 2)
    assert np.isclose(grid.sum(), 1.0)
    assert np.isclose(grid[0, 0], 2 / 6)
    assert np.isclose(grid[1, 1], 3 / 6)


def test_missing_gpu_manifest_is_reported_without_implicit_claim(tmp_path: Path) -> None:
    parent = pd.DataFrame({"object_id": ["a", "b"]})
    result = validate_gpu_contract(parent, tmp_path / "not-present.json", allow_mismatch=False)
    assert result["manifest_checked"] is False
