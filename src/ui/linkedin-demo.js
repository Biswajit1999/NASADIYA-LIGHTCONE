import { loadIntegritySummary } from '../utils/integrity.js';
import { formatNumber } from '../utils/format.js';

export const LINKEDIN_DEMO_ENTRY_LAYER_ID = 'all-live';
const TOUR_START_DELAY_MS = 1300;
const CAPTION_INTERVAL_MS = 5500;

function reducedMotion() {
  return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
}

function isRequested() {
  return new URLSearchParams(window.location.search).get('demo') === 'linkedin';
}

/**
 * Curated, read-only presentation mode for sharing the explorer as a LinkedIn
 * post or embedded clip. It only ever calls existing state-changing hooks
 * (layer activation, full-cloud request, guided flyby) that the interactive
 * UI already exposes; it never invents catalogue rows or camera-only
 * "fake" data of its own.
 */
export class LinkedInDemo {
  constructor({ requestFullCloud, flyby, observatory }) {
    this.requestFullCloud = requestFullCloud;
    this.flyby = flyby;
    this.observatory = observatory;
    this.active = isRequested();
    this.captionTimer = null;
    this.captionIndex = 0;
    this.captions = [];
    this.dom = {
      caption: document.querySelector('#demo-caption'),
      captionText: document.querySelector('#demo-caption-text'),
      captionIndex: document.querySelector('#demo-caption-index'),
      captionExit: document.querySelector('#demo-caption-exit'),
    };
    if (this.active) document.body.classList.add('linkedin-demo');
    this.dom.captionExit?.addEventListener('click', () => this.exit());
  }

  async begin() {
    if (!this.active) return;
    const summary = await loadIntegritySummary();
    this.captions = [
      summary.available && summary.desiRows ? `${formatNumber(summary.desiRows)} observed DESI DR1 rows` : 'Millions of observed DESI DR1 rows',
      summary.available && summary.twoMrsRows ? `${formatNumber(summary.twoMrsRows)} 2MRS local anchor rows` : 'A measured 2MRS local anchor',
      'No simulated galaxies.',
      'Measured redshift → distance → cosmic time.',
    ];
    this.showCaption(0);
    this.captionTimer = window.setInterval(() => this.showCaption((this.captionIndex + 1) % this.captions.length), CAPTION_INTERVAL_MS);
    if (this.dom.caption) this.dom.caption.hidden = false;

    window.setTimeout(() => {
      if (!this.active) return;
      this.requestFullCloud?.();
      if (!reducedMotion()) this.flyby?.start();
    }, TOUR_START_DELAY_MS);
  }

  showCaption(index) {
    if (!this.dom.captionText) return;
    this.captionIndex = index;
    this.dom.caption?.classList.remove('is-visible');
    const reveal = () => {
      this.dom.captionText.textContent = this.captions[index];
      if (this.dom.captionIndex) this.dom.captionIndex.textContent = `${index + 1} / ${this.captions.length}`;
      this.dom.caption?.classList.add('is-visible');
    };
    if (reducedMotion()) reveal();
    else window.setTimeout(reveal, 160);
  }

  exit() {
    this.active = false;
    window.clearInterval(this.captionTimer);
    this.captionTimer = null;
    if (this.dom.caption) this.dom.caption.hidden = true;
    document.body.classList.remove('linkedin-demo');
    this.flyby?.stop('demo-exit');
    const url = new URL(window.location.href);
    url.searchParams.delete('demo');
    window.history.replaceState(null, '', url);
    this.observatory?.notify('LinkedIn showcase mode exited');
  }
}
