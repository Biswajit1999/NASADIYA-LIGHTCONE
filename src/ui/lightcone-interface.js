import {
  escapeHtml,
  formatDistance,
  formatLookback,
  formatNumber,
  formatRedshift,
  formatVelocity,
} from '../utils/format.js';

const SPATIAL_COPY = Object.freeze({
  slice: {
    title: 'A slice through the observed galaxy field.',
    description: 'Real spectroscopic survey rows inside a finite observer-centred Cartesian slab. The view makes nearby structure legible without reconstructed filaments or simulated galaxies.',
    railMode: 'Local Cartesian slice',
  },
  lightcone: {
    title: 'The observed Universe as a radial survey volume.',
    description: 'Measured source rows are placed in an observer-centred radial volume. Distance increases outward through the active survey layer.',
    railMode: 'Observer lightcone',
  },
});
const COLOUR_COPY = Object.freeze({
  catalog: 'Observed positions',
  time: 'Colour mapped by look-back time',
  uncertainty: 'Marker scale mapped by redshift uncertainty',
});

function copyForSurvey(meta) {
  const photo = meta.measurement_kind === 'photometric';
  const survey = meta.source_survey || 'active survey';
  return {
    photo,
    intro: photo
      ? `The full ${survey} tile store contains observed photometric-redshift rows. This browser view begins with a deterministic set of real source rows while preserving the layer’s total count and radial uncertainty.`
      : `Real ${survey} rows are shown as an observer-centred survey volume. Drag to orbit, scroll to move closer, and select a point for its source record.`,
    redshift: photo
      ? `${survey} uses photometric redshifts. Radial placement is a navigation convention; each accepted row retains its supplied photo-z uncertainty.`
      : `${survey} uses measured spectroscopic redshifts. Radial placement is a cosmological visual-navigation convention.`,
    footprint: photo
      ? `${survey} has a survey footprint, masking, and photo-z uncertainty. These are measurement properties, not empty physical regions.`
      : `${survey} has target selection and sky coverage limits. Gaps in the view are survey-selection effects, not physical empty space.`,
    empty: photo
      ? `<p class="empty-state">Select a rendered ${escapeHtml(survey)} overview row to open its photometric-redshift source record.</p>`
      : `<p class="empty-state">Select a measured ${escapeHtml(survey)} point to open its source record.</p>`,
  };
}

export class LightconeInterface {
  constructor() {
    this.currentMeta = null;
    this.currentLayer = null;
    this.dom = {
      datasetStatus: document.querySelector('#dataset-status'), datasetDot: document.querySelector('#dataset-dot'), surveyModeStatus: document.querySelector('#survey-mode-status'),
      sceneEyebrow: document.querySelector('#scene-eyebrow'), sceneTitle: document.querySelector('#scene-title'), sceneDescription: document.querySelector('#scene-description'), openingCount: document.querySelector('#opening-count'),
      controlToggle: document.querySelector('#control-toggle'), controlDrawer: document.querySelector('#control-drawer'), closeControls: document.querySelector('#close-controls'),
      surveyLayer: document.querySelector('#survey-layer'), surveyLayerStatus: document.querySelector('#survey-layer-status'), surveyLayerNote: document.querySelector('#survey-layer-note'),
      maxRedshift: document.querySelector('#max-redshift'), maxRedshiftOutput: document.querySelector('#max-redshift-output'), redshiftNote: document.querySelector('#redshift-note'),
      sliceThickness: document.querySelector('#slice-thickness'), sliceThicknessOutput: document.querySelector('#slice-thickness-output'), sliceOffset: document.querySelector('#slice-offset'), sliceOffsetOutput: document.querySelector('#slice-offset-output'), sliceControls: document.querySelector('#slice-controls'),
      pointBudget: document.querySelector('#point-budget'), pointBudgetOutput: document.querySelector('#point-budget-output'), budgetNote: document.querySelector('#budget-note'), footprintNote: document.querySelector('#footprint-note'),
      galaxies: document.querySelector('#toggle-galaxies'), reset: document.querySelector('#reset-view'), focusLocal: document.querySelector('#focus-local'),
      visibleCount: document.querySelector('#visible-count'), depth: document.querySelector('#depth-readout'), lookback: document.querySelector('#lookback-readout'), railMode: document.querySelector('#rail-mode'), railDetail: document.querySelector('#rail-detail'),
      sourceLink: document.querySelector('#source-link'), cornerNote: document.querySelector('#corner-note'), objectInspector: document.querySelector('#object-inspector'), closeInspector: document.querySelector('#close-inspector'), inspector: document.querySelector('#inspector-content'),
      viewButtons: [...document.querySelectorAll('[data-spatial-mode]')], modeButtons: [...document.querySelectorAll('[data-view-mode]')],
      helpButton: document.querySelector('#help-button'), helpModal: document.querySelector('#help-modal'), closeHelp: document.querySelector('#close-help'),
      loadingScreen: document.querySelector('#loading-screen'), loadingTitle: document.querySelector('#loading-title'), loadingCopy: document.querySelector('#loading-copy'), loadingMeterBar: document.querySelector('#loading-meter-bar'), loadingDataset: document.querySelector('#loading-dataset'), loadingCount: document.querySelector('#loading-count'),
    };
  }

