# Validation protocol for browser-scale DESI representations

This protocol turns NĀSADĪYA LIGHTCONE from a visual demonstrator into a testable
research-software case study. Every result must state the parent bundle manifest,
point budget, selection policy, software revision and output checksum.

## Inputs

- **Parent catalogue:** the full locally built DESI DR1 LSS research Parquet bundle.
- **Observed attributes:** canonical object ID, RA, Dec, redshift, tracer, comoving
  Cartesian coordinates and any declared source metadata.
- **Browser budget:** initially 125,000 points; later report a scaling sequence
  from 10,000 to 1,000,000 points where hardware permits.

## Selection experiments

For each budget, generate these samples:

| Label | Selection | Purpose |
| --- | --- | --- |
| `lowest_hash` | Global BLAKE2b-64 lowest object-ID hashes | Validate the current deterministic overview contract. |
| `seeded_random` | Fixed-seed random draw without replacement | Establish expected sampling variability. |
| `tracer_hash` | Proportional tracer strata + lowest hash | Test retention of rare tracer classes. |
| `spatial_redshift_hash` | Tracer × sky cell × redshift-bin strata + lowest hash | Test coverage of sparse observed regions. |

The spatial-redshift grid is a representation grid. It is not an angular survey
mask and must not be described as a completeness correction.

## Metrics

### One-dimensional distributions

For redshift and other declared scalar properties, report:

\[
D_{KS} = \sup_x |F_P(x) - F_S(x)|,
\]

normalized 1-D Wasserstein distance,

\[
\widetilde{W}_1 = \frac{W_1(P,S)}{Q_{0.95}(P)-Q_{0.05}(P)},
\]

and Jensen-Shannon divergence between explicitly declared histograms. Histogram
edges must be shared across all methods in a comparison.

### Footprint and occupancy

Partition the observed sky into a declared equal-area cell grid and 3-D space into
a declared Cartesian voxel grid. For parent occupancy \(n_i\) and sample occupancy
\(s_i\), calculate:

\[
\mathrm{NRMSE} = \frac{\sqrt{\langle (s_i/f-n_i)^2 \rangle}}{\sqrt{\langle n_i^2 \rangle}},
\]

where \(f=|S|/|P|\), alongside Pearson occupancy correlation and occupied-cell
recall. Empty parent cells are excluded from recall denominators but retained in
residual calculations when the grid definition requires them.

### Baseline calibration

Generate repeated seeded-random samples. Each deterministic policy is interpreted
relative to the random-sample distribution of the same metric, rather than against
a universal numerical threshold.

## Reproducibility checks

1. Rerun a deterministic policy from the same parent bundle and compare ordered
   selected object IDs and manifest checksum.
2. Shuffle the parent row order and confirm the selected object-ID set is unchanged.
3. Confirm all selected object IDs belong to the parent bundle.
4. Regenerate figures from the same metrics JSON and compare output checksum where
   plotting libraries and environments are identical.

## Planned paper figures

1. Parent catalogue and browser representation: observed Cartesian projections.
2. Parent and sample sky occupancy maps.
3. Parent and sample redshift distributions.
4. Sampling-method metric comparison against random baselines.
5. Tracer retention by policy.
6. Sky-cell and 3-D voxel occupancy fidelity.
7. Deterministic selection reproducibility checks.
8. Browser performance versus point budget.

## Explicit exclusions

This protocol does not estimate a correlation function, power spectrum, density
field or void catalogue. Those require a separate DESI analysis design with the
appropriate random catalogues, weights, masks and homogeneous tracer selection.
