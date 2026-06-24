"""Metric calculations for DESI sample assessment."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fidelity_grid import cartesian_voxel_cells, equal_area_sky_cells, occupancy_metrics
from fidelity_helpers import categorical_table, scalar_metrics
