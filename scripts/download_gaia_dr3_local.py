#!/usr/bin/env python3
"""Acquire a resumable, quality-cut Gaia DR3 local stellar sample.

Gaia is deliberately kept out of the extragalactic lightcone. This script builds a
bounded Milky-Way context sample from public Gaia DR3 TAP queries. Each right-
ascension bin is written atomically and reused on later runs, so a transient TAP
connection reset does not discard completed work.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
import random
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_existing(destination: Path) -> int | None:
    """Return an existing chunk's row count, or None when it should be rebuilt."""
    if not destination.exists():
        return None
    try:
        from astropy.table import Table

        return len(Table.read(destination, memmap=True))
    except Exception:
        return None


def _write_chunk_atomic(table, destination: Path) -> None:
    """Avoid treating an interrupted local write as a completed Gaia chunk."""
    temporary = destination.with_name(f"{destination.name}.part")
    temporary.unlink(missing_ok=True)
    table.write(temporary, format="fits", overwrite=True)
    temporary.replace(destination)


def _write_manifest(output: Path, *, max_rows: int, ra_bin_deg: float, per_bin: int, produced: list[dict], failures: list[dict], requested_bins: tuple[int, int]) -> None:
    total = sum(int(item["rows"]) for item in produced)
    manifest = {
        "dataset_id": "gaia-dr3-local-sample",
        "survey": "Gaia DR3",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": total,
        "selection": {
            "max_rows": max_rows,
            "ra_bin_deg": ra_bin_deg,
            "per_ra_bin_cap": per_bin,
            "cuts": "parallax>0; parallax_over_error>=10; ruwe<1.4; phot_g_mean_mag<=18",
            "selection_note": "Bounded TAP sample distributed across RA bins; not the full Gaia DR3 catalogue.",
        },
        "requested_bin_range": {"start_inclusive": requested_bins[0], "end_exclusive": requested_bins[1]},
        "files": produced,
        "failed_bins": failures,
        "is_complete": not failures,
        "is_synthetic": False,
        "scope": "Milky Way stellar context; separate from extragalactic browser layers",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _run_query_with_retry(Gaia, query: str, *, retries: int, retry_delay_seconds: float, bin_label: str):
    """Retry transient public-TAP failures with exponential backoff and jitter."""
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            job = Gaia.launch_job_async(query, dump_to_file=False, verbose=False)
            return job.get_results()
        except Exception as exc:  # TAP failures can be transport, status-polling, or server-side resets.
            last_error = exc
            if attempt >= retries:
                break
            delay = retry_delay_seconds * (2 ** (attempt - 1)) + random.uniform(0, min(8.0, retry_delay_seconds * 0.2))
            print(f"{bin_label}: attempt {attempt}/{retries} failed: {exc}")
            print(f"{bin_label}: waiting {delay:.0f} s before retrying…")
            time.sleep(delay)
    raise RuntimeError(f"{bin_label}: TAP query failed after {retries} attempts: {last_error}") from last_error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rows", type=int, default=1_000_000, help="Maximum total rows across all RA bins.")
    parser.add_argument("--ra-bin-deg", type=float, default=12.0, help="RA width per public TAP query.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "raw" / "gaia-dr3")
    parser.add_argument("--yes", action="store_true", help="Required to submit public TAP jobs.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing RA chunks before querying.")
    parser.add_argument("--retries", type=int, default=5, help="Attempts per TAP bin before stopping.")
    parser.add_argument("--retry-delay-seconds", type=float, default=30.0, help="Initial retry wait; later waits grow exponentially.")
    parser.add_argument("--start-bin", type=int, default=0, help="First RA bin, inclusive; useful for a small smoke test.")
    parser.add_argument("--end-bin", type=int, help="Last RA bin, exclusive; omit for all remaining bins.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue to later bins after a failed bin; otherwise stop and preserve progress.")
    args = parser.parse_args()
    if args.max_rows < 1 or not 0 < args.ra_bin_deg <= 180:
        print("--max-rows must be positive and --ra-bin-deg must lie in (0, 180].")
        return 2
    if args.retries < 1 or args.retry_delay_seconds <= 0:
        print("--retries must be at least 1 and --retry-delay-seconds must be positive.")
        return 2

    bins = int(ceil(360 / args.ra_bin_deg))
    start_bin = args.start_bin
    end_bin = bins if args.end_bin is None else args.end_bin
    if not 0 <= start_bin < bins or not start_bin < end_bin <= bins:
        print(f"Requested bin range must satisfy 0 <= start < end <= {bins}.")
        return 2
    per_bin = int(ceil(args.max_rows / bins))

    print("Gaia DR3 resumable local-sample plan:")
    print(f"  Max total rows: {args.max_rows:,}")
    print(f"  Full RA bins: {bins}; cap per bin: {per_bin:,}")
    print(f"  This run: bins {start_bin}–{end_bin - 1} ({start_bin * args.ra_bin_deg:.1f}–{min(360.0, end_bin * args.ra_bin_deg):.1f} deg)")
    print(f"  Retries per bin: {args.retries}; initial backoff: {args.retry_delay_seconds:.0f} s")
    print("  Quality cuts: parallax > 0; parallax_over_error >= 10; ruwe < 1.4; G <= 18")
    print("  This is a bounded stellar context sample, not the full Gaia DR3 catalogue.")
    if not args.yes:
        print("Review the plan then repeat with --yes.")
        return 2

    try:
        from astroquery.gaia import Gaia

        Gaia.ROW_LIMIT = -1
    except ImportError:
        print("Missing astroquery. Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    produced: list[dict] = []
    failures: list[dict] = []
    for index in range(bins):
        lo = index * args.ra_bin_deg
        hi = min(360.0, (index + 1) * args.ra_bin_deg)
        destination = args.output / f"gaia_dr3_ra_{index:03d}.fits"
        existing_count = None if args.overwrite else _read_existing(destination)
        if existing_count is not None:
            produced.append({"file": destination.name, "ra_deg": [lo, hi], "rows": existing_count, "reused": True})
            continue
        if not start_bin <= index < end_bin:
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
        label = f"RA {lo:6.1f}–{hi:6.1f} deg"
        try:
            table = _run_query_with_retry(Gaia, query, retries=args.retries, retry_delay_seconds=args.retry_delay_seconds, bin_label=label)
            _write_chunk_atomic(table, destination)
            count = len(table)
            produced.append({"file": destination.name, "ra_deg": [lo, hi], "rows": count, "reused": False})
            total = sum(int(item["rows"]) for item in produced)
            print(f"{label}: saved {count:,} rows; accumulated {total:,}")
            _write_manifest(args.output, max_rows=args.max_rows, ra_bin_deg=args.ra_bin_deg, per_bin=per_bin, produced=produced, failures=failures, requested_bins=(start_bin, end_bin))
        except Exception as exc:
            failures.append({"bin_index": index, "ra_deg": [lo, hi], "error": str(exc)})
            _write_manifest(args.output, max_rows=args.max_rows, ra_bin_deg=args.ra_bin_deg, per_bin=per_bin, produced=produced, failures=failures, requested_bins=(start_bin, end_bin))
            print(f"{label}: stopped after retries. Existing completed chunks are preserved.")
            if not args.continue_on_error:
                print("Rerun the same command later; the downloader resumes completed RA chunks automatically.")
                return 3

    _write_manifest(args.output, max_rows=args.max_rows, ra_bin_deg=args.ra_bin_deg, per_bin=per_bin, produced=produced, failures=failures, requested_bins=(start_bin, end_bin))
    total = sum(int(item["rows"]) for item in produced)
    if failures:
        print(f"Saved {total:,} observed Gaia DR3 rows with {len(failures)} failed RA bin(s).")
        print("Rerun the same command later to resume; only missing bins will be queried.")
        return 3
    print(f"Saved {total:,} observed Gaia DR3 stellar rows to {args.output}")
    print("Next: scripts/build_gaia_dr3_local_sample.py --max-rows 250000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
