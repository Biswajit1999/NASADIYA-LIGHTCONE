# High-density DESI rendering

## Two delivery modes

NĀSADĪYA LIGHTCONE deliberately separates an instant public overview from a
higher-density local or hosted tile mode.

| Mode | Data available to the browser | Intended use |
| --- | ---: | --- |
| Public GitHub Pages overview | 125,000 deterministic observed DESI rows | Fast first visit and global survey-footprint context |
| Adaptive high-density mode | Up to 1,000,000 camera-relevant observed DESI rows | Local analysis, demonstrations, or an explicitly configured object-store endpoint |

The 1,000,000-row ceiling is a rendering budget, not a new catalogue. Each row
must originate in the existing DESI DR1 tile store. The full catalogue remains
larger than the browser draw budget and is never represented as a
completeness-corrected density field.

## Why GitHub Pages remains at 125,000 rows

The static public deployment includes the overview JSON but not the full DESI
tile payload. GitHub Pages therefore provides immediate access to the surveyed
footprint without requiring an initial download of millions of rows. Moving the
Rendered rows slider above 125,000 in that deployment changes the requested
rendering budget but cannot add rows that are not delivered by an endpoint.

## Local high-density run

A local static server must expose the complete `data/processed/desi-dr1/` tile
store alongside `index.html`. Once the tile probe succeeds, the app requests
camera-relevant tiles and preserves a deterministic global overview for spatial
context. Tile loading is concurrency-limited and cached; the renderer avoids
large spread-operator calls that can cause JavaScript stack overflows at dense
point counts.

## Scientific boundary

High-density rendering improves local visual detail only. It does not correct
for DESI footprint, targeting, fibre assignment, redshift success, masks or any
other survey-selection effect. It must not be used to infer voids, a density
field, a correlation function, BAO, or cosmological parameters without the
appropriate tracer selection, masks, weights and random catalogues.
