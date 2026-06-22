#!/usr/bin/env python3
"""Build a chunked browser tile store from downloaded DESI DR1 LSS products."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Iterator

from astropy.io import fits
from astropy.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from nasadiya_lightcone.desi import build_desi_frame  # noqa: E402
from nasadiya_lightcone.tiles import ChunkedTileStoreWriter  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def iter_fits_chunks(path: Path, chunk_rows: int) -> Iterator:
    with fits.open(path, memmap=True) as hdul:
        hdu = next((item for item in hdul if isinstance(item, fits.BinTableHDU)), None)
        if hdu is None or hdu.data is None:
            raise RuntimeError(f"No binary table HDU in {path.name}")
        for start in range(0, len(hdu.data), chunk_rows):
            yield Table(hdu.data[start:start + chunk_rows]).to_pandas()


def component_from_file(path: Path) -> str:
    name = path.name.upper()
    for component, token in (("bgs", "BGS_"), ("lrg", "LRG_"), ("elg", "ELG_"), ("qso", "QSO_")):
        if token in name:
            return component
    raise RuntimeError(f"Could not identify DESI tracer from {path.name}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "raw" / "desi-dr1")
    p.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "processed" / "desi-dr1")
    p.add_argument("--chunk-rows", type=int, default=250_000)
    p.add_argument("--overview-max-points", type=int, default=125_000)
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()
    files = sorted(args.input.glob("*_clustering.dat.fits"))
    if not files:
        print(f"No DESI clustering FITS files found in {args.input}")
        print("Run scripts/download_desi_dr1_lss.py --yes first.")
        return 2
    if args.output.exists() and any(args.output.iterdir()) and not args.overwrite:
        print(f"Output already exists: {args.output}; use --overwrite to replace it.")
        return 2
    if args.output.exists() and args.overwrite:
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True, exist_ok=True)

    writer = None
    raw_rows = accepted = 0
    file_metadata = []
    try:
        for path in files:
            component = component_from_file(path)
            per_file = {"filename": path.name, "component": component, "sha256": sha256(path), "raw_rows": 0, "accepted_rows": 0}
            for chunk_number, chunk in enumerate(iter_fits_chunks(path, args.chunk_rows), start=1):
                raw_rows += len(chunk); per_file["raw_rows"] += len(chunk)
                frame, mapping, descriptor = build_desi_frame(chunk, component=component, source_file=path.name)
                if writer is None:
                    writer = ChunkedTileStoreWriter(args.output, descriptor=descriptor, radial_shell_mpc=320.0, ra_bins=36, dec_bins=18, overview_max_points=args.overview_max_points)
                writer.ingest(frame)
                accepted += len(frame); per_file["accepted_rows"] += len(frame)
                print(f"{path.name} chunk {chunk_number}: read {per_file['raw_rows']:,}; accepted {per_file['accepted_rows']:,}")
            file_metadata.append(per_file)
        if writer is None:
            raise RuntimeError("No rows were read.")
        manifest = writer.finalise(extra_manifest={"raw_row_count": raw_rows, "accepted_row_count": accepted, "files": file_metadata, "overview_is_not_a_scientific_selection": True})
    except Exception as exc:
        print(f"DESI DR1 tile-store build failed: {exc}")
        return 3
    print(f"Built {manifest['record_count']:,} observed DESI DR1 LSS rows.")
    print(f"Overview: {manifest['overview']['count']:,} deterministic observed rows.")
    print(f"Spatial tiles: {manifest['tile_count']:,}")
    print(f"Manifest: {args.output / 'index.json'}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
