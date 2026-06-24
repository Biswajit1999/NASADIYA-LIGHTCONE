#!/usr/bin/env python3
"""Build a packed full-catalogue DESI rendering cloud from Parquet.

The output is a local or object-storage rendering product. It is not a row-level
research table: individual source inspection remains a provenance-tile task.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "research" / "desi_dr1_lss_research_bundle.parquet")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "processed" / "desi-dr1" / "full-cloud")
    parser.add_argument("--batch-rows", type=int, default=250_000)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    binary_path = args.output_dir / "desi-dr1-full-cloud.f32"
    manifest_path = args.output_dir / "full-cloud.json"
    if (binary_path.exists() or manifest_path.exists()) and not args.overwrite:
        print(f"Output already exists: {args.output_dir}; use --overwrite to replace it.")
        return 2
    records, rejected, tracers = write_cloud(args.input, binary_path, args.batch_rows)
    expected_bytes = records * STRIDE_FLOATS * 4
    if binary_path.stat().st_size != expected_bytes:
        raise RuntimeError("GPU cloud byte-length validation failed.")
    manifest = {
        "format": "nasadiya-gpu-cloud/v1",
        "dataset_id": "desi-dr1-lss-full-observed-cloud",
        "record_count": records,
        "rejected_rows": rejected,
        "binary": {
            "path": binary_path.name,
            "encoding": "little-endian-float32-interleaved",
            "fields": ["x_mpc", "y_mpc", "z_mpc", "redshift", "tracer_code"],
            "stride_floats": STRIDE_FLOATS,
            "stride_bytes": STRIDE_FLOATS * 4,
            "byte_length": expected_bytes,
            "sha256": file_sha256(binary_path),
        },
        "tracer_codes": TRACER_CODES,
        "tracer_counts": dict(sorted(tracers.items())),
        "source": {"input_file": args.input.name, "survey": "DESI DR1 LSS", "release": "DESI DR1", "measurement_kind": "spectroscopic"},
        "rendering_scope": {
            "point_inspection_available": False,
            "tile_store_required_for_row_inspection": True,
            "note": "Full GPU cloud contains real observed rows for rendering only; it is not a completeness-corrected density field or a clustering-ready catalogue.",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {records:,} observed rows to {binary_path}")
    print(f"GPU payload: {expected_bytes / (1024 ** 2):.1f} MiB")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
