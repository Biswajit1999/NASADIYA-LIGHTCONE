# DESI DR1 LSS Research Bundle v1.0.0

## Purpose

This release artifact is the portable research-resolution companion to the browser explorer. It packages the full locally built **DESI DR1 LSS** observed catalogue as compressed Parquet for Python and Google Colab analysis.

It is not part of ordinary Git history. The Parquet file should be attached to a GitHub Release together with its manifest and checksum, while the repository stores the code, documentation and small reproducible figure outputs.

## Validated bundle record

| Field | Value |
|---|---:|
| Input catalogue | DESI DR1 LSS clustering catalogues · iron · LSScats v1.2 |
| Input tiles | 4,205 |
| Observed rows | 6,093,818 |
| Bundle selection | Full observed catalogue; no sampling |
| Parquet size | 185.12 MiB |
| Parquet SHA-256 | `aba7c9236e516459e914d079e4b38bf1e75823ef0707e90da066914a5bda942e` |
| Tile-index SHA-256 | `d6db4cfbfe5fcf67a2a0aa38b688e5a9f9ab7c0f4ee5c50cff5d4184174a8e24` |
| Cosmological placement | Planck18 (Astropy) |

### Tracer counts

| Tracer | Observed rows |
|---|---:|
| BGS | 300,017 |
| LRG | 2,138,604 |
| ELG | 2,432,027 |
| QSO | 1,223,170 |
| **Total** | **6,093,818** |

## Attach to the GitHub Release

Use tag:

```text
desi-dr1-research-v1.0.0
```

Attach these files from the local repository:

```text
data/research/desi_dr1_lss_research_bundle.parquet
data/research/desi_dr1_lss_research_bundle.manifest.json
figures/desi_dr1_lss_3d_research_view.png
figures/desi_dr1_lss_redshift_summary.png
figures/desi_dr1_lss_sky_footprint.png
figures/desi_dr1_lss_research_summary.json
```

## Scientific boundary

- Every bundle row originates in the locally built DESI DR1 LSS observed tile store.
- The release contains no synthetic galaxies, interpolated points, reconstructed filaments, cross-match or completeness correction.
- The plotted 3D field is a deterministic rendering subset only; full-bundle statistics and sky/redshift summaries scan every released row.
- Survey footprint, targeting and completeness are measurement properties. Empty regions in a plot do not demonstrate physical underdensity.

## Reproduce figures

```cmd
.\.venv\Scripts\python.exe scripts\plot_desi_research_figure.py --input data\research\desi_dr1_lss_research_bundle.parquet --output-dir figures --render-rows 120000
```

The figure workflow uses exactly 120,000 global lowest object-ID-hash rows for its 3D rendering subset whenever the bundle contains at least that many valid observed rows.
