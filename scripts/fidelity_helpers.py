"""Numeric helpers for DESI sampling comparisons.

Metrics here compare browser-representation rows with their declared observed
parent catalogue. They are not survey-selection corrections or clustering
estimators.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import ks_2samp, wasserstein_distance


def finite_numeric(values: Sequence[float] | pd.Series | np.ndarray, name: str) -> np.ndarray:
    """Return finite numeric values or raise a validation error."""

    array = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    array = array[np.isfinite(array)]
    if not len(array):
        raise ValueError(f"{name} has no finite values.")
    return array


def scalar_metrics(
    parent: Sequence[float] | pd.Series | np.ndarray,
    sample: Sequence[float] | pd.Series | np.ndarray,
    *,
    bins: Sequence[float] | np.ndarray,
) -> dict[str, float | int]:
    """Calculate scalar-distribution effect sizes without a KS p-value.

    The selected representation is a subset of the parent. The KS value is
    treated as an empirical-CDF distance rather than a hypothesis-test result.
    """

    parent_values = finite_numeric(parent, "parent")
    sample_values = finite_numeric(sample, "sample")
    edges = np.asarray(bins, dtype=float)
    if edges.ndim != 1 or len(edges) < 2 or not np.all(np.diff(edges) > 0):
        raise ValueError("bins must be a strictly increasing edge array.")

    parent_hist = np.histogram(parent_values, bins=edges)[0].astype(float)
    sample_hist = np.histogram(sample_values, bins=edges)[0].astype(float)
    if not parent_hist.sum() or not sample_hist.sum():
        raise ValueError("bins must contain values from both parent and sample.")

    span = float(np.quantile(parent_values, 0.95) - np.quantile(parent_values, 0.05))
    wasserstein = float(wasserstein_distance(parent_values, sample_values))
    js_divergence = float(
        jensenshannon(parent_hist / parent_hist.sum(), sample_hist / sample_hist.sum(), base=2.0) ** 2
    )
    return {
        "parent_rows": int(len(parent_values)),
        "sample_rows": int(len(sample_values)),
        "ks_distance": float(ks_2samp(parent_values, sample_values, method="asymp").statistic),
        "wasserstein_distance": wasserstein,
        "normalized_wasserstein_distance": wasserstein / span if span > 0 else 0.0,
        "jensen_shannon_divergence_bits": js_divergence,
    }


def categorical_table(parent: pd.Series, sample: pd.Series, *, name: str) -> pd.DataFrame:
    """Return observed category fractions with sample-minus-parent residuals."""

    parent_values = parent.astype("string").fillna("MISSING")
    sample_values = sample.astype("string").fillna("MISSING")
    labels = sorted(set(parent_values) | set(sample_values))
    parent_counts = parent_values.value_counts().reindex(labels, fill_value=0)
    sample_counts = sample_values.value_counts().reindex(labels, fill_value=0)
    table = pd.DataFrame(
        {
            name: labels,
            "parent_rows": parent_counts.to_numpy(dtype=np.int64),
            "sample_rows": sample_counts.to_numpy(dtype=np.int64),
            "parent_fraction": parent_counts.to_numpy(dtype=float) / len(parent_values),
            "sample_fraction": sample_counts.to_numpy(dtype=float) / len(sample_values),
        }
    )
    table["fraction_residual"] = table["sample_fraction"] - table["parent_fraction"]
    return table
