import { formatNumber } from '../utils/format.js';
import { LightconeInterface } from './lightcone-interface.js';

const originalSetLayerControls = LightconeInterface.prototype.setLayerControls;
const originalUpdateTelemetry = LightconeInterface.prototype.updateTelemetry;

function shortLayerName(layer) {
  if (layer?.id === 'all-live') return '2MRS + DESI DR1';
  if (layer?.id === 'desi-dr1') return 'DESI DR1 LSS';
  if (layer?.id === '2mrs') return '2MRS';
  return layer?.label || 'Observed survey';
}

function contextRows() {
  return [...document.querySelectorAll('.what-you-see .explanation-row')];
}

LightconeInterface.prototype.setLayerControls = function dashboardSetLayerControls(meta, state, layer) {
  originalSetLayerControls.call(this, meta, state, layer);
  const [, localAnchor, footprint] = contextRows();
  const comparison = layer?.id === 'all-live' || Boolean(meta?.composite);
  if (localAnchor) localAnchor.hidden = !comparison;
  if (footprint) {
    const text = footprint.querySelector('span');
    if (text) {
      text.textContent = layer?.id === '2mrs'
        ? 'Coverage follows the 2MRS selection and all-sky survey mask.'
        : 'Separated regions follow observed DESI targeting, masks and footprint geometry.';
    }
  }
};

LightconeInterface.prototype.updateTelemetry = function dashboardUpdateTelemetry(metrics, state) {
  originalUpdateTelemetry.call(this, metrics, state);
  const layer = this.currentLayer;
  const resident = Number(metrics.gpuResidentCount || metrics.underlyingCount || this.currentMeta?.object_count || metrics.visibleCount || 0);
  const displayed = Number(metrics.drawBudget || metrics.visibleCount || 0);
  this.dom.datasetStatus.textContent = shortLayerName(layer);
  this.dom.observedRowsStatus.textContent = metrics.fullCatalogue
    ? `${formatNumber(resident)} GPU-resident rows`
    : `${formatNumber(this.currentMeta?.object_count || displayed)} source rows`;
  const origin = document.querySelector('#spatial-origin');
  if (origin) origin.textContent = 'Observer-centred Cartesian';
  const coordinateNote = document.querySelector('#spatial-coordinate-note');
  if (coordinateNote) coordinateNote.textContent = 'Axes are display coordinates derived from source RA/Dec and comoving distance.';
};
