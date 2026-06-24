#!/usr/bin/env python3
"""Build a packed full-catalogue DESI rendering cloud from Parquet."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_COLUMNS = ("tracer", "x_mpc", "y_mpc", "z_mpc", "redshift")
TRACER_CODES = {"UNKNOWN": 0, "BGS": 1, "LRG": 2, "ELG": 3, "QSO": 4}
STRIDE_FLOATS = 5


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pack_rows(frame: pd.DataFrame) -> tuple[np.ndarray, Counter[str]]:
    numeric = frame.loc[:, ["x_mpc", "y_mpc", "z_mpc", "redshift"]].apply(pd.to_numeric, errors="coerce")
    valid = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
    valid &= numeric["redshift"].between(0.0, 10.0).to_numpy(dtype=bool)
    if not valid.any():
        return np.empty((0, STRIDE_FLOATS), dtype="<f4"), Counter()
    accepted = numeric.loc[valid]
    labels = frame.loc[valid, "tracer"].fillna("UNKNOWN").astype(str).str.upper().str.strip()
    packed = np.empty((len(accepted), STRIDE_FLOATS), dtype="<f4")
    packed[:, :4] = accepted[["x_mpc", "y_mpc", "z_mpc", "redshift"]].to_numpy(dtype=np.float32)
    packed[:, 4] = labels.map(TRACER_CODES).fillna(0).to_numpy(dtype=np.float32)
    return packed, Counter(labels.tolist())


def write_cloud(input_path: Path, binary_path: Path, batch_rows: int) -> tuple[int, int, Counter[str]]:
    parquet = pq.ParquetFile(input_path)
    missing = sorted(set(INPUT_COLUMNS) - set(parquet.schema.names))
    if missing:
        raise ValueError(f"Input bundle is missing: {', '.join(missing)}")
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    records, rejected = 0, 0
    tracers: Counter[str] = Counter()
    with binary_path.open("wb") as handle:
        for batch in parquet.iter_batches(batch_size=batch_rows, columns=list(INPUT_COLUMNS)):
            packed, batch_counts = pack_rows(batch.to_pandas())
            rejected += len(batch) - len(packed)
            handle.write(packed.tobytes(order="C"))
            records += len(packed)
            tracers.update(batch_counts)
    return records, rejected, tracers
