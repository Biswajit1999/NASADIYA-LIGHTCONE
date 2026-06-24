#!/usr/bin/env python3
"""Compare browser-scale DESI samples with their observed parent bundle.

The generated statistics quantify representation fidelity for real catalogue
rows. They do not apply survey weights, random catalogues, masks, density
reconstruction or clustering estimators.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from assess_desi_common import file_sha256, load_parent  # noqa: E402
from desi_strata import redshift_bin_labels  # noqa: E402
from fidelity_grid import cartesian_voxel_cells, equal_area_sky_cells, occupancy_metrics  # noqa: E402
from fidelity_helpers import categorical_table, scalar_metrics  # noqa: E402
from nasadiya_lightcone.sampling import select_lowest_hash, select_seeded_random, select_stratified_lowest_hash  # noqa: E402


def build_samples(parent: pd.DataFrame, args: argparse.Namespace) -> dict[str, pd.DataFrame]:
    """Construct the declared browser-representation policies."""

    working = parent.copy()
    working["sky_cell"] = equal_area_sky_cells(
        working["ra_deg"],
        working["dec_deg"],
        ra_bins=args.sky_ra_bins,
        sin_dec_bins=args.sky_sin_dec_bins,
    )
    working["redshift_bin"] = redshift_bin_labels(
        working["redshift"],
        z_max=args.z_max,
        z_bins=args.z_bins,
    )
    return {
        "lowest_hash": select_lowest_hash(working, args.point_budget),
        "seeded_random": select_seeded_random(working, args.point_budget, seed=args.random_seed),
        "tracer_hash": select_stratified_lowest_hash(
            working,
            args.point_budget,
            group_columns=("tracer",),
        ),
        "spatial_redshift_hash": select_stratified_lowest_hash(
            working,
            args.point_budget,
            group_columns=("tracer", "sky_cell", "redshift_bin"),
        ),
    }


def metrics_for_sample(
    parent: pd.DataFrame,
    sample: pd.DataFrame,
    *,
    parent_sky: pd.Series,
    parent_voxels: pd.Series,
    edges: np.ndarray,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Calculate observed-row distribution and occupancy metrics."""

    fraction = len(sample) / len(parent)
    tracer_table = categorical_table(parent["tracer"], sample["tracer"], name="tracer")
    sample_sky = equal_area_sky_cells(
        sample["ra_deg"],
        sample["dec_deg"],
        ra_bins=args.sky_ra_bins,
        sin_dec_bins=args.sky_sin_dec_bins,
    )
    sample_voxels = cartesian_voxel_cells(sample, cell_size_mpc=args.voxel_size_mpc)
    return {
        "sampling_fraction": fraction,
        "redshift": scalar_metrics(parent["redshift"], sample["redshift"], bins=edges),
        "tracer_total_variation_distance": float(0.5 * np.abs(tracer_table["fraction_residual"]).sum()),
        "sky_occupancy": occupancy_metrics(parent_sky, sample_sky, sampling_fraction=fraction),
        "voxel_occupancy": occupancy_metrics(parent_voxels, sample_voxels, sampling_fraction=fraction),
    }, tracer_table


def metric_row(label: str, metrics: dict[str, Any]) -> dict[str, float | str]:
    """Flatten nested metrics for a publication-ready CSV table."""

    redshift = metrics["redshift"]
    sky = metrics["sky_occupancy"]
    voxel = metrics["voxel_occupancy"]
    return {
        "method": label,
        "sampling_fraction": metrics["sampling_fraction"],
        "ks_distance": redshift["ks_distance"],
        "normalized_wasserstein_distance": redshift["normalized_wasserstein_distance"],
        "jensen_shannon_divergence_bits": redshift["jensen_shannon_divergence_bits"],
        "tracer_total_variation_distance": metrics["tracer_total_variation_distance"],
        "sky_occupancy_recall": sky["occupied_cell_recall"],
        "sky_occupancy_correlation": sky["occupancy_correlation"],
        "sky_occupancy_nrmse": sky["occupancy_nrmse"],
        "voxel_occupancy_recall": voxel["occupied_cell_recall"],
        "voxel_occupancy_correlation": voxel["occupancy_correlation"],
        "voxel_occupancy_nrmse": voxel["occupancy_nrmse"],
    }


