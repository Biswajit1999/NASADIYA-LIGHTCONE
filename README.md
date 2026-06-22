# NĀSADĪYA LIGHTCONE

> **A survey-native browser for exploring measured galaxy structure through distance, redshift, and cosmic time.**

Created and developed by **Biswajit Jana**.

NĀSADĪYA LIGHTCONE starts with the real 2MASS Redshift Survey (2MRS) and now has tested local ingestion paths for **2MPZ**, **WISE × SuperCOSMOS**, **DESI DR1 LSS**, and a separate bounded **Gaia DR3 local-star sample**. It does not generate galaxies, reconstruct decorative filaments, or mix Galactic stars into extragalactic counts.

[![CI](https://github.com/Biswajit1999/NASADIYA-LIGHTCONE/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![Code: MIT](https://img.shields.io/badge/code-MIT-8be9fd.svg)](LICENSE)

## Data layers

| Layer | Measurement | Build status |
|---|---|---|
| **2MRS** | Spectroscopic recession velocities | Browser-ready baseline: 43,533 accepted observed rows |
| **2MPZ** | Photometric redshifts with explicit per-row uncertainty | Discovery download + chunked tile-store builder |
| **WISE × SuperCOSMOS** | Photometric redshifts with explicit per-row uncertainty | Discovery download + chunked tile-store builder |
| **DESI DR1 LSS** | Spectroscopic BGS, LRG, ELG and QSO clustering catalogues | Official-file downloader + chunked tile-store builder |
| **Gaia DR3** | Astrometric local-star sample | Separate bounded Galactic product; not an extragalactic layer |

## Scientific guardrails

- Every browser point must derive from an observed source row with source metadata.
- Photometric layers are rejected unless their selected source table contains an explicit redshift-uncertainty field.
- Photo-z catalogues are observer-lightcone layers, not exact Cartesian 3D maps.
- Gaia remains separate from galaxy statistics and the extragalactic lightcone.
- Raw survey downloads and multi-million-row tile stores are excluded from Git history.
- A wide overview is clearly labelled as a deterministic real-row level of detail, **not** a scientific subsample.

Read [docs/scientific-scope.md](docs/scientific-scope.md) before using the visualisation for scientific interpretation.

## Run the baseline 2MRS layer locally

```cmd
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\verify_browser_catalog.py
.\.venv\Scripts\python.exe -m http.server 8080
```

Open `http://localhost:8080/?v=070`. Do not double-click `index.html`; the browser blocks module fetches from `file://` paths.

## Build additional real survey layers

Print the local plan first:

```cmd
.\.venv\Scripts\python.exe scripts\survey_manager.py
```

### 2MPZ

```cmd
.\.venv\Scripts\python.exe scripts\download_2mpz.py
.\.venv\Scripts\python.exe scripts\build_2mpz_tile_store.py
```

### WISE × SuperCOSMOS

```cmd
.\.venv\Scripts\python.exe scripts\download_wise_sc.py
.\.venv\Scripts\python.exe scripts\build_wise_sc_tile_store.py
```

The downloader uses VizieR discovery rather than a brittle guessed table key. It will only save a table after it verifies source identifier, coordinates, photo-z and **per-row** photo-z uncertainty columns. It stops cleanly rather than building a scientifically invalid layer.

### DESI DR1 LSS

```cmd
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --dry-run
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --yes
.\.venv\Scripts\python.exe scripts\build_desi_dr1_tile_store.py
```

The default selection contains official BGS, LRG, ELG and QSO LSS clustering products. Use `--components bgs,lrg` to begin with a smaller explicit tracer selection.

### Gaia DR3 local stellar context

```cmd
.\.venv\Scripts\python.exe scripts\download_gaia_dr3_local.py --yes
.\.venv\Scripts\python.exe scripts\build_gaia_dr3_local_sample.py
```

This is a bounded quality-cut stellar sample, not Gaia’s full catalogue and not a galaxy layer.

After each completed tile build, restart the local server and select the installed survey from **Data lens → Survey layer**.

## Repository layout

```text
NASADIYA-LIGHTCONE/
├── src/                                # Browser modules and WebGL view
├── pipeline/nasadiya_lightcone/         # Validation, cosmology, adapters, tile store
├── scripts/download_*.py                # Source-preserving public acquisition commands
├── scripts/build_*.py                   # Chunked local spatial tile builders
├── data/raw/                            # Raw source downloads — ignored by Git
├── data/processed/                      # Local derived tiles — ignored by Git except 2MRS baseline
├── docs/                                # Scope, architecture, source policy
└── tests/                               # Offline parser, cosmology and tile-store checks
```

## Checks

```cmd
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check pipeline scripts tests
npm run check:modules
```

## Licence and data acknowledgement

Code is released under the [MIT License](LICENSE). Survey catalogues retain their own licences, reuse terms, citations and acknowledgements. See [docs/sources.md](docs/sources.md).
