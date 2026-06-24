import { RENDERING_LIMITS } from '../config.js';
import { HighDensityControls } from './high-density-controls.js';
import { LightconeInterface } from './lightcone-interface.js';

const originalInstall = HighDensityControls.prototype.install;
const originalUpdateVisual = HighDensityControls.prototype.updateVisual;
const originalUpdateStatus = HighDensityControls.prototype.updateStatus;
const originalTileStatus = LightconeInterface.prototype.setTileStreamingStatus;
const originalTelemetry = LightconeInterface.prototype.updateTelemetry;

function compact(value) {
  const number = Number(value) || 0;
  return number >= 1_000_000 ? `${(number / 1_000_000).toFixed(number % 1_000_000 ? 2 : 0)}M` : `${Math.round(number / 1_000)}K`;
}

HighDensityControls.prototype.install = function installFullProfile() {
  originalInstall.call(this);
  if (this.fullProfileInstalled || !this.profile) return;
  this.fullProfileInstalled = true;
  this.fullCatalogue = { available: false, active: false, recordCount: 0 };
  this.fullButton = this.buttons.find((button) => Number(button.dataset.densityRows) > RENDERING_LIMITS.highDensityRows);
  if (!this.fullButton) return;
  this.fullButton.disabled = true;
  this.fullButton.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!this.fullCatalogue.available && !this.fullCatalogue.active) return;
    window.dispatchEvent(new CustomEvent('nasadiya:full-catalogue-request'));
  }, true);
};

HighDensityControls.prototype.setFullCatalogueStatus = function setFullCatalogueStatus(status = {}) {
  this.fullCatalogue = { available: false, active: false, recordCount: 0, ...status };
  if (this.fullButton) {
    this.fullButton.disabled = !this.fullCatalogue.available && !this.fullCatalogue.active;
    this.fullButton.title = this.fullCatalogue.available
      ? `Load all ${compact(this.fullCatalogue.recordCount)} observed DESI rows from the GPU cloud.`
      : (this.fullCatalogue.reason || 'Build the local full DESI GPU cloud first.');
  }
  this.updateVisual(this.input?.value);
  this.updateStatus();
};

HighDensityControls.prototype.updateVisual = function updateFullProfile(value) {
  originalUpdateVisual.call(this, value);
  if (!this.fullButton || !this.fullCatalogue?.active) return;
  this.fullButton.classList.add('is-active');
  this.fullButton.setAttribute('aria-pressed', 'true');
  if (this.readout) this.readout.textContent = `${compact(this.fullCatalogue.recordCount)} FULL`;
};

HighDensityControls.prototype.updateStatus = function updateFullProfileStatus() {
  if (this.status && this.profile && !this.profile.hidden && this.fullCatalogue?.active) {
    this.status.textContent = `Full GPU cloud active: ${compact(this.fullCatalogue.recordCount)} real observed rows. Point inspection remains tile-based.`;
    return;
  }
  if (this.status && this.profile && !this.profile.hidden && this.fullCatalogue?.available) {
    this.status.textContent = `Full ${compact(this.fullCatalogue.recordCount)} GPU cloud ready. Select Full DESI to draw every observed row.`;
    return;
  }
  originalUpdateStatus.call(this);
};

LightconeInterface.prototype.setTileStreamingStatus = function setFullCloudStatus(status = {}) {
  if (!status.fullCatalogue) {
    originalTileStatus.call(this, status);
    return;
  }
  if (!['desi-dr1', 'all-live'].includes(this.currentLayer?.id)) return;
  this.tileStreamStatus = status;
  const total = compact(status.streamedRows || 0);
  this.dom.surveyLayerNote.textContent = `Full observed-row GPU cloud is active: ${total} DESI source rows are resident in GPU buffers. Row-level provenance and point inspection remain available through the separate tile store.`;
  this.dom.budgetNote.textContent = `Full-cloud mode draws every accepted DESI row from one packed binary. It does not remove survey footprint, targeting, mask, or selection effects.`;
};

LightconeInterface.prototype.updateTelemetry = function updateFullCloudTelemetry(metrics, state) {
  originalTelemetry.call(this, metrics, state);
  if (!metrics?.fullCatalogue) return;
  const total = compact(metrics.visibleCount);
  this.dom.visibleCount.textContent = `${total} GPU`;
  this.dom.summaryCount.textContent = `${total} full cloud`;
  this.dom.railDetail.textContent = `Full observed DESI GPU cloud · z ≤ ${Number(state.maxRedshift).toFixed(4)} · GPU filters change visibility without changing source rows`;
};
