#!/usr/bin/env python3
"""Create reproducible DESI DR1 LSS research figures from a Parquet bundle.

The complete observed bundle is scanned for tracer, redshift and footprint summaries.
A bounded exact deterministic subset is used only for the 3D scatter rendering, so
interactive-scale plotting never changes the catalogue-level statistics.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
FOOTPRINT_RA_BINS = 360
FOOTPRINT_DEC_BINS = 180


def stable_hashes(ids: pd.Series) -> pd.Series:
    """Return reproducible unsigned object-ID hashes for deterministic selection."""
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
    """Keep exactly the globally lowest object-ID hashes seen so far.

    This bounded streaming reduction avoids loading the full Parquet table into
    memory. Sorting the hash and object ID together also makes the vanishingly rare
    hash ties deterministic.
    """
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


def update_sky_histogram(
    histogram: np.ndarray,
    group: pd.DataFrame,
    dec_edges: np.ndarray,
    ra_edges: np.ndarray,
) -> None:
    coordinates = group.loc[group["ra_deg"].notna() & group["dec_deg"].notna()]
    if coordinates.empty:
        return
    counts, _, _ = np.histogram2d(
        np.clip(coordinates["dec_deg"].to_numpy(dtype=float), -90.0, 90.0),
        np.mod(coordinates["ra_deg"].to_numpy(dtype=float), 360.0),
        bins=[dec_edges, ra_edges],
    )
    histogram += counts.astype(np.int64)


def scan_bundle(
    input_path: Path,
    *,
    render_rows: int,
    hist_z_max: float,
    hist_bins: int,
) -> tuple[pd.DataFrame, dict, dict[str, np.ndarray]]:
    parquet = pq.ParquetFile(input_path)
    total_rows = parquet.metadata.num_rows
    bins = np.linspace(0.0, hist_z_max, hist_bins + 1)
    ra_edges = np.linspace(0.0, 360.0, FOOTPRINT_RA_BINS + 1)
    dec_edges = np.linspace(-90.0, 90.0, FOOTPRINT_DEC_BINS + 1)
    histograms = defaultdict(lambda: np.zeros(hist_bins, dtype=np.int64))
    sky_histograms = {
        tracer: np.zeros((FOOTPRINT_DEC_BINS, FOOTPRINT_RA_BINS), dtype=np.int64)
        for tracer in TRACERS
    }
    tracer_counts: Counter[str] = Counter()
    render_candidates: pd.DataFrame | None = None
    over_range = 0
    max_distance = 0.0
    max_lookback = 0.0
    max_redshift = 0.0
    columns = [
        "object_id",
        "tracer",
        "ra_deg",
        "dec_deg",
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
        frame["ra_deg"] = pd.to_numeric(frame["ra_deg"], errors="coerce")
        frame["dec_deg"] = pd.to_numeric(frame["dec_deg"], errors="coerce")
        valid = frame["redshift"].notna() & frame["redshift"].ge(0)
        frame = frame.loc[valid].copy()
        if frame.empty:
            continue

        tracer_counts.update(frame["tracer"].tolist())
        max_redshift = max(max_redshift, float(frame["redshift"].max()))
        for tracer, group in frame.groupby("tracer", sort=False):
            values = group["redshift"].to_numpy(dtype=float)
            histograms[tracer] += np.histogram(values, bins=bins)[0]
            over_range += int(np.count_nonzero(values > hist_z_max))
            if tracer not in sky_histograms:
                sky_histograms[tracer] = np.zeros(
                    (FOOTPRINT_DEC_BINS, FOOTPRINT_RA_BINS),
                    dtype=np.int64,
                )
            update_sky_histogram(sky_histograms[tracer], group, dec_edges, ra_edges)

        max_distance = max(
            max_distance,
            float(pd.to_numeric(frame["comoving_distance_mpc"], errors="coerce").max()),
        )
        max_lookback = max(
            max_lookback,
            float(pd.to_numeric(frame["lookback_time_gyr"], errors="coerce").max()),
        )
        render_candidates = retain_lowest_hashes(render_candidates, frame, render_rows)

    if render_candidates is None or render_candidates.empty:
        raise RuntimeError("No valid DESI rows were available for plotting.")
    render_frame = render_candidates.drop(columns="_stable_hash").copy()
    render_frame = render_frame.sort_values("object_id", kind="mergesort", ignore_index=True)
    summary = {
        "input_file": input_path.name,
        "input_rows": int(total_rows),
        "rendered_rows": int(len(render_frame)),
        "requested_render_rows": int(render_rows),
        "render_selection": "exact global lowest object-ID hash values",
        "hash_key_contract": HASH_KEY,
        "tracer_counts": dict(sorted(tracer_counts.items())),
        "render_tracer_counts": dict(
            sorted(render_frame["tracer"].value_counts().astype(int).to_dict().items())
        ),
        "redshift_histogram": {
            "z_min": 0.0,
            "z_max": hist_z_max,
            "bins": hist_bins,
            "counts": {name: values.tolist() for name, values in sorted(histograms.items())},
            "rows_above_z_max": over_range,
            "maximum_observed_redshift": max_redshift,
        },
        "sky_footprint": {
            "ra_bins": FOOTPRINT_RA_BINS,
            "dec_bins": FOOTPRINT_DEC_BINS,
            "bin_size_deg": [1.0, 1.0],
            "quantity": "observed rows per sky bin",
            "not_physical_density": True,
        },
        "maximum_comoving_distance_mpc": max_distance,
        "maximum_lookback_time_gyr": max_lookback,
        "is_synthetic": False,
    }
    return render_frame, summary, sky_histograms


def set_3d_panes_transparent(axis) -> None:
    for pane in (axis.xaxis.pane, axis.yaxis.pane, axis.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("#c5ccd4")


def plot_3d(
    render_frame: pd.DataFrame,
    summary: dict,
    output_path: Path,
    dpi: int,
) -> None:
    figure = plt.figure(figsize=(11.4, 9.1), dpi=dpi)
    axis = figure.add_subplot(111, projection="3d")
    set_3d_panes_transparent(axis)
    axis.grid(False)

    for tracer in TRACERS:
        group = render_frame.loc[render_frame["tracer"] == tracer]
        if group.empty:
            continue
        axis.scatter(
            group["x_mpc"],
            group["y_mpc"],
            group["z_mpc"],
            s=0.56,
            alpha=0.32,
            marker=".",
            color=TRACER_COLOURS.get(tracer, TRACER_COLOURS["UNKNOWN"]),
            label=f"{tracer} ({len(group):,})",
            depthshade=False,
            rasterized=True,
        )

    coordinates = render_frame[["x_mpc", "y_mpc", "z_mpc"]].to_numpy(dtype=float)
    spans = np.ptp(coordinates, axis=0)
    axis.set_box_aspect(tuple(spans / max(spans.max(), 1.0)))
    axis.set_xlabel("X [Mpc]", labelpad=8)
    axis.set_ylabel("Y [Mpc]", labelpad=8)
    axis.set_zlabel("Z [Mpc]", labelpad=8)
    axis.tick_params(labelsize=8, pad=1)
    axis.set_proj_type("ortho")
    axis.view_init(elev=19, azim=-58)
    axis.legend(
        loc="upper left",
        frameon=False,
        markerscale=8,
        fontsize=9,
        title="Rendered tracer rows",
        title_fontsize=9,
    )
    figure.suptitle(
        "DESI DR1 LSS — observed 3D survey footprint",
        x=0.5,
        y=0.965,
        fontsize=16,
        fontweight="semibold",
    )
    figure.text(
        0.5,
        0.935,
        f"Full bundle: {summary['input_rows']:,} observed rows  |  "
        f"Rendered: {summary['rendered_rows']:,} exact deterministic rows  |  "
        "Planck18 visual placement",
        ha="center",
        va="center",
        fontsize=9,
        color="#4f5b66",
    )
    figure.text(
        0.5,
        0.02,
        "Observed DESI DR1 LSS rows only. Separated regions trace survey footprint and target selection; "
        "no synthetic galaxies, interpolation or reconstructed filaments are shown.",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#4f5b66",
    )
    figure.subplots_adjust(left=0.03, right=0.97, bottom=0.07, top=0.90)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def plot_redshift_summary(summary: dict, output_path: Path, dpi: int) -> None:
    histogram = summary["redshift_histogram"]
    bins = np.linspace(histogram["z_min"], histogram["z_max"], histogram["bins"] + 1)
    centres = 0.5 * (bins[1:] + bins[:-1])
    figure, axis = plt.subplots(figsize=(10.6, 6.25), dpi=dpi)

    for tracer in TRACERS:
        values = histogram["counts"].get(tracer)
        if not values:
            continue
        count = summary["tracer_counts"].get(tracer, 0)
        axis.step(
            centres,
            values,
            where="mid",
            linewidth=1.55,
            color=TRACER_COLOURS.get(tracer, TRACER_COLOURS["UNKNOWN"]),
            label=f"{tracer} ({count:,})",
        )

    axis.set_yscale("log")
    axis.set_xlim(histogram["z_min"], histogram["z_max"])
    axis.set_xlabel("Spectroscopic redshift, z")
    axis.set_ylabel("Observed rows per bin")
    axis.set_title("DESI DR1 LSS — full-bundle redshift distribution", loc="left", pad=12)
    axis.grid(axis="y", alpha=0.22)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, title="Tracer", ncol=2, loc="upper right")
    figure.text(
        0.125,
        0.02,
        f"Full observed bundle scan: {summary['input_rows']:,} rows  |  "
        f"z ≤ {histogram['z_max']:.1f}: {summary['input_rows'] - histogram['rows_above_z_max']:,} rows  |  "
        f"Above range: {histogram['rows_above_z_max']:,}",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#4f5b66",
    )
    figure.subplots_adjust(bottom=0.13, left=0.11, right=0.97, top=0.91)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def plot_sky_footprint(
    sky_histograms: dict[str, np.ndarray],
    summary: dict,
    output_path: Path,
    dpi: int,
) -> None:
    display_tracers = tuple(tracer for tracer in TRACERS if tracer != "UNKNOWN")
    panels = [sky_histograms.get(tracer, np.zeros((FOOTPRINT_DEC_BINS, FOOTPRINT_RA_BINS))) for tracer in display_tracers]
    maximum = max(float(np.log10(panel + 1).max()) for panel in panels)
    figure, axes = plt.subplots(2, 2, figsize=(12.4, 7.5), dpi=dpi, sharex=True, sharey=True)
    image = None
    for axis, tracer, panel in zip(axes.ravel(), display_tracers, panels):
        image = axis.imshow(
            np.log10(panel + 1),
            extent=(360.0, 0.0, -90.0, 90.0),
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            cmap="magma",
            vmin=0.0,
            vmax=maximum,
        )
        axis.set_title(
            f"{tracer}  ·  {summary['tracer_counts'].get(tracer, 0):,} observed rows",
            loc="left",
            fontsize=10,
            fontweight="semibold",
        )
        axis.set_xlabel("Right ascension [deg]")
        axis.set_ylabel("Declination [deg]")
        axis.set_xticks([360, 300, 240, 180, 120, 60, 0])
        axis.grid(alpha=0.16, linewidth=0.55)

    figure.suptitle(
        "DESI DR1 LSS — observed sky footprint by tracer class",
        x=0.5,
        y=0.98,
        fontsize=15,
        fontweight="semibold",
    )
    if image is not None:
        colourbar = figure.colorbar(image, ax=axes.ravel().tolist(), shrink=0.86, pad=0.02)
        colourbar.set_label(r"$\log_{10}$(observed rows + 1) per 1° × 1° bin")
    figure.text(
        0.5,
        0.012,
        "Counts show survey footprint, targeting and completeness structure. They are not an estimate of physical sky density.",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#4f5b66",
    )
    figure.subplots_adjust(left=0.07, right=0.91, bottom=0.10, top=0.90, wspace=0.16, hspace=0.24)
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
    parser.add_argument("--hist-z-max", type=float, default=3.6)
    parser.add_argument("--hist-bins", type=int, default=90)
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
        render_frame, summary, sky_histograms = scan_bundle(
            args.input,
            render_rows=args.render_rows,
            hist_z_max=args.hist_z_max,
            hist_bins=args.hist_bins,
        )
        plot_3d(
            render_frame,
            summary,
            args.output_dir / "desi_dr1_lss_3d_research_view.png",
            args.dpi,
        )
        plot_redshift_summary(
            summary,
            args.output_dir / "desi_dr1_lss_redshift_summary.png",
            args.dpi,
        )
        plot_sky_footprint(
            sky_histograms,
            summary,
            args.output_dir / "desi_dr1_lss_sky_footprint.png",
            args.dpi,
        )
        summary_path = args.output_dir / "desi_dr1_lss_research_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"DESI research-figure build failed: {exc}")
        return 3

    print(f"Saved {args.output_dir / 'desi_dr1_lss_3d_research_view.png'}")
    print(f"Saved {args.output_dir / 'desi_dr1_lss_redshift_summary.png'}")
    print(f"Saved {args.output_dir / 'desi_dr1_lss_sky_footprint.png'}")
    print(f"Saved {summary_path}")
    print(f"3D render sample: {summary['rendered_rows']:,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
