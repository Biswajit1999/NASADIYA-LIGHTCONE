"""Metric calculations for DESI sample assessment."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fidelity_grid import cartesian_voxel_cells, equal_area_sky_cells, occupancy_metrics
from fidelity_helpers import categorical_table, scalar_metrics


def assess_sample(
    parent: pd.DataFrame,
    sample: pd.DataFrame,
    *,
    parent_sky: pd.Series,
    parent_voxels: pd.Series,
    redshift_edges: np.ndarray,
    sky_ra_bins: int,
    sky_sin_dec_bins: int,
    voxel_size_mpc: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Calculate observed-row distribution and occupancy metrics for one sample."""

    fraction = len(sample) / len(parent)
    tracer = categorical_table(parent["tracer"], sample["tracer"], name="tracer")
    sample_sky = equal_area_sky_cells(
        sample["ra_deg"],
        sample["dec_deg"],
        ra_bins=sky_ra_bins,
        sin_dec_bins=sky_sin_dec_bins,
    )
    sample_voxels = cartesian_voxel_cells(sample, cell_size_mpc=voxel_size_mpc)
    metrics = {
        "sampling_fraction": fraction,
        "redshift": scalar_metrics(parent["redshift"], sample["redshift"], bins=redshift_edges),
        "tracer_total_variation_distance": float(0.5 * np.abs(tracer["fraction_residual"]).sum()),
        "sky_occupancy": occupancy_metrics(parent_sky, sample_sky, sampling_fraction=fraction),
        "voxel_occupancy": occupancy_metrics(parent_voxels, sample_voxels, sampling_fraction=fraction),
    }
    return metrics, tracer


def flat_metric_row(name: str, metrics: dict[str, Any]) -> dict[str, float | str]:
    """Flatten one nested metric result into a CSV-friendly row."""

    redshift = metrics["redshift"]
    sky = metrics["sky_occupancy"]
    voxel = metrics["voxel_occupancy"]
    return {
        "method": name,
        "sampling_fraction": metrics["sampling_fraction"],
        "ks_distance": redshift["ks_distance"],
        "normalized_wasserstein_distance": redshift["normalized_wasserstein_distance"],
        "jensen_shannon_divergence_bits": redshift["jensen_shannon_divergence_bits"],
        "tracer_total_variation_distance": metrics["tracer_total_variation_distance"],
        "sky_occupancy_recall": sky["occupied_cell_recall"],
        "sky_occupancy_correlation": sky["occupancy_correlation"],
        "sky_occupancy_nrmse": sky["occupancy_nrmse"],
        "voxel_occupancy_recall": voxel["occupied_cell_recall"],
        "voxel_occupancy_correlation": voxel["occupancy_correlation"],
        "voxel_occupancy_nrmse": voxel["occupancy_nrmse"],
    }
