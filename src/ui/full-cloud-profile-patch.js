import { RENDERING_LIMITS } from '../config.js';
import { HighDensityControls } from './high-density-controls.js';

const originalInstall = HighDensityControls.prototype.install;
const originalUpdateVisual = HighDensityControls.prototype.updateVisual;
const originalUpdateStatus = HighDensityControls.prototype.updateStatus;

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
