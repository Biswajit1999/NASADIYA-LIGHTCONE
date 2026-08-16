# Next survey build: validated photo-z layers

NĀSADĪYA adds new data layers one survey at a time. **2MPZ is deployed** (933,447 real
rows). **WISE × SuperCOSMOS** is next, following the same provenance-first pattern at
roughly 20x the row count.

## Why this order

- **2MPZ** bridges the nearby 2MRS anchor and the deeper DESI footprint: an
  approximately one-million-galaxy, almost-all-sky photometric-redshift catalogue. Its
  real source table (`TWOMPZ..twompzPhotoz` on the SSA SQL server) has no per-object
  uncertainty column, only a published survey-wide accuracy figure (σz = 0.015), so it
  ships using the `SurveyDescriptor.global_redshift_sigma` path: positions stay exact,
  and the one real number drives the browser's existing "Uncertainty" display mode
  uniformly rather than being written into a fabricated per-row field.
- **WISE × SuperCOSMOS** is much larger (~18.5M rows) and has the identical gap — a real
  downloadable CSV exists but exposes no per-object uncertainty, only σz/(1+z) = 0.033.
  It should reuse the proven `global_redshift_sigma` mechanism rather than a new one.
- **Gaia DR3** remains a separate Milky Way mode, not an extragalactic lightcone layer.

## The `global_redshift_sigma` gate

A photometric layer must declare uncertainty one of two ways before
`canonicalise_survey_frame` will accept it:

1. a **per-object** `redshift_error_column` (e.g. a future release that publishes one), or
2. `SurveyDescriptor.global_redshift_sigma` — the source survey's own published
   survey-wide accuracy figure, applied uniformly, never written into a per-row field.

Providing neither raises a `ValueError`. Do not manufacture a per-object value from a
survey-wide number to satisfy the per-object path — that is exactly the case
`global_redshift_sigma` exists to handle honestly instead.

## Building 2MPZ locally

```cmd
.\.venv\Scripts\python.exe scripts\download_2mpz.py --probe
.\.venv\Scripts\python.exe scripts\download_2mpz.py
.\.venv\Scripts\python.exe scripts\build_2mpz_tile_store.py
```

The raw source file stays local (gitignored); the processed tile store (index, overview,
tiles) is committed, matching the DESI DR1 deployment pattern.

## Building WISE × SuperCOSMOS (not yet implemented)

A real bulk file is confirmed reachable at
`http://ssa.roe.ac.uk/cats/wiseScosPhotoz160708.csv.gz` (1.7 GB). Implementation should
mirror `download_2mpz.py`/`build_2mpz_tile_store.py`, using
`global_redshift_sigma_kind="proportional_to_one_plus_z"` since WISE × SuperCOSMOS's
published accuracy scales with `(1+z)` rather than being constant.

## No synthetic backfill

Do not add points to fill the Zone of Avoidance, DESI masks or any catalogue footprint. A dark region may be an observational limitation rather than a physical void.
