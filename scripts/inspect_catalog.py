#!/usr/bin/env python3
"""Print the schema of a survey file before defining an explicit ingestion mapping."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from astropy.table import Table


def read_catalog(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt", ".tsv"}:
        separator = "\t" if suffix == ".tsv" else None
        return pd.read_csv(path, sep=separator, nrows=5)
    if suffix in {".fits", ".fit", ".fz"}:
        return Table.read(path, memmap=True).to_pandas().head(5)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path).head(5)
    raise ValueError(f"Unsupported source format: {path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    if not args.input.exists():
        raise SystemExit(f"Missing source file: {args.input}")
    frame = read_catalog(args.input)
    print(f"Columns ({len(frame.columns)}):")
    for name, dtype in frame.dtypes.items():
        print(f"  {name}\t{dtype}")
    print("\nFirst rows:")
    print(frame.to_string(index=False, max_cols=20))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
