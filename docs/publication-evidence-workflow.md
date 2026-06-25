# Figure-first publication evidence workflow

This workflow produces the figures that will determine whether a conference poster or manuscript can make a defensible claim about the NĀSADĪYA browser representation.

## What this analysis tests

The analysis compares browser display subsets with the same observed DESI DR1 LSS parent table.

It reports:

- redshift-distribution divergence;
- tracer-fraction residuals;
- observed sky-cell representation residuals;
- Cartesian voxel-occupancy representation metrics; and
- the difference between the current GPU index-threshold display policy and two deterministic alternatives.

It does **not** apply survey weights, a random catalogue, angular masks, completeness modelling, a correlation-function estimator, a power-spectrum estimator, or a density reconstruction. It must not be described as a cosmic-web reconstruction or a clustering measurement.

## Exact current-renderer check

`gpu_index` intentionally reproduces the current full-cloud WebGL selection rule:

```text
(index × 0.618033988749895) mod 1 <= displayed_rows / GPU_resident_rows
```

The browser stores this sequence in a `Float32Array`; the evidence code reproduces the Float32 conversion. This policy depends on the row order used by `scripts/full_gpu.py`. The analysis checks that the valid parent-row count matches `full-cloud.json` before treating it as an exact renderer comparison.

## Run locally with the installed Anaconda Python

Use the same Python executable that owns the installed Parquet dependencies:

```bat
C:\Users\biswa\anaconda3\python.exe
```

When PyArrow is missing or has a Windows DLL problem, install the dependencies through Conda rather than mixing unrelated Python installations:

```bat
C:\Users\biswa\anaconda3\Scripts\conda.exe install -n base -c conda-forge pyarrow pandas numpy scipy matplotlib -y
```

Verify the exact interpreter and PyArrow import:

```bat
C:\Users\biswa\anaconda3\python.exe -c "import sys, pyarrow; print(sys.executable); print(pyarrow.__version__)"
```

Then run:

```bat
cd /d C:\Users\biswa\Documents\GitHub\NASADIYA-LIGHTCONE
C:\Users\biswa\anaconda3\python.exe scripts\build_desi_publication_figures.py ^
  --input data\research\desi_dr1_lss_research_bundle.parquet ^
  --full-cloud-manifest data\processed\desi-dr1\full-cloud\full-cloud.json ^
  --output-dir figures\publication_evidence ^
  --budgets 125000,250000,500000,1000000 ^
  --poster-budget 125000 ^
  --dpi 300
```

## Run in Google Colab

Open `notebooks/DESI_DR1_Publication_Evidence_Colab.ipynb` directly in Google Colab. It is a real notebook, not a Windows command. It installs dependencies in Colab, accepts the Parquet file from Google Drive or direct upload, runs the figure suite, displays the outputs, and downloads a ZIP archive.

## Outputs

The run writes both PNG and vector PDF figures, `representation_fidelity_metrics.csv`, `tracer_fraction_residuals.csv`, and `evidence_manifest.json`.

## Required review before poster construction

Open the six figures and inspect the metric CSV. The poster must use only the figures and numerical values created in that run. Do not replace a result with a synthetic visualisation.

Recommended poster figure selection:

1. `fig_01_parent_tracer_redshift` — survey context;
2. `fig_02_redshift_residuals` — direct browser-representation comparison;
3. `fig_04_voxel_fidelity_convergence` — spatial-representation metric;
4. `fig_05_sky_cell_residuals` — observed-footprint representation;
5. one dashboard screenshot marked explicitly as *browser interface*, not as scientific evidence.

## Version the evidence package

After a successful run:

```bat
git add figures\publication_evidence\*.png figures\publication_evidence\*.pdf figures\publication_evidence\*.csv figures\publication_evidence\*.json
git commit -m "results: add DESI browser representation evidence figures"
git push origin main
```

Do not commit the 194 MB research Parquet bundle or the 120+ MB raw GPU binary as ordinary Git objects.
