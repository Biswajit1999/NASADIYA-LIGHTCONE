#!/usr/bin/env python3
"""Generate figure-first evidence for the NĀSADĪYA DESI browser representation.

This script compares real, observed DESI DR1 LSS rows with three browser-level
rendering policies at declared point budgets:

- ``gpu_index`` exactly reproduces the active full-cloud shader threshold
  ``aSample <= pointBudget / recordCount``. It is index-order dependent.
- ``lowest_hash`` selects the lowest stable BLAKE2b-64 object-ID hashes.
- ``tracer_sky_redshift_hash`` is a deterministic candidate policy, stratified
  by tracer class, equal-area sky cell and redshift bin.

All outputs are representation-fidelity diagnostics. They do not apply survey
weights or random catalogues and must not be interpreted as a clustering
measurement, density reconstruction, completeness correction or physical void
analysis.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable

import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from assess_desi_common import file_sha256, load_parent  # noqa: E402
from desi_strata import redshift_bin_labels  # noqa: E402
from fidelity_grid import cartesian_voxel_cells, equal_area_sky_cells, occupancy_metrics  # noqa: E402
from fidelity_helpers import categorical_table, scalar_metrics  # noqa: E402
from nasadiya_lightcone.sampling import (  # noqa: E402
    select_gpu_golden_ratio_index,
    select_lowest_hash,
    select_stratified_lowest_hash,
)

TRACERS = ("BGS", "LRG", "ELG", "QSO", "UNKNOWN")
TRACER_COLOURS = {
    "BGS": "#35b8d4",
    "LRG": "#e6a243",
    "ELG": "#65c987",
    "QSO": "#b58bf3",
    "UNKNOWN": "#8999a7",
}
POLICIES = ("gpu_index", "lowest_hash", "tracer_sky_redshift_hash")
POLICY_LABELS = {
    "gpu_index": "Current GPU index threshold",
    "lowest_hash": "Object-ID lowest hash",
    "tracer_sky_redshift_hash": "Tracer + sky + redshift hash",
}
POLICY_COLOURS = {
    "gpu_index": "#e6a243",
    "lowest_hash": "#35b8d4",
    "tracer_sky_redshift_hash": "#65c987",
}


def parse_budgets(raw: str) -> list[int]:
    values = sorted({int(value.strip()) for value in raw.split(",") if value.strip()})
    if not values or values[0] < 1:
        raise argparse.ArgumentTypeError("At least one positive point budget is required.")
    return values


def make_parent(path: Path, args: argparse.Namespace) -> pd.DataFrame:
    parent = load_parent(path)
    parent = parent.copy()
    parent["sky_cell"] = equal_area_sky_cells(
        parent["ra_deg"], parent["dec_deg"], ra_bins=args.sky_ra_bins, sin_dec_bins=args.sky_sin_dec_bins
    )
    parent["redshift_bin"] = redshift_bin_labels(parent["redshift"], z_max=args.z_max, z_bins=args.z_bins)
    return parent


def select_policy(parent: pd.DataFrame, policy: str, budget: int) -> pd.DataFrame:
    if policy == "gpu_index":
        return select_gpu_golden_ratio_index(parent, budget)
    if policy == "lowest_hash":
        return select_lowest_hash(parent, budget)
    if policy == "tracer_sky_redshift_hash":
        return select_stratified_lowest_hash(
            parent,
            budget,
            group_columns=("tracer", "sky_cell", "redshift_bin"),
        )
    raise ValueError(f"Unknown policy: {policy}")


def evaluate_sample(
    parent: pd.DataFrame,
    sample: pd.DataFrame,
    *,
    parent_sky: pd.Series,
    parent_voxels: pd.Series,
    redshift_edges: np.ndarray,
    args: argparse.Namespace,
) -> tuple[dict[str, float], pd.DataFrame]:
    fraction = len(sample) / len(parent)
    sample_sky = equal_area_sky_cells(
        sample["ra_deg"], sample["dec_deg"], ra_bins=args.sky_ra_bins, sin_dec_bins=args.sky_sin_dec_bins
    )
    sample_voxels = cartesian_voxel_cells(sample, cell_size_mpc=args.voxel_size_mpc)
    tracer = categorical_table(parent["tracer"], sample["tracer"], name="tracer")
    redshift = scalar_metrics(parent["redshift"], sample["redshift"], bins=redshift_edges)
    sky = occupancy_metrics(parent_sky, sample_sky, sampling_fraction=fraction)
    voxel = occupancy_metrics(parent_voxels, sample_voxels, sampling_fraction=fraction)
    metrics = {
        "requested_rows": float("nan"),
        "selected_rows": float(len(sample)),
        "sampling_fraction": fraction,
        "redshift_ks_distance": redshift["ks_distance"],
        "redshift_normalized_wasserstein": redshift["normalized_wasserstein_distance"],
        "redshift_js_bits": redshift["jensen_shannon_divergence_bits"],
        "tracer_total_variation_distance": float(0.5 * np.abs(tracer["fraction_residual"]).sum()),
        "sky_occupancy_correlation": sky["occupancy_correlation"],
        "sky_occupancy_nrmse": sky["occupancy_nrmse"],
        "sky_occupied_cell_recall": sky["occupied_cell_recall"],
        "voxel_occupancy_correlation": voxel["occupancy_correlation"],
        "voxel_occupancy_nrmse": voxel["occupancy_nrmse"],
        "voxel_occupied_cell_recall": voxel["occupied_cell_recall"],
    }
    return metrics, tracer


def configure_axis(axis) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=0.20, linewidth=0.7)


def figure_parent_tracer_redshift(parent: pd.DataFrame, edges: np.ndarray, output: Path, dpi: int) -> None:
    centres = 0.5 * (edges[:-1] + edges[1:])
    counts = np.vstack([np.histogram(parent.loc[parent["tracer"] == tracer, "redshift"], bins=edges)[0] for tracer in TRACERS])
    total = counts.sum(axis=0)
    fraction = np.divide(counts, total, out=np.zeros_like(counts, dtype=float), where=total > 0)
    figure, axis = plt.subplots(figsize=(9.8, 5.3), dpi=dpi)
    lower = np.zeros_like(centres)
    for tracer, values in zip(TRACERS, fraction):
        if not np.any(values):
            continue
        axis.fill_between(centres, lower, lower + values, step="mid", alpha=0.86, color=TRACER_COLOURS[tracer], label=tracer)
        lower += values
    axis.set(xlabel="Spectroscopic redshift, z", ylabel="Fraction of observed rows per redshift bin", ylim=(0.0, 1.0))
    axis.set_title("DESI DR1 LSS observed tracer composition", loc="left", pad=12, fontweight="bold")
    axis.legend(title="DESI tracer", ncol=5, frameon=False, loc="upper center")
    configure_axis(axis)
    figure.text(0.125, 0.015, "Observed-row distribution only; it is not a completeness-corrected population fraction.", fontsize=8)
    figure.subplots_adjust(bottom=0.16, left=0.12, right=0.98, top=0.90)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def figure_redshift_residuals(
    parent: pd.DataFrame,
    samples: dict[str, pd.DataFrame],
    edges: np.ndarray,
    output: Path,
    dpi: int,
) -> None:
    centres = 0.5 * (edges[:-1] + edges[1:])
    parent_fraction = np.histogram(parent["redshift"], bins=edges)[0] / len(parent)
    figure, axis = plt.subplots(figsize=(9.8, 5.3), dpi=dpi)
    axis.axhline(0.0, color="#253b4a", linewidth=1.0)
    for policy, sample in samples.items():
        sample_fraction = np.histogram(sample["redshift"], bins=edges)[0] / len(sample)
        residual = 100.0 * (sample_fraction - parent_fraction)
        axis.step(centres, residual, where="mid", linewidth=1.5, color=POLICY_COLOURS[policy], label=POLICY_LABELS[policy])
    axis.set(xlabel="Spectroscopic redshift, z", ylabel="Sample − parent fraction [percentage points]")
    axis.set_title("Browser representation redshift residuals", loc="left", pad=12, fontweight="bold")
    axis.legend(frameon=False, fontsize=8)
    configure_axis(axis)
    figure.text(0.125, 0.015, "Each line uses the same observed parent catalogue and declared display budget.", fontsize=8)
    figure.subplots_adjust(bottom=0.16, left=0.12, right=0.98, top=0.90)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def figure_metric_convergence(metrics: pd.DataFrame, metric: str, ylabel: str, output: Path, dpi: int, *, ylim: tuple[float, float] | None = None) -> None:
    figure, axis = plt.subplots(figsize=(8.8, 5.0), dpi=dpi)
    for policy in POLICIES:
        subset = metrics.loc[metrics["policy"] == policy].sort_values("requested_rows")
        axis.plot(subset["requested_rows"], subset[metric], marker="o", linewidth=1.8, markersize=5.5, color=POLICY_COLOURS[policy], label=POLICY_LABELS[policy])
    axis.set_xscale("log")
    axis.set(xlabel="Declared display-row budget", ylabel=ylabel)
    axis.set_title("Representation fidelity versus display budget", loc="left", pad=12, fontweight="bold")
    if ylim is not None:
        axis.set_ylim(*ylim)
    axis.legend(frameon=False, fontsize=8, loc="best")
    configure_axis(axis)
    figure.text(0.125, 0.015, "Diagnostic values compare a browser subset with the same observed parent; they are not clustering statistics.", fontsize=8)
    figure.subplots_adjust(bottom=0.17, left=0.13, right=0.98, top=0.90)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def occupancy_fraction_grid(cells: pd.Series, *, ra_bins: int, sin_dec_bins: int) -> np.ndarray:
    counts = pd.Series(cells).value_counts(sort=False)
    values = np.zeros(ra_bins * sin_dec_bins, dtype=float)
    values[counts.index.to_numpy(dtype=int)] = counts.to_numpy(dtype=float)
    return (values / values.sum()).reshape(ra_bins, sin_dec_bins).T


def figure_sky_residuals(
    parent_sky: pd.Series,
    samples: dict[str, pd.DataFrame],
    args: argparse.Namespace,
    output: Path,
    dpi: int,
) -> None:
    parent_grid = occupancy_fraction_grid(parent_sky, ra_bins=args.sky_ra_bins, sin_dec_bins=args.sky_sin_dec_bins)
    residuals = []
    for policy in POLICIES:
        sample_sky = equal_area_sky_cells(samples[policy]["ra_deg"], samples[policy]["dec_deg"], ra_bins=args.sky_ra_bins, sin_dec_bins=args.sky_sin_dec_bins)
        residuals.append(100.0 * (occupancy_fraction_grid(sample_sky, ra_bins=args.sky_ra_bins, sin_dec_bins=args.sky_sin_dec_bins) - parent_grid))
    limit = max(float(np.max(np.abs(values))) for values in residuals)
    limit = max(limit, 0.01)
    figure, axes = plt.subplots(1, 3, figsize=(12.2, 3.8), dpi=dpi, sharex=True, sharey=True, constrained_layout=True)
    image = None
    for axis, policy, residual in zip(axes, POLICIES, residuals):
        image = axis.imshow(residual, origin="lower", aspect="auto", cmap="coolwarm", norm=TwoSlopeNorm(vcenter=0.0, vmin=-limit, vmax=limit))
        axis.set_title(POLICY_LABELS[policy], fontsize=9, fontweight="bold")
        axis.set_xlabel("RA equal-area cell")
    axes[0].set_ylabel("sin(Dec) equal-area cell")
    colourbar = figure.colorbar(image, ax=axes, shrink=0.88, pad=0.015)
    colourbar.set_label("Sample − parent fraction [percentage points]")
    figure.suptitle("Observed sky-cell representation residuals", x=0.08, ha="left", fontsize=13, fontweight="bold")
    figure.text(0.08, 0.015, "Equal-area sky cells describe observed-row representation only; no angular mask or completeness correction is applied.", fontsize=8)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def figure_slice_comparison(
    parent: pd.DataFrame,
    samples: dict[str, pd.DataFrame],
    args: argparse.Namespace,
    output: Path,
    dpi: int,
) -> None:
    half = args.slice_thickness_mpc / 2.0
    parent_slice = parent.loc[parent["z_mpc"].abs() <= half]
    figure, axes = plt.subplots(1, 3, figsize=(12.2, 4.1), dpi=dpi, sharex=True, sharey=True, constrained_layout=True)
    for axis, policy in zip(axes, POLICIES):
        sample_slice = samples[policy].loc[samples[policy]["z_mpc"].abs() <= half]
        for tracer in TRACERS:
            group = sample_slice.loc[sample_slice["tracer"] == tracer]
            if group.empty:
                continue
            axis.scatter(group["x_mpc"], group["y_mpc"], s=0.55, marker=".", alpha=0.38, color=TRACER_COLOURS[tracer], rasterized=True)
        axis.set_title(f"{POLICY_LABELS[policy]}\n{len(sample_slice):,} slice rows", fontsize=8.5, fontweight="bold")
        axis.set_xlabel("X [Mpc]")
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(alpha=0.16)
        axis.set_aspect("equal", adjustable="box")
    axes[0].set_ylabel("Y [Mpc]")
    figure.suptitle("Cartesian display subset in the same central slice", x=0.08, ha="left", fontsize=13, fontweight="bold")
    figure.text(0.08, 0.015, f"Slice condition: |Z| ≤ {half:.0f} Mpc. Rendered subset comparison; not a density reconstruction. Parent slice rows: {len(parent_slice):,}.", fontsize=8)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def save_figure_pair(generator: Callable[..., None], *args, output_stem: Path, dpi: int) -> None:
    generator(*args, output_stem.with_suffix(".png"), dpi)
    generator(*args, output_stem.with_suffix(".pdf"), dpi)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "research" / "desi_dr1_lss_research_bundle.parquet")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "figures" / "publication_evidence")
    parser.add_argument("--full-cloud-manifest", type=Path, default=PROJECT_ROOT / "data" / "processed" / "desi-dr1" / "full-cloud" / "full-cloud.json")
    parser.add_argument("--budgets", type=parse_budgets, default=parse_budgets("125000,250000,500000,1000000"))
    parser.add_argument("--poster-budget", type=int, default=125_000)
    parser.add_argument("--z-max", type=float, default=3.6)
    parser.add_argument("--z-bins", type=int, default=48)
    parser.add_argument("--sky-ra-bins", type=int, default=24)
    parser.add_argument("--sky-sin-dec-bins", type=int, default=12)
    parser.add_argument("--voxel-size-mpc", type=float, default=250.0)
    parser.add_argument("--slice-thickness-mpc", type=float, default=300.0)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--allow-gpu-row-count-mismatch", action="store_true")
    return parser.parse_args()


def validate_gpu_contract(parent: pd.DataFrame, manifest_path: Path, allow_mismatch: bool) -> dict:
    if not manifest_path.exists():
        return {"manifest_checked": False, "note": "No full-cloud manifest was found; GPU-index validation was not cross-checked."}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record_count = int(manifest["record_count"])
    if len(parent) != record_count and not allow_mismatch:
        raise ValueError(
            f"Parent validation rows ({len(parent):,}) do not equal full-cloud records ({record_count:,}). "
            "Use --allow-gpu-row-count-mismatch only after documenting why the GPU row order cannot be reproduced."
        )
    return {
        "manifest_checked": True,
        "manifest_path": str(manifest_path),
        "manifest_record_count": record_count,
        "parent_rows_match_manifest": len(parent) == record_count,
        "manifest_binary_sha256": manifest.get("binary", {}).get("sha256"),
    }


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Input bundle does not exist: {args.input}")
    if args.poster_budget not in args.budgets:
        raise ValueError("poster-budget must be one of the declared budgets.")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    parent = make_parent(args.input, args)
    if max(args.budgets) > len(parent):
        raise ValueError("A declared display budget exceeds the valid observed parent rows.")
    gpu_contract = validate_gpu_contract(parent, args.full_cloud_manifest, args.allow_gpu_row_count_mismatch)
    redshift_edges = np.linspace(0.0, args.z_max, args.z_bins + 1)
    parent_sky = equal_area_sky_cells(parent["ra_deg"], parent["dec_deg"], ra_bins=args.sky_ra_bins, sin_dec_bins=args.sky_sin_dec_bins)
    parent_voxels = cartesian_voxel_cells(parent, cell_size_mpc=args.voxel_size_mpc)

    summary_rows: list[dict[str, float | str]] = []
    tracer_rows: list[pd.DataFrame] = []
    poster_samples: dict[str, pd.DataFrame] = {}
    for budget in args.budgets:
        for policy in POLICIES:
            sample = select_policy(parent, policy, budget)
            metrics, tracer = evaluate_sample(parent, sample, parent_sky=parent_sky, parent_voxels=parent_voxels, redshift_edges=redshift_edges, args=args)
            metrics.update({"policy": policy, "policy_label": POLICY_LABELS[policy], "requested_rows": budget, "selected_rows": len(sample)})
            summary_rows.append(metrics)
            tracer.insert(0, "policy", policy)
            tracer.insert(1, "requested_rows", budget)
            tracer_rows.append(tracer)
            if budget == args.poster_budget:
                poster_samples[policy] = sample

    metrics = pd.DataFrame(summary_rows).sort_values(["policy", "requested_rows"], ignore_index=True)
    tracer_residuals = pd.concat(tracer_rows, ignore_index=True)
    metrics.to_csv(args.output_dir / "representation_fidelity_metrics.csv", index=False)
    tracer_residuals.to_csv(args.output_dir / "tracer_fraction_residuals.csv", index=False)

    save_figure_pair(figure_parent_tracer_redshift, parent, redshift_edges, output_stem=args.output_dir / "fig_01_parent_tracer_redshift", dpi=args.dpi)
    save_figure_pair(figure_redshift_residuals, parent, poster_samples, redshift_edges, output_stem=args.output_dir / "fig_02_redshift_residuals", dpi=args.dpi)
    save_figure_pair(figure_metric_convergence, metrics, "redshift_js_bits", "Redshift Jensen–Shannon divergence [bits]", output_stem=args.output_dir / "fig_03_redshift_fidelity_convergence", dpi=args.dpi)
    save_figure_pair(figure_metric_convergence, metrics, "voxel_occupancy_correlation", "Scaled voxel-occupancy correlation", output_stem=args.output_dir / "fig_04_voxel_fidelity_convergence", dpi=args.dpi, ylim=(0.0, 1.02))
    save_figure_pair(figure_sky_residuals, parent_sky, poster_samples, args, output_stem=args.output_dir / "fig_05_sky_cell_residuals", dpi=args.dpi)
    save_figure_pair(figure_slice_comparison, parent, poster_samples, args, output_stem=args.output_dir / "fig_06_cartesian_slice_comparison", dpi=args.dpi)

    manifest = {
        "format": "nasadiya-publication-evidence/v1",
        "input": {"filename": args.input.name, "sha256": file_sha256(args.input), "validated_parent_rows": len(parent)},
        "gpu_render_contract": gpu_contract,
        "configuration": {
            "budgets": args.budgets,
            "poster_budget": args.poster_budget,
            "redshift_range": [0.0, args.z_max],
            "redshift_bins": args.z_bins,
            "sky_grid": {"ra_bins": args.sky_ra_bins, "sin_dec_bins": args.sky_sin_dec_bins},
            "voxel_size_mpc": args.voxel_size_mpc,
            "slice_thickness_mpc": args.slice_thickness_mpc,
        },
        "policies": {
            "gpu_index": "Exact full-cloud shader aSample threshold; depends on packed source-row order.",
            "lowest_hash": "Stable BLAKE2b-64 object-ID selection.",
            "tracer_sky_redshift_hash": "Stable proportional selection within tracer × equal-area sky × redshift strata.",
        },
        "scientific_boundary": {
            "observed_rows_only": True,
            "survey_weights_applied": False,
            "random_catalogue_used": False,
            "clustering_estimator": False,
            "density_reconstruction": False,
            "statement": "These figures validate browser representation of observed rows, not cosmological clustering or physical density.",
        },
        "figure_files": [
            "fig_01_parent_tracer_redshift", "fig_02_redshift_residuals", "fig_03_redshift_fidelity_convergence",
            "fig_04_voxel_fidelity_convergence", "fig_05_sky_cell_residuals", "fig_06_cartesian_slice_comparison",
        ],
    }
    (args.output_dir / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Validated observed parent rows: {len(parent):,}")
    print(f"Wrote evidence pack: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
