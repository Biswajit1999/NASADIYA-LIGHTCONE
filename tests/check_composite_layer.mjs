import assert from 'node:assert/strict';

import { SURVEY_LAYERS, TILE_STREAMING } from '../src/config.js';

const stack = SURVEY_LAYERS['all-live'];
assert.equal(stack.dataKind, 'composite');
assert.deepEqual(stack.memberLayerIds, ['2mrs', 'desi-dr1']);
assert.equal(stack.installed, true);
assert.equal(SURVEY_LAYERS['2mrs'].installed, true);
assert.equal(SURVEY_LAYERS['desi-dr1'].installed, true);
assert.equal(SURVEY_LAYERS['2mpz'].installed, false);
assert.equal(SURVEY_LAYERS['wise-sc'].installed, false);
assert.equal(TILE_STREAMING['all-live'].enabled, true);

console.log('Available-survey composite contract passed.');
