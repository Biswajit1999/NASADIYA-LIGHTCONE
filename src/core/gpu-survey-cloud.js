import * as THREE from 'three';

import { LIGHTCONE_CONFIG } from '../config.js';
import { lookbackTimeGyr } from '../utils/cosmology.js';

const VERTEX_SHADER = /* glsl */ `
  attribute float aRedshift;
  attribute float aTracer;
  uniform float uDisplayScale;
  uniform float uMaxRedshift;
  uniform float uShowGalaxies;
  uniform float uTracerBGS;
  uniform float uTracerLRG;
  uniform float uTracerELG;
  uniform float uTracerQSO;
  uniform float uViewMode;
  uniform float uPointScale;
  varying vec3 vColor;
  varying float vAlpha;

  bool tracerEnabled() {
    if (aTracer < 0.5) return true;
    if (aTracer < 1.5) return uTracerBGS > 0.5;
    if (aTracer < 2.5) return uTracerLRG > 0.5;
    if (aTracer < 3.5) return uTracerELG > 0.5;
    return uTracerQSO > 0.5;
  }

  vec3 tracerColour() {
    if (aTracer < 0.5) return vec3(0.55, 0.67, 0.74);
    if (aTracer < 1.5) return vec3(0.30, 0.86, 1.0);
    if (aTracer < 2.5) return vec3(1.0, 0.70, 0.41);
    if (aTracer < 3.5) return vec3(0.47, 0.93, 0.63);
    return vec3(0.73, 0.61, 1.0);
  }

  vec3 timeColour(float z) {
    float t = clamp(z / max(0.001, uMaxRedshift), 0.0, 1.0);
    return mix(vec3(0.32, 0.84, 1.0), vec3(1.0, 0.58, 0.26), t);
  }

  void main() {
    bool visible = uShowGalaxies > 0.5 && aRedshift <= uMaxRedshift && tracerEnabled();
    vec4 mvPosition = modelViewMatrix * vec4(position * uDisplayScale, 1.0);
    if (!visible) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      gl_PointSize = 0.0;
      vAlpha = 0.0;
      vColor = vec3(0.0);
      return;
    }
    float perspective = clamp(760.0 / max(1.0, -mvPosition.z), 0.14, 3.0);
    gl_PointSize = clamp(uPointScale * perspective, 0.42, 2.45);
    gl_Position = projectionMatrix * mvPosition;
    float depthFade = mix(1.0, 0.62, clamp(aRedshift / max(0.001, uMaxRedshift), 0.0, 1.0));
    vAlpha = 0.115 * depthFade;
    vColor = uViewMode < 0.5 ? vec3(0.40, 0.86, 1.0) : uViewMode < 1.5 ? tracerColour() : timeColour(aRedshift);
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vec2 uv = gl_PointCoord - vec2(0.5);
    float radius = length(uv);
    float body = 1.0 - smoothstep(0.18, 0.50, radius);
    float alpha = body * vAlpha;
    if (alpha < 0.008) discard;
    gl_FragColor = vec4(vColor, alpha);
  }
`;

function enabled(state, tracer) {
  return state.tracerFilters?.[tracer] !== false ? 1.0 : 0.0;
}

function modeCode(mode) {
  if (mode === 'tracer') return 1.0;
  if (mode === 'time') return 2.0;
  return 0.0;
}

function summarizeCloud(values, stride) {
  let maxDistance = 0;
  let maxRedshift = 0;
  for (let offset = 0; offset < values.length; offset += stride) {
    const x = values[offset];
    const y = values[offset + 1];
    const z = values[offset + 2];
    const redshift = values[offset + 3];
    const radial = Math.sqrt(x * x + y * y + z * z);
    if (radial > maxDistance) maxDistance = radial;
    if (redshift > maxRedshift) maxRedshift = redshift;
  }
  return { maxDistanceMpc: maxDistance, maxRedshift };
}

/**
 * GPU-backed full DESI cloud. The ArrayBuffer is interleaved as x, y, z,
 * redshift and tracer-code float32 values. It has no object IDs, so source
 * inspection remains deliberately tile-based.
 */
