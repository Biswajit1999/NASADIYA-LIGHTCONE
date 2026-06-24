# DESI DR1 Large-Scale Structure Catalogue Diagnostics

**Project:** NĀSADĪYA-LIGHTCONE  
**Dataset:** `desi_dr1_lss_research_bundle.parquet`  
**Analysis type:** Descriptive catalogue diagnostics and deterministic Cartesian-slice rendering  
**Generated:** 24 June 2026

---

## 1. Overview

This report summarises descriptive diagnostics produced from the local DESI DR1 Large-Scale Structure research bundle. The analysis scanned **6,093,818 catalogue rows** and was designed to inspect:

- tracer populations across redshift;
- consistency between Cartesian coordinates and stored comoving distances;
- the observed geometry of a thin Cartesian slice through the catalogue;
- reproducible rendering of a representative DESI point sample.

The rendered slice contains **100,000 deterministically selected rows**. It clearly shows nested radial populations and a bilateral survey-footprint geometry.

This is a catalogue-diagnostic and visualisation workflow. It does **not** estimate a correlation function, power spectrum, density field, void catalogue, or cosmological parameter constraints.

---

## 2. Input data and tracer populations

The analysis used the local Parquet file:

```text
data/research/desi_dr1_lss_research_bundle.parquet
```

The catalogue contains four DESI LSS tracer classes:

- **BGS** — Bright Galaxy Survey targets, primarily nearby galaxies.
- **LRG** — Luminous Red Galaxies, tracing comparatively massive red galaxies at intermediate redshift.
- **ELG** — Emission Line Galaxies, extending to higher redshift than BGS and much of the LRG sample.
- **QSO** — Quasars, reaching the highest redshifts in the displayed catalogue.

For every valid row, the diagnostic uses:

- object identifier;
- tracer classification;
- spectroscopic redshift;
- stored comoving distance;
- Cartesian comoving coordinates $x$, $y$, and $z$.

### 2.1 Catalogue composition

| Tracer | Rows | Fraction of catalogue |
|---|---:|---:|
| BGS | 300,017 | 4.92% |
| ELG | 2,432,027 | 39.91% |
| LRG | 2,138,604 | 35.10% |
| QSO | 1,223,170 | 20.08% |
| **Total** | **6,093,818** | **100.00%** |

The catalogue is dominated by ELG and LRG populations, with QSOs providing the deepest redshift reach and BGS occupying the low-redshift regime.

---

## 3. Analysis method

### 3.1 Data cleaning

Rows are retained only when all of the following values are finite:

- redshift;
- comoving distance;
- $x$ coordinate;
- $y$ coordinate;
- $z$ coordinate.

Tracer labels are normalised to uppercase, and missing labels are assigned to `UNKNOWN`.

---

### 3.2 Redshift-composition diagnostic

The catalogue is divided into redshift bins from $z=0$ to $z=3.6$.

For each bin, the fractional contribution of each tracer population is calculated:

$$
f_i(z) = \frac{N_i(z)}{\sum_j N_j(z)}
$$

where:

- $N_i(z)$ is the number of observed rows belonging to tracer $i$ in a redshift bin;
- $\sum_j N_j(z)$ is the total number of observed rows in that bin.

This produces a tracer-composition plot rather than a completeness-corrected population fraction.

---

### 3.3 Coordinate-consistency diagnostic

The analysis checks whether the stored Cartesian coordinates are consistent with the catalogue comoving distance.

For every object, the Cartesian radial distance is calculated as:

$$
r_{\mathrm{Cartesian}} = \sqrt{x^2 + y^2 + z^2}
$$

The coordinate residual is then defined as:

$$
\Delta r = r_{\mathrm{Cartesian}} - \chi
$$

where:

- $x$, $y$, and $z$ are the stored Cartesian comoving coordinates in Mpc;
- $\chi$ is the stored line-of-sight comoving distance in Mpc;
- $\Delta r$ should remain close to zero when both representations are internally consistent.

For each DESI tracer population, the following quantities are calculated across the full catalogue:

