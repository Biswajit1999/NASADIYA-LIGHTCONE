# DESI DR1 LSS Catalogue Diagnostics Report

**Project:** NĀSADĪYA-LIGHTCONE  
**Dataset:** `desi_dr1_lss_research_bundle.parquet`  
**Analysis type:** Descriptive catalogue diagnostics and deterministic Cartesian slice rendering  
**Generated:** 24 June 2026  

---

## 1. Executive summary

This report documents a first-pass diagnostic analysis of the local DESI DR1 Large-Scale Structure (LSS) research bundle. The analysis scanned **6,093,818 catalogue rows** and produced:

- a per-tracer redshift summary;
- an internal coordinate-consistency check between stored Cartesian coordinates and comoving distance;
- a deterministic Cartesian slice at **Z = 0 Mpc** with a thickness of **300 Mpc**;
- a redshift-dependent tracer-composition figure.

The rendered slice contains **100,000 deterministically selected rows**. It clearly shows nested radial populations and a bilateral survey-footprint geometry. These visible structures should **not** be interpreted directly as cosmological overdensities, voids, or filaments because the view is strongly shaped by the DESI angular footprint and tracer-specific target selection.

The coordinate-consistency diagnostic is excellent. For all tracer populations, the maximum difference between the Cartesian radius,

\[
r = \sqrt{x^2+y^2+z^2},
\]

and the stored comoving distance \(\chi\) is below **5.75 × 10⁻⁴ Mpc** (about **0.575 kpc**). This confirms that the Cartesian positions in the research bundle are internally consistent with the supplied radial distances to high numerical precision.

---

## 2. Dataset and analysis scope

The analysis used the local Parquet file:

```text
data/research/desi_dr1_lss_research_bundle.parquet
```

The catalogue contains four tracer classes:

- **BGS** — Bright Galaxy Survey targets;
- **LRG** — Luminous Red Galaxies;
- **ELG** — Emission Line Galaxies;
- **QSO** — Quasars.

The present analysis is deliberately limited to catalogue description and visual diagnostics. It does **not** estimate:

- the two-point correlation function;
- a power spectrum;
- a density field;
- void candidates;
- cosmological parameters;
- completeness-corrected number densities.

Those analyses require the tracer-specific DESI random catalogues, angular completeness information, survey masks, and a validated estimator.

---

## 3. Methodology

### 3.1 Catalogue normalisation

For each row, the analysis retained only finite values of:

- spectroscopic redshift;
- comoving distance;
- Cartesian coordinates \(x\), \(y\), and \(z\).

Tracer labels were standardised to uppercase.

### 3.2 Redshift diagnostics

For each tracer, the 16th percentile, median, and 84th percentile of the observed redshift distribution were estimated from a binned histogram over \(0 \le z \le 3.6\).

### 3.3 Coordinate-consistency diagnostic

The analysis calculated:

\[
\Delta r = \sqrt{x^2+y^2+z^2} - \chi,
\]

where \(\chi\) is the stored comoving distance in Mpc.

For each tracer, the mean, root-mean-square (RMS), mean absolute, and maximum absolute value of \(\Delta r\) were computed across the full catalogue.

### 3.4 Cartesian slice rendering

A thin slab centred at:

\[
Z = 0 \; \mathrm{Mpc}
\]

with thickness:

\[
\Delta Z = 300 \; \mathrm{Mpc}
\]

was selected. To make the figure reproducible and prevent overplotting, exactly **100,000** rows were retained by selecting the globally lowest stable hashes of object IDs inside the slab. This makes the rendered subset deterministic: identical input data and settings produce identical plotted points.

---

## 4. Catalogue composition

| Tracer | Rows | Fraction of catalogue |
|---|---:|---:|
| BGS | 300,017 | 4.92% |
| ELG | 2,432,027 | 39.91% |
| LRG | 2,138,604 | 35.10% |
| QSO | 1,223,170 | 20.08% |
| **Total** | **6,093,818** | **100.00%** |

The catalogue is dominated by ELG and LRG populations, with QSOs providing the deepest redshift reach and BGS occupying the low-redshift regime.

---

## 5. Redshift distribution by tracer

| Tracer | z16 | Median z | z84 | Interpretation |
|---|---:|---:|---:|---|
| BGS | 0.2143 | 0.3142 | 0.3754 | Nearby bright-galaxy population |
| LRG | 0.5463 | 0.7532 | 0.9210 | Intermediate-redshift massive/red galaxy population |
| ELG | 0.9241 | 1.1601 | 1.4237 | Higher-redshift star-forming galaxy population |
| QSO | 1.1840 | 1.7417 | 2.4385 | Deepest tracer population in this bundle |

### Interpretation

The tracer-composition plot shows a clear radial/redshift sequence:

1. **BGS** dominates at low redshift.
2. **LRG** becomes prominent at intermediate redshift.
3. **ELG** dominates much of the approximately \(0.8 \lesssim z \lesssim 1.6\) interval.
4. **QSO** becomes the dominant observed tracer beyond approximately \(z \sim 1.6\).