def plot_redshift(parent: pd.DataFrame, samples: dict[str, pd.DataFrame], edges: np.ndarray, output: Path, dpi: int) -> None:
    """Write the first paper-grade observed redshift fidelity figure."""

    figure, axis = plt.subplots(figsize=(10.5, 5.8), dpi=dpi)
    centres = 0.5 * (edges[:-1] + edges[1:])
    parent_hist = np.histogram(parent["redshift"], bins=edges)[0] / len(parent)
    axis.step(centres, parent_hist, where="mid", linewidth=2.2, label="Full observed parent")
    for label, sample in samples.items():
        histogram = np.histogram(sample["redshift"], bins=edges)[0] / len(sample)
        axis.step(centres, histogram, where="mid", linewidth=1.2, label=label)
    axis.set(xlabel="Spectroscopic redshift, z", ylabel="Observed-row fraction per bin")
    axis.set_title("DESI DR1 LSS browser representation: redshift fidelity", loc="left", pad=12)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, fontsize=8)
    figure.text(0.125, 0.02, "Observed-row comparison only; not completeness corrected.", fontsize=8)
    figure.subplots_adjust(bottom=0.16, left=0.11, right=0.97, top=0.90)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "research" / "desi_dr1_lss_research_bundle.parquet")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "figures" / "browser_fidelity")
    parser.add_argument("--point-budget", type=int, default=125_000)
    parser.add_argument("--random-repeats", type=int, default=5)
    parser.add_argument("--random-seed", type=int, default=20260624)
    parser.add_argument("--z-max", type=float, default=3.6)
    parser.add_argument("--z-bins", type=int, default=24)
    parser.add_argument("--sky-ra-bins", type=int, default=24)
    parser.add_argument("--sky-sin-dec-bins", type=int, default=12)
    parser.add_argument("--voxel-size-mpc", type=float, default=250.0)
    parser.add_argument("--dpi", type=int, default=240)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Input bundle does not exist: {args.input}")
    if args.point_budget < 1 or args.random_repeats < 1:
        raise ValueError("point_budget and random_repeats must be positive.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    parent = load_parent(args.input)
    if args.point_budget > len(parent):
        raise ValueError("point_budget cannot exceed the valid parent row count.")
    edges = np.linspace(0.0, args.z_max, args.z_bins + 1)
    parent_sky = equal_area_sky_cells(
        parent["ra_deg"], parent["dec_deg"], ra_bins=args.sky_ra_bins, sin_dec_bins=args.sky_sin_dec_bins
    )
    parent_voxels = cartesian_voxel_cells(parent, cell_size_mpc=args.voxel_size_mpc)
    samples = build_samples(parent, args)

    policy_settings = {
        "lowest_hash": {"group_columns": [], "random_seed": None, "hash_algorithm": "blake2b-64"},
        "seeded_random": {"group_columns": [], "random_seed": args.random_seed, "hash_algorithm": None},
        "tracer_hash": {"group_columns": ["tracer"], "random_seed": None, "hash_algorithm": "blake2b-64"},
        "spatial_redshift_hash": {"group_columns": ["tracer", "sky_cell", "redshift_bin"], "random_seed": None, "hash_algorithm": "blake2b-64"},
    }
    method_payload: dict[str, Any] = {}
    summary_rows: list[dict[str, float | str]] = []
    for label, sample in samples.items():
        metrics, tracer_table = metrics_for_sample(
            parent,
            sample,
            parent_sky=parent_sky,
            parent_voxels=parent_voxels,
            edges=edges,
            args=args,
        )
        tracer_table.to_csv(args.output_dir / f"tracer_fractions_{label}.csv", index=False)
        method_payload[label] = {
            "selection": {
                "strategy": label,
                "parent_rows": int(len(parent)),
                "selected_rows": int(len(sample)),
                "object_id_column": "object_id",
                **policy_settings[label],
            },
            "metrics": metrics,
        }
        summary_rows.append(metric_row(label, metrics))

    baseline_rows: list[dict[str, float | str]] = []
    for repeat in range(args.random_repeats):
        seed = args.random_seed + repeat
        sample = select_seeded_random(parent, args.point_budget, seed=seed)
        metrics, _ = metrics_for_sample(
            parent,
            sample,
            parent_sky=parent_sky,
            parent_voxels=parent_voxels,
            edges=edges,
            args=args,
        )
        row = metric_row(f"random_{repeat:03d}", metrics)
        row["seed"] = seed
        baseline_rows.append(row)

    pd.DataFrame(summary_rows).to_csv(args.output_dir / "sampling_fidelity_metrics.csv", index=False)
    pd.DataFrame(baseline_rows).to_csv(args.output_dir / "seeded_random_baselines.csv", index=False)
    plot_redshift(parent, samples, edges, args.output_dir / "desi_browser_redshift_fidelity.png", args.dpi)
    payload = {
        "format": "nasadiya-browser-fidelity/v1",
        "input": {"filename": args.input.name, "sha256": file_sha256(args.input), "parent_rows": int(len(parent))},
        "configuration": {"point_budget": args.point_budget, "redshift_edges": edges.tolist(), "sky_ra_bins": args.sky_ra_bins, "sky_sin_dec_bins": args.sky_sin_dec_bins, "voxel_size_mpc": args.voxel_size_mpc, "random_repeats": args.random_repeats, "random_seed": args.random_seed},
        "methods": method_payload,
        "random_baselines": baseline_rows,
        "scientific_scope": {"observed_rows_only": True, "survey_selection_corrected": False, "clustering_estimator": False, "density_reconstruction": False},
    }
    output = args.output_dir / "browser_fidelity_metrics.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Validated parent rows: {len(parent):,}")
    print(f"Wrote: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
