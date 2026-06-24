#!/usr/bin/env python3
"""Validate DESI LSS random catalogues before selection-corrected analysis.

This tool is deliberately a preflight diagnostic. It does not measure a two-point
correlation function or reconstruct density. It verifies that a supplied random
catalogue has the fields needed to be matched to the local DESI DR1 research bundle,
then writes tracer and redshift-composition diagnostics.

Examples
--------
python scripts/desi_lss_random_preflight.py \
  --data data/research/desi_dr1_lss_research_bundle.parquet \
  --random /path/to/desi_randoms.parquet \
  --output-dir figures/random_preflight
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = {
    "tracer": ("tracer", "TRACER", "target", "TARGET"),
    "redshift": ("redshift", "Z", "z"),
    "ra": ("ra", "RA"),
    "dec": ("dec", "DEC"),
    "weight": ("weight", "WEIGHT", "WEIGHT_SYS", "WEIGHT_COMP"),
}


def read_table(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path, columns=columns)
    if suffix == ".csv":
        return pd.read_csv(path, usecols=columns)
    raise ValueError(f"Unsupported file type: {path.suffix}. Use Parquet or CSV.")


def resolve_columns(columns: list[str]) -> dict[str, str | None]:
    available = set(columns)
    return {
        canonical: next((name for name in aliases if name in available), None)
        for canonical, aliases in CANONICAL.items()
    }


def normalise(frame: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    for canonical, source in mapping.items():
        if source is None:
            continue
        if canonical == "tracer":
            out[canonical] = frame[source].fillna("UNKNOWN").astype(str).str.upper()
        else:
            out[canonical] = pd.to_numeric(frame[source], errors="coerce")
    return out


def tracer_summary(frame: pd.DataFrame) -> list[dict]:
    if "tracer" not in frame:
        return []
    counts = frame["tracer"].value_counts(dropna=False).sort_index()
    total = int(counts.sum())
    return [
        {"tracer": str(tracer), "rows": int(rows), "fraction": float(rows / total) if total else None}
        for tracer, rows in counts.items()
    ]


def plot_redshift_comparison(data: pd.DataFrame, randoms: pd.DataFrame, path: Path, z_max: float, bins: int) -> None:
    if "redshift" not in data or "redshift" not in randoms:
        return
    edges = np.linspace(0.0, z_max, bins + 1)
    figure, axis = plt.subplots(figsize=(10.5, 5.8), dpi=200)
    for label, frame, linestyle in (("Science bundle", data, "-"), ("Random catalogue", randoms, "--")):
        values = frame["redshift"].to_numpy(float)
        values = values[np.isfinite(values) & (values >= 0.0) & (values <= z_max)]
        if values.size == 0:
            continue
        counts, _ = np.histogram(values, bins=edges)
        density = counts / counts.sum() if counts.sum() else counts
        centres = 0.5 * (edges[:-1] + edges[1:])
        axis.step(centres, density, where="mid", label=label, linestyle=linestyle, linewidth=1.8)
    axis.set_xlabel("Redshift")
    axis.set_ylabel("Normalised observed rows per bin")
    axis.set_title("DESI LSS preflight — science bundle versus supplied random catalogue", loc="left", pad=12)
    axis.grid(alpha=0.22)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False)
    figure.text(0.125, 0.02, "A visual diagnostic only. Matching requires tracer, mask, completeness and weighting checks.", fontsize=8, color="#4f5b66")
    figure.subplots_adjust(bottom=0.14, left=0.11, right=0.97, top=0.90)
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROJECT_ROOT / "data" / "research" / "desi_dr1_lss_research_bundle.parquet")
    parser.add_argument("--random", type=Path, required=True, help="DESI random catalogue in Parquet or CSV form.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "figures" / "random_preflight")
    parser.add_argument("--z-max", type=float, default=3.6)
    parser.add_argument("--z-bins", type=int, default=90)
    args = parser.parse_args()

    if not args.data.exists() or not args.random.exists():
        print("Both --data and --random must exist.")
        return 2

    data_raw = read_table(args.data)
    random_raw = read_table(args.random)
    data_map = resolve_columns(data_raw.columns.tolist())
    random_map = resolve_columns(random_raw.columns.tolist())
    data = normalise(data_raw, data_map)
    randoms = normalise(random_raw, random_map)

    required = ("redshift",)
    missing_data = [key for key in required if data_map[key] is None]
    missing_random = [key for key in required if random_map[key] is None]
    if missing_data or missing_random:
        print(f"Missing required redshift field. data={missing_data}, random={missing_random}")
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "format": "nasadiya-desi-random-preflight/v1",
        "science_bundle": {"file": args.data.name, "rows": int(len(data_raw)), "column_mapping": data_map, "tracers": tracer_summary(data)},
        "random_catalogue": {"file": args.random.name, "rows": int(len(random_raw)), "column_mapping": random_map, "tracers": tracer_summary(randoms)},
        "checks": {
            "science_has_redshift": data_map["redshift"] is not None,
            "random_has_redshift": random_map["redshift"] is not None,
            "science_has_tracer": data_map["tracer"] is not None,
            "random_has_tracer": random_map["tracer"] is not None,
            "science_has_ra_dec": data_map["ra"] is not None and data_map["dec"] is not None,
            "random_has_ra_dec": random_map["ra"] is not None and random_map["dec"] is not None,
            "random_has_weight": random_map["weight"] is not None,
        },
        "status": "PRELIMINARY_ONLY",
        "next_gate": "Use only tracer-matched, mask-consistent DESI random catalogues and documented weights before pair-count analysis.",
    }
    summary_path = args.output_dir / "desi_random_preflight.json"
    figure_path = args.output_dir / "desi_random_redshift_comparison.png"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    plot_redshift_comparison(data, randoms, figure_path, args.z_max, args.z_bins)

    print(f"Saved {summary_path}")
    if figure_path.exists():
        print(f"Saved {figure_path}")
    print("Status: PRELIMINARY_ONLY — no clustering or density inference was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
