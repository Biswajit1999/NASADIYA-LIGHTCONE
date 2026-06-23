#!/usr/bin/env python3
"""Build a portable DESI DR1 LSS research bundle for Python and Google Colab.

The browser uses a small overview and adaptive tiles. This script instead writes one
compressed Parquet research bundle from the locally built, observed DESI tile store.
It first attempts the full 6M-row product. If that exceeds the requested size cap, it
creates a deterministic object-ID-hash sample and records the selection in a manifest.
No synthetic rows, inferred objects, or cross-survey matches are introduced.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Iterator

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TILE_FORMAT = "nasadiya-tile-store/v1"
HASH_KEY = "0123456789abcdef"
FLOAT_COLUMNS = (
    "ra_deg",
    "dec_deg",
    "redshift",
    "redshift_error",
    "comoving_distance_mpc",
    "lookback_time_gyr",
    "x_mpc",
    "y_mpc",
    "z_mpc",
    "magnitude",
)
OUTPUT_COLUMNS = ("object_id", *FLOAT_COLUMNS, "tracer")
PARQUET_SCHEMA = pa.schema(
    [
        pa.field("object_id", pa.string()),
        *[pa.field(name, pa.float32()) for name in FLOAT_COLUMNS],
        pa.field("tracer", pa.string()),
    ]
)


@dataclass
class BundleStats:
    rows: int
    tracer_counts: Counter[str]
    tile_count: int
    bytes_written: int


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_index(index_path: Path) -> dict:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if payload.get("format") != TILE_FORMAT:
        raise RuntimeError(
            f"Unsupported tile-store format in {index_path}: {payload.get('format')!r}"
        )
    if payload.get("dataset", {}).get("dataset_id") != "desi-dr1":
        raise RuntimeError("Research bundle input must be the observed DESI DR1 tile store.")
    if payload.get("dataset", {}).get("is_synthetic") is not False:
        raise RuntimeError("DESI research bundles require explicitly observed source rows.")
    if not isinstance(payload.get("tiles"), list) or not payload["tiles"]:
        raise RuntimeError("DESI tile manifest contains no tile entries.")
    return payload


def tile_paths(index_path: Path, manifest: dict) -> list[Path]:
    paths = [index_path.parent / item["path"] for item in manifest["tiles"]]
    missing = [path for path in paths if not path.exists()]
    if missing:
        preview = "\n".join(f"  - {path}" for path in missing[:5])
        raise RuntimeError(
            "The full local DESI tile store is incomplete. Missing tile file(s):\n" + preview
        )
    return sorted(paths)


def tracer_from_id(ids: pd.Series) -> pd.Series:
    tracer = ids.astype("string").str.extract(r"^desi-dr1:([^:]+):", expand=False)
    return tracer.fillna("UNKNOWN").str.upper()


def normalise_tile_frame(tile_path: Path, expected_columns: list[str]) -> pd.DataFrame:
    payload = json.loads(tile_path.read_text(encoding="utf-8"))
    if payload.get("format") != TILE_FORMAT:
        raise RuntimeError(f"Unsupported tile payload in {tile_path}")
    columns = payload.get("columns") or expected_columns
    if list(columns) != list(expected_columns):
        raise RuntimeError(f"Column contract changed in {tile_path}")
    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError(f"Tile records missing in {tile_path}")
    frame = pd.DataFrame(records, columns=columns)
    if frame.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    frame["object_id"] = frame["object_id"].astype("string")
    for column in FLOAT_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float32")
    required = ["ra_deg", "dec_deg", "redshift", "x_mpc", "y_mpc", "z_mpc"]
    frame = frame.dropna(subset=required).copy()
    frame = frame.loc[frame["object_id"].str.len().fillna(0).gt(0)].copy()
    frame["tracer"] = tracer_from_id(frame["object_id"])
    return frame.loc[:, OUTPUT_COLUMNS]


def stable_hash_mask(ids: pd.Series, fraction: float) -> pd.Series:
    if fraction >= 1:
        return pd.Series(True, index=ids.index)
    if fraction <= 0:
        return pd.Series(False, index=ids.index)
    values = pd.util.hash_pandas_object(
        ids.astype("string"),
        index=False,
        hash_key=HASH_KEY,
    ).astype("uint64")
    threshold = int(fraction * ((1 << 64) - 1))
    return values.le(threshold)


def iter_frames(paths: list[Path], columns: list[str]) -> Iterator[pd.DataFrame]:
    for path in paths:
        frame = normalise_tile_frame(path, columns)
        if not frame.empty:
            yield frame


def write_bundle(
    paths: list[Path],
    columns: list[str],
    output_path: Path,
    *,
    sample_fraction: float,
) -> BundleStats:
    output_path.unlink(missing_ok=True)
    writer: pq.ParquetWriter | None = None
    rows = 0
    tracer_counts: Counter[str] = Counter()
    try:
        for frame in iter_frames(paths, columns):
            keep = stable_hash_mask(frame["object_id"], sample_fraction)
            frame = frame.loc[keep].copy()
            if frame.empty:
                continue
            table = pa.Table.from_pandas(frame, schema=PARQUET_SCHEMA, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(
                    output_path,
                    PARQUET_SCHEMA,
                    compression="zstd",
                    compression_level=9,
                    use_dictionary=["tracer"],
                    write_statistics=True,
                )
            writer.write_table(table, row_group_size=min(100_000, len(frame)))
            rows += len(frame)
            tracer_counts.update(frame["tracer"].astype(str).tolist())
    finally:
        if writer is not None:
            writer.close()
    if rows == 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("No observed DESI rows passed the requested research-bundle selection.")
    return BundleStats(
        rows=rows,
        tracer_counts=tracer_counts,
        tile_count=len(paths),
        bytes_written=output_path.stat().st_size,
    )


def build_manifest(
    *,
    index_path: Path,
    source_manifest: dict,
    output_path: Path,
    full_candidate: BundleStats,
    output_stats: BundleStats,
    target_bytes: int,
    sample_fraction: float,
) -> dict:
    full_rows = int(source_manifest.get("record_count", full_candidate.rows))
    selection = {
        "mode": "full-observed-catalogue" if sample_fraction >= 1 else "deterministic-object-id-hash",
        "sample_fraction": sample_fraction,
        "hash_key_contract": HASH_KEY if sample_fraction < 1 else None,
        "input_record_count": full_rows,
        "output_record_count": output_stats.rows,
        "not_a_completeness_correction": True,
        "not_a_crossmatch": True,
    }
    return {
        "format": "nasadiya-research-bundle/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": source_manifest["dataset"],
        "input_tile_index": str(index_path.relative_to(PROJECT_ROOT)),
        "input_tile_index_sha256": sha256(index_path),
        "input_tile_count": output_stats.tile_count,
        "input_record_count": full_rows,
        "full_candidate": {
            "rows": full_candidate.rows,
            "bytes": full_candidate.bytes_written,
            "megabytes": round(full_candidate.bytes_written / 1024**2, 2),
        },
        "bundle": {
            "file": output_path.name,
            "sha256": sha256(output_path),
            "bytes": output_stats.bytes_written,
            "megabytes": round(output_stats.bytes_written / 1024**2, 2),
            "target_megabytes": round(target_bytes / 1024**2, 2),
            "rows": output_stats.rows,
            "tracer_counts": dict(sorted(output_stats.tracer_counts.items())),
        },
        "selection": selection,
        "provenance_note": (
            "All bundle rows originate in the locally built DESI DR1 LSS observed tile store. "
            "No synthetic rows or reconstructed filaments are present."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "desi-dr1" / "index.json",
        help="Local DESI tile-store manifest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "research" / "desi_dr1_lss_research_bundle.parquet",
        help="Research Parquet output. This is ignored by normal Git history.",
    )
    parser.add_argument(
        "--target-mb",
        type=float,
        default=480.0,
        help="Maximum final Parquet size in MiB; default leaves release-asset headroom.",
    )
    parser.add_argument(
        "--safety-factor",
        type=float,
        default=0.90,
        help="Extra reduction applied if a deterministic sample is required.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing research bundle and manifest.",
    )
    args = parser.parse_args()

    if args.target_mb <= 0 or not 0 < args.safety_factor < 1:
        print("--target-mb must be positive and --safety-factor must lie between 0 and 1.")
        return 2
    index_path = args.index.resolve()
    output_path = args.output.resolve()
    manifest_path = output_path.with_suffix(".manifest.json")
    if output_path.exists() and not args.overwrite:
        print(f"Research bundle already exists: {output_path}")
        print("Use --overwrite to replace it.")
        return 2

    source_manifest = load_index(index_path)
    paths = tile_paths(index_path, source_manifest)
    columns = list(source_manifest.get("record_columns", []))
    if not columns:
        print("DESI tile manifest does not define record_columns.")
        return 2
    output_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path = output_path.with_name(f".{output_path.stem}.full-candidate.parquet")
    candidate_path.unlink(missing_ok=True)
    target_bytes = int(args.target_mb * 1024**2)

    try:
        print(f"Reading {len(paths):,} observed DESI tile file(s)…")
        full_candidate = write_bundle(
            paths,
            columns,
            candidate_path,
            sample_fraction=1.0,
        )
        print(
            "Full candidate: "
            f"{full_candidate.rows:,} rows · {full_candidate.bytes_written / 1024**2:.2f} MiB"
        )

        fraction = 1.0
        output_stats = full_candidate
        if full_candidate.bytes_written <= target_bytes:
            shutil.move(candidate_path, output_path)
            print("Full observed catalogue fits the requested research-bundle size cap.")
        else:
            fraction = min(
                1.0,
                (target_bytes / full_candidate.bytes_written) * args.safety_factor,
            )
            print(
                "Full candidate exceeds the cap; building deterministic object-ID-hash "
                f"sample at fraction {fraction:.6f}."
            )
            output_stats = write_bundle(
                paths,
                columns,
                output_path,
                sample_fraction=fraction,
            )
            for _ in range(2):
                if output_stats.bytes_written <= target_bytes:
                    break
                fraction *= (target_bytes / output_stats.bytes_written) * args.safety_factor
                print(
                    "Sample still exceeds the cap; refining to hash fraction "
                    f"{fraction:.6f}."
                )
                output_stats = write_bundle(
                    paths,
                    columns,
                    output_path,
                    sample_fraction=fraction,
                )
            candidate_path.unlink(missing_ok=True)
            if output_stats.bytes_written > target_bytes:
                raise RuntimeError(
                    "The deterministic research sample still exceeds the target after refinement. "
                    "Use a smaller --target-mb value or inspect the local tile store."
                )

        bundle_manifest = build_manifest(
            index_path=index_path,
            source_manifest=source_manifest,
            output_path=output_path,
            full_candidate=full_candidate,
            output_stats=output_stats,
            target_bytes=target_bytes,
            sample_fraction=fraction,
        )
        manifest_path.write_text(json.dumps(bundle_manifest, indent=2), encoding="utf-8")
    except Exception as exc:
        candidate_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        print(f"DESI research-bundle build failed: {exc}")
        return 3

    print(f"Saved research bundle: {output_path}")
    print(f"Saved manifest: {manifest_path}")
    print(
        f"Final: {output_stats.rows:,} observed rows · "
        f"{output_stats.bytes_written / 1024**2:.2f} MiB"
    )
    print("Next: scripts/plot_desi_research_figure.py --input <bundle>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
