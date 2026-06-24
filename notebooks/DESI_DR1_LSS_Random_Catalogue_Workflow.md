# DESI DR1 LSS Random-Catalogue Upgrade Workflow

## Purpose

This workflow is the next stage after the descriptive DESI DR1 catalogue diagnostics. It prepares the project for **selection-aware** large-scale-structure analysis without falsely treating the observed survey footprint as a physical density field.

The current science bundle is useful for visualisation and internal coordinate checks. It is not, by itself, sufficient for clustering, overdensity, void, or filament claims.

---

## What a usable random catalogue must represent

A random catalogue is not simply a uniform cloud of points. For a valid comparison, it must reproduce the relevant observational selection of the corresponding DESI tracer sample, including as applicable:

- angular footprint and vetoed regions;
- radial/redshift selection;
- tracer identity;
- completeness and target-selection effects;
- documented weights;
- the same redshift cuts used for the science sample.

A random catalogue that is not tracer-matched or mask-consistent must not be used for quantitative pair-count inference.

---

## New repository tool

The repository now includes:

```text
scripts/desi_lss_random_preflight.py
```

It is a **validation gate**, not a clustering estimator. Given the science bundle and a supplied random catalogue, it:

1. identifies usable redshift, tracer, angular-coordinate, and weight columns;
2. records the detected schema and row counts;
3. checks whether the random file has the minimum fields needed for follow-up work;
4. compares normalised science and random redshift distributions;
5. writes a JSON audit file and a diagnostic plot;
6. labels the result `PRELIMINARY_ONLY` rather than implying a scientific measurement.

---

## Running the preflight check

Place a downloaded DESI random catalogue outside version control, for example:

```text
data/private/desi_randoms/<your_random_file>.parquet
```

Then run:

```bash
python scripts/desi_lss_random_preflight.py \
  --data data/research/desi_dr1_lss_research_bundle.parquet \
  --random data/private/desi_randoms/<your_random_file>.parquet \
  --output-dir figures/random_preflight
```

The tool supports Parquet and CSV inputs.

Expected outputs:

```text
figures/random_preflight/desi_random_preflight.json
figures/random_preflight/desi_random_redshift_comparison.png
```

---

## Pass/fail interpretation

### Minimum pass for further preparation

The random catalogue should provide:

- a usable redshift field;
- right ascension and declination, where angular-mask validation is required;
- tracer identity or a clear external guarantee that it belongs to one specific tracer selection;
- documented weights where relevant.

### Do not proceed to pair counts when

- the random file has no redshift information;
- the randoms are not demonstrably associated with the science tracer selection;
- the sky mask or completeness convention is unknown;
- the redshift distribution is visibly incompatible without a documented reason;
- a random file is being reused across tracers without verified compatibility.

---

## Planned analysis gates

### Gate A — catalogue and mask validation

- Confirm release/version compatibility.
- Record exact source locations, tracer definitions, redshift cuts, and weight columns.
- Compare science/random tracer counts and redshift distributions.
- Verify angular coverage with RA/Dec diagnostics.

### Gate B — weighted pair-count implementation

Only after Gate A passes, implement a documented weighted estimator, for example the Landy–Szalay form:

```text
xi(s) = [DD(s) - 2DR(s) + RR(s)] / RR(s)
```

where `DD`, `DR`, and `RR` are weighted data–data, data–random, and random–random pair counts in separation bin `s`.

### Gate C — validation and uncertainty

- Test estimator behaviour on controlled subsets.
- State all weights and masks explicitly.
- Estimate uncertainties with an appropriate resampling or mock-catalogue method.
- Compare against DESI release documentation before making physical claims.

### Gate D — research products

After successful validation, possible products include:

- redshift-binned two-point correlation functions;
- projected/angular correlation measurements;
- selection-corrected density visualisations;
- carefully validated void-candidate searches.

---

## Repository policy

Large DESI random catalogues should **not** be committed to GitHub. Keep them in ignored local storage or a suitable external data location. Commit only:

- scripts;
- notebook logic;
- configuration templates;
- lightweight metadata;
- derived figures or compact summaries where redistribution is appropriate.

---

## Current scientific status

The project is now ready to validate an externally supplied DESI random catalogue. No random catalogue has been incorporated into this repository yet, and no selection-corrected clustering or density result has been produced.
