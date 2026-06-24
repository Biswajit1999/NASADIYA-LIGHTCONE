import assert from 'node:assert/strict';

import { RENDERING_LIMITS, TILE_STREAMING } from '../src/config.js';

assert.equal(RENDERING_LIMITS.publicOverviewRows, 125_000);
assert.equal(RENDERING_LIMITS.highDensityRows, 1_000_000);

for (const layerId of ['desi-dr1', 'all-live']) {
  const config = TILE_STREAMING[layerId];
  assert.equal(config.maxLoadedRows, RENDERING_LIMITS.highDensityRows, `${layerId} must expose the one-million-row cap`);
  assert.ok(config.maxTiles >= 700, `${layerId} must allow enough camera-relevant tiles for high-density mode`);
  assert.ok(config.maxCachedTiles >= config.maxTiles, `${layerId} cache must cover the active tile budget`);
  assert.ok(config.loadConcurrency >= 1, `${layerId} must retain positive tile-load concurrency`);
}

console.log('High-density rendering configuration passed.');
