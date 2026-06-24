# DESI DR1 Large-Scale Structure Catalogue Diagnostics

**Project:** NĀSADĪYA-LIGHTCONE  
**Dataset:** `desi_dr1_lss_research_bundle.parquet`  
**Analysis type:** Descriptive catalogue diagnostics and deterministic Cartesian-slice rendering  
**Generated:** 24 June 2026

---

## 1. Overview

This report summarises descriptive diagnostics produced from the local DESI DR1 Large-Scale Structure research bundle. The analysis scanned **6,093,818 catalogue rows** and inspected tracer populations across redshift, coordinate consistency, and the observed geometry of a deterministic Cartesian slice.

The rendered slice contains **100,000 deterministically selected rows**. It clearly shows nested radial populations and a bilateral survey-footprint geometry.

This is a catalogue-diagnostic and visualisation workflow. It does **not** estimate a correlation function, power spectrum, density field, void catalogue, or cosmological parameter constraints.

---

## 2. Input data and tracer populations

The analysis used:

```text
data/research/desi_dr1_lss_research_bundle.parquet
```

The DESI LSS tracer classes are:

- **BGS** — Bright Galaxy Survey targets, primarily nearby galaxies.
- **LRG** — Luminous Red Galaxies at intermediate redshift.
- **ELG** — Emission Line Galaxies, extending to higher redshift.
- **QSO** — Quasars, reaching the highest redshifts in this catalogue.

For every valid row, the diagnostic uses object ID, tracer class, spectroscopic redshift, stored comoving distance, and Cartesian comoving coordinates `x`, `y`, and `z`.

### 2.1 Catalogue composition

| Tracer | Rows | Fraction of catalogue |
|---|---:|---:|
| BGS | 300,017 | 4.92% |
| ELG | 2,432,027 | 39.91% |
| LRG | 2,138,604 | 35.10% |
| QSO | 1,223,170 | 20.08% |
| **Total** | **6,093,818** | **100.00%** |

---

## 3. Analysis method

### 3.1 Data cleaning

Rows are retained only when redshift, comoving distance, and all Cartesian coordinates are finite. Tracer labels are normalised to uppercase; missing labels are assigned to `UNKNOWN`.

### 3.2 Redshift-composition diagnostic

The catalogue is divided into redshift bins from `z = 0` to `z = 3.6`.

For each bin, the observed fraction of each tracer is calculated:

```text
fraction_i(z) = N_i(z) / sum_j N_j(z)
```

This is an observed-row composition, not a completeness-corrected population fraction.

### 3.3 Coordinate-consistency diagnostic

For every object, the Cartesian radial distance is calculated as:

```text
r_cartesian = sqrt(x² + y² + z²)
```

The coordinate residual is:

```text
delta_r = r_cartesian - chi
```

where `chi` is the stored line-of-sight comoving distance in Mpc.

For each tracer, the analysis calculates:

- mean `delta_r`;
- RMS `delta_r`;
- mean absolute `delta_r`;
- maximum absolute `delta_r`.

This is a catalogue-validation diagnostic only. It does not test the cosmological model or estimate a physical distance-scale uncertainty.

### 3.4 Cartesian slice rendering

A thin slab is selected around:

```text
Z = 0 Mpc
```

with total thickness:

```text
delta_Z = 300 Mpc
```

Displayed objects therefore satisfy:

```text
abs(z_cartesian) <= 150 Mpc
```

The selected objects are projected into the X–Y plane. To preserve reproducibility while keeping the plot responsive, the rendered sample is limited to 100,000 rows selected by the globally lowest stable object-ID hashes within the slice.

---

## 4. Results

### 4.1 Redshift distribution by tracer

| Tracer | z16 | Median z | z84 | Interpretation |
|---|---:|---:|---:|---|
| BGS | 0.2143 | 0.3142 | 0.3754 | Nearby bright-galaxy population |
| LRG | 0.5463 | 0.7532 | 0.9210 | Intermediate-redshift massive/red galaxy population |
| ELG | 0.9241 | 1.1601 | 1.4237 | Higher-redshift star-forming galaxy population |
| QSO | 1.1840 | 1.7417 | 2.4385 | Deepest tracer population in this bundle |

The tracer-composition plot shows a clear redshift sequence:

1. **BGS** dominates at low redshift.
2. **LRG** becomes prominent at intermediate redshift.
3. **ELG** dominates much of the approximate range `0.8 < z < 1.6`.
4. **QSO** becomes the dominant observed tracer beyond approximately `z ~ 1.6`.

This progression is expected from tracer-target selection. It is not a completeness-corrected estimate of the cosmic population mix.

### 4.2 Coordinate consistency

