import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const annotations = readFileSync(new URL('../src/ui/scene-annotations.js', import.meta.url), 'utf8');
const scene = readFileSync(new URL('../src/core/lightcone-scene.js', import.meta.url), 'utf8');

assert.match(annotations, /\.project\(camera\)/, 'spatial labels must be projected from the active camera');
assert.match(annotations, /host\.querySelector\('\.anchor-label'\)\?\.remove\(\)/, 'unsupported 2MRS point label must be removed');
assert.match(annotations, /not a Galactic coordinate grid/, 'coordinate convention must be explicit');
assert.match(scene, /SceneAnnotations/, 'the scene must install projected labels');
assert.match(scene, /annotations\?\.update\(this\.camera\)/, 'the scene must update labels each frame');

console.log('Projected spatial annotation checks passed.');
