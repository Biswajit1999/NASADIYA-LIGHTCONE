# Adaptive DESI tile delivery

## Why the live explorer begins with 125,000 rows

The public GitHub Pages explorer starts from a deterministic **125,000-row** overview of the full **6,093,818-row** DESI DR1 LSS build. The overview gives a fast, reproducible first render and preserves the global North/South survey footprint. It is not a scientific subsample and it does not replace the full source store.

The complete local build is partitioned into **4,205** spatial tiles. Each tile contains real observed source rows and metadata bounds in right ascension, declination, comoving Cartesian position and redshift.

## What Explorer 1.1 does

When a tile directory is reachable, the browser now:

1. keeps the 125k overview as global context;
2. identifies tiles that intersect the current camera frustum and selected redshift range;
3. fetches a bounded camera-relevant subset of those tiles;
4. keeps a small least-recently-used tile cache; and
5. caps the combined overview plus detail layer at a browser-safe render budget.

No source rows are invented, interpolated or moved. A point loaded from a tile remains a real DESI record with its source identifier and tracer class.

## Local high-resolution mode

After a full local DESI build, serve the repository from its root:

```cmd
.\.venv\Scripts\python.exe -m http.server 8080
```

Open `http://localhost:8080`, switch to **DESI DR1 LSS**, then orbit or zoom. The app probes `data/processed/desi-dr1/tiles/` automatically. When available, the Data Lens states that adaptive tile delivery is active.

## Public high-resolution mode

GitHub Pages serves the committed overview, but not the full tiles. To make tiles available to public visitors, upload the contents of:

```text
data/processed/desi-dr1/tiles/
```

to a static object-store directory that preserves each `tiles/<tile-id>.json` path. Set `remoteBaseUrl` for `desi-dr1` in `src/config.js` to that directory URL ending in `/`.

Example shape only:

```js
remoteBaseUrl: 'https://your-static-data-domain.example/desi-dr1/'
```

The object-store CORS policy must permit `GET` and `HEAD` from:

```text
https://biswajit1999.github.io
```

Keep `index.json` and `overview.json` in the repository. The browser uses the committed manifest for provenance and tile bounds; it requests high-resolution JSON only when the tile endpoint is available.

## Performance boundary

Do not publish all DESI rows as one browser JSON document. The adaptive path is deliberately bounded by `maxTiles`, `maxCachedTiles` and `maxLoadedRows` in `src/config.js`. Increase these only after testing desktop and mobile memory behaviour.
