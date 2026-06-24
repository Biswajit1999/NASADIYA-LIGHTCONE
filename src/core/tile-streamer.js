import * as THREE from 'three';

import { LIGHTCONE_CONFIG } from '../config.js';
import { loadTileRecords, probeTileStoreDelivery } from './catalog-loader.js';

function boxForTile(entry) {
  const bounds = entry?.bounds;
  const fields = ['x_mpc', 'y_mpc', 'z_mpc'];
  if (!bounds || !fields.every((field) => Array.isArray(bounds[field]) && bounds[field].length === 2)) return null;
  const minimum = new THREE.Vector3(...fields.map((field) => Number(bounds[field][0]) * LIGHTCONE_CONFIG.displayScale));
  const maximum = new THREE.Vector3(...fields.map((field) => Number(bounds[field][1]) * LIGHTCONE_CONFIG.displayScale));
  if (![...minimum.toArray(), ...maximum.toArray()].every(Number.isFinite)) return null;
  return new THREE.Box3(minimum.min(maximum.clone()), minimum.max(maximum));
}

function tileRedshiftMin(entry) {
  const value = Number(entry?.bounds?.redshift?.[0]);
  return Number.isFinite(value) ? value : 0;
}

function selectStableStride(objects, limit) {
  if (limit <= 0 || !objects.length) return [];
  if (objects.length <= limit) return objects.slice();
  const selected = new Array(limit);
  for (let index = 0; index < limit; index += 1) {
    selected[index] = objects[Math.floor((index * objects.length) / limit)];
  }
  return selected;
}

function appendObjects(target, source) {
  for (let index = 0; index < source.length; index += 1) target.push(source[index]);
}

/**
 * Streams camera-relevant observed tiles while retaining a deterministic global
 * overview. It never invents rows or creates a cross-survey master catalogue.
 *
 * The public GitHub Pages deployment normally falls back to the committed 125k
 * overview. A local tile build or configured object-store endpoint can request
 * up to the configured high-density rendering ceiling.
 */
export class TileStreamer {
  constructor({
    manifest,
    indexUrl,
    overviewObjects,
    remoteBaseUrl = null,
    maxTiles = 18,
    maxCachedTiles = 42,
    maxLoadedRows = 180_000,
    loadConcurrency = 6,
    overviewReserveRows = 25_000,
    overviewReserveFraction = 0.15,
    minOverviewRows = 10_000,
  }) {
    this.manifest = manifest;
    this.indexUrl = indexUrl;
    this.overviewObjects = overviewObjects;
    this.remoteBaseUrl = remoteBaseUrl;
    this.maxTiles = maxTiles;
    this.maxCachedTiles = maxCachedTiles;
    this.maxLoadedRows = maxLoadedRows;
    this.loadConcurrency = Math.max(1, loadConcurrency);
    this.overviewReserveRows = overviewReserveRows;
    this.overviewReserveFraction = overviewReserveFraction;
    this.minOverviewRows = minOverviewRows;
    this.cache = new Map();
    this.activeIds = new Set();
    this.lastSignature = '';
    this.delivery = null;
    this.activeRowLimit = Math.min(maxLoadedRows, overviewObjects.length);
  }

  async probeDelivery() {
    this.delivery = await probeTileStoreDelivery(this.manifest, this.indexUrl, { remoteBaseUrl: this.remoteBaseUrl });
    return this.delivery;
  }

  targetRowsFor(state) {
    const requested = Math.max(1, Math.floor(Number(state?.pointBudget) || 1));
    return Math.min(this.maxLoadedRows, requested);
  }

  overviewBudgetFor(targetRows) {
    const proportional = Math.round(targetRows * this.overviewReserveFraction);
    const desired = Math.max(this.minOverviewRows, proportional);
    return Math.min(this.overviewObjects.length, targetRows, this.overviewReserveRows, desired);
  }

  selectEntries(camera, maxRedshift, targetRows) {
    camera.updateMatrixWorld();
    const projection = new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    const frustum = new THREE.Frustum().setFromProjectionMatrix(projection);
    const candidates = [];

    for (const entry of this.manifest.tiles || []) {
      if (tileRedshiftMin(entry) > Number(maxRedshift)) continue;
      const box = boxForTile(entry);
      if (!box || !frustum.intersectsBox(box)) continue;
      const centre = box.getCenter(new THREE.Vector3());
      candidates.push({ entry, distance: centre.distanceTo(camera.position) });
    }

    candidates.sort((left, right) => left.distance - right.distance || tileRedshiftMin(left.entry) - tileRedshiftMin(right.entry));
    const selected = [];
    const detailBudget = Math.max(0, targetRows - this.overviewBudgetFor(targetRows));
    let estimatedRows = 0;
    for (const candidate of candidates) {
      if (selected.length >= this.maxTiles) break;
      if (selected.length && estimatedRows >= detailBudget) break;
      selected.push(candidate.entry);
      estimatedRows += Math.max(1, Number(candidate.entry.count) || 1);
    }
    return { entries: selected, detailBudget, estimatedRows };
  }

