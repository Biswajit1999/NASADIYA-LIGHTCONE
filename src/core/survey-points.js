import * as THREE from 'three';
import { LIGHTCONE_CONFIG, PALETTE } from '../config.js';
import { pointFragmentShader, pointVertexShader } from '../shaders/point-shaders.js';
import { hslToRgb } from '../utils/math.js';

function clamp01(value) {
  return Math.min(1, Math.max(0, value));
}

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

function sliceEdgeAlpha(distanceFromPlane, halfThickness) {
  if (halfThickness <= 0) return 0;
  const edgeStart = halfThickness * 0.7;
  if (distanceFromPlane <= edgeStart) return 1;
  return 1 - clamp01((distanceFromPlane - edgeStart) / Math.max(halfThickness - edgeStart, 0.001));
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
    objects.forEach((object, index) => {
      const offset = index * 3;
      this.rawPositions[offset] = Number(object.x_mpc);
      this.rawPositions[offset + 1] = Number(object.y_mpc);
      this.rawPositions[offset + 2] = Number(object.z_mpc);
      displayPositions[offset] = this.rawPositions[offset] * LIGHTCONE_CONFIG.displayScale;
      displayPositions[offset + 1] = this.rawPositions[offset + 1] * LIGHTCONE_CONFIG.displayScale;
      displayPositions[offset + 2] = this.rawPositions[offset + 2] * LIGHTCONE_CONFIG.displayScale;
      colours.set(PALETTE.cyan, offset);
      alphas[index] = 0;
      const magnitude = magnitudeOf(object);
      sizes[index] = magnitude === null
        ? 1.75
        : THREE.MathUtils.clamp(4.8 - magnitude * 0.18, 1.45, 4.4);
      uncertainties[index] = Math.max(0, Number(object.redshift_error) || 0);
      twinkles[index] = ((index * 73) % 97) / 97;
      this.maxDatasetDistance = Math.max(this.maxDatasetDistance, Number(object.comoving_distance_mpc) || 0);
    });

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
      uniforms: {
        uPointScale: { value: 1.0 },
        uMode: { value: 0 },
        uTime: { value: 0 },
      },
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

    const maxRedshift = Math.max(0.001, Number(state.maxRedshift));
    const halfThickness = Math.max(1, Number(state.sliceThickness) / 2);
    const sliceOffset = Number(state.sliceOffset);

    this.objects.forEach((object, index) => {
      const offset = index * 3;
      const x = this.rawPositions[offset];
      const y = this.rawPositions[offset + 1];
      const z = this.rawPositions[offset + 2];
      const redshift = Number(object.redshift) || 0;
      const inRedshiftRange = redshift <= maxRedshift;
      const slabDistance = Math.abs(z - sliceOffset);
      const inSlice = slabDistance <= halfThickness;
      const isSlice = state.spatialMode === 'slice';
      const visibleCandidate = state.showGalaxies && inRedshiftRange && (!isSlice || inSlice);
      if (visibleCandidate) candidates.push(index);

      if (isSlice) {
        position.setXYZ(
          index,
          x * LIGHTCONE_CONFIG.displayScale,
          y * LIGHTCONE_CONFIG.displayScale,
          (z - sliceOffset) * LIGHTCONE_CONFIG.displayScale * 0.12,
        );
      } else {
        position.setXYZ(
          index,
          x * LIGHTCONE_CONFIG.displayScale,
          y * LIGHTCONE_CONFIG.displayScale,
          z * LIGHTCONE_CONFIG.displayScale,
        );
      }
    });

    const stride = Math.max(1, Math.ceil(candidates.length / Math.max(1, state.pointBudget)));
    const visibleSet = new Set(candidates.filter((_, rank) => rank % stride === 0));
    this.visibleIndices = visibleSet;

    this.objects.forEach((object, index) => {
      const visible = visibleSet.has(index);
      const offset = index * 3;
      const zCoordinate = this.rawPositions[offset + 2];
      const slabDistance = Math.abs(zCoordinate - sliceOffset);
      const magnitude = magnitudeOf(object);
      const brightness = magnitude === null ? 0.18 : clamp01((14.2 - magnitude) / 10.2);
      const radialDistance = Number(object.comoving_distance_mpc) || 0;
      const radialWeight = clamp01(radialDistance / this.maxDatasetDistance);
      const edgeFade = state.spatialMode === 'slice' ? sliceEdgeAlpha(slabDistance, halfThickness) : 1;
      const baseAlpha = 0.10 + brightness * 0.50 + (1 - radialWeight) * 0.11;
      alpha.setX(index, visible ? THREE.MathUtils.clamp(baseAlpha * edgeFade, 0.05, 0.86) : 0);

      const rgb = state.viewMode === 'time'
        ? timeColour(object, maxRedshift)
        : state.viewMode === 'uncertainty'
          ? PALETTE.violet
          : observedColour(object, maxRedshift);
      colour.setXYZ(index, rgb[0], rgb[1], rgb[2]);

      const baseSize = magnitude === null
        ? 1.85
        : THREE.MathUtils.clamp(4.9 - magnitude * 0.19, 1.45, 4.7);
      size.setX(index, state.spatialMode === 'slice' ? baseSize * 1.25 : baseSize);
    });

    position.needsUpdate = true;
    alpha.needsUpdate = true;
    colour.needsUpdate = true;
    size.needsUpdate = true;

    this.material.uniforms.uMode.value = state.viewMode === 'uncertainty' ? 1 : state.viewMode === 'time' ? 2 : 0;
    const denseScale = this.objects.length > 75_000 ? 0.82 : 1.0;
    this.material.uniforms.uPointScale.value = state.spatialMode === 'slice'
      ? denseScale * (state.pointBudget < 12_000 ? 1.28 : 1.1)
      : denseScale * (state.pointBudget < 12_000 ? 1.14 : 1.0);

    const candidateObjects = candidates.map((index) => this.objects[index]);
    return {
      visibleCount: visibleSet.size,
      candidateCount: candidates.length,
      underlyingCount: Number(this.meta.object_count || this.objects.length),
      overviewCount: Number(this.meta.overview_count || this.objects.length),
      maxDistance: Math.max(0, ...candidateObjects.map((item) => Number(item.comoving_distance_mpc) || 0)),
      maxLookback: Math.max(0, ...candidateObjects.map((item) => Number(item.lookback_time_gyr) || 0)),
      sliceThickness: state.spatialMode === 'slice' ? halfThickness * 2 : null,
      sliceOffset: state.spatialMode === 'slice' ? sliceOffset : null,
    };
  }

  updateTime(seconds) {
    this.material.uniforms.uTime.value = seconds;
  }

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
