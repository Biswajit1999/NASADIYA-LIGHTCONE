# Future survey architecture

NĀSADĪYA prepares adapters before it claims that a survey is available. The browser mission queue reads `data/registry/surveys.json`; it does not generate placeholder objects or imply that planned catalogues are installed.

## Readiness states

- **Deployed** means a cited source, validated schema, provenance manifest and browser product exist.
- **Source gate** means the adapter exists but a required source field or uncertainty product has not passed validation.
- **Planned** means the registry defines the scientific contract only. No points are rendered.

## Mission boundaries

- Future DESI releases receive immutable release-specific identifiers and never silently replace DR1.
- Rubin/LSST detections require a cited distance or photo-z product with per-object uncertainty before radial placement.
- Euclid spectroscopic and photometric products remain distinguishable.
- Roman adapters are release-specific and do not infer absent distances.
- SPHEREx redshift estimates retain uncertainty and are not styled as exact spectroscopic positions.
- Gaia remains a separate Galactic astrometry mode and is not mixed into extragalactic counts.

## Adapter gate

Every new layer must provide a stable object identifier, sky coordinates, measurement type, release provenance and the fields required by its declared radial-distance method. Photometric and spectrophotometric products must include per-object uncertainty. Large releases use manifests, deterministic overview samples and adaptive tile delivery; they are never downloaded in full on initial page load.
