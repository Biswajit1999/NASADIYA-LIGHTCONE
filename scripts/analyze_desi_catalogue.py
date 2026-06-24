#!/usr/bin/env python3
"""Create descriptive, provenance-safe DESI DR1 LSS catalogue diagnostics.

This script scans every row in the released research Parquet bundle. It creates
selection-function diagnostics, coordinate-consistency checks and a deterministic
Cartesian slice. It deliberately does *not* estimate a two-point correlation function,
power spectrum, density field or physical underdensity: those require an appropriate
survey random catalogue, angular mask and tracer-specific selection treatment.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HASH_KEY = "0123456789abcdef"
TRACERS = ("BGS", "LRG", "ELG", "QSO", "UNKNOWN")
TRACER_COLOURS = {
    "BGS": "#2399d6",
    "LRG": "#d58a2a",
    "ELG": "#45a45b",
    "QSO": "#d95562",
    "UNKNOWN": "#7f8791",
}


def stable_hashes(ids: pd.Series) -> pd.Series:
    return pd.util.hash_pandas_object(
        ids.astype("string"),
        index=False,
        hash_key=HASH_KEY,
    ).astype("uint64")


def retain_lowest_hashes(
    current: pd.DataFrame | None,
    incoming: pd.DataFrame,
    limit: int,
) -> pd.DataFrame:
    incoming = incoming.copy()
    incoming["_stable_hash"] = stable_hashes(incoming["object_id"])
    candidates = incoming if current is None else pd.concat([current, incoming], ignore_index=True)
    if len(candidates) <= limit:
        return candidates
    return candidates.sort_values(
        ["_stable_hash", "object_id"],
        kind="mergesort",
        ignore_index=True,
    ).head(limit)


def finite_values(series: pd.Series) -> np.ndarray:
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    return values[np.isfinite(values)]


def histogram_quantile(counts: np.ndarray, edges: np.ndarray, q: float) -> float | None:
    total = int(counts.sum())
    if total == 0:
        return None
    target = q * total
    cumulative = np.cumsum(counts)
    index = int(np.searchsorted(cumulative, target, side="left"))
    index = min(max(index, 0), len(counts) - 1)
    previous = int(cumulative[index - 1]) if index else 0
    within = int(counts[index])
    fraction = 0.5 if within == 0 else (target - previous) / within
    return float(edges[index] + fraction * (edges[index + 1] - edges[index]))


def normalise_tracer(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["tracer"] = frame["tracer"].fillna("UNKNOWN").astype(str).str.upper()
    for column in ("redshift", "comoving_distance_mpc", "x_mpc", "y_mpc", "z_mpc"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    valid = frame[["redshift", "comoving_distance_mpc", "x_mpc", "y_mpc", "z_mpc"]].notna().all(axis=1)
    return frame.loc[valid].copy()


def scan_catalogue(
    input_path: Path,
    *,
    slice_z_mpc: float,
    slice_thickness_mpc: float,
    slice_render_rows: int,
    z_max: float,
    z_bins: int,
) -> tuple[pd.DataFrame, dict]:
    parquet = pq.ParquetFile(input_path)
    total_rows = int(parquet.metadata.num_rows)
    redshift_edges = np.linspace(0.0, z_max, z_bins + 1)
    z_histograms = defaultdict(lambda: np.zeros(z_bins, dtype=np.int64))
    tracer_counts: Counter[str] = Counter()
    residual_sums: Counter[str] = Counter()
    residual_sq_sums: Counter[str] = Counter()
    residual_abs_sums: Counter[str] = Counter()
    residual_counts: Counter[str] = Counter()
    residual_max_abs: defaultdict(float)
    slice_candidates: pd.DataFrame | None = None
    rows_above_z_max = 0
    columns = [
        "object_id",
        "tracer",
        "redshift",
        "comoving_distance_mpc",
        "x_mpc",
        "y_mpc",
        "z_mpc",
    ]
    half_thickness = slice_thickness_mpc / 2.0

    for batch in parquet.iter_batches(batch_size=200_000, columns=columns):
        frame = normalise_tracer(batch.to_pandas())
        if frame.empty:
            continue
        tracer_counts.update(frame["tracer"].tolist())
        for tracer, group in frame.groupby("tracer", sort=False):
            redshift = group["redshift"].to_numpy(dtype=float)
            z_histograms[tracer] += np.histogram(redshift, bins=redshift_edges)[0]
            rows_above_z_max += int(np.count_nonzero(redshift > z_max))

            radius = np.sqrt(
                group["x_mpc"].to_numpy(dtype=float) ** 2
                + group["y_mpc"].to_numpy(dtype=float) ** 2
                + group["z_mpc"].to_numpy(dtype=float) ** 2
            )
            residual = radius - group["comoving_distance_mpc"].to_numpy(dtype=float)
            residual_sums[tracer] += float(residual.sum())
            residual_sq_sums[tracer] += float(np.square(residual).sum())
            residual_abs_sums[tracer] += float(np.abs(residual).sum())
            residual_counts[tracer] += len(residual)
            residual_max_abs[tracer] = max(residual_max_abs[tracer], float(np.abs(residual).max()))

        in_slice = frame["z_mpc"].sub(slice_z_mpc).abs().le(half_thickness)
        if in_slice.any():
            slice_candidates = retain_lowest_hashes(
                slice_candidates,
                frame.loc[in_slice, ["object_id", "tracer", "x_mpc", "y_mpc", "z_mpc", "redshift"]],
                slice_render_rows,
            )

    tracer_statistics = {}
    for tracer in sorted(tracer_counts):
        count = int(tracer_counts[tracer])
        residual_count = int(residual_counts[tracer])
        mean = residual_sums[tracer] / residual_count if residual_count else None
        rms = (residual_sq_sums[tracer] / residual_count) ** 0.5 if residual_count else None
        mean_abs = residual_abs_sums[tracer] / residual_count if residual_count else None
        histogram = z_histograms[tracer]
        tracer_statistics[tracer] = {
            "rows": count,
            "redshift_p16": histogram_quantile(histogram, redshift_edges, 0.16),
            "redshift_median": histogram_quantile(histogram, redshift_edges, 0.50),
            "redshift_p84": histogram_quantile(histogram, redshift_edges, 0.84),
            "coordinate_radius_minus_chi_mean_mpc": mean,
            "coordinate_radius_minus_chi_rms_mpc": rms,
            "coordinate_radius_minus_chi_mean_abs_mpc": mean_abs,
            "coordinate_radius_minus_chi_max_abs_mpc": residual_max_abs[tracer],
        }

    if slice_candidates is None:
        slice_frame = pd.DataFrame(columns=["object_id", "tracer", "x_mpc", "y_mpc", "z_mpc", "redshift"])
    else:
        slice_frame = slice_candidates.drop(columns="_stable_hash").sort_values(
            "object_id", kind="mergesort", ignore_index=True
        )

    summary = {
        "format": "nasadiya-desi-catalogue-diagnostics/v1",
        "input_file": input_path.name,
        "input_rows": total_rows,
        "tracer_statistics": tracer_statistics,
        "redshift_histogram": {
            "z_min": 0.0,
            "z_max": z_max,
            "bins": z_bins,
            "rows_above_z_max": rows_above_z_max,
            "counts": {key: value.tolist() for key, value in sorted(z_histograms.items())},
        },
        "cartesian_slice": {
            "z_center_mpc": slice_z_mpc,
            "thickness_mpc": slice_thickness_mpc,
            "rendered_rows": int(len(slice_frame)),
            "selection": "exact global lowest object-ID hash values inside slice",
            "hash_key_contract": HASH_KEY,
        },
        "scientific_boundary": {
            "is_synthetic": False,
            "is_correlation_measurement": False,
            "is_density_reconstruction": False,
            "note": "Selection-sensitive clustering estimators require random catalogues and survey-mask treatment.",
        },
    }
    return slice_frame, summary


def write_statistics_csv(summary: dict, output_path: Path) -> None:
    fields = [
        "tracer",
        "rows",
        "redshift_p16",
        "redshift_median",
        "redshift_p84",
        "coordinate_radius_minus_chi_mean_mpc",
        "coordinate_radius_minus_chi_rms_mpc",
        "coordinate_radius_minus_chi_mean_abs_mpc",
        "coordinate_radius_minus_chi_max_abs_mpc",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for tracer, values in sorted(summary["tracer_statistics"].items()):
            writer.writerow({"tracer": tracer, **values})


def plot_tracer_fractions(summary: dict, output_path: Path, dpi: int) -> None:
    histogram = summary["redshift_histogram"]
    edges = np.linspace(histogram["z_min"], histogram["z_max"], histogram["bins"] + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    counts = np.vstack([
        np.asarray(histogram["counts"].get(tracer, np.zeros(histogram["bins"])), dtype=float)
        for tracer in TRACERS
        if tracer in histogram["counts"]
    ])
    labels = [tracer for tracer in TRACERS if tracer in histogram["counts"]]
    totals = counts.sum(axis=0)
    fractions = np.divide(counts, totals, out=np.zeros_like(counts), where=totals > 0)

    figure, axis = plt.subplots(figsize=(10.8, 5.8), dpi=dpi)
    cumulative = np.zeros_like(centres)
    for tracer, fraction in zip(labels, fractions):
        axis.fill_between(
            centres,
            cumulative,
            cumulative + fraction,
            step="mid",
            alpha=0.78,
            color=TRACER_COLOURS.get(tracer, "#7f8791"),
            label=tracer,
        )
        cumulative += fraction
    axis.set_xlim(histogram["z_min"], histogram["z_max"])
    axis.set_ylim(0.0, 1.0)
    axis.set_xlabel("Spectroscopic redshift, z")
    axis.set_ylabel("Fraction of observed rows per redshift bin")
    axis.set_title("DESI DR1 LSS — tracer composition by redshift", loc="left", pad=12)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=0.22)
    axis.legend(frameon=False, title="Tracer", ncol=4, loc="upper center")
    figure.text(
        0.125,
        0.02,
        "Descriptive observed-row fractions only. This is not a completeness-corrected population fraction.",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#4f5b66",
    )
    figure.subplots_adjust(bottom=0.14, left=0.11, right=0.97, top=0.90)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def plot_cartesian_slice(
    slice_frame: pd.DataFrame,
    summary: dict,
    output_path: Path,
    dpi: int,
) -> None:
    figure, axis = plt.subplots(figsize=(9.5, 8.2), dpi=dpi)
    for tracer in TRACERS:
        group = slice_frame.loc[slice_frame["tracer"] == tracer]
        if group.empty:
            continue
        axis.scatter(
            group["x_mpc"],
            group["y_mpc"],
            s=1.0,
            alpha=0.35,
            marker=".",
            color=TRACER_COLOURS.get(tracer, "#7f8791"),
            label=f"{tracer} ({len(group):,})",
            rasterized=True,
        )
    slice_meta = summary["cartesian_slice"]
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("X [Mpc]")
    axis.set_ylabel("Y [Mpc]")
    axis.set_title(
        "DESI DR1 LSS — observed Cartesian slice",
        loc="left",
        pad=12,
    )
    axis.grid(alpha=0.18)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, title="Rendered tracer rows", loc="upper right")
    figure.text(
        0.125,
        0.02,
        f"Slice: Z = {slice_meta['z_center_mpc']:.0f} Mpc, thickness = "
        f"{slice_meta['thickness_mpc']:.0f} Mpc  |  "
        f"Rendered: {slice_meta['rendered_rows']:,} exact deterministic rows. "
        "Not a density reconstruction.",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#4f5b66",
    )
    figure.subplots_adjust(bottom=0.14, left=0.11, right=0.97, top=0.92)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "research" / "desi_dr1_lss_research_bundle.parquet",
    )
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "figures")
    parser.add_argument("--slice-z-mpc", type=float, default=0.0)
    parser.add_argument("--slice-thickness-mpc", type=float, default=300.0)
    parser.add_argument("--slice-render-rows", type=int, default=100_000)
    parser.add_argument("--z-max", type=float, default=3.6)
    parser.add_argument("--z-bins", type=int, default=90)
    parser.add_argument("--dpi", type=int, default=240)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Research bundle not found: {args.input}")
        return 2
    if args.slice_thickness_mpc <= 0 or args.slice_render_rows < 1 or args.z_bins < 5:
        print("Slice thickness/render limit and redshift bins must be positive.")
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        slice_frame, summary = scan_catalogue(
            args.input,
            slice_z_mpc=args.slice_z_mpc,
            slice_thickness_mpc=args.slice_thickness_mpc,
            slice_render_rows=args.slice_render_rows,
            z_max=args.z_max,
            z_bins=args.z_bins,
        )
        summary_path = args.output_dir / "desi_dr1_catalogue_diagnostics.json"
        csv_path = args.output_dir / "desi_dr1_tracer_statistics.csv"
        fraction_path = args.output_dir / "desi_dr1_tracer_composition.png"
        slice_path = args.output_dir / "desi_dr1_cartesian_slice.png"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        write_statistics_csv(summary, csv_path)
        plot_tracer_fractions(summary, fraction_path, args.dpi)
        plot_cartesian_slice(slice_frame, summary, slice_path, args.dpi)
    except Exception as exc:
        print(f"DESI catalogue diagnostic build failed: {exc}")
        return 3

    print(f"Saved {summary_path}")
    print(f"Saved {csv_path}")
    print(f"Saved {fraction_path}")
    print(f"Saved {slice_path}")
    print(f"Slice render: {summary['cartesian_slice']['rendered_rows']:,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
