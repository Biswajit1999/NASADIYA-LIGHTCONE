#!/usr/bin/env python3
"""Build a compact, separate Gaia DR3 local-star sample product.

The resulting JSON is intentionally *not* added to the extragalactic survey selector.
It preserves Gaia's galactic identity and lists the use of naive inverse-parallax
positions as a navigation visualisation, not a distance-inference product.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from astropy.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from nasadiya_lightcone.gaia import build_gaia_local_frame  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "raw" / "gaia-dr3")
    p.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "processed" / "gaia-dr3" / "local-star-sample.json")
    p.add_argument("--max-rows", type=int, default=250_000)
    args = p.parse_args()
    files = sorted(args.input.glob("gaia_dr3_ra_*.fits"))
    if not files:
        print(f"No Gaia FITS chunks found in {args.input}")
        print("Run scripts/download_gaia_dr3_local.py --yes first.")
        return 2
    parts=[]
    for file in files:
        parts.append(Table.read(file, memmap=True).to_pandas())
    raw=pd.concat(parts, ignore_index=True)
    frame=build_gaia_local_frame(raw)
    if len(frame) > args.max_rows:
        # Deterministic stride view, retains real rows and says so in metadata.
        frame=frame.iloc[::max(1, len(frame)//args.max_rows)].head(args.max_rows).copy()
    records=[]
    for row in frame.itertuples(index=False):
        values=row._asdict()
        records.append({key:(None if isinstance(value,float) and not np.isfinite(value) else value) for key,value in values.items()})
    payload={
        "format":"nasadiya-gaia-local-sample/v1",
        "dataset":{"dataset_id":"gaia-dr3-local-sample","survey":"Gaia DR3","measurement_kind":"astrometric","is_synthetic":False,"scope":"Milky Way stellar context only","distance_note":"Naive inverse-parallax visual placement; not a Bayesian distance inference"},
        "record_count":len(records),
        "selection":{"method":"deterministic-input-stride" if len(raw)>args.max_rows else "all-built-rows", "max_rows":args.max_rows},
        "records":records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, separators=(',',':')), encoding='utf-8')
    print(f"Built {len(records):,} observed Gaia DR3 local-star rows: {args.output}")
    return 0

if __name__=='__main__':
    raise SystemExit(main())
