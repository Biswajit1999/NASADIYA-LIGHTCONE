# Full observed DESI GPU cloud

## Purpose

The public explorer begins with a 125,000-row deterministic DESI overview. The
adaptive tile path can add camera-relevant observed rows up to one million.
This optional full-cloud product is the third delivery tier: it stores **every
accepted row** in the local DESI DR1 research bundle as one packed GPU-friendly
float32 payload.

This is a rendering product, not a replacement catalogue. The full binary does
not carry object IDs, provenance strings, survey weights, masks, or random
catalogues. Use the existing tile store and research Parquet bundle for
row-level inspection and analysis.

## Build locally

From the repository root, after Python dependencies are installed:

```bat
python scripts\full_gpu.py --input data\research\desi_dr1_lss_research_bundle.parquet --output-dir data\processed\desi-dr1\full-cloud --overwrite
```

The command writes:

```text
 data/processed/desi-dr1/full-cloud/full-cloud.json
 data/processed/desi-dr1/full-cloud/desi-dr1-full-cloud.f32
```

The manifest validates the record count, fixed five-float layout, byte length,
tracer codes, and binary checksum. The packed record layout is:

```text
x_mpc | y_mpc | z_mpc | redshift | tracer_code
```

The resulting binary is roughly 20 bytes per accepted source row: about 116 MiB
for 6.09 million rows before HTTP transfer overhead. It must be excluded from
Git history and delivered from the local static server or object storage.

## Browser behaviour

When `full-cloud.json` and its binary are reachable, the DESI Data Lens enables
**Full DESI 6M+**. This mode maps the interleaved buffer directly to a WebGL
`BufferGeometry`; it does not build millions of JavaScript objects. Redshift and
DESI tracer filters run in the vertex shader. This means the source rows remain
unchanged while visibility changes.

Full-cloud mode deliberately disables point inspection. Switch back to adaptive
tiles or the 125K overview to inspect a row and its provenance.

## Scientific boundary

Rendering all observed rows improves visual completeness within the published
DESI catalogue. It does not correct for the survey footprint, targeting,
fibre-assignment effects, redshift success, masks, or other selection effects.
Sparse regions must not be interpreted as cosmological voids or a reconstructed
matter-density field.