This pattern is expected from the target-selection design of the DESI LSS samples. It is an observed-row composition, not a completeness-corrected estimate of the cosmic population mix.

---

## 6. Coordinate consistency results

| Tracer | Mean Δr [Mpc] | RMS Δr [Mpc] | Mean |Δr| [Mpc] | Max |Δr| [Mpc] |
|---|---:|---:|---:|---:|
| BGS | -2.72 × 10⁻⁸ | 4.10 × 10⁻⁵ | 3.30 × 10⁻⁵ | 1.40 × 10⁻⁴ |
| LRG | +2.94 × 10⁻⁸ | 8.70 × 10⁻⁵ | 7.00 × 10⁻⁵ | 2.92 × 10⁻⁴ |
| ELG | +6.27 × 10⁻⁸ | 1.22 × 10⁻⁴ | 9.70 × 10⁻⁵ | 4.87 × 10⁻⁴ |
| QSO | +1.56 × 10⁻⁷ | 1.64 × 10⁻⁴ | 1.31 × 10⁻⁴ | 5.75 × 10⁻⁴ |

### Interpretation

The residuals are extremely small compared with the several-thousand-Mpc scale of the plotted survey volume. The largest residual, found for QSO rows, is only about **0.575 kpc**.

This strongly supports the conclusion that:

- the Cartesian coordinates are numerically consistent with the stored comoving distances;
- the slice geometry is being rendered from internally coherent positional information;
- any large-scale visual patterns in the slice are not caused by a basic coordinate-conversion mismatch.

---

## 7. Cartesian slice interpretation

The Cartesian slice is centred on \(Z=0\) Mpc and includes objects satisfying:

\[
|Z| \le 150 \; \mathrm{Mpc}.
\]

The figure shows a pronounced bilateral or “butterfly-like” geometry, with nested regions associated with the tracer populations.

### What the plot shows

- **Blue BGS points** occupy the closest radial region.
- **Orange LRG points** form a larger intermediate-distance layer.
- **Green ELG points** extend farther outward.
- **Pink QSO points** populate the broadest and most distant visible region.
- The two-sided structure and central gaps arise primarily from the observed DESI sky footprint intersected by a thin Cartesian slab.

### What the plot does not show

The visible arcs, gaps, wedges, and apparent sparse regions are **not sufficient evidence** for physical voids or underdensities. They may arise from:

- DESI’s angular footprint;
- target-selection boundaries;
- fibre-assignment and observational completeness;
- redshift-dependent tracer selection;
- the chosen slice thickness;
- the projection of a three-dimensional survey into a two-dimensional plane.

A scientifically defensible density or void analysis must model the selection function using random catalogues and the survey mask.

---

## 8. Main conclusions

1. The local research bundle contains **6.09 million** DESI DR1 LSS rows across BGS, LRG, ELG, and QSO tracers.
2. The tracer populations occupy distinct redshift regimes, producing the nested radial appearance in the Cartesian slice.
3. The displayed bilateral geometry is dominated by survey footprint and selection effects, not automatically by real cosmic underdensity.
4. Cartesian coordinates and stored comoving distances are internally consistent to substantially better than 1 kpc.
5. The current analysis is suitable for a transparent, educational, browser-facing lightcone visualisation and for catalogue-quality checks.
6. The current products should not be labelled as a density reconstruction, void map, or clustering measurement.

---

## 9. Recommended next steps

### For the interactive NĀSADĪYA-LIGHTCONE website

- Add tracer toggles for BGS, LRG, ELG, and QSO.
- Display the active selection and redshift range clearly.
- Add a persistent note: “Observed survey geometry; not completeness-corrected.”
- Offer the Z-slice thickness as an interactive control.
- Add an optional radial-distance or redshift colour scale within each tracer.

### For research-grade large-scale structure analysis

1. Obtain the correct DESI random catalogues for each tracer.
2. Apply the relevant angular mask and completeness weights.
3. Use a documented estimator, such as Landy–Szalay, for correlation-function work.
4. Validate redshift cuts and tracer weights against DESI documentation.
5. Only then attempt density-field reconstruction, void finding, or clustering inference.

---

## 10. Output files

The notebook creates the following products:

```text
figures/desi_dr1_tracer_statistics.csv
figures/desi_dr1_tracer_composition.png
figures/desi_dr1_cartesian_slice.png
figures/desi_dr1_catalogue_diagnostics.json
```

---

## 11. Suggested figure captions

**Figure 1 — DESI DR1 LSS observed Cartesian slice.**  
Observed DESI DR1 LSS objects in a Cartesian slab centred at \(Z=0\) Mpc with a thickness of 300 Mpc. Exactly 100,000 rows were selected deterministically by stable object-ID hash for reproducibility. Colours identify tracer populations. The bilateral footprint and gaps reflect DESI angular coverage and tracer selection; this figure is not a density reconstruction.

**Figure 2 — DESI DR1 LSS tracer composition by redshift.**  
Fraction of observed catalogue rows in each redshift bin for the BGS, LRG, ELG, and QSO tracer samples. The plot represents the observed sample composition only and is not corrected for selection completeness, angular mask, or survey volume.
