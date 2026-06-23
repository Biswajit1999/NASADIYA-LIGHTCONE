# NĀSADĪYA LIGHTCONE

> **A survey-native browser for navigating measured galaxy catalogues through redshift, distance, and cosmic time.**

Created and developed by **Biswajit Jana**.

![NĀSADĪYA LIGHTCONE survey visualisation](assets/nasadiya-lightcone-banner.png)

NĀSADĪYA LIGHTCONE is not a synthetic cosmic-web animation. Each rendered point originates in a published survey product, preserves source provenance, and remains separate from any future derived density or reconstruction layer. The project currently combines a nearby 2MRS anchor with a deep DESI DR1 LSS browser layer.

[![CI](https://github.com/Biswajit1999/NASADIYA-LIGHTCONE/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![Code: MIT](https://img.shields.io/badge/code-MIT-8be9fd.svg)](LICENSE)
[![Data policy](https://img.shields.io/badge/data-provenance--first-efb276.svg)](DATA_POLICY.md)

## Explorer 1.0

The public interface now separates four visitor tasks: **Explorer** for the live WebGL field, **Data** for catalogue status, **Methods** for placement and uncertainty, and **Community** for contribution. This crawlable document layer complements the browser canvas without changing the survey pipeline.

- [About the project](about.html)
- [Public data ledger](data.html)
- [Methods note](methods.html)
- [Community guide](community.html)
- [Explorer v1 design note](docs/frontend-v1.md)

## What is live now

| Layer | Measurement | Current browser status |
|---|---|---|
| **2MRS Table 3** | Nearby spectroscopic recession velocities | Public local-Universe layer with **43,533** accepted rows |
| **DESI DR1 LSS** | Deep spectroscopic BGS, LRG, ELG, and QSO clustering catalogues | Public deterministic overview with **125,000 real rows**; a local build retains **6,093,818 accepted rows** across **4,205 spatial tiles** |
| **2MPZ** | Photometric redshifts | Adapter contract retained; official-source retrieval is paused until a validated published endpoint is wired in |
| **WISE × SuperCOSMOS** | Photometric redshifts | Adapter contract retained; official-source retrieval is paused until a validated published endpoint is wired in |
| **Gaia DR3** | Stellar astrometry/parallax | Planned as a separate Milky Way mode; never merged into extragalactic galaxy counts |

The public DESI overview is a browser level of detail, not a scientific subsample. It uses a deterministic object-hash selection so the same public build is reproducible. Raw DESI FITS products and high-resolution tiles remain outside ordinary Git history.

## Scientific guardrails

- No generated galaxies, interpolated filaments, or decorative density points are stored as observed catalogue objects.
- Survey footprint, masking, target selection, and incompleteness are visualised as measurement limits. Empty regions do **not** establish low physical density.
- 2MRS local placement uses `z ≈ cz / c` and a Planck18 comoving-distance transform only for visual navigation; local peculiar velocities matter.
- DESI DR1 LSS is a deep spectroscopic footprint, not an all-sky reconstruction. Its separated North/South regions are expected survey geometry.
- Photometric-redshift layers must carry a published per-object uncertainty and cannot be presented as exact radial positions.
- Derived products must have a distinct identifier, method description, and citation; they may not silently blend with observed-point layers.

Read [docs/scientific-scope.md](docs/scientific-scope.md) before using the visualisation for scientific interpretation.

## Explore locally

```cmd
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe -m http.server 8080
```

Open `http://localhost:8080`. Do not double-click `index.html`: browser module security prevents it from loading local JSON products directly.

For a clean clone that does not yet contain generated data, first build the small 2MRS baseline:

```cmd
.\.venv\Scripts\python.exe scripts\download_2mrs.py
.\.venv\Scripts\python.exe scripts\build_2mrs_lightcone.py
.\.venv\Scripts\python.exe scripts\verify_browser_catalog.py
```

## Build the deep DESI layer locally

The following build uses the official DESI DR1 LSS clustering products selected by the project. It downloads source FITS files, validates and converts rows, then creates a spatial tile store and deterministic browser overview.

```cmd
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --dry-run
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --yes
.\.venv\Scripts\python.exe scripts\build_desi_dr1_tile_store.py
```

The generated products are deliberately excluded from normal Git commits:

```text
data/raw/desi-dr1/                 # official downloaded source FITS files
data/processed/desi-dr1/tiles/     # full local spatial tile store
data/processed/desi-dr1/index.json # compact public index
data/processed/desi-dr1/overview.json # compact public browser overview
```

## Community entry points

- [Getting started](docs/getting-started.md)
- [Data access and hosting model](docs/data-access.md)
- [Community guide](COMMUNITY.md)
- [Contribution guide](CONTRIBUTING.md)
- [Scientific scope](docs/scientific-scope.md)
- [Sources and survey acknowledgement](docs/sources.md)
- [Project report in LaTeX](report/NASADIYA_LIGHTCONE_Project_Report.tex)
- [Banner-art direction prompt](docs/banner-prompt.md)

## Repository layout

```text
NASADIYA-LIGHTCONE/
├── src/                                # Browser modules and WebGL view
├── pipeline/nasadiya_lightcone/         # Validation, cosmology, tile store
├── scripts/                             # Download/build commands for each layer
├── data/registry/                       # Layer registry and public contracts
├── data/raw/                            # Source downloads - ignored by Git
├── data/processed/2mrs/                 # Compact 2MRS browser product
├── data/processed/desi-dr1/             # Public index/overview; full tiles ignored
├── docs/                                # Scientific scope, quickstart, data access
├── report/                              # LaTeX technical project report and bibliography
├── tests/                               # Parser, cosmology, tile-store, UI contracts
└── .github/                             # CI, issue templates, pull request template
```

## Checks

```cmd
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check pipeline scripts tests
npm run check:modules
```

## Citation and licence

Code is released under the [MIT License](LICENSE). Please cite the software using [CITATION.cff](CITATION.cff) **and** cite every survey catalogue used in a visualisation or analysis. Survey data retain their original licences, terms, acknowledgements, and attribution requirements; they are not relicensed by this repository.
