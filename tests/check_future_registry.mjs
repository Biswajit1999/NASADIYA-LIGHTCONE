import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const registry = JSON.parse(readFileSync(new URL('../data/registry/surveys.json', import.meta.url), 'utf8'));
const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const readiness = readFileSync(new URL('../src/ui/survey-readiness.js', import.meta.url), 'utf8');

assert.equal(registry.format, 'nasadiya-survey-registry/v4');
const byId = new Map(registry.layers.map((layer) => [layer.id, layer]));
['desi-future-release', 'rubin-lsst', 'euclid', 'roman', 'spherex', 'gaia-dr3-local-sample'].forEach((id) => {
  const layer = byId.get(id);
  assert.ok(layer, `missing future survey: ${id}`);
  assert.ok(['planned', 'blocked'].includes(layer.readiness), `${id} must not appear deployed`);
  assert.ok(Array.isArray(layer.required_contract) && layer.required_contract.length >= 4, `${id} needs a scientific contract`);
});
assert.ok(html.includes('id="mission-queue-list"'));
assert.ok(readiness.includes("layer.readiness !== 'deployed'"));

console.log('Future survey registry contracts passed.');
