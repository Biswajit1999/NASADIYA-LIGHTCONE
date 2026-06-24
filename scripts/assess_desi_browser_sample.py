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
from fidelity_grid import equal_area_sky_cells  # noqa: E402
from nasadiya_lightcone.sampling import select_lowest_hash, select_seeded_random, select_stratified_lowest_hash  # noqa: E402


def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
