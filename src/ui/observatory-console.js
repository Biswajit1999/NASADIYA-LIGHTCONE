import { loadIntegritySummary } from '../utils/integrity.js';
import { formatNumber } from '../utils/format.js';

const THEME_KEY = 'nasadiya:observatory-theme';
const BOOKMARK_KEY = 'nasadiya:camera-bookmark';

function readStorage(key, fallback = null) {
  try { return window.localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}

function writeStorage(key, value) {
  try { window.localStorage.setItem(key, value); } catch { /* Storage can be unavailable in privacy mode. */ }
}

function isTypingTarget(target) {
  return ['INPUT', 'SELECT', 'TEXTAREA'].includes(target?.tagName) || target?.isContentEditable;
}

export class ObservatoryConsole {
  constructor({ scene, canvas, getState }) {
    this.scene = scene;
    this.canvas = canvas;
    this.getState = getState;
    this.dom = {
      theme: document.querySelector('#theme-toggle'),
      bookmark: document.querySelector('#bookmark-view'),
      capture: document.querySelector('#capture-view'),
      showcaseCapture: document.querySelector('#showcase-capture'),
      presentation: document.querySelector('#presentation-toggle'),
      fps: document.querySelector('#instrument-fps'),
      gpu: document.querySelector('#instrument-gpu'),
      camera: document.querySelector('#instrument-camera'),
      toast: document.querySelector('#observatory-toast'),
      themeMeta: document.querySelector('meta[name="theme-color"]'),
      paletteToggle: document.querySelector('#command-palette-toggle'),
      palette: document.querySelector('#command-palette'),
      paletteClose: document.querySelector('#close-command-palette'),
      commandSearch: document.querySelector('#command-search-input'),
      commandButtons: [...document.querySelectorAll('[data-observatory-command]')],
      objectSearch: document.querySelector('#object-search-command'),
      objectSearchLabel: document.querySelector('#object-search-label'),
    };
    this.presentation = false;
    this.lastFrame = 0;
    this.frameSamples = [];
    this.lastInstrumentUpdate = 0;
    this.toastTimer = null;
    this.filteredCommands = this.dom.commandButtons;
    this.commandIndex = 0;
    this.applyTheme(readStorage(THEME_KEY, 'night'));
    this.updateBookmarkState();
    this.bind();
  }

  bind() {
    this.dom.theme?.addEventListener('click', () => this.toggleTheme());
    this.dom.bookmark?.addEventListener('click', () => this.saveBookmark());
    this.dom.bookmark?.addEventListener('dblclick', () => this.restoreBookmark());
    this.dom.capture?.addEventListener('click', () => this.capture());
    this.dom.showcaseCapture?.addEventListener('click', () => this.captureShowcase());
    this.dom.presentation?.addEventListener('click', () => this.togglePresentation());
    this.dom.paletteToggle?.addEventListener('click', () => this.openPalette(true));
    this.dom.paletteClose?.addEventListener('click', () => this.openPalette(false));
    this.dom.palette?.addEventListener('click', (event) => { if (event.target === this.dom.palette) this.openPalette(false); });
    this.dom.commandSearch?.addEventListener('input', () => this.filterCommands());
    this.dom.commandSearch?.addEventListener('keydown', (event) => this.handlePaletteKey(event));
    this.dom.commandButtons.forEach((button) => button.addEventListener('click', () => this.runCommand(button.dataset.observatoryCommand)));
    this.dom.objectSearch?.addEventListener('click', () => this.runCommand('object-search', this.dom.commandSearch?.value));
    window.addEventListener('keydown', (event) => {
      if (isTypingTarget(event.target) || event.ctrlKey || event.metaKey || event.altKey) return;
      const key = event.key.toLowerCase();
      if (key === 't') this.toggleTheme();
      if (key === 'p') this.togglePresentation();
      if (key === 'b') this.saveBookmark();
      if (key === '1') this.restoreBookmark();
      if (key === 's') this.capture();
      if (event.key === 'Escape' && this.presentation) this.togglePresentation(false);
    });
    window.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        this.openPalette(true);
      }
      if (event.key === 'Escape' && !this.dom.palette?.hidden) this.openPalette(false);
    });
  }

  openPalette(open) {
    if (!this.dom.palette) return;
    this.dom.palette.hidden = !open;
    this.dom.paletteToggle?.setAttribute('aria-expanded', String(open));
    if (open) {
      this.dom.commandSearch.value = '';
      this.filterCommands();
      this.dom.commandSearch.focus();
    } else {
      this.dom.paletteToggle?.focus();
    }
  }

  filterCommands() {
    const query = this.dom.commandSearch?.value.trim().toLowerCase() || '';
    this.filteredCommands = this.dom.commandButtons.filter((button) => {
      const visible = !query || button.textContent.toLowerCase().includes(query);
      button.hidden = !visible;
      return visible;
    });
    const showObjectSearch = query.length >= 3;
    if (this.dom.objectSearch) this.dom.objectSearch.hidden = !showObjectSearch;
    if (showObjectSearch) {
      this.dom.objectSearchLabel.textContent = `Find observed object “${this.dom.commandSearch.value.trim()}”`;
      this.filteredCommands.push(this.dom.objectSearch);
    }
    this.commandIndex = 0;
    this.syncCommandSelection();
  }

  syncCommandSelection() {
    this.dom.commandButtons.forEach((button) => button.classList.remove('is-selected'));
    this.filteredCommands[this.commandIndex]?.classList.add('is-selected');
  }

  handlePaletteKey(event) {
    if (!this.filteredCommands.length) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.commandIndex = (this.commandIndex + 1) % this.filteredCommands.length;
      this.syncCommandSelection();
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.commandIndex = (this.commandIndex - 1 + this.filteredCommands.length) % this.filteredCommands.length;
      this.syncCommandSelection();
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      this.filteredCommands[this.commandIndex]?.click();
    }
  }

  runCommand(command, query = null) {
    this.openPalette(false);
    if (command === 'toggle-presentation') return this.togglePresentation();
    if (command === 'share-view') return this.shareView();
    window.dispatchEvent(new CustomEvent('nasadiya:observatory-command', { detail: { command, query } }));
  }

  applyTheme(theme) {
    const next = theme === 'day' ? 'day' : 'night';
    document.body.dataset.theme = next;
    writeStorage(THEME_KEY, next);
    this.dom.theme?.setAttribute('aria-pressed', String(next === 'day'));
    this.dom.theme?.setAttribute('aria-label', `Switch to ${next === 'day' ? 'night' : 'day'} observatory theme`);
    const label = this.dom.theme?.querySelector('b');
    if (label) label.textContent = next === 'day' ? 'Day' : 'Night';
    if (this.dom.themeMeta) this.dom.themeMeta.content = next === 'day' ? '#eaf2f6' : '#020914';
    this.scene.scene.background.set(next === 'day' ? 0x071522 : 0x020611);
    this.scene.scene.fog.color.set(next === 'day' ? 0x071522 : 0x020611);
  }

  toggleTheme() {
    const next = document.body.dataset.theme === 'day' ? 'night' : 'day';
    this.applyTheme(next);
    this.notify(`${next === 'day' ? 'Day research' : 'Night observatory'} theme active`);
  }

  togglePresentation(force = null) {
    this.presentation = force ?? !this.presentation;
    document.body.classList.toggle('presentation-mode', this.presentation);
    this.dom.presentation?.setAttribute('aria-pressed', String(this.presentation));
    this.dom.presentation?.setAttribute('aria-label', this.presentation ? 'Exit presentation focus mode' : 'Enter presentation focus mode');
    const label = this.dom.presentation?.querySelector('b');
    if (label) label.textContent = this.presentation ? 'Exit focus' : 'Focus';
    window.setTimeout(() => this.scene.resize(), 220);
    this.notify(this.presentation ? 'Presentation focus active · press Esc to exit' : 'Observatory panels restored');
  }

  currentBookmark() {
    try { return JSON.parse(readStorage(BOOKMARK_KEY)); } catch { return null; }
  }

  saveBookmark() {
    const bookmark = {
      position: this.scene.camera.position.toArray(),
      target: this.scene.controls.target.toArray(),
      mode: this.scene.mode,
      savedAt: new Date().toISOString(),
    };
    writeStorage(BOOKMARK_KEY, JSON.stringify(bookmark));
    this.updateBookmarkState();
    this.notify('Camera bookmark saved · double-click or press 1 to restore');
  }

  restoreBookmark() {
    const bookmark = this.currentBookmark();
    if (!bookmark?.position || !bookmark?.target) {
      this.notify('No camera bookmark saved yet');
      return;
    }
    const position = this.scene.camera.position.clone().fromArray(bookmark.position);
    const target = this.scene.controls.target.clone().fromArray(bookmark.target);
    this.scene.animateCamera(position, target, 820);
    this.notify('Camera bookmark restored');
  }

  updateBookmarkState() {
    const saved = Boolean(this.currentBookmark());
    this.dom.bookmark?.classList.toggle('has-bookmark', saved);
    this.dom.bookmark?.setAttribute('aria-label', saved ? 'Save camera bookmark; double-click to restore saved view' : 'Save camera bookmark');
  }

  capture() {
    this.scene.renderer.render(this.scene.scene, this.scene.camera);
    this.canvas.toBlob((blob) => {
      if (!blob) {
        this.notify('Viewport capture is unavailable in this browser');
        return;
      }
      const link = document.createElement('a');
      link.download = `nasadiya-lightcone-${new Date().toISOString().replaceAll(':', '-').slice(0, 19)}.png`;
      link.href = URL.createObjectURL(blob);
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
      this.notify('Scientific viewport captured as PNG');
    }, 'image/png');
  }

  /**
   * Prepares a clean, branded poster frame for sharing: hides interactive
   * chrome, renders at the "quality" pixel ratio, then composites the raw
   * WebGL frame with a provenance stat line read from the same audited
   * registry as the boot badges. It never alters catalogue rendering itself.
   */
  async captureShowcase() {
    if (this.showcaseBusy) return;
    this.showcaseBusy = true;
    const previousQuality = this.scene.renderQuality;
    document.body.classList.add('showcase-capturing');
    this.scene.setRenderQuality('quality');
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    this.scene.renderer.render(this.scene.scene, this.scene.camera);
    const summary = await loadIntegritySummary();
    const composite = document.createElement('canvas');
    composite.width = this.canvas.width;
    composite.height = this.canvas.height;
    const context = composite.getContext('2d');
    context.drawImage(this.canvas, 0, 0);
    this.paintShowcaseFrame(context, composite.width, composite.height, summary);
    composite.toBlob((blob) => {
      document.body.classList.remove('showcase-capturing');
      this.scene.setRenderQuality(previousQuality);
      this.showcaseBusy = false;
      if (!blob) {
        this.notify('Showcase capture is unavailable in this browser');
        return;
      }
      const link = document.createElement('a');
      link.download = `nasadiya-lightcone-showcase-${new Date().toISOString().replaceAll(':', '-').slice(0, 19)}.png`;
      link.href = URL.createObjectURL(blob);
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
      this.notify('Showcase frame captured for LinkedIn');
    }, 'image/png');
  }

  paintShowcaseFrame(context, width, height, summary) {
    const scale = width / 1600;
    const gradient = context.createLinearGradient(0, height * 0.74, 0, height);
    gradient.addColorStop(0, 'rgba(2,6,12,0)');
    gradient.addColorStop(1, 'rgba(2,6,12,0.86)');
    context.fillStyle = gradient;
    context.fillRect(0, height * 0.74, width, height * 0.26);

    context.textAlign = 'left';
    context.fillStyle = '#eaf7ff';
    context.font = `800 ${34 * scale}px "Iowan Old Style", Georgia, serif`;
    context.fillText('NĀSADĪYA LIGHTCONE', width * 0.035, height - 74 * scale);

    context.fillStyle = '#62def7';
    context.font = `700 ${15 * scale}px "JetBrains Mono", monospace`;
    const statLine = summary.available
      ? `${formatNumber(summary.desiRows)} observed DESI DR1 rows · ${formatNumber(summary.twoMrsRows)} 2MRS anchor rows · measured, not simulated`
      : 'Survey-native measured galaxy catalogues · measured, not simulated';
    context.fillText(statLine.toUpperCase(), width * 0.035, height - 42 * scale);

    context.fillStyle = 'rgba(180, 202, 217, 0.85)';
    context.font = `700 ${11 * scale}px "JetBrains Mono", monospace`;
    context.textAlign = 'right';
    context.fillText('CREATED BY BISWAJIT JANA', width * 0.965, height - 42 * scale);
    context.textAlign = 'left';
  }

  sharedViewFromLocation() {
    const match = window.location.hash.match(/^#view=([A-Za-z0-9_-]+)$/);
    if (!match) return null;
    try {
      const encoded = match[1].replaceAll('-', '+').replaceAll('_', '/');
      return JSON.parse(window.atob(encoded));
    } catch { return null; }
  }

  shareView() {
    const currentState = this.getState?.() || {};
    const payload = {
      version: 1,
      layerId: currentState.layerId,
      maxRedshift: currentState.maxRedshift,
      pointBudget: currentState.pointBudget,
      viewMode: currentState.viewMode,
      renderQuality: currentState.renderQuality,
      tracerFilters: currentState.tracerFilters,
      camera: this.scene.camera.position.toArray().map((value) => Number(value.toFixed(3))),
      target: this.scene.controls.target.toArray().map((value) => Number(value.toFixed(3))),
      theme: document.body.dataset.theme || 'night',
    };
    const token = window.btoa(JSON.stringify(payload)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
    window.history.replaceState(null, '', `#view=${token}`);
    const copy = navigator.clipboard?.writeText(window.location.href);
    if (copy?.catch) copy.catch(() => {});
    this.notify('Shareable view copied · URL includes camera, layer and filters');
  }

  notify(message) {
    if (!this.dom.toast) return;
    window.clearTimeout(this.toastTimer);
    this.dom.toast.textContent = message;
    this.dom.toast.classList.add('is-visible');
    this.toastTimer = window.setTimeout(() => this.dom.toast.classList.remove('is-visible'), 2600);
  }

  tick(now) {
    if (this.lastFrame) {
      this.frameSamples.push(now - this.lastFrame);
      if (this.frameSamples.length > 45) this.frameSamples.shift();
    }
    this.lastFrame = now;
    if (now - this.lastInstrumentUpdate < 500) return;
    this.lastInstrumentUpdate = now;
    const meanFrame = this.frameSamples.reduce((sum, value) => sum + value, 0) / Math.max(1, this.frameSamples.length);
    const fps = Math.min(999, Math.round(1000 / Math.max(1, meanFrame)));
    const memory = this.scene.renderer.info.memory;
    const cameraRadius = this.scene.camera.position.distanceTo(this.scene.controls.target);
    if (this.dom.fps) this.dom.fps.textContent = `${fps} FPS`;
    if (this.dom.gpu) this.dom.gpu.textContent = `${memory.geometries} GEO · ${memory.textures} TEX`;
    if (this.dom.camera) this.dom.camera.textContent = `${Math.round(cameraRadius).toLocaleString('en-GB')} U`;
    window.dispatchEvent(new CustomEvent('nasadiya:performance-sample', { detail: { fps } }));
  }
}
