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
  constructor({ scene, canvas }) {
    this.scene = scene;
    this.canvas = canvas;
    this.dom = {
      theme: document.querySelector('#theme-toggle'),
      bookmark: document.querySelector('#bookmark-view'),
      capture: document.querySelector('#capture-view'),
      presentation: document.querySelector('#presentation-toggle'),
      fps: document.querySelector('#instrument-fps'),
      gpu: document.querySelector('#instrument-gpu'),
      camera: document.querySelector('#instrument-camera'),
      toast: document.querySelector('#observatory-toast'),
      themeMeta: document.querySelector('meta[name="theme-color"]'),
    };
    this.presentation = false;
    this.lastFrame = 0;
    this.frameSamples = [];
    this.lastInstrumentUpdate = 0;
    this.toastTimer = null;
    this.applyTheme(readStorage(THEME_KEY, 'night'));
    this.updateBookmarkState();
    this.bind();
  }

  bind() {
    this.dom.theme?.addEventListener('click', () => this.toggleTheme());
    this.dom.bookmark?.addEventListener('click', () => this.saveBookmark());
    this.dom.bookmark?.addEventListener('dblclick', () => this.restoreBookmark());
    this.dom.capture?.addEventListener('click', () => this.capture());
    this.dom.presentation?.addEventListener('click', () => this.togglePresentation());
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
  }
}