| Tracer | Mean delta_r (Mpc) | RMS delta_r (Mpc) | Mean abs(delta_r) (Mpc) | Max abs(delta_r) (Mpc) |
|---|---:|---:|---:|---:|
| BGS | -2.72e-8 | 4.10e-5 | 3.30e-5 | 1.40e-4 |
| LRG | +2.94e-8 | 8.70e-5 | 7.00e-5 | 2.92e-4 |
| ELG | +6.27e-8 | 1.22e-4 | 9.70e-5 | 4.87e-4 |
| QSO | +1.56e-7 | 1.64e-4 | 1.31e-4 | 5.75e-4 |

The residuals are extremely small compared with the several-thousand-Mpc scale of the plotted survey volume. The maximum absolute mismatch is below approximately:

```text
5.8e-4 Mpc = 0.58 kpc
```

This demonstrates that the stored Cartesian coordinates and catalogue comoving distances are internally consistent to much better than one kiloparsec.

For interactive visualisation and descriptive analysis, the Cartesian coordinate transformation can therefore be treated as numerically reliable.

### 4.3 Observed Cartesian slice

The Cartesian slice shows a strongly structured bilateral geometry with:

- two broad survey lobes;
- missing central angular regions;
- nested radial distributions for different tracer classes;
- sparse high-redshift QSO coverage extending to the largest comoving radii.

The apparent shell-like structure is primarily caused by the combination of DESI sky footprint, tracer-specific target selection, redshift coverage, radial selection effects, and the chosen thin slice around `Z = 0 Mpc`.

The plot should not be interpreted as a direct density map of the Universe. The central gaps are not evidence for cosmic voids; the catalogue is not a uniform all-sky sample.

---

## 5. Interpretation of the figures

### Figure 1 — DESI DR1 LSS observed Cartesian slice

The X–Y slice includes objects satisfying:

```text
abs(Z) <= 150 Mpc
```

The bilateral structure reflects the DESI observed footprint and target selection.

The coloured nested distributions show how different tracer populations occupy distinct redshift and distance regimes:

- BGS objects remain closest to the observer;
- LRG objects populate larger comoving radii;
- ELGs extend farther outward;
- QSOs occupy the broadest and most distant radial range.

The geometry is observational rather than a reconstruction of the underlying matter distribution.

### Figure 2 — DESI DR1 LSS tracer composition by redshift

The redshift-composition plot shows that tracer class changes strongly with redshift. Therefore, an apparent increase or decrease in point density with distance cannot be interpreted directly as cosmological structure without modelling the relevant selection function.

---

## 6. Scientific limitations

The current diagnostics are intentionally descriptive. They do not account for:

- DESI angular completeness;
- bright-star masks;
- imaging-systematics masks;
- tracer-specific selection functions;
- radial completeness;
- DESI random catalogues;
- fibre-assignment effects;
- survey window functions.

For this reason, the current point distribution cannot be used alone to claim galaxy overdensities, underdensities, voids, filament significance, clustering amplitude, cosmological anisotropy, or physical asymmetry between the two visible lobes.

Any such inference requires comparison with an appropriately matched DESI random catalogue and a validated clustering estimator.

---

## 7. Recommended next analysis stage

A rigorous next stage should include:

1. Obtain DESI random catalogues matched to each tracer population.
2. Apply the relevant angular mask and completeness information.
3. Construct weighted number-density fields.
4. Estimate the two-point correlation function, for example with the Landy–Szalay estimator:

```text
xi(s) = [DD(s) - 2DR(s) + RR(s)] / RR(s)
```

where `DD`, `DR`, and `RR` are data–data, data–random, and random–random pair counts.

5. Only after selection-function correction, investigate density contrast, void candidates, filamentary structure, baryon acoustic oscillation signatures, or redshift-space distortions.

---

## 8. Suggested wording for the repository

> The DESI DR1 lightcone visualisation uses observed spectroscopic objects with tracer-aware colouring and deterministic sampling. Apparent arcs, wedges, gaps, and bilateral structure reflect the DESI survey footprint and tracer-dependent selection, rather than direct measurements of cosmic density. Quantitative clustering, overdensity, or void inference requires the corresponding DESI random catalogues, angular masks, and survey-selection corrections.

---

## 9. Generated outputs

```text
figures/desi_dr1_tracer_statistics.csv
figures/desi_dr1_tracer_composition.png
figures/desi_dr1_cartesian_slice.png
figures/desi_dr1_catalogue_diagnostics.json
```

These outputs provide numerical tracer statistics, redshift-distribution diagnostics, deterministic Cartesian slice rendering, and machine-readable summary metadata.

---

## 10. Conclusion

The DESI DR1 research bundle is internally consistent in its Cartesian and radial coordinate representation and produces a visually informative tracer-aware lightcone slice.

The visible large-scale geometry is dominated by survey footprint and tracer-selection structure. It is valuable for educational visualisation and catalogue exploration, but should not yet be presented as a reconstructed cosmic density field.

The appropriate next step is to integrate the DESI random catalogues and survey masks, enabling statistically valid large-scale structure analysis.
