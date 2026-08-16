import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { SURVEY_LAYERS, TILE_STREAMING } from '../src/config.js';

const layer = SURVEY_LAYERS['2mpz'];
assert.equal(layer.installed, true, '2mpz should be a deployed layer');
assert.equal(layer.dataKind, 'tile-store');
assert.ok(layer.defaultMaxRedshift >= 0.4, '2mpz redshift ceiling should cover the real ~0.4 data max');
assert.ok(TILE_STREAMING['2mpz']?.enabled, '2mpz should have adaptive tile streaming configured');

const catalogLoader = readFileSync(new URL('../src/core/catalog-loader.js', import.meta.url), 'utf8');
assert.ok(catalogLoader.includes('hasGlobalUncertainty'), 'catalog-loader must accept survey-wide uncertainty, not just per-object');
assert.ok(catalogLoader.includes('global_redshift_sigma'), 'catalog-loader must propagate global_redshift_sigma into layer meta');
assert.ok(catalogLoader.includes('record.magnitude == null ? NaN'), 'absent magnitude must not silently coerce to a fabricated 0');

const surveyPoints = readFileSync(new URL('../src/core/survey-points.js', import.meta.url), 'utf8');
assert.ok(surveyPoints.includes('meta.global_redshift_sigma'), 'SurveyPoints must feed the survey-wide sigma into the uncertainty attribute');

const interfaceModule = readFileSync(new URL('../src/ui/lightcone-interface.js', import.meta.url), 'utf8');
assert.ok(interfaceModule.includes('survey-wide, not per-object'), 'inspector must disclose survey-wide vs per-object uncertainty');

const cosmology = readFileSync(new URL('../src/utils/cosmology.js', import.meta.url), 'utf8');
assert.ok(cosmology.includes('export function comovingDistanceMpc'), 'cosmology.js must expose comoving distance for shell-thickness math');
assert.ok(cosmology.includes('export function redshiftShellHalfThicknessMpc'));

const registry = JSON.parse(readFileSync(new URL('../data/registry/surveys.json', import.meta.url), 'utf8'));
const registryLayer = registry.layers.find((item) => item.id === '2mpz');
assert.equal(registryLayer.readiness, 'deployed');
assert.equal(registryLayer.global_redshift_sigma, 0.015);

console.log('2MPZ integration contracts passed.');
