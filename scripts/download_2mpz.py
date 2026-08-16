#!/usr/bin/env python3
"""Download the real 2MPZ (2MASS Photometric Redshift Catalogue) source table.

2MPZ is served by the Wide Field Astronomy Unit's SuperCOSMOS Science Archive
(SSA) as a SQL Server table (``TWOMPZ..twompzPhotoz``), not as a static bulk
file. This submits the documented SQL Cookbook query
(http://ssa.roe.ac.uk/sqlcookbook.html, section 6) through the SSA's
freeform-SQL CGI endpoint and downloads the generated results file.

2MPZ publishes only one survey-wide photometric-redshift accuracy figure
(sigma_z = 0.015; Bilicki et al. 2014, http://ssa.roe.ac.uk/TWOMPZ.html) -
there is no per-object uncertainty column in twompzPhotoz. This downloader
does not fabricate one; the tile-store builder records that single number at
the manifest level so the browser renders 2MPZ as an uncertainty shell, never
as exact points.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from nasadiya_lightcone.http_download import download_file  # noqa: E402

SQL_ENDPOINT = "http://ssa.roe.ac.uk:8080/ssa/SSASQL"
SOURCE_URL = "http://ssa.roe.ac.uk/TWOMPZ.html"
SQL_QUERY = "SELECT twomassID, ra, dec, zPhoto, zSpec FROM TWOMPZ..twompzPhotoz"
USER_AGENT = "NasadiyaLightcone/1.5 (public-survey-ingestion)"
GLOBAL_REDSHIFT_SIGMA = 0.015
EXPECTED_MIN_ROWS = 900_000


def submit_query(sql: str, *, max_rows: int, timeout_seconds: int) -> str:
    """Submit the SQL query and return the generated results-file URL."""
    response = requests.post(
        SQL_ENDPOINT,
        data={
            "sqlstmt": sql,
            "format": "CSV",
            "compress": "NONE",
            "rows": str(max_rows),
            # The hidden form field is literally named "action" with value
            # "freeform" - it is not the submit button's label. Sending any
            # other value (e.g. "Submit") makes the server silently ignore
            # sqlstmt and report "must be a select statement".
            "action": "freeform",
            "server": "amachine",
            "emailAddress": "",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    error_match = re.search(r"SQL Error:</b>\s*([^<]+)", response.text)
    if error_match:
        raise RuntimeError(f"SSA SQL query failed: {error_match.group(1).strip()}")
    link_match = re.search(r'href="(http://ssa\.roe\.ac\.uk/tmp/[^"]+\.csv)"', response.text)
    if not link_match:
        raise RuntimeError(
            "SSA did not return a results-file link; the query service may be offline."
        )
    return link_match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "data" / "raw" / "2mpz" / "2mpz_source.csv"
    )
    parser.add_argument(
        "--max-rows", type=int, default=1_500_000,
        help="Safety ceiling passed to the SQL service; the real table has ~934k rows.",
    )
    parser.add_argument("--query-timeout", type=int, default=180)
    parser.add_argument(
        "--probe", action="store_true",
        help="Run a 3-row probe query only; do not download the full table.",
    )
    args = parser.parse_args()

    query = "SELECT TOP 3 twomassID, ra, dec, zPhoto, zSpec FROM TWOMPZ..twompzPhotoz" if args.probe else SQL_QUERY
    print(f"Submitting SSA SQL query ({'probe' if args.probe else 'full table'})...")
    try:
        results_url = submit_query(
            query, max_rows=3 if args.probe else args.max_rows, timeout_seconds=args.query_timeout
        )
    except Exception as exc:
        print(f"2MPZ query failed: {exc}")
        print("No raw file was written.")
        return 3
    print(f"Results file: {results_url}")

    if args.probe:
        print("Probe succeeded. Run without --probe to download the full table.")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = download_file(results_url, args.output, overwrite=True, timeout_seconds=args.query_timeout)
    except Exception as exc:
        print(f"Downloading results file failed: {exc}")
        return 3

    with args.output.open("r", encoding="utf-8", errors="replace") as handle:
        row_count = sum(1 for _ in handle) - 1
    if row_count < EXPECTED_MIN_ROWS:
        print(
            f"Downloaded only {row_count:,} rows; expected at least {EXPECTED_MIN_ROWS:,}. "
            "Refusing to publish a truncated source file."
        )
        args.output.unlink(missing_ok=True)
        return 3

    metadata = {
        "dataset_id": "2mpz",
        "survey": "2MASS Photometric Redshift Catalogue (2MPZ)",
        "provider": "ssa-sql",
        "source_url": SOURCE_URL,
        "sql_query": query,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "raw_file": args.output.name,
        "row_count": row_count,
        "sha256": result.sha256,
        "bytes": result.bytes_written,
        "is_synthetic": False,
        "global_redshift_sigma": GLOBAL_REDSHIFT_SIGMA,
        "global_redshift_sigma_kind": "constant",
        "global_redshift_sigma_note": (
            "2MPZ publishes only a survey-wide photo-z accuracy figure "
            "(sigma_z = 0.015; Bilicki et al. 2014); no per-object uncertainty "
            "column exists in the twompzPhotoz table."
        ),
    }
    args.output.with_suffix(".source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved 2MPZ source file: {args.output}")
    print(f"Rows: {row_count:,}")
    print("Next: scripts/build_2mpz_tile_store.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
