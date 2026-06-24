"""Shared input helpers for DESI browser-sample assessment."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ("object_id", "tracer", "ra_deg", "dec_deg", "redshift", "x_mpc", "y_mpc", "z_mpc")


def file_sha256(path: Path) -> str:
    """Return the SHA256 checksum of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_parent(path: Path) -> pd.DataFrame:
    """Read required observed fields and reject malformed rows."""

    frame = pd.read_parquet(path, columns=list(COLUMNS))
    numeric = [column for column in COLUMNS if column not in {"object_id", "tracer"}]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["object_id"] = frame["object_id"].astype("string")
    frame["tracer"] = frame["tracer"].fillna("UNKNOWN").astype(str).str.upper()
    valid = frame["object_id"].notna() & frame["object_id"].str.len().gt(0)
    valid &= np.isfinite(frame[numeric]).all(axis=1)
    frame = frame.loc[valid].copy()
    if frame.empty:
        raise ValueError("No valid observed rows remain after field validation.")
    if frame["object_id"].duplicated().any():
        raise ValueError("Parent bundle contains duplicate object IDs.")
    return frame.reset_index(drop=True)
