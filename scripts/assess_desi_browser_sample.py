#!/usr/bin/env python3
"""Compare browser-scale samples with a DESI parent bundle."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from assess_desi_common import load_parent  # noqa: E402
from desi_strata import redshift_bin_labels  # noqa: E402
from fidelity_grid import cartesian_voxel_cells, equal_area_sky_cells, occupancy_metrics  # noqa: E402
from fidelity_helpers import categorical_table, scalar_metrics  # noqa: E402
from nasadiya_lightcone.sampling import select_lowest_hash, select_seeded_random, select_stratified_lowest_hash  # noqa: E402


def build_samples(parent: pd.DataFrame, args: argparse.Namespace) -> dict[str, pd.DataFrame]:
    """Construct the declared browser-representation policies."""

    working = parent.copy()
    working["sky_cell"] = equal_area_sky_cells(
        working["ra_deg"],
        working["dec_deg"],
        ra_bins=args.sky_ra_bins,
        sin_dec_bins=args.sky_sin_dec_bins,
    )
    working["redshift_bin"] = redshift_bin_labels(
        working["redshift"],
        z_max=args.z_max,
        z_bins=args.z_bins,
    )
    return {
        "lowest_hash": select_lowest_hash(working, args.point_budget),
        "seeded_random": select_seeded_random(working, args.point_budget, seed=args.random_seed),
        "tracer_hash": select_stratified_lowest_hash(
            working,
            args.point_budget,
            group_columns=("tracer",),
        ),
        "spatial_redshift_hash": select_stratified_lowest_hash(
            working,
            args.point_budget,
            group_columns=("tracer", "sky_cell", "redshift_bin"),
        ),
    }


def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
