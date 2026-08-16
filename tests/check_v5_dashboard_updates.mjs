import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { SURVEY_LAYERS } from '../src/config.js';

// Real DESI DR1 rows (already committed and audited) extend to z~3.5; the UI
// must not artificially cap the redshift ceiling back below that.
assert.ok(SURVEY_LAYERS['desi-dr1'].defaultMaxRedshift >= 3.4, 'desi-dr1 defaultMaxRedshift regressed below the real data ceiling');
assert.ok(SURVEY_LAYERS['all-live'].defaultMaxRedshift >= 3.4, 'all-live defaultMaxRedshift regressed below the real data ceiling');

const pointShaders = readFileSync(new URL('../src/shaders/point-shaders.js', import.meta.url), 'utf8');
const gpuCloud = readFileSync(new URL('../src/core/gpu-survey-cloud.js', import.meta.url), 'utf8');
const surveyPoints = readFileSync(new URL('../src/core/survey-points.js', import.meta.url), 'utf8');
const compositeFullCloud = readFileSync(new URL('../src/core/composite-full-cloud.js', import.meta.url), 'utf8');
const appModule = readFileSync(new URL('../src/app.js', import.meta.url), 'utf8');

[pointShaders, gpuCloud].forEach((source) => assert.ok(source.includes('uCinematicBoost'), 'shader missing uCinematicBoost uniform'));
[surveyPoints, gpuCloud].forEach((source) => assert.ok(source.includes('setCinematicBoost('), 'renderable missing setCinematicBoost()'));
assert.ok(compositeFullCloud.includes('setCinematicBoost(active)'), 'CompositeFullCloud does not forward the cinematic boost to its members');
assert.ok(appModule.includes('flyby.onChange((status) => { ui.setTourStatus(status); points?.setCinematicBoost(status.active); })'), 'app.js does not drive the cinematic boost from the guided flythrough state');

// Day theme must define its own accent RGB triplets (cyan/amber/green/violet),
// not silently inherit the night theme's neon values through the shared
// rgba(var(--x-rgb), alpha) pattern used across main.css/observatory-v3.css.
const mainCss = readFileSync(new URL('../styles/main.css', import.meta.url), 'utf8');
const observatoryCss = readFileSync(new URL('../styles/observatory-v3.css', import.meta.url), 'utf8');
['--cyan-rgb', '--amber-rgb', '--green-rgb', '--violet-rgb'].forEach((token) => assert.ok(mainCss.includes(`${token}:`), `main.css missing root definition for ${token}`));
const dayThemeBlock = observatoryCss.slice(observatoryCss.indexOf('body[data-theme="day"] {'), observatoryCss.indexOf('body[data-theme="day"] .command-bar'));
['--cyan-rgb', '--amber-rgb', '--green-rgb', '--violet-rgb'].forEach((token) => assert.ok(dayThemeBlock.includes(token), `day theme does not override ${token} — night glow colours will leak through`));
assert.ok(!/rgba\(\s*98,\s*222,\s*247/.test(mainCss + observatoryCss), 'hardcoded night-cyan rgba() leaked back into the stylesheets');

console.log('V5 dashboard update contracts passed.');
