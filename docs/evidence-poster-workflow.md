# Evidence-poster workflow

The A0 poster is generated from the completed representation-evidence package. It does not contain a synthetic cosmic-web illustration or placeholder metrics.

## Required inputs

Run `scripts/build_desi_publication_figures.py` first. The poster builder requires:

- `representation_fidelity_metrics.csv`
- `fig_01_parent_tracer_redshift.png`
- `fig_02_redshift_residuals.png`
- `fig_04_voxel_fidelity_convergence.png`
- `fig_05_sky_cell_residuals.png`
- `fig_06_cartesian_slice_comparison.png`

## Build the white A0 poster

```bat
cd /d C:\Users\biswa\Documents\GitHub\NASADIYA-LIGHTCONE
C:\Users\biswa\anaconda3\Scripts\conda.exe run -n nasadiya-evidence python scripts\build_desi_evidence_poster.py ^
  --evidence-dir figures\publication_evidence ^
  --output-dir assets\posters ^
  --budget 125000 ^
  --dpi 180
```

The script writes:

```text
assets/posters/nasadiya_lightcone_A0_evidence_poster_white.pdf
assets/posters/nasadiya_lightcone_A0_evidence_poster_white.png
```

The PDF uses the exact A0 portrait canvas: **841 mm x 1189 mm**.

## Review before printing or publishing

Open the PNG at 100% and verify:

- figure captions remain readable;
- no panel title overlaps a plot;
- the conclusion refers only to values present in `representation_fidelity_metrics.csv`;
- the limitation statement remains visible;
- the embedded figures are the outputs from the matching evidence run.

Do not call this a DESI clustering, cosmic-web, void, or density-reconstruction result. The poster reports browser-representation fidelity of observed rows.
