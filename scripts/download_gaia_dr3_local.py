#!/usr/bin/env python3
"""Acquire a bounded, quality-cut Gaia DR3 local stellar sample.

Gaia is deliberately not included in the extragalactic lightcone. This script creates
an explicit local Milky Way sample from Gaia DR3 using public TAP queries; it does not
claim to download the full Gaia catalogue.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rows", type=int, default=1_000_000, help="Maximum total rows across all RA bins.")
    parser.add_argument("--ra-bin-deg", type=float, default=12.0, help="RA width per public TAP query.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "raw" / "gaia-dr3")
    parser.add_argument("--yes", action="store_true", help="Required to submit public TAP jobs.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.max_rows < 1 or not 0 < args.ra_bin_deg <= 180:
        print("--max-rows must be positive and --ra-bin-deg must lie in (0, 180].")
        return 2
    bins = int(ceil(360 / args.ra_bin_deg))
    per_bin = int(ceil(args.max_rows / bins))
    print("Gaia DR3 local-sample plan:")
    print(f"  Max total rows: {args.max_rows:,}")
    print(f"  RA bins: {bins}; cap per bin: {per_bin:,}")
    print("  Quality cuts: parallax > 0; parallax_over_error >= 10; ruwe < 1.4; G <= 18")
    print("  This is a bounded stellar context sample, not the full Gaia DR3 catalogue.")
    if not args.yes:
        print("Review the plan then repeat with --yes.")
        return 2
    try:
        from astroquery.gaia import Gaia
    except ImportError:
        print("Missing astroquery. Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    produced = []; total = 0
    try:
        for index in range(bins):
            lo = index * args.ra_bin_deg
            hi = min(360.0, (index + 1) * args.ra_bin_deg)
            destination = args.output / f"gaia_dr3_ra_{index:03d}.fits"
            if destination.exists() and not args.overwrite:
                from astropy.table import Table
                count = len(Table.read(destination, memmap=True))
                produced.append({"file": destination.name, "ra_deg": [lo, hi], "rows": count, "reused": True})
                total += count
                continue
            query = f"""
            SELECT TOP {per_bin}
              source_id, ra, dec, parallax, parallax_error, phot_g_mean_mag, ruwe
            FROM gaiadr3.gaia_source
            WHERE ra >= {lo:.8f} AND ra < {hi:.8f}
              AND parallax > 0
              AND parallax_over_error >= 10
              AND ruwe < 1.4
              AND phot_g_mean_mag <= 18.0
            """
            job = Gaia.launch_job_async(query, dump_to_file=False)
            table = job.get_results()
            table.write(destination, overwrite=True)
            count = len(table); total += count
            produced.append({"file": destination.name, "ra_deg": [lo, hi], "rows": count, "reused": False})
            print(f"RA {lo:6.1f}–{hi:6.1f} deg: {count:,} rows; total {total:,}")
            if total >= args.max_rows:
                break
    except Exception as exc:
        print(f"Gaia DR3 acquisition failed: {exc}")
        return 3

    manifest = {
        "dataset_id": "gaia-dr3-local-sample",
        "survey": "Gaia DR3",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": total,
        "selection": {"max_rows": args.max_rows, "ra_bin_deg": args.ra_bin_deg, "cuts": "parallax>0; parallax_over_error>=10; ruwe<1.4; phot_g_mean_mag<=18"},
        "files": produced,
        "is_synthetic": False,
        "scope": "Milky Way stellar context; separate from extragalactic browser layers",
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved {total:,} observed Gaia DR3 stellar rows to {args.output}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
