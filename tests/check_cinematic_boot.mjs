import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../styles/cinematic-v4.css', import.meta.url), 'utf8');
const bootModule = readFileSync(new URL('../src/ui/boot-sequence.js', import.meta.url), 'utf8');
const demoModule = readFileSync(new URL('../src/ui/linkedin-demo.js', import.meta.url), 'utf8');
const consoleModule = readFileSync(new URL('../src/ui/observatory-console.js', import.meta.url), 'utf8');
const sceneModule = readFileSync(new URL('../src/core/lightcone-scene.js', import.meta.url), 'utf8');
const appModule = readFileSync(new URL('../src/app.js', import.meta.url), 'utf8');

['id="provenance-badges"', 'id="demo-caption"', 'id="demo-caption-text"', 'id="demo-caption-exit"', 'id="showcase-capture"'].forEach((contract) => {
  assert.ok(html.includes(contract), `missing cinematic boot / demo mode DOM contract: ${contract}`);
});

['og:image:width', 'og:image:height', 'og:locale'].forEach((tag) => {
  assert.ok(html.includes(tag), `missing LinkedIn share metadata: ${tag}`);
});

['body.boot-field', 'body.boot-telemetry', 'body.boot-provenance', '.provenance-badge', 'body.linkedin-demo', '.demo-caption', 'body.showcase-capturing'].forEach((selector) => {
  assert.ok(css.includes(selector), `missing cinematic V4 style: ${selector}`);
});

['export class BootSequence', 'arm()', 'async run()', 'renderBadges('].forEach((contract) => {
  assert.ok(bootModule.includes(contract), `missing boot sequence behaviour: ${contract}`);
});

['export class LinkedInDemo', 'export const LINKEDIN_DEMO_ENTRY_LAYER_ID', 'async begin()', 'showCaption(', 'exit()'].forEach((contract) => {
  assert.ok(demoModule.includes(contract), `missing LinkedIn demo behaviour: ${contract}`);
});

['async captureShowcase()', 'paintShowcaseFrame('].forEach((contract) => {
  assert.ok(consoleModule.includes(contract), `missing showcase capture behaviour: ${contract}`);
});

assert.ok(sceneModule.includes('beginCinematicEntry('), 'missing cinematic camera entry on LightconeScene');
assert.ok(appModule.includes('boot.run()'), 'app.js does not trigger the boot sequence on initial load');
assert.ok(appModule.includes('linkedinDemo.begin()'), 'app.js does not start the LinkedIn demo after initial load');

console.log('Cinematic boot / LinkedIn demo contracts passed.');
