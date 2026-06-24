"""Sky and voxel occupancy helpers for sampling comparisons."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd

VOXEL_BITS = 21
VOXEL_OFFSET = 1 << (VOXEL_BITS - 1)
VOXEL_MAX = VOXEL_OFFSET - 1


def finite_numeric(values: Sequence[float] | pd.Series | np.ndarray, name: str) -> np.ndarray:
    """Return finite numeric values or raise a clear error."""

    array = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    array = array[np.isfinite(array)]
    if not len(array):
        raise ValueError(f"{name} has no finite values.")
    return array


def equal_area_sky_cells(
    ra_deg: Sequence[float] | pd.Series | np.ndarray,
    dec_deg: Sequence[float] | pd.Series | np.ndarray,
    *,
    ra_bins: int,
    sin_dec_bins: int,
) -> pd.Series:
    """Create compact equal-area cell IDs using RA and uniform sin(Dec) bins."""

    if ra_bins < 1 or sin_dec_bins < 1:
        raise ValueError("Sky-grid dimensions must be positive.")
    ra = finite_numeric(ra_deg, "ra_deg")
    dec = finite_numeric(dec_deg, "dec_deg")
    if len(ra) != len(dec):
        raise ValueError("RA and Dec must have the same number of values.")
    if np.any((dec < -90) | (dec > 90)):
        raise ValueError("Dec values must lie in [-90, 90].")
    ra_index = np.floor(np.mod(ra, 360.0) / 360.0 * ra_bins).astype(np.int64)
    dec_fraction = np.clip((np.sin(np.deg2rad(dec)) + 1.0) / 2.0, 0.0, 1.0 - np.finfo(float).eps)
    dec_index = np.floor(dec_fraction * sin_dec_bins).astype(np.int64)
    return pd.Series(ra_index * sin_dec_bins + dec_index, dtype="int64")


def cartesian_voxel_cells(
    frame: pd.DataFrame,
    *,
    cell_size_mpc: float,
    columns: tuple[str, str, str] = ("x_mpc", "y_mpc", "z_mpc"),
) -> pd.Series:
    """Create collision-free 64-bit IDs for a regular Cartesian occupancy grid."""

    if cell_size_mpc <= 0:
        raise ValueError("cell_size_mpc must be positive.")
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Frame is missing Cartesian column(s): {', '.join(missing)}.")
    coordinates = frame.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")
    if coordinates.isna().any(axis=None):
        raise ValueError("Cartesian voxel labels require finite coordinates.")
    indices = np.floor(coordinates.to_numpy(dtype=float) / cell_size_mpc).astype(np.int64)
    if np.any(indices < -VOXEL_OFFSET) or np.any(indices > VOXEL_MAX):
        raise ValueError("Voxel index exceeds the documented 21-bit packing range.")
    shifted = (indices + VOXEL_OFFSET).astype(np.uint64)
    packed = (shifted[:, 0] << (2 * VOXEL_BITS)) | (shifted[:, 1] << VOXEL_BITS) | shifted[:, 2]
    return pd.Series(packed, dtype="uint64")


def occupancy_metrics(
    parent_cells: pd.Series,
    sample_cells: pd.Series,
    *,
    sampling_fraction: float,
) -> dict[str, float | int]:
    """Compare parent and sample counts after scaling by their point fraction."""

    if not 0 < sampling_fraction <= 1:
        raise ValueError("sampling_fraction must lie in (0, 1].")
    parent_counts = pd.Series(parent_cells).value_counts(sort=False)
    sample_counts = pd.Series(sample_cells).value_counts(sort=False).reindex(parent_counts.index, fill_value=0)
    parent = parent_counts.to_numpy(dtype=float)
    scaled_sample = sample_counts.to_numpy(dtype=float) / sampling_fraction
    residual = scaled_sample - parent
    denominator = math.sqrt(float(np.mean(np.square(parent))))
    nrmse = math.sqrt(float(np.mean(np.square(residual)))) / denominator if denominator else 0.0
    occupied = sample_counts.to_numpy(dtype=float) > 0
    correlation = float(np.corrcoef(parent, scaled_sample)[0, 1]) if len(parent) > 1 and np.std(parent) and np.std(scaled_sample) else 1.0
    return {
        "parent_occupied_cells": int(len(parent_counts)),
        "sample_occupied_cells": int(np.count_nonzero(occupied)),
        "occupied_cell_recall": float(np.count_nonzero(occupied) / len(parent)),
        "occupancy_correlation": correlation,
        "occupancy_nrmse": nrmse,
    }
