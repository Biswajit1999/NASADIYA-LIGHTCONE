# Data access and hosting model

NĀSADĪYA LIGHTCONE uses a two-level distribution model.

## Public repository and Pages payload

The GitHub repository may contain code, documentation, validation fixtures, compact source manifests, and small deterministic browser overviews. The current DESI public overview is intentionally compact enough for a static deployment.

## Local or external large-data payload

Raw archive files and high-resolution tile stores remain outside ordinary Git history. They are reproducible from documented source products and local scripts. For a future public high-resolution service, the intended pattern is:

```text
survey archive -> validated local build -> manifest + spatial tiles -> object storage/CDN -> camera-aware browser requests
```

This avoids treating Git commits as a bulk-data distribution service while preserving a reproducible code path and provenance manifest.

## Why a browser overview is not a scientific sample

The overview exists for interactive rendering at normal web budgets. It is selected deterministically from observed rows and is clearly labelled as a display level of detail. Statistical analysis should use the original survey products or a documented, purpose-built analysis selection - never the browser overview alone.

## Rules for external hosting

Before a tile store is hosted publicly, document:

1. source survey release and redistribution terms;
2. preprocessing version and checksum;
3. selection/quality filters;
4. coordinate and cosmology transform;
5. tile scheme and browser decimation method;
6. how footprint and uncertainty are exposed to users;
7. citation and acknowledgement requirements.
