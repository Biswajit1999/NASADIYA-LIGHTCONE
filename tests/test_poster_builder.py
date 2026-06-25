from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def write_image(path: Path) -> None:
    figure, axis = plt.subplots(figsize=(1.2, 0.8))
    axis.imshow(np.linspace(0.0, 1.0, 64).reshape(8, 8), cmap="viridis")
    axis.set_axis_off()
    figure.savefig(path, dpi=30, bbox_inches="tight")
    plt.close(figure)


def test_poster_builder_generates_a0_pdf_and_png(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    pd.DataFrame(
        [
            {
                "requested_rows": 125000,
                "selected_rows": 125001,
                "sampling_fraction": 0.0205127557,
                "redshift_js_bits": 2.2e-5,
                "sky_occupancy_nrmse": 0.0075,
                "voxel_occupancy_correlation": 0.9842,
                "voxel_occupied_cell_recall": 0.5956,
                "policy": "gpu_index",
            },
            {
                "requested_rows": 125000,
                "selected_rows": 125000,
                "sampling_fraction": 0.0205125916,
                "redshift_js_bits": 1.5e-6,
                "sky_occupancy_nrmse": 0.0021,
                "voxel_occupancy_correlation": 0.9788,
                "voxel_occupied_cell_recall": 0.5819,
                "policy": "tracer_sky_redshift_hash",
            },
        ]
    ).to_csv(evidence / "representation_fidelity_metrics.csv", index=False)
    for filename in (
        "fig_01_parent_tracer_redshift.png",
        "fig_02_redshift_residuals.png",
        "fig_04_voxel_fidelity_convergence.png",
        "fig_05_sky_cell_residuals.png",
        "fig_06_cartesian_slice_comparison.png",
    ):
        write_image(evidence / filename)
    output = tmp_path / "poster"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_desi_evidence_poster.py"),
            "--evidence-dir",
            str(evidence),
            "--output-dir",
            str(output),
            "--dpi",
            "20",
        ],
        check=True,
    )
    assert (output / "nasadiya_lightcone_A0_evidence_poster_white.pdf").exists()
    assert (output / "nasadiya_lightcone_A0_evidence_poster_white.png").exists()
