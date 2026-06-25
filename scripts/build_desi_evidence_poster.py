#!/usr/bin/env python3
"""Build a white A0 poster from a completed DESI representation-evidence run.

The poster uses only figures and metrics written by
``scripts/build_desi_publication_figures.py``. It deliberately avoids synthetic
cosmic-web illustration and makes the browser-representation scope explicit.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import textwrap

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
A0_WIDTH_IN = 33.1102
A0_HEIGHT_IN = 46.8110

NAVY = "#071827"
INK = "#102b3b"
MUTED = "#4f6877"
CYAN = "#23aac8"
CYAN_LIGHT = "#e9f8fb"
AMBER = "#d98d2b"
AMBER_LIGHT = "#fff5e6"
LINE = "#bdd3dc"


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=PROJECT_ROOT / "figures" / "publication_evidence")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "assets" / "posters")
    parser.add_argument("--budget", type=int, default=125_000)
    parser.add_argument("--dpi", type=int, default=180)
    return parser.parse_args()


def metric_row(metrics: pd.DataFrame, budget: int, policy: str) -> pd.Series:
    selection = metrics.loc[(metrics["requested_rows"] == budget) & (metrics["policy"] == policy)]
    if len(selection) != 1:
        raise ValueError(f"Expected one row for budget={budget:,}, policy={policy!r}; found {len(selection)}.")
    return selection.iloc[0]


def figure_panel(fig, slot, image_path: Path, heading: str, caption: str) -> None:
    axis = fig.add_subplot(slot)
    axis.imshow(mpimg.imread(image_path))
    axis.set_axis_off()
    axis.set_title(heading, loc="left", fontsize=15, color=NAVY, fontweight="bold", pad=9)
    axis.text(0.0, -0.075, caption, transform=axis.transAxes, ha="left", va="top", fontsize=9.4, color=MUTED, wrap=True)


def card(axis, x: float, y: float, width: float, height: float, title: str, value: str, note: str, *, accent: str = CYAN, background: str = "#ffffff") -> None:
    patch = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.012,rounding_size=0.018", linewidth=1.0, edgecolor=accent, facecolor=background, transform=axis.transAxes)
    axis.add_patch(patch)
    axis.text(x + 0.022, y + height * 0.72, title.upper(), transform=axis.transAxes, fontsize=8.5, color=accent, fontweight="bold", va="center")
    axis.text(x + 0.022, y + height * 0.45, value, transform=axis.transAxes, fontsize=19, color=NAVY, fontweight="bold", va="center")
    axis.text(x + 0.022, y + height * 0.16, note, transform=axis.transAxes, fontsize=8.1, color=MUTED, va="center", wrap=True)


def write_wrapped(axis, x: float, y: float, text: str, width: int, *, fontsize: float = 10.4, color: str = INK, weight: str = "normal") -> None:
    axis.text(x, y, textwrap.fill(text, width=width), transform=axis.transAxes, ha="left", va="top", fontsize=fontsize, color=color, fontweight=weight, linespacing=1.42)


def main() -> int:
    options = args()
    evidence = options.evidence_dir
    required = [
        "representation_fidelity_metrics.csv",
        "fig_01_parent_tracer_redshift.png",
        "fig_02_redshift_residuals.png",
        "fig_04_voxel_fidelity_convergence.png",
        "fig_05_sky_cell_residuals.png",
        "fig_06_cartesian_slice_comparison.png",
    ]
    missing = [name for name in required if not (evidence / name).exists()]
    if missing:
        raise FileNotFoundError("Missing evidence output(s): " + ", ".join(missing))

    metrics = pd.read_csv(evidence / "representation_fidelity_metrics.csv")
    gpu = metric_row(metrics, options.budget, "gpu_index")
    stratified = metric_row(metrics, options.budget, "tracer_sky_redshift_hash")
    parent_rows = 6_093_818
    fraction = float(gpu["sampling_fraction"])
    js_ratio = float(gpu["redshift_js_bits"] / stratified["redshift_js_bits"])
    sky_ratio = float(gpu["sky_occupancy_nrmse"] / stratified["sky_occupancy_nrmse"])

    options.output_dir.mkdir(parents=True, exist_ok=True)
    output_stem = options.output_dir / "nasadiya_lightcone_A0_evidence_poster_white"
    figure = plt.figure(figsize=(A0_WIDTH_IN, A0_HEIGHT_IN), facecolor="white")
    grid = figure.add_gridspec(36, 12, left=0.045, right=0.955, top=0.965, bottom=0.045, wspace=0.42, hspace=1.15)

    header = figure.add_subplot(grid[0:4, :])
    header.axis("off")
    header.add_patch(Rectangle((0, 0.91), 1, 0.026, transform=header.transAxes, color=CYAN, clip_on=False))
    header.text(0.0, 0.79, "NĀSADĪYA LIGHTCONE", fontsize=16, color=AMBER, fontweight="bold")
    header.text(0.0, 0.57, "Validating browser-level representations of the DESI DR1 LSS catalogue", fontsize=32, color=NAVY, fontweight="bold", va="center")
    header.text(0.0, 0.32, "A reproducible comparison of full-GPU point-cloud display policies for 6,093,818 observed rows", fontsize=15, color=MUTED)
    header.text(0.0, 0.11, "Biswajit Jana  |  Independent Researcher  |  github.com/Biswajit1999/NASADIYA-LIGHTCONE", fontsize=10.5, color=INK)
    header.text(1.0, 0.11, "DESI DR1 LSS observed catalogue", fontsize=10.5, color=INK, ha="right")

    summary = figure.add_subplot(grid[4:7, :])
    summary.axis("off")
    card(summary, 0.000, 0.08, 0.232, 0.82, "Observed parent", f"{parent_rows:,}", "Rows validated against the GPU-cloud manifest.", accent=CYAN, background=CYAN_LIGHT)
    card(summary, 0.255, 0.08, 0.232, 0.82, "Poster profile", f"{int(gpu['selected_rows']):,}", f"Displayed rows ({fraction * 100:.3f}% of parent).", accent=AMBER, background=AMBER_LIGHT)
    card(summary, 0.510, 0.08, 0.232, 0.82, "GPU spatial score", f"{gpu['voxel_occupancy_correlation']:.5f}", "Scaled 250 Mpc voxel-occupancy correlation at the poster budget.", accent=CYAN, background=CYAN_LIGHT)
    card(summary, 0.765, 0.08, 0.232, 0.82, "Redshift JSD", f"{gpu['redshift_js_bits']:.2e}", "Bits relative to the same observed parent redshift distribution.", accent=AMBER, background=AMBER_LIGHT)

    left = figure.add_subplot(grid[7:11, 0:6])
    left.axis("off")
    left.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.016,rounding_size=0.018", facecolor="#f5fafc", edgecolor=LINE, linewidth=1.0, transform=left.transAxes))
    left.text(0.035, 0.90, "QUESTION", fontsize=12, color=CYAN, fontweight="bold")
    write_wrapped(left, 0.035, 0.77, "Can a browser display a small deterministic subset of the DESI DR1 LSS catalogue while retaining the observed redshift distribution, sky-footprint occupancy and three-dimensional display structure?", 64, fontsize=12.2, color=NAVY, weight="bold")
    left.text(0.035, 0.24, "Representation metrics only", fontsize=10.3, color=AMBER, fontweight="bold")
    write_wrapped(left, 0.035, 0.16, "No random catalogue, survey weights, completeness correction, correlation estimator, or density reconstruction is used.", 75, fontsize=9.4)

    right = figure.add_subplot(grid[7:11, 6:12])
    right.axis("off")
    right.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.016,rounding_size=0.018", facecolor="#fffaf2", edgecolor="#ecd4b2", linewidth=1.0, transform=right.transAxes))
    right.text(0.035, 0.90, "METHOD", fontsize=12, color=AMBER, fontweight="bold")
    write_wrapped(right, 0.035, 0.77, "At 125K, 250K, 500K and 1M display budgets, the deployed GPU low-discrepancy index threshold is compared with an object-ID hash and a tracer × equal-area-sky × redshift stratified hash.", 67, fontsize=10.5, color=NAVY)
    right.text(0.035, 0.26, "Diagnostics", fontsize=10.3, color=CYAN, fontweight="bold")
    write_wrapped(right, 0.035, 0.18, "Redshift Jensen-Shannon divergence; tracer total-variation distance; equal-area sky-cell residuals; and 250 Mpc Cartesian voxel-occupancy diagnostics.", 73, fontsize=9.4)

    figure_panel(figure, grid[11:17, 0:6], evidence / "fig_02_redshift_residuals.png", "A. Redshift residuals at 125K", "The stratified candidate follows the parent redshift distribution more closely. The current GPU profile remains within approximately ±0.07 percentage points per plotted bin.")
    figure_panel(figure, grid[11:17, 6:12], evidence / "fig_04_voxel_fidelity_convergence.png", "B. Spatial fidelity across display budgets", "The deployed GPU profile produces the highest tested voxel-occupancy correlation at every budget. This is the relevant default criterion for interactive spatial exploration.")
    figure_panel(figure, grid[18:24, 0:12], evidence / "fig_05_sky_cell_residuals.png", "C. Observed sky-footprint representation at 125K", "The tracer + sky + redshift profile reduces angular-cell residuals. These are representation diagnostics of observed rows, not an angular-mask-corrected analysis.")
    figure_panel(figure, grid[25:31, 0:12], evidence / "fig_06_cartesian_slice_comparison.png", "D. Same Cartesian slice, three display policies", "All panels use the same central |Z| <= 150 Mpc slice. The visual comparison is included to show the displayed survey geometry, not to claim a density field or reconstructed cosmic web.")

    conclusion = figure.add_subplot(grid[32:35, :])
    conclusion.axis("off")
    conclusion.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.016,rounding_size=0.018", facecolor="#f7fbfc", edgecolor=LINE, linewidth=1.1, transform=conclusion.transAxes))
    conclusion.text(0.025, 0.79, "RESULT AND PLATFORM DECISION", fontsize=12, color=CYAN, fontweight="bold")
    write_wrapped(conclusion, 0.025, 0.61, f"At {int(gpu['selected_rows']):,} displayed rows, the stratified candidate reduces redshift divergence by {js_ratio:.1f}× and sky-cell NRMSE by {sky_ratio:.2f}×. However, the deployed GPU profile retains stronger three-dimensional occupancy representation: voxel correlation {gpu['voxel_occupancy_correlation']:.5f} versus {stratified['voxel_occupancy_correlation']:.5f}, and occupied-cell recall {gpu['voxel_occupied_cell_recall']:.3f} versus {stratified['voxel_occupied_cell_recall']:.3f}.", 190, fontsize=10.4, color=INK)
    conclusion.text(0.025, 0.18, "Decision: retain the GPU low-discrepancy profile as the default spatial-exploration display. A distribution-balanced profile remains future work and must include a finer 3D spatial constraint before it can replace the default.", fontsize=10.5, color=NAVY, fontweight="bold", wrap=True)

    footer = figure.add_subplot(grid[35:, :])
    footer.axis("off")
    footer.add_patch(Rectangle((0, 0.75), 1, 0.025, transform=footer.transAxes, color=CYAN, clip_on=False))
    footer.text(0.0, 0.40, "Input SHA-256: aba7c9236e516459e914d079e4b38bf1e75823ef0707e90da066914a5bda942e", fontsize=8.2, color=MUTED)
    footer.text(1.0, 0.40, "Reproducible scripts and data ledger: github.com/Biswajit1999/NASADIYA-LIGHTCONE", fontsize=8.2, color=MUTED, ha="right")

    figure.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight")
    figure.savefig(output_stem.with_suffix(".png"), dpi=options.dpi, bbox_inches="tight")
    plt.close(figure)
    print(f"Wrote {output_stem.with_suffix('.pdf')}")
    print(f"Wrote {output_stem.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
