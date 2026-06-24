# NĀSADĪYA LIGHTCONE: publication validation scope

## Objective

This repository will evaluate whether a reproducible browser-scale selection of
real DESI DR1 LSS rows retains declared observed-catalogue properties at a fixed
point budget. The study concerns data representation, provenance and rendering;
it is not a cosmological parameter-estimation analysis.

The DESI DR1 LSS research Parquet bundle is the primary parent catalogue. 2MRS
is a separate nearby-survey demonstrator and is never treated as a statistically
complete joint volume with DESI.

## Research question

At a fixed browser point budget, how do deterministic object-ID hash selection,
seeded random selection, and explicit stratified selections compare in preserving
the observed redshift, tracer, angular-footprint and three-dimensional occupancy
properties of the DESI parent catalogue?

## Representation policies

Every policy retains real rows from the declared parent catalogue only.

1. **Lowest object-ID hash:** use the numerically lowest BLAKE2b-64 hashes of
   canonical object IDs. This matches the chunked DESI overview builder.
2. **Seeded random baseline:** draw rows without replacement using a declared
   pseudorandom-generator seed.
3. **Tracer-stratified hash:** allocate the point budget proportionally by
   tracer class and apply lowest-hash selection inside each class.
4. **Spatial-redshift stratified hash:** allocate over tracer, sky cell and
   redshift-bin strata before applying lowest-hash selection inside each stratum.

The latter two policies are comparison methods. They become production browser
policies only if measured fidelity gains justify their extra complexity.

## Evidence required before manuscript drafting

### Provenance and reproducibility

- Record the parent file checksum, schema, row count and source release.
- Emit a machine-readable manifest for each selected representation.
- Re-run deterministic selections and obtain identical object-ID selections.
- Generate figures and metrics from version-controlled commands.

### Descriptive-fidelity evaluation

For each policy and point budget, measure:

- redshift-distribution differences;
- tracer-fraction differences;
- occupied sky-cell recall and occupancy residuals;
- Cartesian-voxel occupancy residuals;
- comparison against repeated seeded-random baselines.

The published metrics will include KS distance, normalized 1-D Wasserstein
distance, Jensen-Shannon divergence, occupancy correlation and normalized RMSE.
We will report effect sizes and bootstrap uncertainty rather than using one
null-hypothesis p-value as the pass/fail condition.

### Browser measurements

At declared hardware/browser configurations, record time to first rendered frame,
median FPS, first-percentile FPS and, when exposed by the browser, JavaScript
heap memory. These measurements are configuration-specific rather than universal
performance claims.

## Scientific boundary

A blank or sparse region in an observed survey can arise from footprint, masking,
targeting, fibre assignment, redshift success or other selection effects. The
browser does not reconstruct a matter density field. It must not be used to infer
voids, a two-point correlation function, a power spectrum, BAO, or cosmological
parameters without an appropriate homogeneous tracer sample, official random
catalogues, weights and mask treatment.

## Paper-ready decision

The project is paper-ready when deterministic artifacts can be regenerated,
all reported figures have source manifests, fidelity trade-offs are stated
honestly including any failures, and browser benchmarking defines the usable
operating range.
