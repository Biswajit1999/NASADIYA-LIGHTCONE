# DESI DR1 LSS analysis suite

## Purpose

The research bundle contains the full locally built DESI DR1 LSS observed catalogue: 6,093,818 rows in a 185.12 MiB Parquet file. The scripts in this suite turn that bundle into reproducible **descriptive diagnostics** without presenting survey-selection structure as cosmological inference.

## Run the catalogue diagnostics

```cmd
.\.venv\Scripts\python.exe scripts\analyze_desi_catalogue.py --input data\research\desi_dr1_lss_research_bundle.parquet --output-dir figures --slice-z-mpc 0 --slice-thickness-mpc 300 --slice-render-rows 100000
```

It scans every released row and writes:

```text
figures/desi_dr1_catalogue_diagnostics.json
figures/desi_dr1_tracer_statistics.csv
figures/desi_dr1_tracer_composition.png
figures/desi_dr1_cartesian_slice.png
```

### What each output means

| Output | What it measures | What it does not measure |
|---|---|---|
| `tracer_composition.png` | Fraction of observed rows assigned to BGS/LRG/ELG/QSO in each redshift bin | Completeness-corrected population fractions |
| `cartesian_slice.png` | A thin observed Cartesian slice using Planck18 placement | Matter density, filament reconstruction or a statistically complete volume |
| `tracer_statistics.csv` | Counts, approximate redshift quantiles, and geometric-radius versus stored-distance consistency | Astrophysical parameter estimation |
| `catalogue_diagnostics.json` | Reproducible machine-readable settings and statistics | A correlation-function result |

## Scientific boundary

This repository has the observed target catalogues and source positions, but a defensible DESI clustering estimator additionally requires the matching random catalogue, angular mask, redshift selection function, weights, and tracer-specific treatment.

Therefore, do **not** calculate or label the following from this bundle alone:

- two-point correlation function, \(\xi(r)\);
- power spectrum, \(P(k)\);
- physical density field or “void” map;
- bias, growth-rate or BAO measurement; or
- cross-tracer clustering amplitude.

A future `clustering/` workflow can be added after the corresponding official DESI random catalogues and weighting documentation are ingested and validated.

## Useful parameter variations

A near-observer slice:

```cmd
.\.venv\Scripts\python.exe scripts\analyze_desi_catalogue.py --slice-z-mpc 0 --slice-thickness-mpc 300
```

A deep slice through the North/South footprint:

```cmd
.\.venv\Scripts\python.exe scripts\analyze_desi_catalogue.py --slice-z-mpc 2500 --slice-thickness-mpc 500
```

The slice rendering remains deterministic: it selects the global lowest object-ID hashes among observed rows inside the requested slab.