export class GpuSurveyCloud {
  constructor(buffer, manifest, meta = {}) {
    const binary = manifest?.binary || {};
    const records = Number(manifest?.record_count);
    const stride = Number(binary.stride_floats);
    const expectedBytes = Number(binary.byte_length);
    if (!(buffer instanceof ArrayBuffer) || !Number.isInteger(records) || records < 1 || stride !== 5) {
      throw new Error('Full GPU cloud metadata is incomplete or invalid.');
    }
    if (buffer.byteLength !== expectedBytes || buffer.byteLength !== records * stride * 4) {
      throw new Error('Full GPU cloud binary length does not match its manifest.');
    }

    this.meta = meta;
    this.manifest = manifest;
    this.recordCount = records;
    this.objects = [];
    this.visibleIndices = new Set();
    this.geometry = new THREE.BufferGeometry();
    const values = new Float32Array(buffer);
    this.stats = summarizeCloud(values, stride);
    this.buffer = new THREE.InterleavedBuffer(values, stride);
    this.geometry.setAttribute('position', new THREE.InterleavedBufferAttribute(this.buffer, 3, 0, false));
    this.geometry.setAttribute('aRedshift', new THREE.InterleavedBufferAttribute(this.buffer, 1, 3, false));
    this.geometry.setAttribute('aTracer', new THREE.InterleavedBufferAttribute(this.buffer, 1, 4, false));
    this.geometry.setDrawRange(0, records);
    this.material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      transparent: true,
      depthWrite: false,
      depthTest: true,
      blending: THREE.NormalBlending,
      uniforms: {
        uDisplayScale: { value: LIGHTCONE_CONFIG.displayScale },
        uMaxRedshift: { value: this.stats.maxRedshift },
        uShowGalaxies: { value: 1.0 },
        uTracerBGS: { value: 1.0 },
        uTracerLRG: { value: 1.0 },
        uTracerELG: { value: 1.0 },
        uTracerQSO: { value: 1.0 },
        uViewMode: { value: 0.0 },
        uPointScale: { value: 0.82 },
      },
    });
    this.points = new THREE.Points(this.geometry, this.material);
    this.points.name = 'desi-dr1-full-gpu-cloud';
    this.points.frustumCulled = false;
  }

  get maxDistanceMpc() { return this.stats.maxDistanceMpc; }

  applyState(state) {
    const uniforms = this.material.uniforms;
    const activeRedshift = Math.min(this.stats.maxRedshift, Math.max(0.001, Number(state.maxRedshift) || 0.001));
    uniforms.uMaxRedshift.value = activeRedshift;
    uniforms.uShowGalaxies.value = state.showGalaxies ? 1.0 : 0.0;
    uniforms.uTracerBGS.value = enabled(state, 'BGS');
    uniforms.uTracerLRG.value = enabled(state, 'LRG');
    uniforms.uTracerELG.value = enabled(state, 'ELG');
    uniforms.uTracerQSO.value = enabled(state, 'QSO');
    uniforms.uViewMode.value = modeCode(state.viewMode);
    uniforms.uPointScale.value = state.viewMode === 'uncertainty' ? 0.92 : 0.82;
    return {
      visibleCount: this.recordCount,
      gpuResidentCount: this.recordCount,
      candidateCount: this.recordCount,
      underlyingCount: this.recordCount,
      overviewCount: Number(this.meta.overview_count || 0),
      maxDistance: this.stats.maxDistanceMpc,
      maxLookback: lookbackTimeGyr(activeRedshift),
      tracerCounts: this.manifest.tracer_counts || {},
      sourceCounts: { 'desi-dr1': this.recordCount },
      gpuFiltered: true,
      fullCatalogue: true,
      sliceThickness: null,
      sliceOffset: null,
    };
  }

  updateTime() {}

  dispose() {
    this.geometry.dispose();
    this.material.dispose();
    this.buffer = null;
  }

  getObject() { return null; }

  getDisplayPosition() { return new THREE.Vector3(); }

  selectFromRaycaster() { return null; }
}
