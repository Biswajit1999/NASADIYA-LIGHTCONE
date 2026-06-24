"""Representation-policy helpers for DESI browser samples."""

from __future__ import annotations

import numpy as np
import pandas as pd


def redshift_bin_labels(values: pd.Series, *, z_max: float, z_bins: int) -> pd.Series:
    """Return bounded integer labels for a declared redshift-bin grid."""

    if z_max <= 0 or z_bins < 1:
        raise ValueError("z_max and z_bins must be positive.")
    edges = np.linspace(0.0, z_max, z_bins + 1)
    labels = np.clip(
        np.digitize(values.to_numpy(dtype=float), edges, right=False) - 1,
        0,
        z_bins - 1,
    )
    return pd.Series(labels.astype(np.int16), index=values.index)
