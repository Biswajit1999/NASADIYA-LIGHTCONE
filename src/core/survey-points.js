import * as THREE from 'three';

import { LIGHTCONE_CONFIG, PALETTE } from '../config.js';
import { pointFragmentShader, pointVertexShader } from '../shaders/point-shaders.js';
import { hslToRgb } from '../utils/math.js';

const TRACER_COLOURS = Object.freeze({
  BGS: [0.30, 0.86, 1.0],
  LRG: [1.0, 0.70, 0.41],
  ELG: [0.47, 0.93, 0.63],
  QSO: [0.73, 0.61, 1.0],
});

function clamp01(value) { return Math.min(1, Math.max(0, value)); }

function magnitudeOf(object) {
  const candidate = Number(object.magnitude ?? object.ks_mag);
  return Number.isFinite(candidate) ? candidate : null;
}

function timeColour(object, maxRedshift) {
  const fraction = clamp01(Number(object.redshift) / Math.max(maxRedshift, 0.001));
  return hslToRgb(0.59 - fraction * 0.45, 0.8, 0.62);
}

function observedColour(object, maxRedshift) {
  const z = clamp01(Number(object.redshift) / Math.max(maxRedshift, 0.001));
  const magnitude = magnitudeOf(object);
  const brightness = magnitude === null ? 0.2 : clamp01((14.0 - magnitude) / 10.0);
  return [
    THREE.MathUtils.lerp(PALETTE.cyan[0], 0.94, brightness * 0.22 + z * 0.08),
    THREE.MathUtils.lerp(PALETTE.cyan[1], 0.91, brightness * 0.12),
    THREE.MathUtils.lerp(PALETTE.cyan[2], 0.9, brightness * 0.16 + z * 0.08),
  ];
}

function tracerColour(object, maxRedshift) {
  const base = TRACER_COLOURS[object.tracer];
  if (!base) return observedColour(object, maxRedshift);
  const distanceFade = clamp01(Number(object.redshift) / Math.max(maxRedshift, 0.001));
  return base.map((component) => THREE.MathUtils.lerp(component, 0.96, distanceFade * 0.10));
}

function surveyColour(object, maxRedshift) {
  const source = `${object.source_layer || ''}|${object.source_survey || ''}`.toLowerCase();
  const base = source.includes('2mrs') ? PALETTE.cyan : source.includes('desi') ? PALETTE.amber : PALETTE.green;
  const distanceFade = clamp01(Number(object.redshift) / Math.max(maxRedshift, 0.001));
  return base.map((component) => THREE.MathUtils.lerp(component, 0.97, distanceFade * 0.10));
}

function sliceEdgeAlpha(distanceFromPlane, halfThickness) {
  if (halfThickness <= 0) return 0;
  const edgeStart = halfThickness * 0.7;
  if (distanceFromPlane <= edgeStart) return 1;
  return 1 - clamp01((distanceFromPlane - edgeStart) / Math.max(halfThickness - edgeStart, 0.001));
}

function isTracerEnabled(object, state) {
  return !object.tracer || state.tracerFilters?.[object.tracer] !== false;
}

function evenlySelect(indices, limit) {
  if (indices.length <= limit) return indices;
  const selected = new Array(limit);
  for (let index = 0; index < limit; index += 1) selected[index] = indices[Math.floor((index * indices.length) / limit)];
  return selected;
}

function visibleIndicesFor(candidates, objects, budget, isComposite) {
  if (!isComposite || candidates.length <= budget) return evenlySelect(candidates, budget);
  const localAnchor = [];
  const deep = [];
  for (const index of candidates) {
    if (objects[index]?.source_layer === '2mrs') localAnchor.push(index);
    else deep.push(index);
  }
  if (!localAnchor.length) return evenlySelect(candidates, budget);
  if (localAnchor.length >= budget) return evenlySelect(localAnchor, budget);
  return localAnchor.concat(evenlySelect(deep, budget - localAnchor.length));
}