  async loadEntries(entries) {
    const pending = entries.filter((entry) => !this.cache.has(entry.id));
    const failed = [];
    let nextIndex = 0;
    const workerCount = Math.min(this.loadConcurrency, pending.length);

    const worker = async () => {
      while (nextIndex < pending.length) {
        const entry = pending[nextIndex];
        nextIndex += 1;
        try {
          const objects = await loadTileRecords(entry, this.manifest, this.indexUrl, { remoteBaseUrl: this.remoteBaseUrl });
          this.cache.set(entry.id, { objects, lastUsed: performance.now() });
        } catch (error) {
          failed.push({ id: entry.id, error: error?.message || 'unknown tile error' });
        }
      }
    };

    await Promise.all(Array.from({ length: workerCount }, () => worker()));
    return failed;
  }

  async update(camera, state) {
    if (!this.delivery?.available) return { changed: false, available: false, reason: this.delivery?.reason || 'Tile endpoint is unavailable.' };
    const targetRows = this.targetRowsFor(state);
    const selection = this.selectEntries(camera, state.maxRedshift, targetRows);
    const signature = `${targetRows}|${selection.entries.map((entry) => entry.id).join('|')}`;
    if (signature === this.lastSignature) {
      return { changed: false, available: true, targetRows, ...this.status(selection.entries) };
    }

    const failed = await this.loadEntries(selection.entries);
    this.activeIds = new Set(selection.entries.filter((entry) => this.cache.has(entry.id)).map((entry) => entry.id));
    this.activeRowLimit = targetRows;
    this.lastSignature = signature;
    this.pruneCache();
    const objects = this.composeObjects();
    return {
      changed: true,
      available: true,
      failed,
      objects,
      targetRows,
      renderedRows: objects.length,
      estimatedDetailRows: selection.estimatedRows,
      ...this.status(selection.entries),
    };
  }

  composeObjects() {
    const streamed = [];
    for (const id of this.activeIds) appendObjects(streamed, this.cache.get(id)?.objects || []);
    const streamedIds = new Set();
    for (const object of streamed) streamedIds.add(object.object_id);

    const localAnchor = [];
    const overviewRemainder = [];
    for (const object of this.overviewObjects) {
      if (streamedIds.has(object.object_id)) continue;
      if (object.source_layer === '2mrs') localAnchor.push(object);
      else overviewRemainder.push(object);
    }

    const combined = [];
    appendObjects(combined, selectStableStride(localAnchor, Math.min(this.activeRowLimit, localAnchor.length)));

    const overviewBudget = Math.max(0, this.overviewBudgetFor(this.activeRowLimit) - combined.length);
    const selectedOverview = selectStableStride(overviewRemainder, overviewBudget);
    appendObjects(combined, selectedOverview);

    const detailBudget = Math.max(0, this.activeRowLimit - combined.length);
    appendObjects(combined, selectStableStride(streamed, detailBudget));

    if (combined.length < this.activeRowLimit) {
      const selectedOverviewIds = new Set();
      for (const object of selectedOverview) selectedOverviewIds.add(object.object_id);
      const supplementalOverview = overviewRemainder.filter((object) => !selectedOverviewIds.has(object.object_id));
      appendObjects(combined, selectStableStride(supplementalOverview, this.activeRowLimit - combined.length));
    }
    return combined;
  }

  status(entries = []) {
    let streamedRows = 0;
    for (const id of this.activeIds) streamedRows += this.cache.get(id)?.objects.length || 0;
    return {
      requestedTiles: entries.length,
      loadedTiles: this.activeIds.size,
      streamedRows,
      cachedTiles: this.cache.size,
      totalTiles: Number(this.manifest.tile_count || this.manifest.tiles?.length || 0),
      highDensityCap: this.maxLoadedRows,
    };
  }

  pruneCache() {
    while (this.cache.size > this.maxCachedTiles) {
      const removable = [...this.cache.entries()]
        .filter(([id]) => !this.activeIds.has(id))
        .sort((left, right) => left[1].lastUsed - right[1].lastUsed)[0];
      if (!removable) return;
      this.cache.delete(removable[0]);
    }
  }
}
