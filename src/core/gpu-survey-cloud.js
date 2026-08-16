import * as THREE from 'three';

import { LIGHTCONE_CONFIG } from '../config.js?v=20260816-v7';
import { lookbackTimeGyr } from '../utils/cosmology.js?v=20260816-v7';

const VERTEX_SHADER = /* glsl */ `
  attribute float aRedshift;
  attribute float aTracer;
  attribute float aSample;
  uniform float uDisplayScale;
  uniform float uMaxRedshift;
  uniform float uDisplayFraction;
  uniform float uShowGalaxies;
  uniform float uTracerBGS;
  uniform float uTracerLRG;
  uniform float uTracerELG;
  uniform float uTracerQSO;
  uniform float uViewMode;
  uniform float uPointScale;
  uniform float uTime;
  uniform float uMotion;
  uniform float uCinematicBoost;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vLuminosity;

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

  vec3 colourForMode() {
    if (uViewMode < 0.5) return vec3(0.40, 0.86, 1.0);
    if (uViewMode < 1.5) return tracerColour();
    if (uViewMode < 2.5) return timeColour(aRedshift);
    return vec3(1.0, 0.70, 0.41);
  }

  float tracerPointScale() {
    if (aTracer < 0.5) return 0.92;
    if (aTracer < 1.5) return 1.18;
    if (aTracer < 2.5) return 1.06;
    if (aTracer < 3.5) return 0.96;
    return 1.20;
  }

  void main() {
    bool visible = uShowGalaxies > 0.5 && aRedshift <= uMaxRedshift && tracerEnabled() && aSample <= uDisplayFraction;
    vec4 mvPosition = modelViewMatrix * vec4(position * uDisplayScale, 1.0);
    if (!visible) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      gl_PointSize = 0.0;
      vAlpha = 0.0;
      vColor = vec3(0.0);
      return;
    }
    float perspective = clamp(760.0 / max(1.0, -mvPosition.z), 0.14, 3.0);
    float shimmer = 1.0 + uMotion * 0.035 * sin(uTime * (0.42 + aSample * 0.74) + aSample * 6.28318);
    float sizeBoost = mix(1.0, 3.2, uCinematicBoost);
    gl_PointSize = clamp(uPointScale * tracerPointScale() * perspective * shimmer * sizeBoost, 0.42, 7.5);
    gl_Position = projectionMatrix * mvPosition;
    float depthFade = mix(1.0, 0.62, clamp(aRedshift / max(0.001, uMaxRedshift), 0.0, 1.0));
    vAlpha = 0.115 * depthFade;
    vColor = colourForMode();
    vLuminosity = shimmer;
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  varying float vLuminosity;
  uniform float uCinematicBoost;
  void main() {
    vec2 uv = gl_PointCoord - vec2(0.5);
    float radius = length(uv);
    float core = 1.0 - smoothstep(0.02, 0.18, radius);
    float body = 1.0 - smoothstep(0.15, 0.48, radius);
    float halo = 1.0 - smoothstep(0.28, 0.50, radius);
    float alpha = max(core, body * 0.72 + halo * 0.12 * vLuminosity) * vAlpha;
    alpha = clamp(alpha * mix(1.0, 5.8, uCinematicBoost), 0.0, 1.0);
    if (alpha < 0.008) discard;
    gl_FragColor = vec4(mix(vColor, vec3(1.0), core * (0.34 + uCinematicBoost * 0.34)), alpha);
  }
`;

function enabled(state, tracer) { return state.tracerFilters?.[tracer] !== false ? 1.0 : 0.0; }
function modeCode(mode) { return mode === 'tracer' ? 1.0 : mode === 'time' ? 2.0 : mode === 'survey' ? 3.0 : 0.0; }

function summarizeCloud(values, stride) {
  let maxDistance = 0; let maxRedshift = 0;
  for (let offset = 0; offset < values.length; offset += stride) {
    const x = values[offset]; const y = values[offset + 1]; const z = values[offset + 2]; const redshift = values[offset + 3];
    maxDistance = Math.max(maxDistance, Math.hypot(x, y, z));
    maxRedshift = Math.max(maxRedshift, redshift);
  }
  return { maxDistanceMpc: maxDistance, maxRedshift };
}

function deterministicSamples(count) {
  const values = new Float32Array(count);
  const ratio = 0.618033988749895;
  for (let index = 0; index < count; index += 1) values[index] = (index * ratio) % 1;
  return values;
}