export class SurveyPoints {
  constructor(objects, meta = {}) {
    this.objects = objects;
    this.meta = meta;
    this.visibleIndices = new Set();
    this.geometry = new THREE.BufferGeometry();
    const count = objects.length;
    this.rawPositions = new Float32Array(count * 3);
    const displayPositions = new Float32Array(count * 3);
    const colours = new Float32Array(count * 3);
    const alphas = new Float32Array(count);
    const sizes = new Float32Array(count);
    const uncertainties = new Float32Array(count);
    const twinkles = new Float32Array(count);

    this.maxDatasetDistance = 1;
    for (let index = 0; index < count; index += 1) {
      const object = objects[index];
      const offset = index * 3;
      this.rawPositions[offset] = Number(object.x_mpc);
      this.rawPositions[offset + 1] = Number(object.y_mpc);
      this.rawPositions[offset + 2] = Number(object.z_mpc);
      displayPositions[offset] = this.rawPositions[offset] * LIGHTCONE_CONFIG.displayScale;
      displayPositions[offset + 1] = this.rawPositions[offset + 1] * LIGHTCONE_CONFIG.displayScale;
      displayPositions[offset + 2] = this.rawPositions[offset + 2] * LIGHTCONE_CONFIG.displayScale;
      colours.set(PALETTE.cyan, offset);
      const magnitude = magnitudeOf(object);
      sizes[index] = magnitude === null ? 1.75 : THREE.MathUtils.clamp(4.8 - magnitude * 0.18, 1.45, 4.4);
      uncertainties[index] = Math.max(0, Number(object.redshift_error) || 0);
      twinkles[index] = ((index * 73) % 97) / 97;
      this.maxDatasetDistance = Math.max(this.maxDatasetDistance, Number(object.comoving_distance_mpc) || 0);
    }

    this.geometry.setAttribute('position', new THREE.BufferAttribute(displayPositions, 3));
    this.geometry.setAttribute('color', new THREE.BufferAttribute(colours, 3));
    this.geometry.setAttribute('aAlpha', new THREE.BufferAttribute(alphas, 1));
    this.geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
    this.geometry.setAttribute('aUncertainty', new THREE.BufferAttribute(uncertainties, 1));
    this.geometry.setAttribute('aTwinkle', new THREE.BufferAttribute(twinkles, 1));

    this.material = new THREE.ShaderMaterial({
      vertexShader: pointVertexShader,
      fragmentShader: pointFragmentShader,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: { uPointScale: { value: 1.0 }, uMode: { value: 0 }, uTime: { value: 0 } },
    });
    this.points = new THREE.Points(this.geometry, this.material);
    this.points.name = `observed-${meta.dataset_id || 'survey'}-points`;
    this.points.frustumCulled = false;
  }

