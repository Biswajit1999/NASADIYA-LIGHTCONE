import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../styles/observatory-v3.css', import.meta.url), 'utf8');
const module = readFileSync(new URL('../src/ui/observatory-console.js', import.meta.url), 'utf8');

['theme-toggle', 'bookmark-view', 'capture-view', 'presentation-toggle', 'instrument-fps', 'command-palette-toggle', 'command-palette', 'command-search-input'].forEach((id) => {
  assert.ok(html.includes(`id="${id}"`), `missing observatory control: ${id}`);
});
['body[data-theme="day"]', 'body.presentation-mode', '.observatory-hud', '.observatory-toast', '.command-palette-card'].forEach((selector) => {
  assert.ok(css.includes(selector), `missing observatory style: ${selector}`);
});
['toggleTheme()', 'togglePresentation(force = null)', 'saveBookmark()', 'restoreBookmark()', 'capture()', 'shareView()', 'openPalette(open)', 'tick(now)'].forEach((contract) => {
  assert.ok(module.includes(contract), `missing observatory behaviour: ${contract}`);
});

console.log('Observatory console contracts passed.');
