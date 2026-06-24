"""Packed GPU-cloud contract for full observed catalogue rendering.

The full cloud is a rendering product, not a replacement research table. It keeps
only the fields required for a GPU point cloud and deliberately omits object IDs
and row-level provenance. Clicking individual rows remains a tile/overview task.
"""

from __future__ import annotations

from collections import Counter
from typing import Final

import numpy as np
import pandas as pd

GPU_CLOUD_FORMAT: Final[str] = "nasadiya-gpu-cloud/v1"
GPU_CLOUD_FIELDS: Final[tuple[str, ...]] = (
    "x_mpc",
    "y_mpc",
    "z_mpc",
    "redshift",
    "tracer_code",
)
GPU_CLOUD_STRIDE_FLOATS: Final[int] = len(GPU_CLOUD_FIELDS)
TRACER_CODES: Final[dict[str, int]] = {
    "UNKNOWN": 0,
    "BGS": 1,
    "LRG": 2,
    "ELG": 3,
    "QSO": 4,
}


def normalise_tracer_codes(values: pd.Series) -> np.ndarray:
    """Map declared DESI tracer labels to compact float-compatible codes."""

    labels = values.fillna("UNKNOWN").astype(str).str.upper().str.strip()
    return labels.map(TRACER_CODES).fillna(TRACER_CODES["UNKNOWN"]).to_numpy(dtype=np.float32)


def pack_gpu_cloud_rows(frame: pd.DataFrame) -> tuple[np.ndarray, Counter[str]]:
    """Pack valid observed coordinates into little-endian float32 GPU records.

    Output layout is ``x_mpc, y_mpc, z_mpc, redshift, tracer_code``. Invalid
    coordinate/redshift rows are rejected rather than represented as synthetic
    placeholders. The function is deliberately batch-safe for multi-million-row
    Parquet streaming.
    """

    required = {"tracer", "x_mpc", "y_mpc", "z_mpc", "redshift"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"GPU cloud input is missing required field(s): {', '.join(missing)}.")

    numeric = frame.loc[:, ["x_mpc", "y_mpc", "z_mpc", "redshift"]].apply(pd.to_numeric, errors="coerce")
    valid = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
    valid &= numeric["redshift"].between(0.0, 10.0).to_numpy(dtype=bool)
    if not valid.any():
        return np.empty((0, GPU_CLOUD_STRIDE_FLOATS), dtype="<f4"), Counter()

    accepted = numeric.loc[valid]
    labels = frame.loc[valid, "tracer"].fillna("UNKNOWN").astype(str).str.upper().str.strip()
    packed = np.empty((len(accepted), GPU_CLOUD_STRIDE_FLOATS), dtype="<f4")
    packed[:, 0] = accepted["x_mpc"].to_numpy(dtype=np.float32)
    packed[:, 1] = accepted["y_mpc"].to_numpy(dtype=np.float32)
    packed[:, 2] = accepted["z_mpc"].to_numpy(dtype=np.float32)
    packed[:, 3] = accepted["redshift"].to_numpy(dtype=np.float32)
    packed[:, 4] = normalise_tracer_codes(labels)
    return packed, Counter(labels.tolist())
