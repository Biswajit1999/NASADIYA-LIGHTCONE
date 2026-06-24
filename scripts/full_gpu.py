#!/usr/bin/env python3
"""Build a packed full-catalogue DESI rendering cloud from Parquet.

The output is a rendering product for local or object-storage delivery. It is
not a row-level research table: individual source inspection remains available
through the provenance-preserving DESI tile store.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_COLUMNS = ("tracer", "x_mpc", "y_mpc", "z_mpc", "redshift")
TRACER_CODES = {"UNKNOWN": 0, "BGS": 1, "LRG": 2, "ELG": 3, "QSO": 4}
STRIDE_FLOATS = 5


def file_sha256(path: Path) -> str:
    """Calculate a streamed SHA256 checksum."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pack_rows(frame: pd.DataFrame) -> tuple[np.ndarray, Counter[str]]:
    """Return valid observed rows in x,y,z,redshift,tracer-code float32 layout."""

    numeric = frame.loc[:, ["x_mpc", "y_mpc", "z_mpc", "redshift"]].apply(pd.to_numeric, errors="coerce")
    valid = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
    valid &= numeric["redshift"].between(0.0, 10.0).to_numpy(dtype=bool)
    if not valid.any():
        return np.empty((0, STRIDE_FLOATS), dtype="<f4"), Counter()

    accepted = numeric.loc[valid]
    labels = frame.loc[valid, "tracer"].fillna("UNKNOWN").astype(str).str.upper().str.strip()
    codes = labels.map(TRACER_CODES).fillna(0).to_numpy(dtype=np.float32)
    packed = np.empty((len(accepted), STRIDE_FLOATS), dtype="<f4")
    packed[:, 0] = accepted["x_mpc"].to_numpy(dtype=np.float32)
    packed[:, 1] = accepted["y_mpc"].to_numpy(dtype=np.float32)
    packed[:, 2] = accepted["z_mpc"].to_numpy(dtype=np.float32)
    packed[:, 3] = accepted["redshift"].to_numpy(dtype=np.float32)
    packed[:, 4] = codes
    return packed, Counter(labels.tolist())
