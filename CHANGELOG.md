# Changelog

## 0.7.0 — Multi-survey ingestion foundation

- Replaced the failed hard-coded 2MPZ VizieR retrieval path with official-archive link discovery and VizieR metadata fallback.
- Added strict photo-z schema validation for 2MPZ and WISE × SuperCOSMOS.
- Added chunked tile-store builders that retain all accepted real source rows locally while limiting browser overview rows deterministically.
- Added DESI DR1 LSS acquisition/build commands for selected BGS, LRG, ELG and QSO official products.
- Added a bounded Gaia DR3 local-star acquisition/build path kept separate from extragalactic layers.
- Expanded Data Lens with 2MPZ, WISE × SuperCOSMOS and DESI DR1 layer choices.
- Preserved the 2MRS 43,533-row baseline and Biswajit Jana authorship line.

No raw catalogue, million-row tile store, or synthetic data is included in this source release.
