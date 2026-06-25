import { RENDERING_LIMITS } from '../config.js';

const PROFILES = [
  [125_000, 'Overview', '125K'], [250_000, 'Dense', '250K'], [500_000, 'Deep', '500K'], [1_000_000, 'Max detail', '1M'], [6_093_818, 'Full DESI', '6M+'],
];

function compact(value) {
  const n = Number(value) || 0;
  return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(n % 1_000_000 ? 2 : 0)}M` : `${Math.round(n / 1000)}K`;
}

function ensureStyleLink() {
  if (document.querySelector('link[data-research-console-ui]')) return;
  const link = document.createElement('link');
  link.rel = 'stylesheet'; link.href = './styles/research-console-ui.css?v=3';
  link.dataset.researchConsoleUi = 'true'; document.head.append(link);
}

export class HighDensityControls {
  constructor() {
    ensureStyleLink();
    this.input = document.querySelector('#point-budget');
    this.profile = null; this.buttons = []; this.status = null; this.readout = null;
    this.delivery = null; this.installed = false;
    this.fullCatalogue = { available: false, active: false, recordCount: 0 };
  }

  install() {
    if (this.installed || !this.input) return;
    this.installed = true;
    const host = this.input.closest('.drawer-section');
    if (!host) return;
    this.profile = document.createElement('div');
    this.profile.className = 'density-profile density-profile--tiered';
    this.profile.hidden = true;
    this.profile.innerHTML = `<div class="density-profile__heading"><span>DISPLAY DENSITY</span><strong data-density-readout>125K / 1M</strong></div><div class="density-presets" role="group" aria-label="DESI display density">${PROFILES.map(([rows, label, detail]) => `<button type="button" class="density-preset" data-density-rows="${rows}" title="Display up to ${rows.toLocaleString('en-GB')} observed DESI rows"><small>${label}</small><b>${detail}</b></button>`).join('')}</div><p class="density-status" data-density-status>Overview mode is ready.</p>`;
    this.input.insertAdjacentElement('afterend', this.profile);
    this.status = this.profile.querySelector('[data-density-status]');
    this.readout = this.profile.querySelector('[data-density-readout]');
    this.buttons = [...this.profile.querySelectorAll('[data-density-rows]')];
    this.fullButton = this.buttons.find((button) => Number(button.dataset.densityRows) > RENDERING_LIMITS.highDensityRows);
    this.buttons.forEach((button) => button.addEventListener('click', () => this.select(Number(button.dataset.densityRows))));
    this.input.addEventListener('input', () => { this.updateVisual(this.input.value); this.updateStatus(); });
  }

  select(requested) {
    if (requested > RENDERING_LIMITS.highDensityRows && !this.fullCatalogue.active) {
      if (this.fullCatalogue.available) window.dispatchEvent(new CustomEvent('nasadiya:full-catalogue-request'));
      return;
    }
    const maximum = this.maximum();
    this.input.value = String(Math.min(maximum, requested));
    this.input.dispatchEvent(new Event('input', { bubbles: true }));
  }

  maximum() { return this.fullCatalogue.active ? this.fullCatalogue.recordCount : RENDERING_LIMITS.highDensityRows; }

  configure({ layer, state }) {
    this.install();
    if (!this.profile || !this.input) return;
    this.profile.hidden = !['desi-dr1', 'all-live'].includes(layer?.id);
    if (!this.profile.hidden) this.sync(state);
  }

  sync(state) {
    const maximum = this.maximum();
    this.input.min = '1000'; this.input.max = String(maximum); this.input.step = String(RENDERING_LIMITS.highDensityStep);
    state.pointBudget = Math.min(maximum, Math.max(1000, Number(state.pointBudget) || 1000));
    this.input.value = String(state.pointBudget);
    this.updateVisual(state.pointBudget); this.updateStatus();
  }

  setDelivery(delivery) { this.delivery = delivery || null; this.updateStatus(); }

  setFullCatalogueStatus(status = {}) {
    this.fullCatalogue = { available: false, active: false, recordCount: 0, ...status };
    if (this.fullButton) {
      this.fullButton.disabled = !this.fullCatalogue.available && !this.fullCatalogue.active;
      this.fullButton.title = this.fullCatalogue.available ? `Keep all ${compact(this.fullCatalogue.recordCount)} DESI rows resident in GPU memory.` : (this.fullCatalogue.reason || 'Full DESI cloud unavailable.');
    }
    const n = Number(this.input?.value) || 1000;
    if (this.input) { this.input.max = String(this.maximum()); this.input.value = String(Math.min(this.maximum(), n)); }
    this.updateVisual(this.input?.value); this.updateStatus();
  }

  updateState(state) { if (!this.profile?.hidden) this.sync(state); }

  updateVisual(value) {
    if (!this.profile || this.profile.hidden) return;
    const maximum = this.maximum(); const budget = Math.min(maximum, Math.max(1000, Number(value) || 1000));
    this.readout.textContent = this.fullCatalogue.active ? `${compact(budget)} / ${compact(maximum)} GPU` : `${compact(budget)} / 1M`;
    this.buttons.forEach((button) => {
      const requested = Number(button.dataset.densityRows);
      const active = requested === budget || (requested > RENDERING_LIMITS.highDensityRows && this.fullCatalogue.active && budget === maximum);
      button.classList.toggle('is-active', active); button.setAttribute('aria-pressed', String(active));
    });
  }

  updateStatus() {
    if (!this.status || !this.profile || this.profile.hidden) return;
    if (this.fullCatalogue.active) {
      const budget = Math.min(this.maximum(), Number(this.input?.value) || this.maximum());
      this.status.textContent = `All ${compact(this.maximum())} DESI rows are loaded in GPU memory. This control sets a deterministic ${compact(budget)}-row display sample.`;
    } else if (this.fullCatalogue.available) {
      this.status.textContent = `Full ${compact(this.fullCatalogue.recordCount)} GPU cloud available. Choose Full DESI to load every observed DESI row.`;
    } else if (this.delivery?.available) {
      this.status.textContent = 'Adaptive tiles are active. Higher profiles request camera-relevant observed rows.';
    } else {
      this.status.textContent = 'Public overview mode. Higher profiles require the local or hosted DESI delivery path.';
    }
  }
}
