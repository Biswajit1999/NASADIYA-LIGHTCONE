#!/usr/bin/env python3
"""Build a chunked observed photo-z tile store for 2MPZ or WISE × SuperCOSMOS.

The source file is read in chunks. The builder writes every accepted observed source
row to spatial tiles while keeping only a deterministic bounded overview in memory.
It never invents radial uncertainties and it does not commit raw/tile assets to Git.
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

from nasadiya_lightcone.photoz import (  # noqa: E402
    PHOTOZ_PROFILES,
    build_photoz_frame,
    infer_photoz_columns,
)
from nasadiya_lightcone.tiles import ChunkedTileStoreWriter  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_chunks(path: Path, chunk_rows: int) -> Iterator[pd.DataFrame]:
    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith((".fits", ".fit", ".fits.gz")):
        from astropy.io import fits
        from astropy.table import Table

        with fits.open(path, memmap=True) as hdul:
            hdu = next((item for item in hdul if isinstance(item, fits.BinTableHDU)), None)
            if hdu is None or hdu.data is None:
                raise RuntimeError(f"No binary table HDU found in {path}")
            total = len(hdu.data)
            for start in range(0, total, chunk_rows):
                yield Table(hdu.data[start : start + chunk_rows]).to_pandas()
        return
    if suffixes.endswith((".csv", ".csv.gz", ".tsv", ".tsv.gz")):
        separator = "\t" if ".tsv" in suffixes else ","
        yield from pd.read_csv(path, sep=separator, chunksize=chunk_rows, low_memory=False)
        return
    raise RuntimeError(f"Unsupported source format: {path.suffixes}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", choices=sorted(PHOTOZ_PROFILES), required=True)
    parser.add_argument(
        "--input",
        type=Path,
        help="Raw FITS/CSV source; defaults to data/raw/<survey>/<survey>_source.fits.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Tile-store directory; defaults to data/processed/<survey>.",
    )
    parser.add_argument("--chunk-rows", type=int, default=100_000)
    parser.add_argument("--overview-max-points", type=int, default=125_000)
    parser.add_argument("--radial-shell-mpc", type=float, default=180.0)
    parser.add_argument("--ra-bins", type=int, default=24)
    parser.add_argument("--dec-bins", type=int, default=12)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing local tile-store output.",
    )
    args = parser.parse_args()

    profile = PHOTOZ_PROFILES[args.survey]
    source = args.input or PROJECT_ROOT / "data" / "raw" / profile.dataset_id / (
        f"{profile.dataset_id}_source.fits"
    )
    output = args.output or PROJECT_ROOT / "data" / "processed" / profile.dataset_id
    if not source.exists():
        print(f"Raw {profile.dataset_id} source file not found: {source}")
        print(
            f"Run scripts/download_{profile.dataset_id.replace('-', '_')}.py first, "
            "or provide --input."
        )
        return 2
    if args.chunk_rows < 1 or args.overview_max_points < 1:
        print("--chunk-rows and --overview-max-points must be positive.")
        return 2
    if output.exists() and any(output.iterdir()):
        allowed = {".gitkeep"}
        contents = {entry.name for entry in output.iterdir()}
        if contents - allowed:
            if not args.overwrite:
                print(f"Output already contains a tile store: {output}")
                print("Use --overwrite to replace this local derived product.")
                return 2
            shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    writer = None
    mapping = None
    accepted = 0
    raw_rows = 0
    try:
        for number, chunk in enumerate(iter_chunks(source, args.chunk_rows), start=1):
            raw_rows += len(chunk)
            if mapping is None:
                mapping = infer_photoz_columns(chunk)
            frame, resolved_mapping, descriptor = build_photoz_frame(
                chunk,
                profile,
                mapping=mapping,
            )
            if resolved_mapping != mapping:
                raise RuntimeError("Source-column mapping changed between chunks.")
            if writer is None:
                writer = ChunkedTileStoreWriter(
                    output,
                    descriptor=descriptor,
                    radial_shell_mpc=args.radial_shell_mpc,
                    ra_bins=args.ra_bins,
                    dec_bins=args.dec_bins,
                    overview_max_points=args.overview_max_points,
                )
            writer.ingest(frame)
            accepted += len(frame)
            print(f"Chunk {number}: read {raw_rows:,}; accepted {accepted:,}")
        if writer is None or mapping is None:
            raise RuntimeError("Source file had no readable rows.")
        manifest = writer.finalise(
            extra_manifest={
                "raw_file": source.name,
                "raw_file_sha256": sha256(source),
                "raw_row_count": raw_rows,
                "accepted_row_count": accepted,
                "column_mapping": mapping.as_dict(),
                "overview_is_not_a_scientific_selection": True,
            }
        )
    except Exception as exc:
        print(f"{profile.dataset_id} tile-store build failed: {exc}")
        return 3

    print(f"Built {manifest['record_count']:,} observed {profile.survey} photo-z rows.")
    print(f"Overview: {manifest['overview']['count']:,} deterministic observed rows.")
    print(f"Spatial tiles: {manifest['tile_count']:,}")
    print(f"Manifest: {output / 'index.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
