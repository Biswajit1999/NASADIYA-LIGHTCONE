#!/usr/bin/env python3
"""Create reproducible DESI DR1 LSS research figures from a Parquet bundle.

The script scans all rows for redshift and tracer summaries but only renders a
bounded deterministic subset in 3D. This keeps the plot responsive while ensuring
that the reported distribution statistics originate from the complete bundle.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HASH_KEY = "0123456789abcdef"
TRACERS = ("BGS", "LRG", "ELG", "QSO", "UNKNOWN")


def select_render_rows(frame: pd.DataFrame, fraction: float) -> pd.DataFrame:
    if fraction >= 1:
        return frame
    hashes = pd.util.hash_pandas_object(
        frame["object_id"].astype("string"),
        index=False,
        hash_key=HASH_KEY,
    ).astype("uint64")
    threshold = int(fraction * ((1 << 64) - 1))
    return frame.loc[hashes.le(threshold)].copy()


def evenly_reduce(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    if len(frame) <= limit:
        return frame
    stride = int(np.ceil(len(frame) / limit))
    return frame.iloc[::stride].head(limit).copy()


def scan_bundle(
    input_path: Path,
    *,
    render_rows: int,
    hist_z_max: float,
    hist_bins: int,
) -> tuple[pd.DataFrame, dict]:
    parquet = pq.ParquetFile(input_path)
    total_rows = parquet.metadata.num_rows
    fraction = min(1.0, (render_rows / max(total_rows, 1)) * 1.15)
    bins = np.linspace(0.0, hist_z_max, hist_bins + 1)
    histograms = defaultdict(lambda: np.zeros(hist_bins, dtype=np.int64))
    tracer_counts: Counter[str] = Counter()
    sampled_frames: list[pd.DataFrame] = []
    over_range = 0
    max_distance = 0.0
    max_lookback = 0.0
    columns = [
        "object_id",
        "tracer",
        "redshift",
        "comoving_distance_mpc",
        "lookback_time_gyr",
        "x_mpc",
        "y_mpc",
        "z_mpc",
    ]

    for batch in parquet.iter_batches(batch_size=200_000, columns=columns):
        frame = batch.to_pandas()
        frame["tracer"] = frame["tracer"].fillna("UNKNOWN").astype(str).str.upper()
        frame["redshift"] = pd.to_numeric(frame["redshift"], errors="coerce")
        valid = frame["redshift"].notna() & frame["redshift"].ge(0)
        frame = frame.loc[valid].copy()
        if frame.empty:
            continue
        tracer_counts.update(frame["tracer"].tolist())
        for tracer, group in frame.groupby("tracer", sort=False):
            values = group["redshift"].to_numpy(dtype=float)
            histograms[tracer] += np.histogram(values, bins=bins)[0]
            over_range += int(np.count_nonzero(values > hist_z_max))
        max_distance = max(
            max_distance,
            float(pd.to_numeric(frame["comoving_distance_mpc"], errors="coerce").max()),
        )
        max_lookback = max(
            max_lookback,
            float(pd.to_numeric(frame["lookback_time_gyr"], errors="coerce").max()),
        )
        sampled = select_render_rows(frame, fraction)
        if not sampled.empty:
            sampled_frames.append(sampled)

    if not sampled_frames:
        raise RuntimeError("No valid DESI rows were available for plotting.")
    render_frame = evenly_reduce(pd.concat(sampled_frames, ignore_index=True), render_rows)
    summary = {
        "input_file": input_path.name,
        "input_rows": int(total_rows),
        "rendered_rows": int(len(render_frame)),
        "render_selection": "deterministic object-ID hash, then stable stride cap",
        "tracer_counts": dict(sorted(tracer_counts.items())),
        "redshift_histogram": {
            "z_min": 0.0,
            "z_max": hist_z_max,
            "bins": hist_bins,
            "counts": {name: values.tolist() for name, values in sorted(histograms.items())},
            "rows_above_z_max": over_range,
        },
        "maximum_comoving_distance_mpc": max_distance,
        "maximum_lookback_time_gyr": max_lookback,
        "is_synthetic": False,
    }
    return render_frame, summary


def plot_3d(render_frame: pd.DataFrame, output_path: Path, dpi: int) -> None:
    figure = plt.figure(figsize=(11.0, 8.8), dpi=dpi)
    axis = figure.add_subplot(111, projection="3d")
    for tracer in TRACERS:
        group = render_frame.loc[render_frame["tracer"] == tracer]
        if group.empty:
            continue
        axis.scatter(
            group["x_mpc"],
            group["y_mpc"],
            group["z_mpc"],
            s=0.35,
            alpha=0.26,
            marker=".",
            label=f"{tracer} ({len(group):,})",
            depthshade=False,
            rasterized=True,
        )
    axis.set_xlabel("X [Mpc]")
    axis.set_ylabel("Y [Mpc]")
    axis.set_zlabel("Z [Mpc]")
    axis.set_title("DESI DR1 LSS: deterministic observed 3D rendering subset")
    axis.view_init(elev=19, azim=-58)
    axis.legend(loc="upper left", frameon=False, markerscale=7)
    figure.text(
        0.5,
        0.02,
        "Observed DESI DR1 LSS rows; 3D rendering is a bounded deterministic subset. "
        "No synthetic galaxies or reconstructed filaments.",
        ha="center",
        va="bottom",
        fontsize=8,
    )
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def plot_redshift_summary(summary: dict, output_path: Path, dpi: int) -> None:
    histogram = summary["redshift_histogram"]
    bins = np.linspace(histogram["z_min"], histogram["z_max"], histogram["bins"] + 1)
    centres = 0.5 * (bins[1:] + bins[:-1])
    figure, axis = plt.subplots(figsize=(10.5, 6.0), dpi=dpi)
    for tracer, values in histogram["counts"].items():
        axis.step(centres, values, where="mid", linewidth=1.2, label=tracer)
    axis.set_yscale("log")
    axis.set_xlabel("Spectroscopic redshift z")
    axis.set_ylabel("Observed rows per bin")
    axis.set_title("DESI DR1 LSS redshift distribution by tracer class")
    axis.grid(True, alpha=0.22)
    axis.legend(frameon=False, title="Tracer")
    figure.text(
        0.5,
        0.01,
        f"Full research bundle scan: {summary['input_rows']:,} observed rows. "
        f"Rows above z={histogram['z_max']:.1f}: {histogram['rows_above_z_max']:,}.",
        ha="center",
        va="bottom",
        fontsize=8,
    )
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "research" / "desi_dr1_lss_research_bundle.parquet",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "figures",
        help="Small PNG and JSON outputs suitable for normal Git history.",
    )
    parser.add_argument("--render-rows", type=int, default=120_000)
    parser.add_argument("--hist-z-max", type=float, default=5.0)
    parser.add_argument("--hist-bins", type=int, default=100)
    parser.add_argument("--dpi", type=int, default=240)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Research bundle not found: {args.input}")
        print("Run scripts/build_desi_research_bundle.py first.")
        return 2
    if args.render_rows < 1 or args.hist_z_max <= 0 or args.hist_bins < 5 or args.dpi < 72:
        print("Invalid plotting parameters.")
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        render_frame, summary = scan_bundle(
            args.input,
            render_rows=args.render_rows,
            hist_z_max=args.hist_z_max,
            hist_bins=args.hist_bins,
        )
        plot_3d(render_frame, args.output_dir / "desi_dr1_lss_3d_research_view.png", args.dpi)
        plot_redshift_summary(
            summary,
            args.output_dir / "desi_dr1_lss_redshift_summary.png",
            args.dpi,
        )
        summary_path = args.output_dir / "desi_dr1_lss_research_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"DESI research-figure build failed: {exc}")
        return 3

    print(f"Saved {args.output_dir / 'desi_dr1_lss_3d_research_view.png'}")
    print(f"Saved {args.output_dir / 'desi_dr1_lss_redshift_summary.png'}")
    print(f"Saved {summary_path}")
    print(f"3D render sample: {summary['rendered_rows']:,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
