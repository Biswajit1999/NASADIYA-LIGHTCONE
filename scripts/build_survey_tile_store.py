#!/usr/bin/env python3
"""Convert one real survey catalogue into a static multi-resolution NĀSADĪYA tile store.

This command intentionally requires explicit column mappings.  Survey catalogues reuse
short field names differently; defining the mapping on the command line makes every
spatial transform auditable.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd
from astropy.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from nasadiya_lightcone.tiles import (  # noqa: E402
    SurveyDescriptor,
    canonicalise_survey_frame,
    write_tile_store,
)


def read_catalog(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt", ".tsv"}:
        separator = "\t" if suffix == ".tsv" else None
        return pd.read_csv(path, sep=separator)
    if suffix in {".fits", ".fit", ".fz"}:
        return Table.read(path, memmap=True).to_pandas()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported source format: {path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--survey", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--citation-key", required=True)
    parser.add_argument("--measurement-kind", choices=("spectroscopic", "photometric"), required=True)
    parser.add_argument("--object-type", default="galaxy")
    parser.add_argument("--id-column", required=True)
    parser.add_argument("--ra-column", required=True)
    parser.add_argument("--dec-column", required=True)
    parser.add_argument("--redshift-column", required=True)
    parser.add_argument("--redshift-error-column")
    parser.add_argument("--magnitude-column")
    parser.add_argument("--radial-shell-mpc", type=float, default=200.0)
    parser.add_argument("--ra-bins", type=int, default=24)
    parser.add_argument("--dec-bins", type=int, default=12)
    parser.add_argument("--overview-max-points", type=int, default=100_000)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Missing source file: {args.input}")
        return 2

    descriptor = SurveyDescriptor(
        dataset_id=args.dataset_id,
        survey=args.survey,
        release=args.release,
        source_url=args.source_url,
        citation_key=args.citation_key,
        measurement_kind=args.measurement_kind,
        object_type=args.object_type,
    )

    try:
        source = read_catalog(args.input)
        canonical = canonicalise_survey_frame(
            source,
            descriptor,
            id_column=args.id_column,
            ra_column=args.ra_column,
            dec_column=args.dec_column,
            redshift_column=args.redshift_column,
            redshift_error_column=args.redshift_error_column,
            magnitude_column=args.magnitude_column,
        )
        manifest = write_tile_store(
            canonical,
            args.output,
            descriptor=descriptor,
            radial_shell_mpc=args.radial_shell_mpc,
            ra_bins=args.ra_bins,
            dec_bins=args.dec_bins,
            overview_max_points=args.overview_max_points,
        )
    except Exception as exc:  # CLI boundary
        print(f"Tile-store build failed: {exc}")
        return 3

    print(f"Built {manifest['record_count']:,} observed {descriptor.survey} rows.")
    print(f"Tiles: {manifest['tile_count']:,}")
    print(f"Index: {args.output / 'index.json'}")
    print(f"Overview: {args.output / 'overview.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
