import assert from 'node:assert/strict';

import { lookbackTimeGyr } from '../src/utils/cosmology.js';

assert.equal(lookbackTimeGyr(0), 0);
assert.ok(lookbackTimeGyr(1) > 7 && lookbackTimeGyr(1) < 9);
assert.ok(lookbackTimeGyr(3.5) > lookbackTimeGyr(1));

console.log('Navigation cosmology checks passed.');