  setLoadingState({ title, copy, dataset, count, progress = 18 } = {}) {
    this.dom.loadingScreen.classList.remove('is-hidden');
    if (title) this.dom.loadingTitle.textContent = title;
    if (copy) this.dom.loadingCopy.textContent = copy;
    if (dataset) this.dom.loadingDataset.textContent = dataset;
    if (count) this.dom.loadingCount.textContent = count;
    this.dom.loadingMeterBar.style.width = `${progress}%`;
  }
  hideLoading() { this.dom.loadingMeterBar.style.width = '100%'; window.setTimeout(() => this.dom.loadingScreen.classList.add('is-hidden'), 280); }
  updateSpatialCopy(mode) {
    const copy = SPATIAL_COPY[mode] || SPATIAL_COPY.slice;
    this.dom.sceneTitle.textContent = copy.title; this.dom.sceneDescription.textContent = copy.description; this.dom.railMode.textContent = copy.railMode; this.dom.sliceControls.hidden = mode !== 'slice';
  }

  setLayerControls(meta, state, layer) {
    const copy = copyForSurvey(meta);
    this.currentMeta = meta; this.currentLayer = layer;
    this.dom.surveyLayer.value = layer.id;
    this.dom.surveyLayerStatus.textContent = copy.photo ? 'photo-z' : 'spectroscopic';
    this.dom.surveyLayerNote.textContent = meta.overview_count
      ? `${formatNumber(meta.object_count)} observed rows; ${formatNumber(meta.overview_count)} real rows in the local browser overview. Full source tiles remain outside Git history.`
      : `${formatNumber(meta.object_count)} observed rows are loaded from the browser catalogue.`;
    this.dom.sceneEyebrow.textContent = layer.eyebrow;
    this.dom.sceneDescription.textContent = copy.intro;
    this.dom.redshiftNote.textContent = copy.redshift;
    this.dom.footprintNote.textContent = copy.footprint;
    this.dom.datasetStatus.textContent = meta.dataset_label || layer.label;
    this.dom.surveyModeStatus.textContent = copy.photo ? 'photo-z uncertainty retained' : 'measured redshifts';
    this.dom.sourceLink.textContent = `${meta.source_survey || layer.id} source record ↗`;
    this.dom.sourceLink.href = 'docs/sources.md';
    this.dom.cornerNote.textContent = `${meta.source_survey || layer.id} · ${meta.source_release || 'source provenance in record'} · ${copy.photo ? 'photometric redshift with radial uncertainty' : 'spectroscopic survey placement'}`;
    this.dom.focusLocal.disabled = !layer.supportsSlice;
    this.dom.focusLocal.textContent = layer.supportsSlice ? 'Return to local slice' : 'Observer lightcone only';
    this.dom.viewButtons.forEach((button) => { button.disabled = button.dataset.spatialMode === 'slice' && !layer.supportsSlice; });
    if (!layer.supportsSlice && state.spatialMode === 'slice') state.spatialMode = 'lightcone';
    this.dom.inspector.innerHTML = copy.empty;
  }

