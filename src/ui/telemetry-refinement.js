import { formatDistance, formatLookback, formatNumber } from '../utils/format.js';
import { LightconeInterface } from './lightcone-interface.js';

const originalTileStatus = LightconeInterface.prototype.setTileStreamingStatus;
const originalTelemetry = LightconeInterface.prototype.updateTelemetry;

function metricLabel(node, value) {
  node?.parentElement?.querySelector('small')?.replaceChildren(value);
}

LightconeInterface.prototype.setTileStreamingStatus = function refinedTileStatus(status = {}) {
  if (!status.fullCatalogue) return originalTileStatus.call(this, status);
  if (!['desi-dr1', 'all-live'].includes(this.currentLayer?.id)) return;
  this.tileStreamStatus = status;
  const desiRows = formatNumber(status.streamedRows || 0);
  const stack = this.currentLayer?.id === 'all-live';
  this.dom.surveyLayerNote.textContent = stack
    ? `Full comparison stack active: the 2MRS nearby anchor is rendered beside ${desiRows} DESI GPU-resident rows. Survey identities remain separate and non-deduplicated.`
    : `Full observed DESI cloud active: ${desiRows} rows are GPU-resident. Row-level inspection remains in the provenance tile view.`;
  this.dom.budgetNote.textContent = 'Display density is a deterministic GPU sample. Redshift and tracer controls change visibility only; they never alter the underlying catalogue.';
};

LightconeInterface.prototype.updateTelemetry = function refinedTelemetry(metrics, state) {
  originalTelemetry.call(this, metrics, state);
  if (!metrics?.fullCatalogue) return;
  const draw = Number(metrics.drawBudget || metrics.visibleCount || 0);
  const resident = Number(metrics.gpuResidentCount || 0);
  const stack = Boolean(metrics.compositeFullCatalogue);
  this.dom.visibleCount.textContent = formatNumber(draw);
  metricLabel(this.dom.visibleCount, 'display sample');
  this.dom.depth.textContent = formatDistance(metrics.maxDistance);
  metricLabel(this.dom.depth, 'radial extent');
  this.dom.lookback.textContent = formatLookback(metrics.maxLookback);
  metricLabel(this.dom.lookback, 'look-back at z ceiling');
  this.dom.summaryCount.textContent = `${formatNumber(resident)} GPU resident`;
  this.dom.railDetail.textContent = stack
    ? `2MRS anchor + full DESI GPU cloud · ${formatNumber(draw)} display sample · source colours retain survey identity`
    : `Full DESI GPU cloud · ${formatNumber(draw)} display sample from ${formatNumber(resident)} GPU-resident rows · shader filters only`;
};
