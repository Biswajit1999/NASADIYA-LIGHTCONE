# Roadmap

## Current milestone — DESI Explorer

The browser now supports a local 2MRS anchor and a public DESI DR1 overview, with BGS/LRG/ELG/QSO class filtering derived from the retained DESI source identifier.

## Next technical releases

1. **Camera-aware DESI tile streaming** — load nearby high-resolution spatial tiles only after the camera settles; keep the 125,000 real-row overview as the baseline view.
2. **Footprint and completeness visualisation** — make survey mask / North-South cap coverage inspectable without fabricating sky coverage.
3. **Validated 2MPZ re-ingestion** — only after a confirmed official source archive and documented photo-z uncertainty columns are implemented.
4. **Validated WISE × SuperCOSMOS re-ingestion** — same requirement: official source provenance plus usable photo-z uncertainty.
5. **Separate Gaia Galactic mode** — stellar astrometry remains distinct from extragalactic datasets.

## Data policy

Raw FITS catalogues and complete high-resolution tile stores are local or externally hosted products. The GitHub site contains reproducible code, metadata, provenance, and deliberately bounded real-record browser overviews.
