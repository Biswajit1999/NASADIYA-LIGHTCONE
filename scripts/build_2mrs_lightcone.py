#!/usr/bin/env python3
"""Transform a downloaded 2MRS Table 3 TSV into the browser data layer."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from nasadiya_lightcone import (  # noqa: E402
    build_2mrs_frame,
    enrich_with_planck18,
    parse_vizier_tsv,
    write_browser_catalog,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/2mrs/2mrs_table3.tsv"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/2mrs/2mrs_lightcone.json")
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Missing source file: {args.input}")
        print("Run: python scripts/download_2mrs.py")
        return 2

    try:
        source = parse_vizier_tsv(args.input)
        frame = enrich_with_planck18(build_2mrs_frame(source))
        digest = hashlib.sha256(args.input.read_bytes()).hexdigest()
        manifest = write_browser_catalog(frame, args.output, input_sha256=digest)
    except Exception as exc:  # CLI boundary
        print(f"2MRS build failed: {exc}")
        return 3

    print(f"Built {manifest['object_count']:,} real 2MRS rows.")
    print(f"Browser data: {args.output}")
    print(f"Manifest: {args.output.parent / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