- mean residual, $\langle \Delta r \rangle$;
- root-mean-square residual, $\mathrm{RMS}(\Delta r)$;
- mean absolute residual, $\langle |\Delta r| \rangle$;
- maximum absolute residual, $\max |\Delta r|$.

This is a catalogue-validation diagnostic only. It does not test the cosmological model or estimate a physical distance-scale uncertainty.

---

### 3.4 Cartesian slice rendering

A thin Cartesian slab is selected around the plane:

$$
Z = 0\ \mathrm{Mpc}
$$

with total thickness:

$$
\Delta Z = 300\ \mathrm{Mpc}
$$

Therefore, displayed objects satisfy:

$$
|z_{\mathrm{Cartesian}}| \leq 150\ \mathrm{Mpc}
$$

The selected objects are projected into the $X$--$Y$ plane.

To keep the rendered figure responsive while preserving reproducibility, the plotted sample is limited to 100,000 objects. The objects are selected using the globally lowest stable hashes of object IDs inside the slice.

This means that the same dataset and the same analysis settings produce the same displayed sample.

---

## 4. Results

### 4.1 Redshift distribution by tracer

| Tracer | $z_{16}$ | Median $z$ | $z_{84}$ | Interpretation |
|---|---:|---:|---:|---|
| BGS | 0.2143 | 0.3142 | 0.3754 | Nearby bright-galaxy population |
| LRG | 0.5463 | 0.7532 | 0.9210 | Intermediate-redshift massive/red galaxy population |
| ELG | 0.9241 | 1.1601 | 1.4237 | Higher-redshift star-forming galaxy population |
| QSO | 1.1840 | 1.7417 | 2.4385 | Deepest tracer population in this bundle |

The tracer-composition plot shows a clear radial/redshift sequence:

1. **BGS** dominates at low redshift.
2. **LRG** becomes prominent at intermediate redshift.
3. **ELG** dominates much of the approximate range $0.8 \lesssim z \lesssim 1.6$.
4. **QSO** becomes the dominant observed tracer beyond approximately $z\sim1.6$.

This pattern is expected from tracer-target selection. It is an observed-row composition, not a completeness-corrected estimate of the cosmic population mix.

---

### 4.2 Coordinate consistency

| Tracer | Mean $\Delta r$ [Mpc] | RMS $\Delta r$ [Mpc] | Mean $|\Delta r|$ [Mpc] | Max $|\Delta r|$ [Mpc] |
|---|---:|---:|---:|---:|
| BGS | $-2.72\times10^{-8}$ | $4.10\times10^{-5}$ | $3.30\times10^{-5}$ | $1.40\times10^{-4}$ |
| LRG | $+2.94\times10^{-8}$ | $8.70\times10^{-5}$ | $7.00\times10^{-5}$ | $2.92\times10^{-4}$ |
| ELG | $+6.27\times10^{-8}$ | $1.22\times10^{-4}$ | $9.70\times10^{-5}$ | $4.87\times10^{-4}$ |
| QSO | $+1.56\times10^{-7}$ | $1.64\times10^{-4}$ | $1.31\times10^{-4}$ | $5.75\times10^{-4}$ |

The residuals are extremely small compared with the several-thousand-Mpc scale of the plotted survey volume. The maximum absolute mismatch is below approximately:

$$
5.8\times10^{-4}\ \mathrm{Mpc}
$$

or about:

$$
0.58\ \mathrm{kpc}
$$

This demonstrates that the stored Cartesian coordinates and the catalogue comoving distances are internally consistent to much better than one kiloparsec.

For the purpose of interactive visualisation and descriptive analysis, the Cartesian coordinate transformation can therefore be treated as numerically reliable.

---

### 4.3 Observed Cartesian slice

The Cartesian slice shows a strongly structured bilateral geometry with:

- two broad survey lobes;
- missing central angular regions;
- nested radial distributions for different tracer classes;
- sparse high-redshift QSO coverage extending to the largest comoving radii.

The apparent shell-like structure is primarily caused by the combination of:

