#!/usr/bin/env python3
"""Science-first descriptive analysis of the DESI DR1 LSS observed catalogue.

This workflow asks astronomical questions that can be answered by the supplied
observed-row Parquet bundle:

* Which DESI tracer populations are observed at which redshifts and look-back
  times?
* How does the observed tracer mix change through the lightcone?
* How does the observed DESI footprint change across redshift slices?
* Are the stored observer-centred Cartesian coordinates consistent with the
  declared Planck18 redshift-to-distance conversion?

The output is intentionally explicit about its boundary: the supplied table is
an observed survey catalogue. Without the official random catalogues, masks,
weights and covariance products, this workflow must not be used to estimate a
physical number-density field, BAO scale, correlation function, power spectrum,
void catalogue, or cosmological parameter constraint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import textwrap

from astropy.cosmology import Planck18
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TRACER_ORDER = ("BGS", "LRG", "ELG", "QSO", "UNKNOWN")
TRACER_COLOURS = {
    "BGS": "#1f9bb6",
    "LRG": "#df7e24",
    "ELG": "#39a96b",
    "QSO": "#7f5bb7",
    "UNKNOWN": "#84939b",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "research" / "desi_dr1_lss_research_bundle.parquet",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "figures" / "desi_dr1_science",
    )
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--redshift-bins", type=int, default=72)
    parser.add_argument("--max-points-per-panel", type=int, default=45_000)
    parser.add_argument("--coordinate-validation-points", type=int, default=80_000)
    parser.add_argument("--seed", type=int, default=20260625)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_catalogue(path: Path) -> pd.DataFrame:
    required = ["object_id", "tracer", "ra_deg", "dec_deg", "redshift", "x_mpc", "y_mpc", "z_mpc"]
    frame = pd.read_parquet(path, columns=required).copy()
    for column in ("ra_deg", "dec_deg", "redshift", "x_mpc", "y_mpc", "z_mpc"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["object_id"] = frame["object_id"].astype("string")
    frame["tracer"] = frame["tracer"].fillna("UNKNOWN").astype(str).str.upper()
    valid = frame["object_id"].notna() & frame["object_id"].str.len().gt(0)
    valid &= np.isfinite(frame[["ra_deg", "dec_deg", "redshift", "x_mpc", "y_mpc", "z_mpc"]]).all(axis=1)
    valid &= frame["redshift"] >= 0
    valid &= frame["dec_deg"].between(-90.0, 90.0)
    frame = frame.loc[valid].copy()
    if frame.empty:
        raise ValueError("No valid observed rows remain after basic catalogue validation.")
    if frame["object_id"].duplicated().any():
        raise ValueError("Duplicate object identifiers remain after validation.")
    frame["radius_mpc"] = np.sqrt(frame["x_mpc"] ** 2 + frame["y_mpc"] ** 2 + frame["z_mpc"] ** 2)
    return frame.reset_index(drop=True)


def z_edges(frame: pd.DataFrame, bins: int) -> np.ndarray:
    upper = max(0.1, float(np.ceil(frame["redshift"].max() * 10.0) / 10.0))
    return np.linspace(0.0, upper, bins + 1)


def tracer_sequence(frame: pd.DataFrame) -> list[str]:
    observed = set(frame["tracer"].unique())
    ordered = [label for label in TRACER_ORDER if label in observed]
    ordered.extend(sorted(observed - set(ordered)))
    return ordered


def deterministic_subsample(frame: pd.DataFrame, max_rows: int, seed: int) -> pd.DataFrame:
    if len(frame) <= max_rows:
        return frame
    return frame.sample(n=max_rows, random_state=seed)


def redshift_slice_edges(frame: pd.DataFrame) -> np.ndarray:
    maximum = float(np.ceil(frame["redshift"].max() * 10.0) / 10.0)
    base = np.array([0.0, 0.4, 0.8, 1.4, maximum], dtype=float)
    base = np.unique(np.clip(base, 0.0, maximum))
    if len(base) < 3:
        base = np.linspace(0.0, maximum, 5)
    return base


def mollweide_longitude(ra_deg: pd.Series) -> np.ndarray:
    wrapped = ((ra_deg.to_numpy(dtype=float) + 180.0) % 360.0) - 180.0
    # Astronomical convention: right ascension increases to the left.
    return -np.deg2rad(wrapped)


def report_table(frame: pd.DataFrame, tracers: list[str]) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for tracer in tracers:
        subset = frame.loc[frame["tracer"] == tracer, "redshift"]
        if subset.empty:
            continue
        quantiles = subset.quantile([0.16, 0.50, 0.84])
        z16, z50, z84 = (float(quantiles.loc[q]) for q in (0.16, 0.50, 0.84))
        rows.append(
            {
                "tracer": tracer,
                "observed_rows": int(len(subset)),
                "observed_fraction": float(len(subset) / len(frame)),
                "z_16": z16,
                "z_median": z50,
                "z_84": z84,
                "lookback_gyr_16": float(Planck18.lookback_time(z16).value),
                "lookback_gyr_median": float(Planck18.lookback_time(z50).value),
                "lookback_gyr_84": float(Planck18.lookback_time(z84).value),
                "comoving_gpc_median": float(Planck18.comoving_distance(z50).value / 1000.0),
            }
        )
    return pd.DataFrame(rows)


def style(axis) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(alpha=0.18, linewidth=0.7)


def save_pair(figure: plt.Figure, output_dir: Path, stem: str, dpi: int) -> None:
    figure.savefig(output_dir / f"{stem}.png", dpi=dpi, bbox_inches="tight")
    figure.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(figure)


def plot_redshift_population(frame: pd.DataFrame, tracers: list[str], edges: np.ndarray, output_dir: Path, dpi: int) -> None:
    centres = 0.5 * (edges[:-1] + edges[1:])
    width = np.diff(edges)
    counts = np.vstack([np.histogram(frame.loc[frame["tracer"] == tracer, "redshift"], bins=edges)[0] for tracer in tracers])
    total = counts.sum(axis=0)
    fractions = np.divide(counts, total, out=np.zeros_like(counts, dtype=float), where=total > 0)

    figure, axes = plt.subplots(2, 1, figsize=(12, 9), dpi=dpi, sharex=True, gridspec_kw={"height_ratios": [1.05, 0.95]})
    for tracer, values in zip(tracers, counts):
        if values.sum():
            axes[0].step(centres, values / width, where="mid", linewidth=1.9, color=TRACER_COLOURS.get(tracer, "#555555"), label=tracer)
    axes[0].set_yscale("log")
    axes[0].set_ylabel(r"Observed rows per $\Delta z$")
    axes[0].set_title("DESI DR1 LSS: observed redshift distributions by tracer", loc="left", fontweight="bold")
    axes[0].legend(title="Target class", frameon=False, ncol=min(5, len(tracers)))
    style(axes[0])

    lower = np.zeros_like(centres)
    for tracer, values in zip(tracers, fractions):
        axes[1].fill_between(centres, lower, lower + values, step="mid", color=TRACER_COLOURS.get(tracer, "#555555"), alpha=0.90, label=tracer)
        lower += values
    axes[1].set_xlabel("Spectroscopic redshift, z")
    axes[1].set_ylabel("Fraction of observed rows")
    axes[1].set_ylim(0.0, 1.0)
    axes[1].set_title("Observed tracer mix through the lightcone", loc="left", fontweight="bold")
    style(axes[1])
    figure.text(0.10, 0.012, "These are observed target distributions. They are shaped by DESI target selection, observing strategy and footprint; they are not volume-corrected galaxy or quasar population fractions.", fontsize=9)
    figure.tight_layout(rect=(0, 0.035, 1, 1))
    save_pair(figure, output_dir, "fig_01_redshift_population", dpi)


def plot_cosmic_epochs(summary: pd.DataFrame, output_dir: Path, dpi: int) -> None:
    summary = summary.sort_values("z_median", ascending=True).reset_index(drop=True)
    y = np.arange(len(summary))
    figure, axis = plt.subplots(figsize=(12, 5.8), dpi=dpi)
    for index, row in summary.iterrows():
        colour = TRACER_COLOURS.get(row["tracer"], "#555555")
        axis.hlines(index, row["z_16"], row["z_84"], color=colour, linewidth=5.0, alpha=0.75)
        axis.scatter(row["z_median"], index, s=95, color=colour, edgecolor="white", linewidth=1.1, zorder=3)
        axis.text(row["z_84"] + 0.03, index, f"{int(row['observed_rows']):,} rows", va="center", fontsize=10, color="#41515b")
    axis.set_yticks(y, summary["tracer"])
    axis.set_xlabel("Spectroscopic redshift, z")
    axis.set_title("Which cosmic epochs do the DESI tracer classes sample?", loc="left", fontweight="bold")
    style(axis)
    top = axis.twiny()
    z_ticks = np.linspace(0.0, max(0.2, float(summary["z_84"].max()) + 0.15), 6)
    top.set_xlim(axis.get_xlim())
    top.set_xticks(z_ticks)
    top.set_xticklabels([f"{Planck18.lookback_time(z).value:.1f}" for z in z_ticks])
    top.set_xlabel("Look-back time [Gyr], Planck18")
    for spine in top.spines.values():
        spine.set_visible(False)
    figure.text(0.10, 0.012, "Horizontal bars span the 16th–84th percentiles of the observed redshift distribution for each tracer; they do not define sharp physical redshift boundaries.", fontsize=9)
    figure.tight_layout(rect=(0, 0.04, 1, 1))
    save_pair(figure, output_dir, "fig_02_tracer_cosmic_epochs", dpi)


def plot_angular_slices(frame: pd.DataFrame, tracers: list[str], edges: np.ndarray, max_points: int, seed: int, output_dir: Path, dpi: int) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=dpi, subplot_kw={"projection": "mollweide"})
    for panel, (left, right) in enumerate(zip(edges[:-1], edges[1:])):
        axis = axes.flat[panel]
        upper = frame["redshift"] <= right if panel == len(edges) - 2 else frame["redshift"] < right
        subset = frame.loc[(frame["redshift"] >= left) & upper]
        subset = deterministic_subsample(subset, max_points, seed + panel)
        for tracer in tracers:
            group = subset.loc[subset["tracer"] == tracer]
            if group.empty:
                continue
            axis.scatter(mollweide_longitude(group["ra_deg"]), np.deg2rad(group["dec_deg"]), s=0.65, alpha=0.28, color=TRACER_COLOURS.get(tracer, "#555555"), rasterized=True, label=tracer)
        axis.set_title(f"{left:.1f} ≤ z < {right:.1f}\n{len(subset):,} displayed observed rows", fontsize=12, fontweight="bold", pad=12)
        axis.grid(alpha=0.23)
        axis.set_xticklabels(["150°", "120°", "90°", "60°", "30°", "0°", "330°", "300°", "270°", "240°", "210°"])
    handles, labels = axes.flat[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=min(5, len(handles)), frameon=False, title="Tracer class")
    figure.suptitle("Observed DESI angular footprint across redshift slices", x=0.10, ha="left", fontsize=17, fontweight="bold")
    figure.text(0.10, 0.018, "Mollweide projections show where the survey observed targets. Uneven coverage and empty regions are primarily footprint and target-selection effects, not evidence for physical underdensities.", fontsize=9)
    figure.tight_layout(rect=(0, 0.07, 1, 0.94))
    save_pair(figure, output_dir, "fig_03_angular_footprint_by_redshift", dpi)


def plot_cartesian_slices(frame: pd.DataFrame, tracers: list[str], edges: np.ndarray, max_points: int, seed: int, output_dir: Path, dpi: int) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 10), dpi=dpi, sharex=True, sharey=True)
    limit = float(np.nanquantile(np.abs(frame[["x_mpc", "y_mpc"]].to_numpy()), 0.997))
    for panel, (left, right) in enumerate(zip(edges[:-1], edges[1:])):
        axis = axes.flat[panel]
        upper = frame["redshift"] <= right if panel == len(edges) - 2 else frame["redshift"] < right
        subset = frame.loc[(frame["redshift"] >= left) & upper]
        subset = deterministic_subsample(subset, max_points, seed + 50 + panel)
        for tracer in tracers:
            group = subset.loc[subset["tracer"] == tracer]
            if group.empty:
                continue
            axis.scatter(group["x_mpc"], group["y_mpc"], s=0.55, alpha=0.26, color=TRACER_COLOURS.get(tracer, "#555555"), rasterized=True)
        axis.set_title(f"{left:.1f} ≤ z < {right:.1f}", fontsize=12, fontweight="bold")
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlim(-limit, limit)
        axis.set_ylim(-limit, limit)
        style(axis)
    for axis in axes[-1, :]:
        axis.set_xlabel("Observer-centred X [Mpc]")
    for axis in axes[:, 0]:
        axis.set_ylabel("Observer-centred Y [Mpc]")
    figure.suptitle("Observer-centred Cartesian views of the observed DESI lightcone", x=0.10, ha="left", fontsize=17, fontweight="bold")
    figure.text(0.10, 0.018, "Coordinates are derived from spectroscopic redshift, RA and Dec under Planck18. Point patterns retain the survey selection function and must not be interpreted as a reconstructed density field.", fontsize=9)
    figure.tight_layout(rect=(0, 0.05, 1, 0.94))
    save_pair(figure, output_dir, "fig_04_cartesian_redshift_slices", dpi)


def plot_observed_radial_selection(frame: pd.DataFrame, tracers: list[str], edges: np.ndarray, output_dir: Path, dpi: int) -> None:
    centres = 0.5 * (edges[:-1] + edges[1:])
    total = np.histogram(frame["redshift"], bins=edges)[0]
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.3), dpi=dpi)
    axes[0].step(centres, total, where="mid", color="#1a5b77", linewidth=2.2)
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Spectroscopic redshift, z")
    axes[0].set_ylabel("Observed rows per bin")
    axes[0].set_title("Observed radial selection, N(z)", loc="left", fontweight="bold")
    style(axes[0])

    for tracer in tracers:
        subset = frame.loc[frame["tracer"] == tracer, "redshift"]
        if subset.empty:
            continue
        values = np.histogram(subset, bins=edges)[0]
        cumulative = np.cumsum(values) / max(1, values.sum())
        axes[1].step(centres, cumulative, where="mid", linewidth=1.9, color=TRACER_COLOURS.get(tracer, "#555555"), label=tracer)
    axes[1].set_xlabel("Spectroscopic redshift, z")
    axes[1].set_ylabel("Cumulative fraction within tracer")
    axes[1].set_ylim(0.0, 1.02)
    axes[1].set_title("Cumulative tracer reach through cosmic time", loc="left", fontweight="bold")
    axes[1].legend(frameon=False)
    style(axes[1])
    figure.text(0.10, 0.012, "N(z) is an observed selection function. It combines intrinsic populations with DESI targeting, redshift success and survey coverage; it is not a physical comoving number-density measurement.", fontsize=9)
    figure.tight_layout(rect=(0, 0.035, 1, 1))
    save_pair(figure, output_dir, "fig_05_observed_radial_selection", dpi)


def plot_coordinate_consistency(frame: pd.DataFrame, max_points: int, seed: int, output_dir: Path, dpi: int) -> dict[str, float]:
    sample = deterministic_subsample(frame, max_points, seed).copy()
    expected = Planck18.comoving_distance(sample["redshift"].to_numpy(dtype=float)).value
    residual = sample["radius_mpc"].to_numpy(dtype=float) - expected
    relative = residual / np.maximum(expected, 1.0)
    figure, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), dpi=dpi)
    hexbin = axes[0].hexbin(expected / 1000.0, sample["radius_mpc"].to_numpy(dtype=float) / 1000.0, gridsize=90, bins="log", mincnt=1, cmap="viridis")
    maximum = max(float(np.nanmax(expected / 1000.0)), float(np.nanmax(sample["radius_mpc"].to_numpy(dtype=float) / 1000.0)))
    axes[0].plot([0, maximum], [0, maximum], color="white", linestyle="--", linewidth=1.2)
    axes[0].set_xlabel("Planck18 comoving distance from z [Gpc]")
    axes[0].set_ylabel("Stored Cartesian radius [Gpc]")
    axes[0].set_title("Coordinate conversion consistency", loc="left", fontweight="bold")
    axes[0].grid(alpha=0.15)
    figure.colorbar(hexbin, ax=axes[0], label="Rows per hexagon (log scale)")

    axes[1].scatter(sample["redshift"], relative * 1e6, s=0.55, alpha=0.16, color="#1f9bb6", rasterized=True)
    axes[1].axhline(0.0, color="#344955", linewidth=1.0)
    axes[1].set_xlabel("Spectroscopic redshift, z")
    axes[1].set_ylabel("(stored radius − Planck18 distance) / distance [ppm]")
    axes[1].set_title("Relative coordinate residuals", loc="left", fontweight="bold")
    style(axes[1])
    figure.text(0.10, 0.012, "This is a coordinate-pipeline validation. It checks that the stored Cartesian coordinates are consistent with the stated Planck18 conversion; it is not a cosmological parameter fit.", fontsize=9)
    figure.tight_layout(rect=(0, 0.035, 1, 1))
    save_pair(figure, output_dir, "fig_06_coordinate_consistency", dpi)
    return {
        "coordinate_validation_rows": int(len(sample)),
        "median_abs_distance_residual_mpc": float(np.median(np.abs(residual))),
        "p95_abs_distance_residual_mpc": float(np.quantile(np.abs(residual), 0.95)),
        "median_abs_relative_residual_ppm": float(np.median(np.abs(relative)) * 1e6),
        "p95_abs_relative_residual_ppm": float(np.quantile(np.abs(relative), 0.95) * 1e6),
    }


def markdown_report(summary: pd.DataFrame, catalogue: pd.DataFrame, coordinate: dict[str, float], digest: str) -> str:
    rows = []
    for _, item in summary.iterrows():
        rows.append(
            f"| {item['tracer']} | {int(item['observed_rows']):,} | {item['z_median']:.3f} | {item['z_16']:.3f}–{item['z_84']:.3f} | {item['lookback_gyr_median']:.2f} | {item['comoving_gpc_median']:.2f} |"
        )
    return "\n".join(
        [
            "# DESI DR1 science-first catalogue summary",
            "",
            "## What this run answers",
            "",
            "This analysis describes the observed DESI DR1 LSS tracer populations across redshift, cosmic time, sky position and observer-centred comoving coordinates.",
            "",
            "## Dataset",
            "",
            f"- Valid observed rows: **{len(catalogue):,}**.",
            f"- Input SHA-256: `{digest}`.",
            f"- Observed redshift range: **{catalogue['redshift'].min():.4f} <= z <= {catalogue['redshift'].max():.4f}**.",
            f"- Maximum stored observer-centred radius: **{catalogue['radius_mpc'].max() / 1000.0:.3f} Gpc**.",
            "",
            "## Tracer epochs",
            "",
            "| Tracer | Observed rows | Median z | 16th–84th z | Median look-back time [Gyr] | Median comoving distance [Gpc] |",
            "|---|---:|---:|---:|---:|---:|",
            *rows,
            "",
            "## Coordinate validation",
            "",
            f"- Rows checked: **{coordinate['coordinate_validation_rows']:,}**.",
            f"- Median absolute radius residual: **{coordinate['median_abs_distance_residual_mpc']:.6f} Mpc**.",
            f"- 95th-percentile absolute radius residual: **{coordinate['p95_abs_distance_residual_mpc']:.6f} Mpc**.",
            f"- Median absolute relative residual: **{coordinate['median_abs_relative_residual_ppm']:.3f} ppm**.",
            "",
            "## Interpretation boundary",
            "",
            "The redshift and angular figures describe observed target distributions. They are affected by DESI target selection, redshift success, footprint and survey strategy. They are not volume-corrected galaxy/quasar population functions, density fields, BAO measurements, correlation functions, void catalogues or cosmological parameter constraints. Those analyses require the official DESI LSS weights, masks, random catalogues and covariance products.",
            "",
            "## Application",
            "",
            "The scientific application of the lightcone is survey-native interpretation: it shows which tracer classes sample which cosmic epochs, makes the observed selection function visible, and prevents a viewer from mistaking masked footprint geometry for physical underdensity. This supports an astronomy visualisation/software contribution; it is not by itself a new cosmological discovery.",
        ]
    )


def main() -> int:
    options = parse_args()
    if not options.input.exists():
        raise FileNotFoundError(f"Input Parquet file was not found: {options.input}")
    if options.redshift_bins < 10:
        raise ValueError("--redshift-bins must be at least 10.")
    options.output_dir.mkdir(parents=True, exist_ok=True)

    catalogue = load_catalogue(options.input)
    tracers = tracer_sequence(catalogue)
    edges = z_edges(catalogue, options.redshift_bins)
    slice_edges = redshift_slice_edges(catalogue)
    summary = report_table(catalogue, tracers)
    summary.to_csv(options.output_dir / "tracer_cosmic_epoch_summary.csv", index=False)

    plot_redshift_population(catalogue, tracers, edges, options.output_dir, options.dpi)
    plot_cosmic_epochs(summary, options.output_dir, options.dpi)
    plot_angular_slices(catalogue, tracers, slice_edges, options.max_points_per_panel, options.seed, options.output_dir, options.dpi)
    plot_cartesian_slices(catalogue, tracers, slice_edges, options.max_points_per_panel, options.seed, options.output_dir, options.dpi)
    plot_observed_radial_selection(catalogue, tracers, edges, options.output_dir, options.dpi)
    coordinate = plot_coordinate_consistency(catalogue, options.coordinate_validation_points, options.seed, options.output_dir, options.dpi)

    digest = sha256(options.input)
    metadata = {
        "analysis": "DESI DR1 observed-catalogue redshift and tracer tomography",
        "input_file": options.input.name,
        "input_sha256": digest,
        "valid_observed_rows": int(len(catalogue)),
        "tracers": tracers,
        "redshift_range": [float(catalogue["redshift"].min()), float(catalogue["redshift"].max())],
        "cosmology": "Astropy Planck18",
        "coordinate_validation": coordinate,
        "scientific_boundary": "Observed catalogue description only. No random catalogue, angular mask correction, survey weights, correlation estimator, density reconstruction, BAO or cosmological-parameter inference.",
    }
    (options.output_dir / "science_analysis_manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (options.output_dir / "science_summary.md").write_text(markdown_report(summary, catalogue, coordinate, digest), encoding="utf-8")

    print(f"Validated observed rows: {len(catalogue):,}")
    print(f"Wrote science-first analysis package: {options.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