  applyState(state) {
    const position = this.geometry.getAttribute('position');
    const alpha = this.geometry.getAttribute('aAlpha');
    const colour = this.geometry.getAttribute('color');
    const size = this.geometry.getAttribute('aSize');
    const candidates = [];
    const tracerCounts = {};
    const sourceCounts = {};
    let maxDistance = 0;
    let maxLookback = 0;
    const maxRedshift = Math.max(0.001, Number(state.maxRedshift));
    const halfThickness = Math.max(1, Number(state.sliceThickness) / 2);
    const sliceOffset = Number(state.sliceOffset);
    const isSlice = state.spatialMode === 'slice';

    for (let index = 0; index < this.objects.length; index += 1) {
      const object = this.objects[index];
      const offset = index * 3;
      const x = this.rawPositions[offset];
      const y = this.rawPositions[offset + 1];
      const z = this.rawPositions[offset + 2];
      const redshift = Number(object.redshift) || 0;
      const slabDistance = Math.abs(z - sliceOffset);
      const visibleCandidate = state.showGalaxies && isTracerEnabled(object, state) && redshift <= maxRedshift && (!isSlice || slabDistance <= halfThickness);
      if (visibleCandidate) {
        candidates.push(index);
        if (object.tracer) tracerCounts[object.tracer] = (tracerCounts[object.tracer] || 0) + 1;
        const source = object.source_layer || object.source_survey || 'active-survey';
        sourceCounts[source] = (sourceCounts[source] || 0) + 1;
        maxDistance = Math.max(maxDistance, Number(object.comoving_distance_mpc) || 0);
        maxLookback = Math.max(maxLookback, Number(object.lookback_time_gyr) || 0);
      }
      position.setXYZ(
        index,
        x * LIGHTCONE_CONFIG.displayScale,
        y * LIGHTCONE_CONFIG.displayScale,
        isSlice ? (z - sliceOffset) * LIGHTCONE_CONFIG.displayScale * 0.12 : z * LIGHTCONE_CONFIG.displayScale,
      );
    }

    const selected = visibleIndicesFor(candidates, this.objects, Math.max(1, state.pointBudget), Boolean(this.meta.composite));
    const visibleSet = new Set(selected);
    this.visibleIndices = visibleSet;

    for (let index = 0; index < this.objects.length; index += 1) {
      const object = this.objects[index];
      const offset = index * 3;
      const slabDistance = Math.abs(this.rawPositions[offset + 2] - sliceOffset);
      const magnitude = magnitudeOf(object);
      const brightness = magnitude === null ? 0.18 : clamp01((14.2 - magnitude) / 10.2);
      const radialWeight = clamp01((Number(object.comoving_distance_mpc) || 0) / this.maxDatasetDistance);
      const edgeFade = isSlice ? sliceEdgeAlpha(slabDistance, halfThickness) : 1;
      const baseAlpha = 0.13 + brightness * 0.56 + (1 - radialWeight) * 0.15;
      alpha.setX(index, visibleSet.has(index) ? THREE.MathUtils.clamp(baseAlpha * edgeFade, 0.06, 0.92) : 0);
      const rgb = state.viewMode === 'time'
        ? timeColour(object, maxRedshift)
        : state.viewMode === 'uncertainty'
          ? PALETTE.violet
          : state.viewMode === 'tracer'
            ? tracerColour(object, maxRedshift)
            : state.viewMode === 'survey'
              ? surveyColour(object, maxRedshift)
              : observedColour(object, maxRedshift);
      colour.setXYZ(index, rgb[0], rgb[1], rgb[2]);
      const baseSize = magnitude === null ? 1.85 : THREE.MathUtils.clamp(4.9 - magnitude * 0.19, 1.45, 4.7);
      size.setX(index, isSlice ? baseSize * 1.25 : baseSize);
    }

    position.needsUpdate = true;
    alpha.needsUpdate = true;
    colour.needsUpdate = true;
    size.needsUpdate = true;
    this.material.uniforms.uMode.value = state.viewMode === 'uncertainty' ? 1 : state.viewMode === 'time' ? 2 : 0;
    const denseScale = this.objects.length > 75_000 ? 0.96 : 1.0;
    this.material.uniforms.uPointScale.value = isSlice
      ? denseScale * (state.pointBudget < 12_000 ? 1.34 : 1.16)
      : denseScale * (state.pointBudget < 12_000 ? 1.20 : 1.08);

    return {
      visibleCount: visibleSet.size,
      candidateCount: candidates.length,
      underlyingCount: Number(this.meta.object_count || this.objects.length),
      overviewCount: Number(this.meta.overview_count || this.objects.length),
      maxDistance,
      maxLookback,
      tracerCounts,
      sourceCounts,
      sliceThickness: isSlice ? halfThickness * 2 : null,
      sliceOffset: isSlice ? sliceOffset : null,
    };
  }

  updateTime(seconds) { this.material.uniforms.uTime.value = seconds; }

  dispose() {
    this.geometry.dispose();
    this.material.dispose();
  }

  getObject(index) { return this.objects[index] ?? null; }

  getDisplayPosition(index) {
    const position = this.geometry.getAttribute('position');
    return new THREE.Vector3(position.getX(index), position.getY(index), position.getZ(index));
  }

  selectFromRaycaster(raycaster) {
    const intersections = raycaster.intersectObject(this.points, false);
    const match = intersections.find((item) => this.visibleIndices.has(item.index));
    if (!match || typeof match.index !== 'number') return null;
    return { index: match.index, object: this.objects[match.index] };
  }
}
