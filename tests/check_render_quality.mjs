import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const app = readFileSync(new URL('../src/app.js', import.meta.url), 'utf8');
const scene = readFileSync(new URL('../src/core/lightcone-scene.js', import.meta.url), 'utf8');
const gpu = readFileSync(new URL('../src/core/gpu-survey-cloud.js', import.meta.url), 'utf8');
const shader = readFileSync(new URL('../src/shaders/point-shaders.js', import.meta.url), 'utf8');

['auto', 'performance', 'quality'].forEach((mode) => assert.ok(html.includes(`data-render-quality="${mode}"`)));
assert.ok(app.includes("renderQuality: 'auto'"));
assert.ok(scene.includes('setRenderQuality(mode'));
assert.ok(scene.includes('samplePerformance(fps)'));
assert.ok(gpu.includes('this.targetDisplayFraction'));
assert.ok(gpu.includes('tracerPointScale()'));
assert.ok(gpu.includes('vec4 mvPosition = modelViewMatrix * vec4(position * uDisplayScale, 1.0);'));
assert.ok(shader.includes('uniform float uMotion'));

console.log('Adaptive render-quality contracts passed.');
