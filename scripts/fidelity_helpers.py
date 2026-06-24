"""Numeric helpers for DESI sampling comparisons."""

from __future__ import annotations

import numpy as np
import pandas as pd


def finite_numeric(values: pd.Series) -> np.ndarray:
    """Convert a series to finite floating-point values."""

    array = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    return array[np.isfinite(array)]
