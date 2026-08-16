# Multi-survey ingestion and scale plan

NĀSADĪYA separates **source acquisition**, **validated spatial products**, and **browser rendering**. The browser must never load a multi-million-row catalogue as a single document, and the project must never add invented rows to make a view look fuller.

## Common contract

```text
Published source archive or public service
  → untouched local raw file + retrieval manifest
  → source-column validation and quality rules
  → Planck18 visual-navigation coordinates
  → spatial tiles + deterministic observed-row overview
  → browser lightcone with provenance on click
```

Every tile-store manifest records source release, field mapping, raw-file checksum, accepted row count, cosmology transform, partition scheme and overview selection. The overview uses deterministic lowest object hashes and is marked **not a scientific selection**.

## 2MPZ (deployed)

2MPZ is served by the Wide Field Astronomy Unit's SuperCOSMOS Science Archive (SSA) as a
SQL Server table (`TWOMPZ..twompzPhotoz`), not a static bulk file or a VizieR catalogue.
`scripts/download_2mpz.py` submits the documented SQL Cookbook query
(http://ssa.roe.ac.uk/sqlcookbook.html §6) through the SSA's freeform-SQL endpoint and
downloads the generated results file — 934,175 raw rows.

The `twompzPhotoz` table exposes no per-object photo-z uncertainty column, only the
published survey-wide accuracy figure (σz = 0.015; Bilicki et al. 2014). This is a
correct scientific constraint, not a missing feature: the pipeline never inserts that
global figure into a per-row `redshift_error` field. Instead, `SurveyDescriptor.
global_redshift_sigma` records the one real number once, at the manifest level, and the
browser reads it from there — `redshift_error` stays honestly absent on every row.

```cmd
.\.venv\Scripts\python.exe scripts\download_2mpz.py
.\.venv\Scripts\python.exe scripts\build_2mpz_tile_store.py
```

## WISE × SuperCOSMOS (pending)

A real bulk CSV exists (http://ssa.roe.ac.uk/cats/wiseScosPhotoz160708.csv.gz, confirmed
reachable) but, like 2MPZ, carries no per-object uncertainty column — only a published
survey-wide figure (σz/(1+z) = 0.033). Ingestion should reuse the same
`global_redshift_sigma` mechanism proven by 2MPZ, at roughly 20x the row count
(~18.5 million), so it is scoped as a separate build after 2MPZ's pipeline pattern is
validated in production.

Photo-z layers are observer-lightcone only. Sparse regions, masks and broad radial error are retained as survey properties.

## DESI DR1 LSS

The local DESI path downloads selected official DR1 LSS clustering products. Its default plan is BGS, LRG, ELG and QSO; the command requires `--yes` after printing a file plan and applies a user-set safety cap.

```cmd
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --dry-run
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --yes
.\.venv\Scripts\python.exe scripts\build_desi_dr1_tile_store.py
```

The resulting manifest retains each input filename and checksum. It does not claim to be a de-duplicated all-purpose DESI master catalogue; it is the explicit set of selected LSS tracers.

## Gaia DR3

Gaia is kept outside the extragalactic survey selector. The optional public-TAP query builds a bounded, quality-cut local star sample. Naive inverse-parallax coordinates are labelled as visual placement only, not a Bayesian distance-inference product.

```cmd
.\.venv\Scripts\python.exe scripts\download_gaia_dr3_local.py --yes
.\.venv\Scripts\python.exe scripts\build_gaia_dr3_local_sample.py
```

## Deployment policy

- Source archives: never committed.
- Large processed tiles: never committed to ordinary Git history.
- Code, schemas, tests, small manifests and 2MRS baseline browser data: committed.
- Public high-volume layers: deploy through versioned object storage or release assets with immutable manifests and CORS configured for the NĀSADĪYA origin.
- The public page must distinguish source count, loaded overview count and any aggregate representation.
