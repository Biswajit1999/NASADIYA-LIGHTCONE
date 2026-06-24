import { RENDERING_LIMITS } from '../config.js';

const PROFILES = Object.freeze([
  { rows: 125_000, label: 'Overview', detail: '125K' },
  { rows: 250_000, label: 'Dense', detail: '250K' },
  { rows: 500_000, label: 'Deep', detail: '500K' },
  { rows: 1_000_000, label: 'Max detail', detail: '1M' },
  { rows: 6_093_818, label: 'Full DESI', detail: '6M+' },
]);

function compactNumber(value) {
  const number = Number(value) || 0;
  if (number >= 1_000_000) return `${(number / 1_000_000).toFixed(number % 1_000_000 ? 2 : 0)}M`;
  if (number >= 1_000) return `${Math.round(number / 1_000)}K`;
  return String(Math.round(number));
}

function ensureStyleLink() {
  if (document.querySelector('link[data-research-console-ui]')) return;
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = './styles/research-console-ui.css?v=1';
  link.dataset.researchConsoleUi = 'true';
  document.head.append(link);
}

/**
 * A browser-side profile selector for DESI's bounded adaptive rendering path.
 * It controls a draw budget only; it never changes, weights, or invents rows.
 */
export class HighDensityControls {
  constructor() {
    ensureStyleLink();
    this.input = document.querySelector('#point-budget');
    this.profile = null;
    this.status = null;
    this.buttons = [];
    this.delivery = null;
    this.installed = false;
  }

  install() {
    if (this.installed || !this.input) return;
    this.installed = true;
    const host = this.input.closest('.drawer-section');
    if (!host) return;

    this.profile = document.createElement('div');
    this.profile.className = 'density-profile';
    this.profile.hidden = true;
    this.profile.innerHTML = `
      <div class="density-profile__heading">
        <span>RENDER PROFILE</span>
        <strong data-density-readout>125K / 1M</strong>
      </div>
      <div class="density-presets" role="group" aria-label="DESI rendering profile">
        ${PROFILES.map((profile) => `<button type="button" class="density-preset" data-density-rows="${profile.rows}" title="Request up to ${profile.rows.toLocaleString('en-GB')} rendered observed rows"><small>${profile.label}</small><b>${profile.detail}</b></button>`).join('')}
      </div>
      <p class="density-status" data-density-status>Overview mode is ready.</p>
    `;
    this.input.insertAdjacentElement('afterend', this.profile);
    this.status = this.profile.querySelector('[data-density-status]');
    this.readout = this.profile.querySelector('[data-density-readout]');
    this.buttons = [...this.profile.querySelectorAll('[data-density-rows]')];

    this.buttons.forEach((button) => button.addEventListener('click', () => {
      const target = Math.min(RENDERING_LIMITS.highDensityRows, Number(button.dataset.densityRows));
      this.input.value = String(target);
      this.input.dispatchEvent(new Event('input', { bubbles: true }));
      this.updateVisual(target);
    }));
    this.input.addEventListener('input', () => this.updateVisual(Number(this.input.value)));
  }

  configure({ layer, state }) {
    this.install();
    const enabled = ['desi-dr1', 'all-live'].includes(layer?.id);
    if (!this.profile || !this.input) return;
    this.profile.hidden = !enabled;
    if (!enabled) return;

    this.input.min = '1000';
    this.input.max = String(RENDERING_LIMITS.highDensityRows);
    this.input.step = String(RENDERING_LIMITS.highDensityStep);
    if (Number(state.pointBudget) > RENDERING_LIMITS.highDensityRows) state.pointBudget = RENDERING_LIMITS.highDensityRows;
    this.input.value = String(state.pointBudget);
    this.updateVisual(state.pointBudget);
    this.updateStatus();
  }

  setDelivery(delivery) {
    this.delivery = delivery || null;
    this.updateStatus();
  }

  updateState(state) {
    if (!this.profile || this.profile.hidden) return;
    this.updateVisual(state.pointBudget);
  }

  updateVisual(value) {
    if (!this.profile || this.profile.hidden) return;
    const budget = Math.min(RENDERING_LIMITS.highDensityRows, Math.max(1_000, Number(value) || 1_000));
    if (this.readout) this.readout.textContent = `${compactNumber(budget)} / 1M`;
    this.buttons.forEach((button) => {
      const target = Number(button.dataset.densityRows);
      const selected = budget === target;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  }

  updateStatus() {
    if (!this.status || !this.profile || this.profile.hidden) return;
    if (this.delivery?.available) {
      this.status.textContent = 'Adaptive tile endpoint active. Profiles above 125K request real camera-relevant observed rows.';
      return;
    }
    this.status.textContent = 'Public overview mode. Profiles above 125K activate when the local or hosted DESI tile endpoint is reachable.';
  }
}
