#!/usr/bin/env python3
"""Build a figure-led white A0 poster from a DESI representation-evidence run.

The poster is intentionally conventional: one short research question, a clear
method statement, large evidence panels, a direct trade-off comparison and an
explicit interpretation boundary. It uses only outputs produced by
``build_desi_publication_figures.py`` and values in the matching metrics CSV.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import textwrap

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
A0_WIDTH_IN = 33.1102
A0_HEIGHT_IN = 46.8110

INK = "#172735"
MUTED = "#526976"
FAINT = "#e5edf1"
LINE = "#c4d5dd"
CYAN = "#178ca9"
AMBER = "#c9771f"
GREEN = "#38855d"
VIOLET = "#7f5bb7"
WHITE = "#ffffff"
PALE_CYAN = "#eff9fb"
PALE_AMBER = "#fff7ec"

POLICY_LABELS = {
    "gpu_index": "GPU low-discrepancy profile",
    "lowest_hash": "Object-ID lowest hash",
    "tracer_sky_redshift_hash": "Tracer + sky + redshift profile",
}
POLICY_COLOURS = {
    "gpu_index": CYAN,
    "lowest_hash": "#9aa8ae",
    "tracer_sky_redshift_hash": AMBER,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=PROJECT_ROOT / "figures" / "publication_evidence")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "assets" / "posters")
    parser.add_argument("--budget", type=int, default=125_000)
    parser.add_argument("--dpi", type=int, default=180)
    return parser.parse_args()


def metric_row(metrics: pd.DataFrame, budget: int, policy: str) -> pd.Series:
    matched = metrics.loc[(metrics["requested_rows"] == budget) & (metrics["policy"] == policy)]
    if len(matched) != 1:
        raise ValueError(f"Expected one metrics row for budget={budget:,}, policy={policy!r}; found {len(matched)}.")
    return matched.iloc[0]


def wrap(text: str, width: int) -> str:
    return textwrap.fill(text, width=width, break_long_words=False)


def turn_off(axis) -> None:
    axis.set_axis_off()


def section_label(axis, text: str, *, colour: str = CYAN) -> None:
    axis.text(0.0, 1.02, text.upper(), transform=axis.transAxes, fontsize=15, color=colour, fontweight="bold", va="bottom")
    axis.plot([0.0, 1.0], [0.985, 0.985], transform=axis.transAxes, color=LINE, linewidth=1.0, clip_on=False)


def image_panel(axis, image_path: Path, title: str, caption: str) -> None:
    axis.imshow(mpimg.imread(image_path))
    axis.set_axis_off()
    axis.text(0.0, 1.02, title, transform=axis.transAxes, fontsize=20, color=INK, fontweight="bold", va="bottom")
    axis.text(0.0, -0.075, wrap(caption, 135), transform=axis.transAxes, fontsize=13.2, color=MUTED, va="top", linespacing=1.28)


def summary_metric(axis, x: float, heading: str, value: str, detail: str, *, colour: str) -> None:
    axis.add_patch(Rectangle((x, 0.10), 0.23, 0.78, transform=axis.transAxes, facecolor=WHITE, edgecolor=LINE, linewidth=1.15))
    axis.add_patch(Rectangle((x, 0.10), 0.23, 0.05, transform=axis.transAxes, facecolor=colour, edgecolor="none"))
    axis.text(x + 0.018, 0.72, heading.upper(), transform=axis.transAxes, fontsize=12.5, color=colour, fontweight="bold")
    axis.text(x + 0.018, 0.43, value, transform=axis.transAxes, fontsize=27, color=INK, fontweight="bold")
    axis.text(x + 0.018, 0.22, wrap(detail, 27), transform=axis.transAxes, fontsize=10.3, color=MUTED, va="top", linespacing=1.2)


def tradeoff_plot(axis, metrics: pd.DataFrame) -> None:
    axis.set_title("B. Angular balance versus 3D display structure", loc="left", fontsize=20, color=INK, fontweight="bold", pad=20)
    for policy, subset in metrics.groupby("policy", sort=False):
        subset = subset.sort_values("requested_rows")
        axis.plot(
            subset["sky_occupancy_nrmse"],
            subset["voxel_occupancy_correlation"],
            color=POLICY_COLOURS[policy],
            linewidth=2.6,
            marker="o",
            markersize=7.5,
            label=POLICY_LABELS[policy],
            zorder=3,
        )
        first = subset.iloc[0]
        last = subset.iloc[-1]
        axis.annotate("125K", (first["sky_occupancy_nrmse"], first["voxel_occupancy_correlation"]), xytext=(7, -15), textcoords="offset points", fontsize=10.5, color=POLICY_COLOURS[policy])
        axis.annotate("1M", (last["sky_occupancy_nrmse"], last["voxel_occupancy_correlation"]), xytext=(7, 8), textcoords="offset points", fontsize=10.5, color=POLICY_COLOURS[policy])
    axis.set_xscale("log")
    axis.set_xlim(1.5e-4, 4e-2)
    axis.set_ylim(0.965, 1.001)
    axis.set_xlabel("Equal-area sky-cell NRMSE (lower is better)", fontsize=13.5)
    axis.set_ylabel("250 Mpc voxel-occupancy correlation (higher is better)", fontsize=13.5)
    axis.grid(alpha=0.22, linewidth=0.8)
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(labelsize=11.5)
    legend = axis.legend(frameon=False, fontsize=11.5, loc="lower right", handlelength=2.5)
    for text in legend.get_texts():
        text.set_color(INK)
    axis.text(
        0.0,
        -0.30,
        "The stratified profile improves one-dimensional redshift and angular-cell balance; the deployed GPU profile retains the strongest tested voxel representation for interactive spatial exploration.",
        transform=axis.transAxes,
        fontsize=12.5,
        color=MUTED,
        va="top",
        wrap=True,
    )


def comparison_table(axis, gpu: pd.Series, balanced: pd.Series) -> None:
    turn_off(axis)
    section_label(axis, "At 125,000 displayed rows")
    axis.text(0.0, 0.88, "Metric", fontsize=14, color=INK, fontweight="bold", transform=axis.transAxes)
    axis.text(0.57, 0.88, "GPU", fontsize=14, color=CYAN, fontweight="bold", transform=axis.transAxes, ha="center")
    axis.text(0.84, 0.88, "Balanced", fontsize=14, color=AMBER, fontweight="bold", transform=axis.transAxes, ha="center")
    rows = [
        ("Redshift JSD [bits]", f"{gpu['redshift_js_bits']:.2e}", f"{balanced['redshift_js_bits']:.2e}", "balanced"),
        ("Sky-cell NRMSE", f"{gpu['sky_occupancy_nrmse']:.5f}", f"{balanced['sky_occupancy_nrmse']:.5f}", "balanced"),
        ("Voxel correlation", f"{gpu['voxel_occupancy_correlation']:.5f}", f"{balanced['voxel_occupancy_correlation']:.5f}", "gpu"),
        ("Occupied-cell recall", f"{gpu['voxel_occupied_cell_recall']:.3f}", f"{balanced['voxel_occupied_cell_recall']:.3f}", "gpu"),
    ]
    for index, (label, gpu_value, balanced_value, winner) in enumerate(rows):
        y = 0.71 - index * 0.16
        axis.plot([0.0, 1.0], [y + 0.08, y + 0.08], transform=axis.transAxes, color=FAINT, linewidth=1.0)
        axis.text(0.0, y, label, fontsize=13, color=INK, transform=axis.transAxes, va="center")
        axis.text(0.57, y, gpu_value, fontsize=14, color=CYAN if winner == "gpu" else MUTED, fontweight="bold" if winner == "gpu" else "normal", transform=axis.transAxes, ha="center", va="center")
        axis.text(0.84, y, balanced_value, fontsize=14, color=AMBER if winner == "balanced" else MUTED, fontweight="bold" if winner == "balanced" else "normal", transform=axis.transAxes, ha="center", va="center")
    axis.text(0.0, 0.02, "Bold values identify the better result for that diagnostic only. No single tested policy dominates every representation criterion.", fontsize=11.3, color=MUTED, transform=axis.transAxes, va="bottom", wrap=True)


def narrative_block(axis, heading: str, body: str, *, accent: str) -> None:
    turn_off(axis)
    axis.add_patch(Rectangle((0, 0), 1, 1, transform=axis.transAxes, facecolor=WHITE, edgecolor=LINE, linewidth=1.1))
    axis.add_patch(Rectangle((0, 0.94), 1, 0.06, transform=axis.transAxes, facecolor=accent, edgecolor="none"))
    axis.text(0.04, 0.80, heading.upper(), fontsize=15, color=accent, transform=axis.transAxes, fontweight="bold")
    axis.text(0.04, 0.61, wrap(body, 60), fontsize=14.1, color=INK, transform=axis.transAxes, va="top", linespacing=1.38)


def main() -> int:
    options = parse_args()
    evidence = options.evidence_dir
    required = [
        "representation_fidelity_metrics.csv",
        "fig_02_redshift_residuals.png",
        "fig_05_sky_cell_residuals.png",
        "fig_06_cartesian_slice_comparison.png",
    ]
    missing = [name for name in required if not (evidence / name).exists()]
    if missing:
        raise FileNotFoundError("Missing evidence output(s): " + ", ".join(missing))

    metrics = pd.read_csv(evidence / "representation_fidelity_metrics.csv")
    gpu = metric_row(metrics, options.budget, "gpu_index")
    balanced = metric_row(metrics, options.budget, "tracer_sky_redshift_hash")
    parent_rows = 6_093_818
    js_ratio = float(gpu["redshift_js_bits"] / balanced["redshift_js_bits"])
    sky_ratio = float(gpu["sky_occupancy_nrmse"] / balanced["sky_occupancy_nrmse"])

    options.output_dir.mkdir(parents=True, exist_ok=True)
    output_stem = options.output_dir / "nasadiya_lightcone_A0_evidence_poster_white"
    figure = plt.figure(figsize=(A0_WIDTH_IN, A0_HEIGHT_IN), facecolor=WHITE)
    grid = figure.add_gridspec(100, 12, left=0.055, right=0.945, top=0.965, bottom=0.048, hspace=0.95, wspace=0.65)

    header = figure.add_subplot(grid[0:11, :])
    turn_off(header)
    header.add_patch(Rectangle((0, 0.93), 1.0, 0.022, transform=header.transAxes, facecolor=CYAN, edgecolor="none"))
    header.text(0.0, 0.79, "NĀSADĪYA LIGHTCONE  /  DESI DR1 LSS", fontsize=17, color=AMBER, fontweight="bold")
    header.text(0.0, 0.52, "Does a browser point cloud preserve the DESI DR1 view?", fontsize=51, color=INK, fontweight="bold", va="center")
    header.text(0.0, 0.28, "Validation of deterministic WebGL display profiles for 6,093,818 observed DESI galaxies and quasars", fontsize=20, color=MUTED)
    header.text(0.0, 0.075, "Biswajit Jana  |  Independent Researcher  |  github.com/Biswajit1999/NASADIYA-LIGHTCONE", fontsize=14, color=INK)
    header.text(1.0, 0.075, "DESI DR1 LSS observed catalogue", fontsize=14, color=INK, ha="right")

    context_left = figure.add_subplot(grid[12:20, 0:5])
    narrative_block(
        context_left,
        "Research question",
        "Can an interactive browser representation use a small, deterministic subset of the DESI DR1 LSS catalogue while retaining key redshift, angular-footprint and three-dimensional display properties of the full observed parent table?",
        accent=CYAN,
    )
    context_right = figure.add_subplot(grid[12:20, 5:12])
    narrative_block(
        context_right,
        "Method and interpretation boundary",
        "Three display policies were compared at 125K, 250K, 500K and 1M rows. The diagnostics use redshift divergence, tracer fractions, equal-area sky cells and 250 Mpc Cartesian voxels. No survey weights, random catalogue, mask correction, correlation estimator or density reconstruction is applied.",
        accent=AMBER,
    )

    summary = figure.add_subplot(grid[21:28, :])
    turn_off(summary)
    summary_metric(summary, 0.000, "Observed parent", f"{parent_rows:,}", "Rows validated against the full GPU-cloud manifest.", colour=CYAN)
    summary_metric(summary, 0.255, "Displayed at 125K", f"{int(gpu['selected_rows']):,}", f"{gpu['sampling_fraction'] * 100:.3f}% of the observed parent table.", colour=AMBER)
    summary_metric(summary, 0.510, "Spatial fidelity", f"{gpu['voxel_occupancy_correlation']:.5f}", "GPU voxel-occupancy correlation in 250 Mpc cells.", colour=CYAN)
    summary_metric(summary, 0.765, "Default decision", "GPU profile", "Retained for spatial exploration after the tested trade-off.", colour=GREEN)

    redshift = figure.add_subplot(grid[30:46, 0:7])
    image_panel(
        redshift,
        evidence / "fig_02_redshift_residuals.png",
        "A. Redshift residuals at 125,000 displayed rows",
        "The distribution-balanced candidate reduces one-dimensional redshift residuals. The deployed GPU profile remains close to the parent distribution while preserving stronger three-dimensional representation.",
    )
    table = figure.add_subplot(grid[30:46, 7:12])
    comparison_table(table, gpu, balanced)

    tradeoff = figure.add_subplot(grid[48:64, 0:12])
    tradeoff_plot(tradeoff, metrics)

    sky = figure.add_subplot(grid[66:80, 0:12])
    image_panel(
        sky,
        evidence / "fig_05_sky_cell_residuals.png",
        "C. Observed sky-footprint residuals at 125,000 displayed rows",
        "Equal-area sky cells test how each browser profile represents the observed survey footprint. These residuals are not an angular-mask-corrected clustering measurement.",
    )

    slice_axis = figure.add_subplot(grid[82:94, 0:12])
    image_panel(
        slice_axis,
        evidence / "fig_06_cartesian_slice_comparison.png",
        "D. Same Cartesian display slice under three policies",
        "All panels use the same |Z| <= 150 Mpc slice. They show the visible observed-row representation, not a reconstructed density field, a cosmic-web inference or a void catalogue.",
    )

    conclusion = figure.add_subplot(grid[95:99, :])
    turn_off(conclusion)
    conclusion.add_patch(Rectangle((0, 0), 1, 1, transform=conclusion.transAxes, facecolor=PALE_CYAN, edgecolor=CYAN, linewidth=1.1))
    conclusion.text(0.018, 0.75, "CONCLUSION", fontsize=16, color=CYAN, fontweight="bold", transform=conclusion.transAxes)
    conclusion.text(
        0.018,
        0.48,
        wrap(
            f"At {int(gpu['selected_rows']):,} displayed rows, the distribution-balanced candidate improves redshift Jensen-Shannon divergence by {js_ratio:.1f}x and sky-cell NRMSE by {sky_ratio:.2f}x. The deployed GPU low-discrepancy profile retains stronger 3D display structure: voxel correlation {gpu['voxel_occupancy_correlation']:.5f} versus {balanced['voxel_occupancy_correlation']:.5f}, with occupied-cell recall {gpu['voxel_occupied_cell_recall']:.3f} versus {balanced['voxel_occupied_cell_recall']:.3f}. It therefore remains the default spatial-exploration profile.",
            225,
        ),
        fontsize=14.3,
        color=INK,
        transform=conclusion.transAxes,
        va="top",
        linespacing=1.3,
    )
    conclusion.text(0.018, 0.09, "Future work: test a distribution-balanced profile that also includes a finer three-dimensional spatial constraint.", fontsize=13.2, color=INK, fontweight="bold", transform=conclusion.transAxes)

    footer = figure.add_subplot(grid[99:, :])
    turn_off(footer)
    footer.text(0.0, 0.05, "Input SHA-256: aba7c9236e516459e914d079e4b38bf1e75823ef0707e90da066914a5bda942e", fontsize=9.5, color=MUTED, transform=footer.transAxes)
    footer.text(1.0, 0.05, "Reproducible scripts, metrics and data ledger: github.com/Biswajit1999/NASADIYA-LIGHTCONE", fontsize=9.5, color=MUTED, ha="right", transform=footer.transAxes)

    figure.savefig(output_stem.with_suffix(".pdf"), facecolor=WHITE)
    figure.savefig(output_stem.with_suffix(".png"), dpi=options.dpi, facecolor=WHITE)
    plt.close(figure)
    print(f"Wrote {output_stem.with_suffix('.pdf')}")
    print(f"Wrote {output_stem.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
