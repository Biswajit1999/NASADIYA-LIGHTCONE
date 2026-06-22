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

## 2MPZ and WISE × SuperCOSMOS

Both are photometric-redshift catalogues. The ingestion client uses VizieR discovery rather than an assumed catalogue ID, then accepts a table only when it can resolve:

- a source identifier;
- right ascension and declination;
- photometric redshift;
- an explicit, positive per-row photo-z uncertainty.

A failure to locate these fields is a correct scientific stop condition. The pipeline does not insert a global literature scatter as a fake per-object error.

```cmd
.\.venv\Scripts\python.exe scripts\download_2mpz.py
.\.venv\Scripts\python.exe scripts\build_2mpz_tile_store.py

.\.venv\Scripts\python.exe scripts\download_wise_sc.py
.\.venv\Scripts\python.exe scripts\build_wise_sc_tile_store.py
```

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