- DESI sky footprint;
- tracer-specific target selection;
- redshift coverage;
- radial selection effects;
- the chosen thin slice around $Z=0$ Mpc.

The plot should not be interpreted as a direct density map of the Universe.

The central gaps are not evidence for cosmic voids. They arise because the catalogue is not a uniform all-sky sample.

---

## 5. Interpretation of the figures

### Figure 1 — DESI DR1 LSS observed Cartesian slice

The displayed $X$--$Y$ slice contains objects satisfying:

$$
|Z| \leq 150\ \mathrm{Mpc}
$$

The bilateral structure reflects the DESI observed footprint and target selection.

The coloured nested distributions show how different tracer populations occupy different redshift and distance regimes:

- BGS objects remain closest to the observer;
- LRG objects populate larger comoving radii;
- ELGs extend farther outward;
- QSOs occupy the broadest and most distant radial range.

The geometry is observational rather than a direct reconstruction of the underlying matter distribution.

### Figure 2 — DESI DR1 LSS tracer composition by redshift

The redshift-composition plot shows the changing mixture of DESI tracers with redshift.

The key conclusion is that:

$$
P(\mathrm{tracer}\mid z)
$$

changes strongly with redshift.

Therefore, an apparent increase or decrease in point density with distance cannot be interpreted directly as cosmological structure without modelling the relevant selection function.

---

## 6. Scientific limitations

The current diagnostics are intentionally descriptive.

They do not account for:

- DESI angular completeness;
- bright-star masks;
- imaging-systematics masks;
- tracer-specific selection functions;
- radial completeness;
- DESI random catalogues;
- fibre-assignment effects;
- survey window functions.

For this reason, the current point distribution cannot be used alone to claim:

- galaxy overdensities;
- underdensities;
- voids;
- filament significance;
- clustering amplitude;
- cosmological anisotropy;
- physical asymmetry between the two visible lobes.

Any such inference requires comparison with an appropriately matched DESI random catalogue and a validated clustering estimator.

---

## 7. Recommended next analysis stage

A rigorous next stage should include:

1. Obtain the DESI random catalogues matched to each tracer population.
2. Apply the relevant DESI angular mask and completeness information.
3. Construct weighted number-density fields.
4. Estimate the two-point correlation function, for example with the Landy--Szalay estimator:

$$
\xi(s) = \frac{DD(s)-2DR(s)+RR(s)}{RR(s)}
$$

where:

- $DD(s)$ is the data-data pair count;
- $DR(s)$ is the data-random pair count;
- $RR(s)$ is the random-random pair count.

5. Only after selection-function correction, investigate density contrast, void candidates, filamentary structure, baryon acoustic oscillation signatures, or redshift-space distortions.

---

## 8. Suggested wording for the repository

> The DESI DR1 lightcone visualisation uses observed spectroscopic objects with tracer-aware colouring and deterministic sampling. Apparent arcs, wedges, gaps, and bilateral structure reflect the DESI survey footprint and tracer-dependent selection, rather than direct measurements of cosmic density. Quantitative clustering, overdensity, or void inference requires the corresponding DESI random catalogues, angular masks, and survey-selection corrections.

---

## 9. Generated outputs

The analysis produces:

```text
figures/desi_dr1_tracer_statistics.csv
figures/desi_dr1_tracer_composition.png
figures/desi_dr1_cartesian_slice.png
figures/desi_dr1_catalogue_diagnostics.json
```

These outputs provide:

- numerical tracer statistics;
- redshift-distribution diagnostics;
- deterministic Cartesian slice rendering;
- machine-readable summary metadata.

---

## 10. Conclusion

The DESI DR1 research bundle is internally consistent in its Cartesian and radial coordinate representation and produces a visually informative tracer-aware lightcone slice.

The visible large-scale geometry is dominated by survey footprint and tracer-selection structure. It is therefore valuable for educational visualisation and catalogue exploration, but it should not yet be presented as a reconstructed cosmic density field.

The appropriate next step is to integrate the DESI random catalogues and survey masks, enabling statistically valid large-scale structure analysis.
