#!/usr/bin/env python3
"""Verify that a browser product is an observed 2MRS catalogue, not a generated field."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=Path("data/processed/2mrs/2mrs_lightcone.json"))
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    meta = payload.get("meta", {})
    objects = payload.get("objects", [])
    if meta.get("is_synthetic") is not False:
        raise SystemExit("Rejected: meta.is_synthetic must be false.")
    if meta.get("source_table") != "J/ApJS/199/26/table3":
        raise SystemExit("Rejected: unexpected source table.")
    if not objects:
        raise SystemExit("Rejected: no objects.")
    if any(row.get("is_synthetic") is not False for row in objects):
        raise SystemExit("Rejected: every object must be marked is_synthetic=false.")
    print(f"Verified {len(objects):,} observed 2MRS browser rows.")


if __name__ == "__main__":
    main()
