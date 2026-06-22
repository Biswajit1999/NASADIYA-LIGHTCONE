# NĀSADĪYA LIGHTCONE

> **A survey-native browser for exploring measured galaxy structure through distance, redshift, and cosmic time.**

NĀSADĪYA LIGHTCONE begins with the real 2MASS Redshift Survey (2MRS) Table 3 catalogue. It is designed as a visual research interface: every rendered galaxy comes from a source row with retained measurement context and provenance.

[![CI](https://github.com/Biswajit1999/NASADIYA-LIGHTCONE/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![GitHub Pages](https://github.com/Biswajit1999/NASADIYA-LIGHTCONE/actions/workflows/pages.yml/badge.svg)](../../actions/workflows/pages.yml)
[![Code: MIT](https://img.shields.io/badge/code-MIT-8be9fd.svg)](LICENSE)

## Current release — 2MRS local Universe

The first data layer is generated from the published 2MRS Table 3 source catalogue through VizieR. It contains sky coordinates, spectroscopic recession velocities, velocity uncertainties, morphology where available, and extinction-corrected `K_s` magnitudes.

This repository does **not** ship an invented galaxy field. The browser data layer is built from observed source rows and is validated to reject synthetic records.

### Two ways to read the same observed catalogue

- **Local slice** — the default view. It selects real 2MRS entries inside a finite Cartesian Z-slab, making nearby galaxy structure readable without added filaments, inferred voids, or simulated points.
- **Observer lightcone** — an observer-centred radial view of the active 2MRS selection, with distance increasing outward.

The data lens exposes the active redshift ceiling, slice thickness, Cartesian slice offset, display budget, and colour treatment. Clicking a point reveals the source identifier, coordinates, recession velocity, redshift estimate, uncertainty, magnitude, and provenance.

## Scientific conventions

- **Coordinates:** ICRS/J2000 sky positions transformed to observer-centred Cartesian coordinates.
- **Redshift navigation:** `z ≈ cz / c`, where `cz` is the source-table recession velocity.
- **Distance display:** `astropy.cosmology.Planck18.comoving_distance(z)` for visual placement.
- **Nearby-Universe caution:** individual positions are not flow-corrected distance estimates; peculiar velocities matter at local distances.
- **Survey geometry:** 2MRS is magnitude-limited and has a Galactic Zone of Avoidance. Sparse regions are not, by themselves, physical void detections.

Read [docs/scientific-scope.md](docs/scientific-scope.md) before using the visualisation for scientific interpretation.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe scripts\download_2mrs.py
.\.venv\Scripts\python.exe scripts\build_2mrs_lightcone.py
.\.venv\Scripts\python.exe scripts\verify_browser_catalog.py
.\.venv\Scripts\python.exe -m http.server 8080
```

Open `http://localhost:8080` in a modern browser. Do not double-click `index.html`; browser security prevents local module code from loading its catalogue JSON directly.

## Repository layout

```text
NASADIYA-LIGHTCONE/
├── index.html                         # Static WebGL entry point
├── src/                               # ES modules: scene, points, loader, interface
├── styles/                            # Editorial visual system
├── data/
│   ├── raw/                           # Survey download — not committed
│   ├── processed/2mrs/                # Browser-ready observed catalogue after build
│   └── schemas/                       # Canonical survey-row contract
├── pipeline/nasadiya_lightcone/       # Parsing, validation, cosmology, export
├── scripts/                           # 2MRS download/build/verification CLI tools
├── docs/                              # Scope, architecture, sources, roadmap
├── tests/                             # Parser and transformation tests
└── .github/workflows/                 # CI and Pages workflows
```

## Multi-survey scale-up

The public v0.4 interface ships with the 2MRS local spectroscopic layer. The repository now also includes a provenance-preserving tile-store builder for multi-million-row catalogues. It is designed for:

- **2MPZ** — a one-million-galaxy photometric-redshift layer with mandatory radial uncertainty;
- **DESI DR1** — deep spectroscopic galaxies and quasars, streamed from externally hosted spatial tiles;
- **Gaia** — a separate Galactic stellar context layer, never mixed into extragalactic galaxy statistics.

Large survey products are deliberately not committed to normal Git history. See [docs/multisurvey-ingestion.md](docs/multisurvey-ingestion.md) for the verified data-flow and source-specific safeguards.

## Roadmap

| Version | Layer | Purpose |
|---|---|---|
| `0.1` | 2MRS | Observed local spectroscopic galaxy catalogue |
| `0.2` | 2MPZ | Wide photometric layer with explicit radial uncertainty |
| `0.3` | DESI | Tile-streamed galaxies and quasars with survey-footprint metadata |
| `0.4` | Cross-survey registry | Duplicate handling, release provenance, and source comparison |
| `1.0` | Reproducible views | Shareable camera, filter, cosmology, and survey-release state |

## Data acknowledgement

The 2MRS source catalogue is Huchra et al. (2012), *The 2MASS Redshift Survey—Description and Data Release*, ApJS 199, 26, accessed through VizieR catalogue `J/ApJS/199/26/table3`.

See [docs/sources.md](docs/sources.md) for the source record and future survey plans.

## Checks

```powershell
pytest -q
ruff check pipeline scripts tests
npm run check:modules
```

## License

Code is released under the [MIT License](LICENSE). Survey catalogues retain their own terms, citation requirements, and acknowledgement conditions.