/** GPU-backed DESI cloud; every source is resident and density is shader-sampled. */
export class GpuSurveyCloud {
  constructor(buffer, manifest, meta = {}) {
    const binary = manifest?.binary || {};
    const records = Number(manifest?.record_count);
    const stride = Number(binary.stride_floats);
    const expectedBytes = Number(binary.byte_length);
    if (!(buffer instanceof ArrayBuffer) || !Number.isInteger(records) || records < 1 || stride !== 5) throw new Error('Full GPU cloud metadata is incomplete or invalid.');
    if (buffer.byteLength !== expectedBytes || buffer.byteLength !== records * stride * 4) throw new Error('Full GPU cloud binary length does not match its manifest.');

    this.meta = meta; this.manifest = manifest; this.recordCount = records;
    this.objects = []; this.visibleIndices = new Set(); this.geometry = new THREE.BufferGeometry();
    const values = new Float32Array(buffer);
    this.stats = summarizeCloud(values, stride);
    this.buffer = new THREE.InterleavedBuffer(values, stride);
    this.geometry.setAttribute('position', new THREE.InterleavedBufferAttribute(this.buffer, 3, 0, false));
    this.geometry.setAttribute('aRedshift', new THREE.InterleavedBufferAttribute(this.buffer, 1, 3, false));
    this.geometry.setAttribute('aTracer', new THREE.InterleavedBufferAttribute(this.buffer, 1, 4, false));
    this.geometry.setAttribute('aSample', new THREE.BufferAttribute(deterministicSamples(records), 1));
    this.geometry.setDrawRange(0, records);
    this.material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER, fragmentShader: FRAGMENT_SHADER, transparent: true, depthWrite: false, depthTest: true, blending: THREE.NormalBlending,
      uniforms: {
        uDisplayScale: { value: LIGHTCONE_CONFIG.displayScale }, uMaxRedshift: { value: this.stats.maxRedshift }, uDisplayFraction: { value: 1.0 }, uShowGalaxies: { value: 1.0 },
        uTracerBGS: { value: 1.0 }, uTracerLRG: { value: 1.0 }, uTracerELG: { value: 1.0 }, uTracerQSO: { value: 1.0 }, uViewMode: { value: 0.0 }, uPointScale: { value: 0.82 }, uTime: { value: 0.0 }, uMotion: { value: 1.0 }, uCinematicBoost: { value: 0.0 },
      },
    });
    this.targetDisplayFraction = 1.0;
    this.targetCinematicBoost = 0;
    this.points = new THREE.Points(this.geometry, this.material);
    this.points.name = 'desi-dr1-full-gpu-cloud'; this.points.frustumCulled = false;
  }

  get maxDistanceMpc() { return this.stats.maxDistanceMpc; }

  applyState(state) {
    const uniforms = this.material.uniforms;
    const activeRedshift = Math.min(this.stats.maxRedshift, Math.max(0.001, Number(state.maxRedshift) || 0.001));
    const drawBudget = Math.min(this.recordCount, Math.max(1_000, Number(state.pointBudget) || this.recordCount));
    uniforms.uMaxRedshift.value = activeRedshift;
    this.targetDisplayFraction = drawBudget / this.recordCount;
    uniforms.uShowGalaxies.value = state.showGalaxies ? 1.0 : 0.0;
    uniforms.uTracerBGS.value = enabled(state, 'BGS'); uniforms.uTracerLRG.value = enabled(state, 'LRG');
    uniforms.uTracerELG.value = enabled(state, 'ELG'); uniforms.uTracerQSO.value = enabled(state, 'QSO');
    uniforms.uViewMode.value = modeCode(state.viewMode);
    const densityScale = THREE.MathUtils.lerp(1.04, 0.76, Math.sqrt(this.targetDisplayFraction));
    const qualityScale = state.renderQuality === 'performance' ? 0.82 : state.renderQuality === 'quality' ? 1.08 : 1.0;
    uniforms.uPointScale.value = (state.viewMode === 'uncertainty' ? 0.92 : 0.82) * densityScale * qualityScale;
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    uniforms.uMotion.value = state.renderQuality === 'performance' || reducedMotion ? 0.0 : 1.0;
    return {
      visibleCount: drawBudget, drawBudget, gpuResidentCount: this.recordCount, candidateCount: this.recordCount, underlyingCount: this.recordCount,
      overviewCount: Number(this.meta.overview_count || 0), maxDistance: this.stats.maxDistanceMpc, maxLookback: lookbackTimeGyr(activeRedshift),
      tracerCounts: this.manifest.tracer_counts || {}, sourceCounts: { 'desi-dr1': this.recordCount }, gpuFiltered: true, fullCatalogue: true, sliceThickness: null, sliceOffset: null,
    };
  }

  updateTime(seconds) {
    this.material.uniforms.uTime.value = seconds;
    const current = this.material.uniforms.uDisplayFraction.value;
    this.material.uniforms.uDisplayFraction.value = THREE.MathUtils.lerp(current, this.targetDisplayFraction, 0.12);
    const boost = this.material.uniforms.uCinematicBoost;
    boost.value = THREE.MathUtils.lerp(boost.value, this.targetCinematicBoost, 0.06);
  }

  /** Only affects apparent brightness/size for the guided flythrough; never touches catalogue rows. */
  setCinematicBoost(active) { this.targetCinematicBoost = active ? 1 : 0; }

  dispose() { this.geometry.dispose(); this.material.dispose(); this.buffer = null; }
  getObject() { return null; }
  getDisplayPosition() { return new THREE.Vector3(); }
  selectFromRaycaster() { return null; }
}
