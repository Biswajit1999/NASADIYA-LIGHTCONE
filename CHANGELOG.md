# Changelog

## 1.3.0 — Research-resolution DESI workflow

- Added a capped Parquet builder for the locally built DESI DR1 LSS tile store.
- The builder first attempts a full observed catalogue bundle, then falls back to a deterministic object-ID-hash sample only when the requested size cap is exceeded.
- Added reproducible Python research figures, a Google Colab workflow and a provenance summary output.
- Added `data/research/` as a release-asset workspace outside ordinary Git history.
- Added the research-mode documentation and rebuilt the README around live and research workflows.
- Removed the obsolete image-generation prompt document.

## 1.2.0 — Available-survey comparison stack

- Added a provenance-preserving 2MRS + DESI DR1 comparison stack.
- Preserved source identity, tracer controls and a non-deduplicated count warning.
- Added source-colour treatment and disabled pending photo-z layers until real source files are validated.

## 1.1.0 — Adaptive DESI detail

- Kept the 125,000-row public DESI overview as the fast GitHub Pages baseline.
- Added bounded, camera-relevant DESI tile streaming for local tile builds or a future configured object-store endpoint.
- Added a strict GCNS metadata probe that rejects generic Gaia tables as evidence for a GCNS layer.

## 1.0.0 — Research Explorer

- Rebuilt the explorer shell around a map-first, product-style information hierarchy.
- Added a direct local-to-deep survey navigator and compact spatial-lens dock.
- Added public About, Data, Methods and Community pages for crawlable context and visitor orientation.
- Added canonical metadata, JSON-LD, robots.txt, sitemap.xml and a web manifest.
- Preserved the existing Three.js renderer, survey pipeline and no-synthetic-data rule.

## 0.9.1 — Banner and sharing metadata

- Added the project survey-visualisation banner to `assets/`.
- Added Open Graph and Twitter sharing metadata.
- Added the banner to the README.

## 0.9.0 — Explorer and community release

- Reframed the browser around a compact explorer-first visual composition, giving the measured point field more of the canvas.
- Tightened deep-lightcone camera framing and increased point-field legibility without inventing any objects or filament geometry.
- Added concise active-layer/source telemetry and a DESI survey-footprint indicator.
- Added public-facing getting-started, data-access, community and roadmap documentation.
- Added a technical LaTeX project report and bibliography.
- Added a feature-request issue template and pull-request checklist.
- Corrected public documentation to state that 2MPZ and WISE × SuperCOSMOS ingestion remains paused until validated official source endpoints are implemented.

## 0.8.0 — DESI Explorer

- Added DESI BGS, LRG, ELG and QSO filters parsed from retained source identifiers.
- Added tracer colour mode and tracer information in the source inspector.
- Added explicit North/South footprint caveats for the DESI LSS layer.
