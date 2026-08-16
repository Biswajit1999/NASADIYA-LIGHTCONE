import { loadIntegritySummary } from '../utils/integrity.js';
import { formatNumber } from '../utils/format.js';

const STAGE_DELAY_MS = { field: 0, telemetry: 420, provenance: 900, settle: 1500, badgesFade: 6200 };

function reducedMotion() {
  return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
}

function badge(label, value, note) {
  const item = document.createElement('div');
  item.className = 'provenance-badge';
  const strong = document.createElement('b');
  strong.textContent = value;
  const span = document.createElement('span');
  span.textContent = label;
  const small = document.createElement('small');
  small.textContent = note;
  item.append(strong, span, small);
  return item;
}

/**
 * One-time first-load choreography: the dark field brightens, instrumentation
 * powers on, then audited provenance badges appear before the camera settles
 * into the active lightcone. Runs once per session and never touches
 * catalogue data or camera math beyond the existing scene animation helpers.
 */
export class BootSequence {
  constructor({ root = document.body } = {}) {
    this.root = root;
    this.badgeHost = document.querySelector('#provenance-badges');
    this.hasRun = false;
    this.timers = [];
  }

  arm() {
    this.root.classList.add('boot-armed');
  }

  async run() {
    if (this.hasRun) return;
    this.hasRun = true;
    const reduced = reducedMotion();
    const summary = await loadIntegritySummary();
    this.renderBadges(summary);

    if (reduced) {
      this.root.classList.remove('boot-armed');
      this.root.classList.add('boot-field', 'boot-telemetry', 'boot-provenance', 'boot-complete');
      return;
    }

    const advance = (stageClass, delay) => {
      const timer = window.setTimeout(() => this.root.classList.add(stageClass), delay);
      this.timers.push(timer);
    };
    this.root.classList.remove('boot-armed');
    advance('boot-field', STAGE_DELAY_MS.field);
    advance('boot-telemetry', STAGE_DELAY_MS.telemetry);
    advance('boot-provenance', STAGE_DELAY_MS.provenance);
    advance('boot-complete', STAGE_DELAY_MS.settle);
    advance('boot-badges-fade', STAGE_DELAY_MS.badgesFade);
  }

  renderBadges(summary) {
    if (!this.badgeHost) return;
    this.badgeHost.replaceChildren();
    if (!summary?.available) {
      this.badgeHost.hidden = true;
      return;
    }
    if (summary.desiRows) this.badgeHost.append(badge('DESI DR1 observed rows', formatNumber(summary.desiRows), 'spectroscopic'));
    if (summary.twoMrsRows) this.badgeHost.append(badge('2MRS local anchor rows', formatNumber(summary.twoMrsRows), 'spectroscopic'));
    this.badgeHost.hidden = this.badgeHost.children.length === 0;
  }

  dispose() {
    this.timers.forEach((timer) => window.clearTimeout(timer));
    this.timers = [];
  }
}
