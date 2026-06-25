# DESI browser-representation validation - run 2026-06-25

## Scope

This run evaluates how browser-level display subsets represent the same observed DESI DR1 LSS parent catalogue. It is a visual-representation validation, not a clustering analysis, density reconstruction, or completeness-corrected scientific sample.

- Validated observed parent rows: **6,093,818**.
- Parent-row count matched the full GPU-cloud manifest: **6,093,818**.
- Budgets tested: **125K, 250K, 500K and 1M** displayed rows.
- Redshift range evaluated: **0.0 <= z <= 3.6**.
- Angular diagnostic: 24 x 12 equal-area RA x sin(Dec) cells.
- Spatial diagnostic: observer-centred Cartesian 250 Mpc voxels.

Three display policies were compared:

1. **GPU low-discrepancy index threshold** - the current WebGL policy, exactly reproduced from the Float32 `aSample` threshold.
2. **Object-ID lowest hash** - stable BLAKE2b-64 object-ID ranking.
3. **Tracer + sky + redshift hash** - proportional deterministic selection within tracer, equal-area sky-cell, and redshift strata.

## Main result

No tested policy dominates every diagnostic.

At **125K displayed rows** (2.0513% of the parent):

| Policy | Redshift JSD [bits] | Tracer TVD | Sky correlation | Sky NRMSE | Voxel correlation | Voxel NRMSE | Voxel recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| GPU low-discrepancy | 2.215e-5 | 6.210e-5 | 0.999945 | 0.007505 | **0.984242** | **0.162496** | **0.595644** |
| Object-ID lowest hash | 6.127e-5 | 1.949e-3 | 0.999407 | 0.024952 | 0.975444 | 0.204316 | 0.578522 |
| Tracer + sky + redshift hash | **1.514e-6** | 2.841e-4 | **0.999996** | **0.002130** | 0.978769 | 0.189532 | 0.581878 |

The stratified candidate reduced redshift Jensen-Shannon divergence by **14.6x** and angular-cell NRMSE by **3.52x** relative to the deployed GPU profile at 125K. However, the deployed GPU profile retained higher voxel correlation, lower voxel NRMSE, and higher voxel occupied-cell recall.

At **1M displayed rows**, the same trade-off persisted:

- GPU voxel correlation: **0.998632**; voxel recall: **0.900178**.
- Stratified redshift JSD: **2.042e-8 bits** versus **4.149e-6 bits** for the GPU profile.
- Stratified sky NRMSE: **2.194e-4** versus **1.272e-3** for the GPU profile.

The object-ID lowest-hash policy is dominated by the other two policies for this implementation and is not a candidate for the public default.

## Platform decision

The NĀSADĪYA browser will retain the **GPU low-discrepancy index threshold as the default spatial-exploration profile**. It has the strongest tested 3D voxel representation at every evaluated display budget and already preserves global tracer fractions closely.

This does **not** make the display subset an unbiased scientific sample. The public interface must describe it as a deterministic visual representation of observed rows.

The tracer + sky + redshift policy remains a candidate for a future optional **distribution-balanced profile**, but only after a follow-up policy includes a finer 3D spatial constraint and is re-evaluated against the same diagnostics. It must not replace the default solely because its one-dimensional redshift and angular-cell metrics are better.

## Reproducibility

- Input SHA-256: `aba7c9236e516459e914d079e4b38bf1e75823ef0707e90da066914a5bda942e`.
- Evidence manifest: `figures/publication_evidence/evidence_manifest.json` after results are committed.
- Generator: `scripts/build_desi_publication_figures.py`.
- Figures: `fig_01` through `fig_06` in `figures/publication_evidence/`.

## Limits of interpretation

No DESI random catalogue, angular mask correction, completeness weight, survey-selection model, correlation-function estimator, power-spectrum estimator, or density reconstruction is used in this validation. These results support claims about browser representation fidelity only.
