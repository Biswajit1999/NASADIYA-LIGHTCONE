# NĀSADĪYA LIGHTCONE

> **A survey-native browser for navigating measured galaxy catalogues through redshift, distance, and cosmic time.**

Created and developed by **Biswajit Jana**.

[![Live Explorer](https://img.shields.io/badge/Live%20Explorer-GitHub%20Pages-1f6feb?logo=githubpages&logoColor=white)](https://biswajit1999.github.io/NASADIYA-LIGHTCONE/)
[![Release](https://img.shields.io/badge/release-v1.0.0-8be9fd.svg)](CHANGELOG.md)
[![2MRS](https://img.shields.io/badge/2MRS-43%2C533%20observed%20rows-66d9ef.svg)](docs/sources.md)
[![DESI DR1 LSS](https://img.shields.io/badge/DESI%20DR1%20LSS-6%2C093%2C818%20observed%20rows-f0b96f.svg)](docs/sources.md)
[![Browser LOD](https://img.shields.io/badge/public%20DESI%20overview-125%2C000%20real%20rows-a78bfa.svg)](data/processed/desi-dr1/overview.json)
[![CI](https://github.com/Biswajit1999/NASADIYA-LIGHTCONE/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![Code: MIT](https://img.shields.io/badge/code-MIT-8be9fd.svg)](LICENSE)
[![Data policy](https://img.shields.io/badge/data-provenance--first-efb276.svg)](DATA_POLICY.md)

<p align="center">
  <a href="https://biswajit1999.github.io/NASADIYA-LIGHTCONE/"><strong>Launch the live explorer →</strong></a>
</p>

![NĀSADĪYA LIGHTCONE survey visualisation](assets/nasadiya-lightcone-banner.png)

NĀSADĪYA LIGHTCONE is not a synthetic cosmic-web animation. Each rendered point originates in a published survey product, preserves source provenance, and remains separate from any future derived density or reconstruction layer. The project currently connects a nearby 2MRS anchor to a deep DESI DR1 LSS browser layer.

## Live explorer

**Website:** [biswajit1999.github.io/NASADIYA-LIGHTCONE](https://biswajit1999.github.io/NASADIYA-LIGHTCONE/)

The live site provides a map-first WebGL explorer with local 2MRS slices, observer-centred radial views, a DESI deep-field layer, tracer controls, source inspection and public documentation pages.

## Current data inventory

| Layer | Measurement | Current status |
|---|---|---|
| **2MRS Table 3** | Nearby spectroscopic recession velocities | **43,533 observed rows** in the public local-Universe layer |
| **DESI DR1 LSS** | Spectroscopic BGS, LRG, ELG and QSO large-scale-structure catalogues | **6,093,818 accepted observed rows** in the local build; **4,205** local spatial tiles; **125,000 deterministic real rows** in the public browser overview |
| **2MPZ** | Photometric redshifts | Not ingested yet. The adapter remains available, but a verified, downloadable source table with per-object photo-z uncertainty is still required |
| **WISE × SuperCOSMOS** | Photometric redshifts | Not ingested yet. Requires the same validated source-table and uncertainty gate before a tile build |
| **Gaia DR3 / GCNS** | Stellar astrometry and parallax | Planned as a **separate Milky Way mode**. Gaia is never mixed into extragalactic galaxy counts; a metadata-only GCNS source probe is available |

> The public DESI overview is a browser level-of-detail layer, not a scientific subsample. It is selected deterministically from real source rows so the public build remains reproducible. Raw DESI FITS archives and the full high-resolution tile store remain outside ordinary Git history.

## Explorer 1.0

The public interface separates four visitor tasks:

- **Explorer** — live WebGL survey field, spatial views, tracer filters and point inspection.
- **Data** — catalogue inventory, local/public data boundary and survey status.
- **Methods** — coordinate placement, deterministic overview construction and uncertainty context.
- **Community** — contribution path and scientific guardrails.

- [About the project](about.html)
- [Public data ledger](data.html)
- [Methods note](methods.html)
- [Community guide](community.html)
- [Explorer v1 design note](docs/frontend-v1.md)
- [UI/UX and SEO audit](docs/ui-ux-seo-audit-v1.md)

## Scientific guardrails

- No generated galaxies, interpolated filaments or decorative density points are stored as observed catalogue objects.
- Survey footprint, masking, target selection and incompleteness are visualised as measurement limits. Empty regions do **not** establish low physical density.
- 2MRS local placement uses `z ≈ cz / c` and a Planck18 comoving-distance transform only for visual navigation; local peculiar velocities matter.
- DESI DR1 LSS is a deep spectroscopic footprint, not an all-sky reconstruction. Its separated North/South regions are expected survey geometry.
- Photometric-redshift layers must carry a published **per-object** uncertainty and cannot be presented as exact radial positions.
- Gaia is a stellar astrometry catalogue and remains separate from extragalactic source counts.
- Derived products must have a distinct identifier, method description and citation; they may not silently blend with observed-point layers.

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

The DESI builder downloads official DR1 LSS source FITS products, validates and converts rows, then creates a spatial tile store plus deterministic browser overview.

```cmd
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --dry-run
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --yes
.\.venv\Scripts\python.exe scripts\build_desi_dr1_tile_store.py
```

### Data boundary

```text
data/raw/desi-dr1/                 # official downloaded source FITS files — local only
data/processed/desi-dr1/tiles/     # full local spatial tile store — local only
data/processed/desi-dr1/index.json # compact public index — committed
data/processed/desi-dr1/overview.json # 125,000-row public browser overview — committed
```

## Community entry points

- [Getting started](docs/getting-started.md)
- [Data access and hosting model](docs/data-access.md)
- [Next survey build workflow](docs/next-survey-build.md)
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
├── scripts/                             # Download/build/probe commands for each layer
├── data/registry/                       # Layer registry and public contracts
├── data/raw/                            # Source downloads — ignored by Git
├── data/processed/2mrs/                 # Compact 2MRS browser product
├── data/processed/desi-dr1/             # Public index/overview; full tiles ignored
├── docs/                                # Scientific scope, quickstart, data access, UI/UX notes
├── report/                              # LaTeX technical project report and bibliography
├── tests/                               # Parser, cosmology, tile-store and UI contracts
└── .github/                             # CI, issue templates and pull-request template
```

## Checks

```cmd
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check pipeline scripts tests
npm run check:modules
```

## Citation and licence

Code is released under the [MIT License](LICENSE). Please cite the software using [CITATION.cff](CITATION.cff) **and** cite every survey catalogue used in a visualisation or analysis. Survey data retain their original licences, terms, acknowledgements and attribution requirements; they are not relicensed by this repository.
