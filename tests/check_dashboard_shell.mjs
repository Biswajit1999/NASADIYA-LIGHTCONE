import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../styles/main.css', import.meta.url), 'utf8');

[
  'id="lightcone-canvas"',
  'class="command-bar"',
  'class="left-rail"',
  'id="control-drawer"',
  'class="telemetry-deck"',
  'id="tour-toggle"',
  'id="density-profiles"',
  'id="spatial-annotation"',
].forEach((contract) => assert.ok(html.includes(contract), `missing dashboard contract: ${contract}`));

['.command-bar', '.left-rail', '.control-drawer', '.telemetry-deck', '#lightcone-canvas'].forEach((selector) => {
  assert.ok(css.includes(selector), `missing dashboard style: ${selector}`);
});

console.log('Dashboard shell contracts passed.');
