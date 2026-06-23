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

function stableStride(objects, limit) {
  if (objects.length <= limit) return objects;
  const stride = Math.ceil(objects.length / Math.max(1, limit));
  return objects.filter((_, index) => index % stride === 0).slice(0, limit);
}

/**
 * Streams only a camera-relevant subset of an observed tile store. It never invents
 * rows or merges records into a deduplicated master catalogue. When tiles are
 * unavailable (the normal GitHub Pages case), the deterministic browser overview
 * remains the active display layer.
 */
export class TileStreamer {
  constructor({ manifest, indexUrl, overviewObjects, remoteBaseUrl = null, maxTiles = 18, maxCachedTiles = 42, maxLoadedRows = 180_000 }) {
    this.manifest = manifest;
    this.indexUrl = indexUrl;
    this.overviewObjects = overviewObjects;
    this.remoteBaseUrl = remoteBaseUrl;
    this.maxTiles = maxTiles;
    this.maxCachedTiles = maxCachedTiles;
    this.maxLoadedRows = maxLoadedRows;
    this.cache = new Map();
    this.activeIds = new Set();
    this.lastSignature = '';
    this.delivery = null;
  }

  async probeDelivery() {
    this.delivery = await probeTileStoreDelivery(this.manifest, this.indexUrl, { remoteBaseUrl: this.remoteBaseUrl });
    return this.delivery;
  }

  selectEntries(camera, maxRedshift) {
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
    let estimatedRows = 0;
    for (const candidate of candidates) {
      const count = Math.max(1, Number(candidate.entry.count) || 1);
      if (selected.length >= this.maxTiles) break;
      if (selected.length && estimatedRows + count > this.maxLoadedRows) continue;
      selected.push(candidate.entry);
      estimatedRows += count;
    }
    return selected;
  }

  async update(camera, state) {
    if (!this.delivery?.available) return { changed: false, available: false, reason: this.delivery?.reason || 'Tile endpoint is unavailable.' };
    const entries = this.selectEntries(camera, state.maxRedshift);
    const signature = entries.map((entry) => entry.id).join('|');
    if (signature === this.lastSignature) {
      return { changed: false, available: true, ...this.status(entries) };
    }

    const failed = [];
    for (const entry of entries) {
      const cached = this.cache.get(entry.id);
      if (cached) {
        cached.lastUsed = performance.now();
        continue;
      }
      try {
        const objects = await loadTileRecords(entry, this.manifest, this.indexUrl, { remoteBaseUrl: this.remoteBaseUrl });
        this.cache.set(entry.id, { objects, lastUsed: performance.now() });
      } catch (error) {
        failed.push({ id: entry.id, error: error?.message || 'unknown tile error' });
      }
    }

    this.activeIds = new Set(entries.filter((entry) => this.cache.has(entry.id)).map((entry) => entry.id));
    this.lastSignature = signature;
    this.pruneCache();
    return { changed: true, available: true, failed, objects: this.composeObjects(), ...this.status(entries) };
  }

  composeObjects() {
    const streamed = [];
    for (const id of this.activeIds) streamed.push(...(this.cache.get(id)?.objects || []));
    const streamedIds = new Set(streamed.map((object) => object.object_id));

    // Keep a deterministic global overview fraction visible even when nearby high-
    // resolution tiles are loaded. The detailed set receives 78% of the budget;
    // the remaining 22% anchors the full survey footprint and any other live layer.
    const detailBudget = Math.max(1, Math.floor(this.maxLoadedRows * 0.78));
    const local = stableStride(streamed, detailBudget);
    const remaining = Math.max(0, this.maxLoadedRows - local.length);
    const overviewRemainder = this.overviewObjects.filter((object) => !streamedIds.has(object.object_id));
    return [...stableStride(overviewRemainder, remaining), ...local];
  }

  status(entries = []) {
    const streamedRows = [...this.activeIds].reduce((total, id) => total + (this.cache.get(id)?.objects.length || 0), 0);
    return {
      requestedTiles: entries.length,
      loadedTiles: this.activeIds.size,
      streamedRows,
      cachedTiles: this.cache.size,
      totalTiles: Number(this.manifest.tile_count || this.manifest.tiles?.length || 0),
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
