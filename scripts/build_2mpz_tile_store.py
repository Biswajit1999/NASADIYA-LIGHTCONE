#!/usr/bin/env python3
"""Build the 2MPZ tile store from the downloaded SSA source CSV.

2MPZ publishes only one survey-wide photometric-redshift accuracy figure
(sigma_z = 0.015; Bilicki et al. 2014), not a per-object uncertainty column.
This builder uses ``SurveyDescriptor.global_redshift_sigma`` so
``redshift_error`` stays honestly absent per row, while the one real
published number is recorded once in the manifest for the browser's
uncertainty-shell renderer. It never invents a per-object error.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import sys
from typing import Iterator

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from nasadiya_lightcone.tiles import (  # noqa: E402
    ChunkedTileStoreWriter,
    SurveyDescriptor,
    canonicalise_survey_frame,
)

DATASET_ID = "2mpz"
GLOBAL_REDSHIFT_SIGMA = 0.015


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_chunks(path: Path, chunk_rows: int) -> Iterator[pd.DataFrame]:
    yield from pd.read_csv(path, chunksize=chunk_rows, skipinitialspace=True, low_memory=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=PROJECT_ROOT / "data" / "raw" / "2mpz" / "2mpz_source.csv"
    )
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "processed" / "2mpz")
    parser.add_argument("--chunk-rows", type=int, default=100_000)
    parser.add_argument("--overview-max-points", type=int, default=100_000)
    parser.add_argument("--radial-shell-mpc", type=float, default=180.0)
    parser.add_argument("--ra-bins", type=int, default=24)
    parser.add_argument("--dec-bins", type=int, default=12)
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing local tile-store output.")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Raw 2MPZ source file not found: {args.input}")
        print("Run scripts/download_2mpz.py first, or provide --input.")
        return 2
    if args.chunk_rows < 1 or args.overview_max_points < 1:
        print("--chunk-rows and --overview-max-points must be positive.")
        return 2
    if args.output.exists() and any(args.output.iterdir()):
        allowed = {".gitkeep"}
        contents = {entry.name for entry in args.output.iterdir()}
        if contents - allowed:
            if not args.overwrite:
                print(f"Output already contains a tile store: {args.output}")
                print("Use --overwrite to replace this local derived product.")
                return 2
            shutil.rmtree(args.output)
    args.output.mkdir(parents=True, exist_ok=True)

    descriptor = SurveyDescriptor(
        dataset_id=DATASET_ID,
        survey="2MASS Photometric Redshift Catalogue (2MPZ)",
        release="Bilicki et al. 2014, v1.1 (SSA twompzPhotoz table)",
        source_url="http://ssa.roe.ac.uk/TWOMPZ.html",
        citation_key="Bilicki2014_2MPZ",
        measurement_kind="photometric",
        object_type="galaxy",
        distance_note=(
            "Photometric-redshift Planck18 visual placement. 2MPZ publishes only a "
            "survey-wide accuracy figure, so the browser renders this layer as an "
            "uncertainty shell, never an exact point."
        ),
        global_redshift_sigma=GLOBAL_REDSHIFT_SIGMA,
        global_redshift_sigma_kind="constant",
    )

    writer = None
    accepted = 0
    raw_rows = 0
    try:
        for number, chunk in enumerate(iter_chunks(args.input, args.chunk_rows), start=1):
            raw_rows += len(chunk)
            frame = canonicalise_survey_frame(
                chunk,
                descriptor,
                id_column="twomassID",
                ra_column="ra",
                dec_column="dec",
                redshift_column="zPhoto",
                redshift_error_column=None,
                cosmology_mode="interpolated",
                interpolation_z_max=1.0,
            )
            if writer is None:
                writer = ChunkedTileStoreWriter(
                    args.output,
                    descriptor=descriptor,
                    radial_shell_mpc=args.radial_shell_mpc,
                    ra_bins=args.ra_bins,
                    dec_bins=args.dec_bins,
                    overview_max_points=args.overview_max_points,
                )
            writer.ingest(frame)
            accepted += len(frame)
            print(f"Chunk {number}: read {raw_rows:,}; accepted {accepted:,}")
        if writer is None:
            raise RuntimeError("Source file had no readable rows.")
        manifest = writer.finalise(
            extra_manifest={
                "raw_file": args.input.name,
                "raw_file_sha256": sha256(args.input),
                "raw_row_count": raw_rows,
                "accepted_row_count": accepted,
                "overview_is_not_a_scientific_selection": True,
                "global_redshift_sigma_note": (
                    "sigma_z = 0.015 is the 2MPZ all-sky accuracy figure from Bilicki "
                    "et al. 2014, applied uniformly; it is not a per-object measurement."
                ),
            }
        )
    except Exception as exc:
        print(f"2mpz tile-store build failed: {exc}")
        return 3

    print(f"Built {manifest['record_count']:,} observed {descriptor.survey} rows.")
    print(f"Overview: {manifest['overview']['count']:,} deterministic observed rows.")
    print(f"Spatial tiles: {manifest['tile_count']:,}")
    print(f"Manifest: {args.output / 'index.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
