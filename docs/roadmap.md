# Roadmap

## v0.7 — Multi-survey local ingestion foundation

- Replace the brittle guessed 2MPZ VizieR identifier with official-archive discovery plus VizieR metadata fallback.
- Require a source-native per-row photo-z uncertainty before 2MPZ or WISE × SuperCOSMOS can be tiled.
- Add chunked builders for 2MPZ and WISE × SuperCOSMOS.
- Add explicit official-file acquisition and chunked tile generation for selected DESI DR1 LSS tracers.
- Add a bounded, separate Gaia DR3 local-star sample workflow.
- Keep raw catalogues and multi-million-row tiles outside ordinary Git history.

## v0.8 — Tile streaming and uncertainty-aware rendering

- Load only camera-relevant spatial tiles after the overview.
- Render photometric radial uncertainty as a separate visual channel instead of a fixed point size alone.
- Add layer-specific selection-mask and footprint overlays.

## v0.9 — Cross-survey provenance

- Add release-aware source comparison and duplicate handling.
- Keep survey records distinct rather than silently merging measurements.
- Add downloadable local manifests for each visual state.

## v1.0 — Galactic context and reproducible views

- Add Gaia as a separate Galactic stellar mode.
- Add shareable camera/filter/layer state.
- Publish versioned manifests for externally hosted high-volume data products.
