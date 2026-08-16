import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../styles/analysis-panel.css', import.meta.url), 'utf8');
const module = readFileSync(new URL('../src/ui/analysis-panel.js', import.meta.url), 'utf8');
const interfaceModule = readFileSync(new URL('../src/ui/lightcone-interface.js', import.meta.url), 'utf8');
const appModule = readFileSync(new URL('../src/app.js', import.meta.url), 'utf8');

['id="analysis-modal"', 'id="close-analysis"', 'id="analysis-sample-note"', 'id="chart-redshift"', 'id="chart-tracer"', 'id="chart-sky"', 'id="chart-lookback"', 'class="analysis-block-toggle"'].forEach((contract) => {
  assert.ok(html.includes(contract), `missing analysis panel DOM contract: ${contract}`);
});

['.analysis-panel', '.analysis-block', '.analysis-block-toggle', '.analysis-svg', '.analysis-legend'].forEach((selector) => {
  assert.ok(css.includes(selector), `missing analysis panel style: ${selector}`);
});

['export class AnalysisPanel', 'open()', 'close()', 'render(', 'update(payload)'].forEach((contract) => {
  assert.ok(module.includes(contract), `missing analysis panel behaviour: ${contract}`);
});

assert.ok(interfaceModule.includes('onAnalysisOpen'), 'rail nav no longer wired to open the analysis panel');
assert.ok(!interfaceModule.includes("window.location.href = 'methods.html'"), 'Analysis rail button should open the in-app panel, not navigate away');
assert.ok(appModule.includes('analysisPanel.update('), 'app.js does not push data updates into the analysis panel');
assert.ok(appModule.includes('onAnalysisOpen: () => analysisPanel.open()'), 'app.js does not wire the analysis panel open callback');

console.log('Analysis panel contracts passed.');