  syncControlsFromState(state) {
    this.dom.maxRedshift.value = String(state.maxRedshift); this.dom.maxRedshiftOutput.textContent = Number(state.maxRedshift).toFixed(4);
    this.dom.sliceThickness.value = String(state.sliceThickness); this.dom.sliceThicknessOutput.textContent = `${Math.round(Number(state.sliceThickness))} Mpc`;
    this.dom.sliceOffset.value = String(state.sliceOffset); this.dom.sliceOffsetOutput.textContent = `${Math.round(Number(state.sliceOffset))} Mpc`;
    this.dom.pointBudget.value = String(state.pointBudget); this.dom.pointBudgetOutput.textContent = formatNumber(state.pointBudget); this.dom.galaxies.checked = state.showGalaxies;
    this.dom.viewButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.spatialMode === state.spatialMode));
    this.dom.modeButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.viewMode === state.viewMode));
    this.updateSpatialCopy(state.spatialMode);
  }

  bind({ getState, onStateChange, onSpatialModeChange, onReset, onFocusLocal, onCloseSelection, onLayerChange }) {
    [this.dom.surveyLayer, this.dom.maxRedshift, this.dom.sliceThickness, this.dom.sliceOffset, this.dom.pointBudget, this.dom.galaxies, this.dom.focusLocal, ...this.dom.viewButtons, ...this.dom.modeButtons].forEach((item) => { item.disabled = false; });
    const drawerOpen = (open) => { this.dom.controlDrawer.hidden = !open; this.dom.controlToggle.setAttribute('aria-expanded', String(open)); };
    this.dom.controlToggle.addEventListener('click', () => drawerOpen(this.dom.controlDrawer.hidden)); this.dom.closeControls.addEventListener('click', () => drawerOpen(false));
    const emit = () => { const state = getState(); state.maxRedshift = Number(this.dom.maxRedshift.value); state.sliceThickness = Number(this.dom.sliceThickness.value); state.sliceOffset = Number(this.dom.sliceOffset.value); state.pointBudget = Number(this.dom.pointBudget.value); state.showGalaxies = this.dom.galaxies.checked; this.syncControlsFromState(state); onStateChange(state); };
    [this.dom.maxRedshift, this.dom.sliceThickness, this.dom.sliceOffset, this.dom.pointBudget, this.dom.galaxies].forEach((item) => item.addEventListener('input', emit));
    this.dom.surveyLayer.addEventListener('change', () => onLayerChange(this.dom.surveyLayer.value));
    this.dom.viewButtons.forEach((button) => button.addEventListener('click', () => { if (button.disabled) return; const state = getState(); state.spatialMode = button.dataset.spatialMode; this.syncControlsFromState(state); onStateChange(state); onSpatialModeChange(state.spatialMode); }));
    this.dom.modeButtons.forEach((button) => button.addEventListener('click', () => { const state = getState(); state.viewMode = button.dataset.viewMode; this.syncControlsFromState(state); onStateChange(state); }));
    this.dom.reset.addEventListener('click', () => { onReset(); this.dom.objectInspector.hidden = true; });
    this.dom.focusLocal.addEventListener('click', () => { if (this.dom.focusLocal.disabled) return; const state = getState(); state.spatialMode = 'slice'; state.sliceThickness = 24; state.sliceOffset = 0; state.maxRedshift = Math.min(0.025, Number(this.dom.maxRedshift.max)); this.syncControlsFromState(state); onStateChange(state); onFocusLocal(); });
    this.dom.closeInspector.addEventListener('click', () => { this.dom.objectInspector.hidden = true; onCloseSelection(); });
    const setHelp = (isOpen) => { this.dom.helpModal.hidden = !isOpen; if (isOpen) this.dom.closeHelp.focus(); };
    this.dom.helpButton.addEventListener('click', () => setHelp(true)); this.dom.closeHelp.addEventListener('click', () => setHelp(false)); this.dom.helpModal.addEventListener('click', (event) => { if (event.target === this.dom.helpModal) setHelp(false); });
    window.addEventListener('keydown', (event) => { if (event.key === 'Escape') { setHelp(false); drawerOpen(false); } });
  }

  setDataReady(meta, maxRedshift, state, layer) {
    const count = formatNumber(meta.object_count); const photo = meta.measurement_kind === 'photometric';
    this.setLayerControls(meta, state, layer); this.dom.datasetDot.classList.remove('status-dot--pending');
    this.dom.openingCount.textContent = meta.overview_count
      ? `${meta.source_survey} · ${count} observed ${photo ? 'photo-z ' : ''}rows · ${formatNumber(meta.overview_count)} real rows in this overview`
      : `${meta.source_survey} · ${count} observed rows`;
    this.dom.maxRedshift.max = Math.max(0.02, Math.ceil(maxRedshift * 10000) / 10000).toFixed(4);
    this.dom.pointBudget.max = String(Math.max(50_000, Number(meta.overview_count || meta.object_count || 50_000)));
    this.syncControlsFromState(state);
    this.setLoadingState({ title: photo ? 'The wide photometric Universe is ready' : 'The observed survey volume is ready', copy: photo ? 'Real photometric-redshift rows are displayed in an observer-centred lightcone with their published radial uncertainty retained.' : 'Real measured spectroscopic rows are now arranged in an observer-centred spatial view.', dataset: meta.dataset_label || layer.label, count: meta.overview_count ? `${count} source rows · ${formatNumber(meta.overview_count)} overview rows` : `${count} observed rows`, progress: 100 });
    this.hideLoading();
  }

  showLayerUnavailable(layer, previousLayer) {
    this.dom.surveyLayer.value = previousLayer.id;
    this.dom.surveyLayerNote.textContent = `${layer.label} is not installed in this deployment. Local build: ${layer.localBuild}`;
    this.dom.inspector.innerHTML = `<div class="object-tag object-tag--warning">LAYER NOT INSTALLED</div><h2>${escapeHtml(layer.label)}</h2><p class="empty-state">The code supports this survey layer, but its real source rows are not bundled with Git. Build the local tile store and serve this project directory again.</p><p class="empty-state"><code>${escapeHtml(layer.localBuild)}</code></p>`;
    this.dom.objectInspector.hidden = false;
  }
  updateTelemetry(metrics, state) {
    this.dom.visibleCount.textContent = formatNumber(metrics.visibleCount); this.dom.depth.textContent = formatDistance(metrics.maxDistance); this.dom.lookback.textContent = formatLookback(metrics.maxLookback);
    this.dom.railDetail.textContent = state.spatialMode === 'slice'
      ? `${Math.round(state.sliceThickness)} Mpc thickness · Cartesian Z = ${Math.round(state.sliceOffset)} Mpc · ${COLOUR_COPY[state.viewMode]}`
      : (this.currentMeta?.measurement_kind === 'photometric' ? `z ≤ ${Number(state.maxRedshift).toFixed(4)} · photo-z radial uncertainty retained` : `z ≤ ${Number(state.maxRedshift).toFixed(4)} · ${COLOUR_COPY[state.viewMode]}`);
  }
  inspect(object) {
    this.dom.objectInspector.hidden = false;
    const photo = object.measurement_kind === 'photometric'; const magnitude = Number(object.magnitude ?? object.ks_mag); const uncertainty = Number(object.redshift_error); const hasCz = Number.isFinite(Number(object.cz_km_s));
    const positional = `<div><dt>RA</dt><dd>${Number.isFinite(Number(object.ra_deg)) ? `${Number(object.ra_deg).toFixed(4)}°` : '—'}</dd></div><div><dt>Dec</dt><dd>${Number.isFinite(Number(object.dec_deg)) ? `${Number(object.dec_deg).toFixed(4)}°` : '—'}</dd></div>`;
    const values = photo
      ? `<div><dt>Photometric z</dt><dd>${formatRedshift(object.redshift)}</dd></div><div><dt>Photo-z uncertainty</dt><dd>±${formatRedshift(uncertainty)}</dd></div><div><dt>Comoving placement</dt><dd>${formatDistance(object.comoving_distance_mpc)}</dd></div><div><dt>Look-back placement</dt><dd>${formatLookback(object.lookback_time_gyr)}</dd></div>${positional}<div><dt>Magnitude</dt><dd>${Number.isFinite(magnitude) ? magnitude.toFixed(3) : '—'}</dd></div><div><dt>Placement note</dt><dd>not exact radial distance</dd></div>`
      : `<div><dt>${hasCz ? 'cz' : 'Spectroscopic z'}</dt><dd>${hasCz ? formatVelocity(object.cz_km_s) : formatRedshift(object.redshift)}</dd></div><div><dt>Comoving distance</dt><dd>${formatDistance(object.comoving_distance_mpc)}</dd></div><div><dt>Look-back time</dt><dd>${formatLookback(object.lookback_time_gyr)}</dd></div>${positional}<div><dt>Magnitude</dt><dd>${Number.isFinite(magnitude) ? magnitude.toFixed(3) : '—'}</dd></div>`;
    this.dom.inspector.innerHTML = `<div class="object-tag">OBSERVED / ${photo ? 'PHOTOMETRIC' : 'SPECTROSCOPIC'}</div><h2>${escapeHtml(object.name || object.object_id)}</h2><p class="object-type">${escapeHtml(object.source_survey)} · ${escapeHtml(object.source_table)} · ${escapeHtml(object.object_id)}</p><dl class="object-metrics">${values}</dl><div class="provenance-block"><span>PROVENANCE</span><strong>${escapeHtml(object.source_release)}</strong><p>${escapeHtml(object.source_url)}</p><p>${escapeHtml(object.distance_note)}</p></div>`;
  }
  showLoadError(message) { this.dom.openingCount.textContent = 'Observed layer unavailable'; this.setLoadingState({ title: 'Observed layer unavailable', copy: message, dataset: 'Survey browser', count: 'Check the local data pipeline, then refresh', progress: 100 }); }
}
