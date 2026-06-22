# Architecture

```text
VizieR 2MRS Table 3
        │
        ▼
scripts/download_2mrs.py       raw TSV + source manifest
        │
        ▼
scripts/build_2mrs_lightcone.py
        │  validates source fields, derives z≈cz/c, applies Planck18,
        │  exports observer-centred Cartesian coordinates
        ▼
data/processed/2mrs/2mrs_lightcone.json
        │
        ▼
Static WebGL browser layer (ES modules + Three.js)
```

The v0.1 browser loads one compact real catalogue. DESI-scale data must use a manifest and spatial tiles served outside ordinary Git history. The next data contract adds a tile identifier, footprint metadata, selection function reference, and release checksum.
