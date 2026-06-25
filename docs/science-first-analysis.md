# Science-first DESI DR1 analysis

## The question

The central question is not whether a browser or graphics processor can draw many points. It is:

> Which astronomical populations does the DESI DR1 LSS observed catalogue sample across cosmic time, and how can a survey-native lightcone make that selection visible without confusing it with a physical density field?

The analysis uses the observed DESI table to measure:

1. the redshift distribution of Bright Galaxy Sample (BGS), Luminous Red Galaxy (LRG), Emission Line Galaxy (ELG) and quasar (QSO) tracer classes;
2. the look-back-time and comoving-distance ranges sampled by those tracers under Planck18;
3. the change in observed tracer mixture with redshift;
4. the angular footprint in successive redshift slices;
5. observer-centred Cartesian redshift slices; and
6. consistency between stored Cartesian radii and the declared Planck18 redshift-distance conversion.

## Scientific application

DESI BAO and full-shape analyses combine different tracer populations across redshift to measure cosmic distances and the growth of structure. DESI DR1 BAO analyses use more than six million extragalactic objects over broad redshift coverage. A tracer-aware lightcone helps a user see where each population contributes in cosmic time and why target selection, footprint and redshift coverage must be separated from claims about physical underdensities. See DESI Collaboration 2024, *DESI 2024 VI*, arXiv:2404.03002.

The NĀSADĪYA application is therefore a **survey-native interpretation and visualisation tool**. It is useful for:

- teaching and communicating the redshift reach of each DESI tracer;
- inspecting how survey selection projects into observer-centred coordinates;
- preventing a viewer from confusing footprint gaps with cosmic voids;
- linking an interactive 3D view to explicit redshift, distance and look-back-time summaries; and
- providing reproducible descriptive figures that can accompany a software or astronomy-visualisation paper.

## What this analysis cannot claim

The supplied observed-row bundle alone cannot support a new BAO, redshift-space distortion, power-spectrum, correlation-function, void or cosmological-parameter result. Such work requires the official DESI LSS catalogues with the relevant weights, angular mask, random catalogues, covariance products and a validated estimator.

The workflow therefore does **not** calculate an observed number density per comoving volume, label a radial count feature as an overdensity, or present the visible lightcone as a reconstructed cosmic web.

## Run the analysis

```bat
cd /d C:\Users\biswa\Documents\GitHub\NASADIYA-LIGHTCONE
C:\Users\biswa\anaconda3\Scripts\conda.exe run -n nasadiya-evidence python scripts\analyze_desi_dr1_science.py ^
  --input data\research\desi_dr1_lss_research_bundle.parquet ^
  --output-dir figures\desi_dr1_science ^
  --dpi 300
```

The output directory contains six figure pairs (`.png` and `.pdf`), a tracer cosmic-epoch summary CSV, a machine-readable analysis manifest and a markdown science summary.
