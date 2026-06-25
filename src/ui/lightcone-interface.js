import {
  escapeHtml,
  formatDistance,
  formatLookback,
  formatNumber,
  formatRedshift,
  formatVelocity,
} from '../utils/format.js';
import { SURVEY_LAYERS } from '../config.js';

const TRACERS = ['BGS', 'LRG', 'ELG', 'QSO'];
const TRACER_LABELS = Object.freeze({
  BGS: 'Bright Galaxy Sample',
  LRG: 'Luminous Red Galaxies',
  ELG: 'Emission Line Galaxies',
  QSO: 'Quasars',
});

const COLOUR_COPY = Object.freeze({
  catalog: 'Observed row colour',
  tracer: 'Tracer class colour',
  time: 'Look-back colour scale',
  uncertainty: 'Uncertainty display',
  survey: 'Source survey colour',
});

function isDesiLayer(layer) { return ['desi-dr1', 'all-live'].includes(layer?.id); }
function compact(value) { const n = Number(value) || 0; return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(n % 1_000_000 ? 2 : 0)}M` : n >= 1_000 ? `${Math.round(n / 1_000)}K` : String(Math.round(n)); }
function noteFor(meta, layer) {
  if (layer?.id === 'all-live' || meta?.composite) return '2MRS and DESI remain separate survey layers in this non-deduplicated comparison stack.';
  if (layer?.id === 'desi-dr1') return 'North and South regions follow DESI survey footprint, target selection, masks and completeness cuts.';
  return 'Survey coverage, target selection and source provenance remain part of the visual context.';
}

export class LightconeInterface {
  constructor() {
    this.currentMeta = null; this.currentLayer = null; this.currentMetrics = null; this.tileStreamStatus = null;
    this.fullCloud = { available: false, active: false, recordCount: 0 };
    this.dom = {
      datasetStatus: document.querySelector('#dataset-status'), observedRowsStatus: document.querySelector('#observed-rows-status'), headerDepthStatus: document.querySelector('#header-depth-status'), headerLookbackStatus: document.querySelector('#header-lookback-status'), surveyModeStatus: document.querySelector('#survey-mode-status'),
      sceneEyebrow: document.querySelector('#scene-eyebrow'), sceneTitle: document.querySelector('#scene-title'), sceneDescription: document.querySelector('#scene-description'), leftSurveyName: document.querySelector('#left-survey-name'), leftRowCount: document.querySelector('#left-row-count'), leftDepth: document.querySelector('#left-depth'), leftLookback: document.querySelector('#left-lookback'), leftRedshift: document.querySelector('#left-redshift'), leftCoverage: document.querySelector('#left-coverage'), sourceLink: document.querySelector('#source-link'),
      controlToggle: document.querySelector('#control-toggle'), controlDrawer: document.querySelector('#control-drawer'), closeControls: document.querySelector('#close-controls'), surveyLayer: document.querySelector('#survey-layer'), surveyLayerStatus: document.querySelector('#survey-layer-status'), surveyLayerNote: document.querySelector('#survey-layer-note'),
      pointBudget: document.querySelector('#point-budget'), pointBudgetOutput: document.querySelector('#point-budget-output'), densityReadout: document.querySelector('#density-readout'), densityProfiles: [...document.querySelectorAll('[data-density-rows]')], budgetNote: document.querySelector('#budget-note'),
      maxRedshift: document.querySelector('#max-redshift'), maxRedshiftOutput: document.querySelector('#max-redshift-output'), redshiftNote: document.querySelector('#redshift-note'), sliceControls: document.querySelector('#slice-controls'), sliceThickness: document.querySelector('#slice-thickness'), sliceThicknessOutput: document.querySelector('#slice-thickness-output'), sliceOffset: document.querySelector('#slice-offset'), sliceOffsetOutput: document.querySelector('#slice-offset-output'),
      tracerSection: document.querySelector('#desi-tracer-section'), tracerInputs: [...document.querySelectorAll('[data-desi-tracer]')], tracerCounts: [...document.querySelectorAll('[data-tracer-count]')], selectAllTracers: document.querySelector('#select-all-tracers'), modeButtons: [...document.querySelectorAll('[data-view-mode]')],
      galaxies: document.querySelector('#toggle-galaxies'), reference: document.querySelector('#toggle-reference'), legend: document.querySelector('#toggle-legend'), reset: document.querySelector('#reset-view'), focusLocal: document.querySelector('#focus-local'),
      tourToggle: document.querySelector('#tour-toggle'), viewportView: document.querySelector('#viewport-view-select'), viewportHelp: document.querySelector('#viewport-help'), viewportTools: [...document.querySelectorAll('[data-viewport-tool]')], fullscreenToggle: document.querySelector('#fullscreen-toggle'), referenceCardToggle: document.querySelector('#toggle-reference-card'), spatialAnnotation: document.querySelector('#spatial-annotation'), spatialCard: document.querySelector('.spatial-card'), legendCard: document.querySelector('.legend-card'), spatialRedshift: document.querySelector('#spatial-redshift'), spatialDepth: document.querySelector('#spatial-depth'), spatialLookback: document.querySelector('#spatial-lookback'), radialTicks: [...document.querySelectorAll('[data-radial-tick]')],
      visibleCount: document.querySelector('#visible-count'), gpuCount: document.querySelector('#gpu-count'), depth: document.querySelector('#depth-readout'), lookback: document.querySelector('#lookback-readout'), redshiftReadout: document.querySelector('#redshift-readout'), coverageReadout: document.querySelector('#coverage-readout'), coverageNote: document.querySelector('#coverage-note'), displayCountNote: document.querySelector('#display-count-note'), gpuCountNote: document.querySelector('#gpu-count-note'), systemStatus: document.querySelector('#system-status'), footerDataSource: document.querySelector('#footer-data-source'),
      objectInspector: document.querySelector('#object-inspector'), closeInspector: document.querySelector('#close-inspector'), inspector: document.querySelector('#inspector-content'), railButtons: [...document.querySelectorAll('[data-rail-section]')], helpButton: document.querySelector('#help-button'), helpModal: document.querySelector('#help-modal'), closeHelp: document.querySelector('#close-help'), loadingScreen: document.querySelector('#loading-screen'), loadingTitle: document.querySelector('#loading-title'), loadingCopy: document.querySelector('#loading-copy'), loadingMeterBar: document.querySelector('#loading-meter-bar'), loadingDataset: document.querySelector('#loading-dataset'), loadingCount: document.querySelector('#loading-count'),
    };
    this.installSurveyOptions();
  }

  installSurveyOptions() {
    [...this.dom.surveyLayer.options].forEach((option) => {
      const layer = SURVEY_LAYERS[option.value];
      if (!layer) return;
      option.disabled = layer.installed === false;
      if (layer.installed === false && !option.textContent.includes('PENDING')) option.textContent = `${option.textContent} — PENDING SOURCE VALIDATION`;
    });
  }

  drawerOpen(open) {
    this.dom.controlDrawer.hidden = !open;
    document.body.classList.toggle('lens-open', open);
    this.dom.controlToggle.setAttribute('aria-expanded', String(open));
    this.dom.controlToggle.classList.toggle('is-active', open);
  }

  setLoadingState({ title, copy, dataset, count, progress = 18 } = {}) {
    this.dom.loadingScreen.classList.remove('is-hidden');
    if (title) this.dom.loadingTitle.textContent = title;
    if (copy) this.dom.loadingCopy.textContent = copy;
    if (dataset) this.dom.loadingDataset.textContent = dataset;
    if (count) this.dom.loadingCount.textContent = count;
    this.dom.loadingMeterBar.style.width = `${progress}%`;
  }

  hideLoading() { this.dom.loadingMeterBar.style.width = '100%'; window.setTimeout(() => this.dom.loadingScreen.classList.add('is-hidden'), 320); }

  setTourStatus({ active = false, phase = 'overview', progress = 0, reason = null } = {}) {
    this.dom.tourToggle.classList.toggle('is-active', active);
    this.dom.tourToggle.setAttribute('aria-pressed', String(active));
    const label = this.dom.tourToggle.querySelector('span:last-child');
    if (label) label.textContent = active ? `${phase} ${Math.round(progress * 100)}%` : 'Flythrough';
    this.dom.tourToggle.title = active ? 'Stop guided flythrough. Any manual interaction restores navigation.' : (reason === 'manual' ? 'Manual navigation restored. Start a new guided flythrough.' : 'Start a guided route through the observed survey footprint.');
  }

  setFullCloudStatus(status = {}) {
    this.fullCloud = { available: false, active: false, recordCount: 0, ...status };
    const fullButton = this.dom.densityProfiles.find((button) => Number(button.dataset.densityRows) > 1_000_000);
    if (fullButton) { fullButton.disabled = !this.fullCloud.available && !this.fullCloud.active; fullButton.title = this.fullCloud.available ? `Load all ${formatNumber(this.fullCloud.recordCount)} DESI rows into the GPU cloud.` : (this.fullCloud.reason || 'The full cloud is not available in this deployment.'); }
  }

  setLayerControls(meta, state, layer) {
    this.currentMeta = meta; this.currentLayer = layer;
    const composite = Boolean(meta.composite || layer?.id === 'all-live');
    const sourceName = meta.source_survey || layer?.label || 'Observed survey';
    this.dom.surveyLayer.value = layer.id;
    this.dom.surveyLayerStatus.textContent = composite ? 'comparison' : meta.measurement_kind === 'photometric' ? 'photo-z' : 'spectroscopic';
    this.dom.surveyLayerNote.textContent = meta.overview_count ? `${formatNumber(meta.object_count)} observed source rows; ${formatNumber(meta.overview_count)} rows in the initial browser view. ${noteFor(meta, layer)}` : `${formatNumber(meta.object_count)} observed source rows. ${noteFor(meta, layer)}`;
    this.dom.sceneEyebrow.textContent = layer.eyebrow || sourceName.toUpperCase();
    this.dom.sceneTitle.textContent = composite ? 'A nearby anchor and deep spectroscopic field.' : layer.id === 'desi-dr1' ? 'DESI DR1 spectroscopic lightcone.' : 'The nearby observed Universe.';
    this.dom.sceneDescription.textContent = composite ? '2MRS and DESI DR1 are shown together for survey comparison. Source layers remain separate and are not cross-matched or completeness-corrected.' : layer.id === 'desi-dr1' ? 'The North and South DESI regions reflect observed footprint, targeting and masks. They are not a fabricated all-sky cosmic web.' : 'A finite display of measured nearby spectroscopic rows. Use the viewport to orbit, zoom, pan and inspect source records.';
    this.dom.surveyModeStatus.textContent = composite ? 'comparison stack' : meta.measurement_kind === 'photometric' ? 'photometric' : 'spectroscopic';
    this.dom.leftSurveyName.textContent = sourceName;
    this.dom.leftRowCount.textContent = formatNumber(meta.object_count);
    this.dom.leftCoverage.textContent = composite ? '2MRS + DESI' : layer.id === 'desi-dr1' ? '~14,000 deg²' : 'survey-defined';
    this.dom.sourceLink.href = 'docs/sources.md'; this.dom.footerDataSource.textContent = sourceName;
    this.dom.maxRedshift.max = Math.max(0.02, Math.ceil(Number(meta.max_redshift || state.maxRedshift || 0.025) * 10000) / 10000).toFixed(4);
    this.dom.sliceControls.hidden = !layer.supportsSlice;
    if (!layer.supportsSlice && state.spatialMode === 'slice') state.spatialMode = 'lightcone';
    this.dom.viewportView.value = state.spatialMode === 'slice' ? 'slice' : 'observer';
    this.dom.focusLocal.disabled = !layer.supportsSlice; this.dom.focusLocal.textContent = layer.supportsSlice ? 'Return to local field' : 'Observer lightcone only';
    this.setTracerControls(meta, state, layer);
  }

  setTracerControls(meta, state, layer) {
    const available = isDesiLayer(layer) && Object.keys(meta.tracer_counts || {}).length > 0;
    this.dom.tracerSection.hidden = !available;
    this.dom.tracerInputs.forEach((input) => { input.disabled = !available; input.checked = state.tracerFilters?.[input.value] !== false; });
    this.dom.tracerCounts.forEach((node) => { node.textContent = available ? formatNumber(meta.tracer_counts?.[node.dataset.tracerCount] || 0) : '—'; });
    this.dom.modeButtons.forEach((button) => {
      const needsDesi = button.dataset.viewMode === 'tracer'; const needsComposite = button.dataset.viewMode === 'survey';
      button.disabled = (needsDesi && !available) || (needsComposite && !meta.composite);
      if (button.disabled && state.viewMode === button.dataset.viewMode) state.viewMode = 'catalog';
    });
  }

  syncControlsFromState(state) {
    this.dom.maxRedshift.value = String(state.maxRedshift); this.dom.maxRedshiftOutput.textContent = Number(state.maxRedshift).toFixed(4);
    this.dom.sliceThickness.value = String(state.sliceThickness); this.dom.sliceThicknessOutput.textContent = `${Math.round(state.sliceThickness)} Mpc`;
    this.dom.sliceOffset.value = String(state.sliceOffset); this.dom.sliceOffsetOutput.textContent = `${Math.round(state.sliceOffset)} Mpc`;
    const maximum = this.fullCloud.active ? this.fullCloud.recordCount : Math.max(125_000, Number(this.currentMeta?.overview_count || this.currentMeta?.object_count || 125_000));
    this.dom.pointBudget.max = String(maximum); state.pointBudget = Math.min(maximum, Math.max(1_000, Number(state.pointBudget) || 1_000));
    this.dom.pointBudget.value = String(state.pointBudget); this.dom.pointBudgetOutput.textContent = formatNumber(state.pointBudget);
    this.dom.densityReadout.textContent = this.fullCloud.active ? `${compact(state.pointBudget)} / ${compact(this.fullCloud.recordCount)} GPU` : `${compact(state.pointBudget)} displayed`;
    this.dom.densityProfiles.forEach((button) => { const target = Number(button.dataset.densityRows); const active = target === state.pointBudget || (target > 1_000_000 && this.fullCloud.active && state.pointBudget === this.fullCloud.recordCount); button.classList.toggle('is-active', active); button.setAttribute('aria-pressed', String(active)); });
    this.dom.galaxies.checked = state.showGalaxies; this.dom.tracerInputs.forEach((input) => { input.checked = state.tracerFilters?.[input.value] !== false; }); this.dom.modeButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.viewMode === state.viewMode)); this.dom.viewportView.value = state.spatialMode === 'slice' ? 'slice' : 'observer';
  }

  bind({ getState, onStateChange, onSpatialModeChange, onReset, onFocusLocal, onCloseSelection, onLayerChange, onReferenceChange, onLegendChange, onTourToggle, onViewportTool, onFullscreen }) {
    [this.dom.surveyLayer, this.dom.maxRedshift, this.dom.sliceThickness, this.dom.sliceOffset, this.dom.pointBudget, this.dom.galaxies, this.dom.focusLocal, this.dom.reference, this.dom.legend, ...this.dom.modeButtons].forEach((item) => { if (item) item.disabled = false; });
    this.drawerOpen(window.innerWidth >= 1180);
    const emit = () => { const state = getState(); state.maxRedshift = Number(this.dom.maxRedshift.value); state.sliceThickness = Number(this.dom.sliceThickness.value); state.sliceOffset = Number(this.dom.sliceOffset.value); state.pointBudget = Number(this.dom.pointBudget.value); state.showGalaxies = this.dom.galaxies.checked; this.syncControlsFromState(state); onStateChange(state); };
    this.dom.controlToggle.addEventListener('click', () => this.drawerOpen(this.dom.controlDrawer.hidden)); this.dom.closeControls.addEventListener('click', () => this.drawerOpen(false));
    [this.dom.maxRedshift, this.dom.sliceThickness, this.dom.sliceOffset, this.dom.pointBudget, this.dom.galaxies].forEach((item) => item.addEventListener('input', emit));
    this.dom.densityProfiles.forEach((button) => button.addEventListener('click', () => { const requested = Number(button.dataset.densityRows); if (requested > 1_000_000 && !this.fullCloud.active) { if (this.fullCloud.available) window.dispatchEvent(new CustomEvent('nasadiya:full-catalogue-request')); return; } const state = getState(); state.pointBudget = Math.min(requested, this.fullCloud.active ? this.fullCloud.recordCount : Number(this.dom.pointBudget.max)); this.syncControlsFromState(state); onStateChange(state); }));
    this.dom.tracerInputs.forEach((input) => input.addEventListener('change', () => { const state = getState(); state.tracerFilters[input.value] = input.checked; this.syncControlsFromState(state); onStateChange(state); }));
    this.dom.selectAllTracers.addEventListener('click', () => { const state = getState(); TRACERS.forEach((tracer) => { state.tracerFilters[tracer] = true; }); this.syncControlsFromState(state); onStateChange(state); });
    this.dom.modeButtons.forEach((button) => button.addEventListener('click', () => { if (button.disabled) return; const state = getState(); state.viewMode = button.dataset.viewMode; this.syncControlsFromState(state); onStateChange(state); }));
    this.dom.surveyLayer.addEventListener('change', () => onLayerChange(this.dom.surveyLayer.value));
    this.dom.viewportView.addEventListener('change', () => { const state = getState(); state.spatialMode = this.dom.viewportView.value === 'slice' ? 'slice' : 'lightcone'; this.syncControlsFromState(state); onStateChange(state); onSpatialModeChange(state.spatialMode); });
    this.dom.reference.addEventListener('change', () => onReferenceChange?.(this.dom.reference.checked)); this.dom.legend.addEventListener('change', () => onLegendChange?.(this.dom.legend.checked)); this.dom.referenceCardToggle.addEventListener('click', () => { this.dom.reference.checked = !this.dom.reference.checked; this.dom.reference.dispatchEvent(new Event('change')); });
    this.dom.tourToggle.addEventListener('click', () => onTourToggle?.()); this.dom.viewportHelp.addEventListener('click', () => this.openHelp(true)); this.dom.viewportTools.forEach((button) => button.addEventListener('click', () => { this.dom.viewportTools.forEach((tool) => tool.classList.toggle('is-active', tool === button)); onViewportTool?.(button.dataset.viewportTool); })); this.dom.fullscreenToggle.addEventListener('click', () => onFullscreen?.());
    this.dom.reset.addEventListener('click', () => { onReset(); this.dom.objectInspector.hidden = true; }); this.dom.focusLocal.addEventListener('click', () => { if (this.dom.focusLocal.disabled) return; const state = getState(); state.spatialMode = 'slice'; state.sliceThickness = 24; state.sliceOffset = 0; state.maxRedshift = Math.min(0.025, Number(this.dom.maxRedshift.max)); this.syncControlsFromState(state); onStateChange(state); onFocusLocal(); });
    this.dom.closeInspector.addEventListener('click', () => { this.dom.objectInspector.hidden = true; onCloseSelection(); }); this.dom.helpButton.addEventListener('click', () => this.openHelp(true)); this.dom.closeHelp.addEventListener('click', () => this.openHelp(false)); this.dom.helpModal.addEventListener('click', (event) => { if (event.target === this.dom.helpModal) this.openHelp(false); });
    this.dom.railButtons.forEach((button) => button.addEventListener('click', () => { this.dom.railButtons.forEach((item) => item.classList.toggle('is-active', item === button)); const section = button.dataset.railSection; if (section === 'filters' || section === 'data') this.drawerOpen(true); if (section === 'compare') { this.dom.surveyLayer.value = 'all-live'; onLayerChange('all-live'); } if (section === 'analysis') window.location.href = 'methods.html'; }));
    window.addEventListener('keydown', (event) => { if (event.key === 'Escape') { this.openHelp(false); this.drawerOpen(false); return; } const editable = ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName); if (!editable && event.key.toLowerCase() === 'r' && !event.metaKey && !event.ctrlKey && !event.altKey) onReset(); });
  }

  openHelp(open) { this.dom.helpModal.hidden = !open; if (open) this.dom.closeHelp.focus(); }

  setDataReady(meta, maxRedshift, state, layer) {
    this.setLayerControls(meta, state, layer); this.dom.maxRedshift.max = Math.max(0.02, Math.ceil(maxRedshift * 10000) / 10000).toFixed(4); this.dom.systemStatus.textContent = 'Observed catalogue ready'; this.syncControlsFromState(state);
    this.setLoadingState({ title: layer.id === 'desi-dr1' ? 'DESI survey field ready' : layer.id === 'all-live' ? 'Comparison stack ready' : 'Observed local field ready', copy: layer.id === 'desi-dr1' ? 'Measured DESI tracer classes and footprint geometry are ready for interactive exploration.' : layer.id === 'all-live' ? 'The 2MRS anchor and DESI overview retain separate survey provenance in the comparison stack.' : 'Measured nearby spectroscopic rows are ready for interactive exploration.', dataset: meta.dataset_label || layer.label, count: `${formatNumber(meta.object_count)} observed source rows`, progress: 100 }); this.hideLoading();
  }

  setTileStreamingStatus(status = {}) {
    this.tileStreamStatus = status; if (!isDesiLayer(this.currentLayer)) return;
    if (status.fullCatalogue) { this.dom.surveyLayerNote.textContent = this.currentLayer.id === 'all-live' ? `Full comparison stack active: 2MRS anchor plus ${formatNumber(status.streamedRows)} DESI GPU-resident rows. Survey identities remain separate.` : `Full DESI GPU cloud active: ${formatNumber(status.streamedRows)} observed rows are GPU-resident. Display density controls the rendered sample.`; this.dom.budgetNote.textContent = 'Redshift and tracer controls change shader visibility. They do not alter, weight or completeness-correct catalogue rows.'; return; }
    if (status.available && status.active) { this.dom.surveyLayerNote.textContent = `Adaptive data delivery active: ${formatNumber(status.streamedRows || 0)} camera-relevant rows from ${status.loadedTiles || 0}/${status.requestedTiles || 0} tiles.`; return; }
    if (status.reason) this.dom.budgetNote.textContent = status.reason;
  }

  updateTelemetry(metrics, state) {
    this.currentMetrics = metrics;
    const displayRows = Number(metrics.drawBudget || metrics.visibleCount || 0); const gpuRows = Number(metrics.gpuResidentCount || metrics.underlyingCount || displayRows); const depth = formatDistance(metrics.maxDistance); const lookback = formatLookback(metrics.maxLookback); const maxZ = Number(state.maxRedshift || 0).toFixed(2);
    this.dom.visibleCount.textContent = formatNumber(displayRows); this.dom.gpuCount.textContent = formatNumber(gpuRows); this.dom.depth.textContent = depth; this.dom.lookback.textContent = lookback; this.dom.redshiftReadout.textContent = `0.00 – ${maxZ}`; this.dom.displayCountNote.textContent = metrics.fullCatalogue ? 'deterministic GPU sample' : 'rendered current view'; this.dom.gpuCountNote.textContent = metrics.fullCatalogue ? 'resident in memory' : 'available catalogue rows';
    this.dom.coverageReadout.textContent = this.currentLayer?.id === 'desi-dr1' ? '~14,000 deg²' : this.currentLayer?.id === 'all-live' ? '2MRS + DESI' : 'survey-defined'; this.dom.coverageNote.textContent = this.currentLayer?.id === 'desi-dr1' ? 'DESI footprint' : this.currentLayer?.id === 'all-live' ? 'non-deduplicated stack' : 'selection footprint';
    this.dom.datasetStatus.textContent = this.currentMeta?.dataset_label || this.currentLayer?.label || 'Observed survey'; this.dom.observedRowsStatus.textContent = `${formatNumber(gpuRows)} observed rows`; this.dom.headerDepthStatus.textContent = `Radial extent ${depth}`; this.dom.headerLookbackStatus.textContent = `Look-back time ${lookback}`; this.dom.leftDepth.textContent = depth; this.dom.leftLookback.textContent = lookback; this.dom.leftRedshift.textContent = `0.00 – ${maxZ}`; this.dom.spatialRedshift.textContent = `0.00 – ${maxZ}`; this.dom.spatialDepth.textContent = depth; this.dom.spatialLookback.textContent = lookback;
    const fractions = [0.29, 0.58, 0.86]; this.dom.radialTicks.forEach((node, index) => { node.textContent = formatDistance(Number(metrics.maxDistance || 0) * fractions[index]); }); this.dom.tracerCounts.forEach((node) => { const value = metrics.tracerCounts?.[node.dataset.tracerCount]; if (value !== undefined) node.textContent = formatNumber(value); }); this.dom.footerDataSource.textContent = this.currentMeta?.source_survey || this.currentLayer?.label || 'Observed catalogue'; this.dom.systemStatus.textContent = metrics.fullCatalogue ? 'Full GPU cloud active' : this.tileStreamStatus?.active ? 'Adaptive data delivery active' : 'Browser overview active';
    if (metrics.fullCatalogue) { this.fullCloud.active = true; this.fullCloud.recordCount = gpuRows; }
    this.syncControlsFromState(state);
    const mode = COLOUR_COPY[state.viewMode] || 'Observed row colour'; this.dom.budgetNote.textContent = metrics.fullCatalogue ? `All ${formatNumber(gpuRows)} DESI rows are GPU-resident. Display density selects ${formatNumber(displayRows)} deterministic rows; ${mode.toLowerCase()} remains active.` : `The current display contains ${formatNumber(displayRows)} observed rows. ${mode}.`;
  }

  showLayerUnavailable(layer, previousLayer) { this.dom.surveyLayer.value = previousLayer.id; this.dom.surveyLayerNote.textContent = `${layer.label} is not installed in this deployment. Local build: ${layer.localBuild}`; this.dom.inspector.innerHTML = `<p class="eyebrow">LAYER NOT INSTALLED</p><h2>${escapeHtml(layer.label)}</h2><p class="empty-state">The code supports this survey layer, but its observed source rows are not bundled with this deployment.</p><p class="empty-state"><code>${escapeHtml(layer.localBuild)}</code></p>`; this.dom.objectInspector.hidden = false; }

  inspect(object) {
    this.dom.objectInspector.hidden = false; const source = object.source_survey || object.source_layer || 'Observed source'; const tracer = object.tracer ? `<div><dt>DESI tracer</dt><dd>${escapeHtml(object.tracer)} · ${escapeHtml(TRACER_LABELS[object.tracer] || object.tracer)}</dd></div>` : ''; const magnitude = Number(object.magnitude ?? object.ks_mag); const cz = Number(object.cz_km_s);
    this.dom.inspector.innerHTML = `<p class="eyebrow">OBSERVED SOURCE RECORD</p><h2>${escapeHtml(object.name || object.object_id || 'Catalogue row')}</h2><dl><div><dt>Survey</dt><dd>${escapeHtml(source)}</dd></div><div><dt>Redshift</dt><dd>${formatRedshift(object.redshift)}</dd></div><div><dt>Comoving distance</dt><dd>${formatDistance(object.comoving_distance_mpc)}</dd></div><div><dt>Look-back placement</dt><dd>${formatLookback(object.lookback_time_gyr)}</dd></div><div><dt>RA</dt><dd>${Number.isFinite(Number(object.ra_deg)) ? `${Number(object.ra_deg).toFixed(4)}°` : '—'}</dd></div><div><dt>Dec</dt><dd>${Number.isFinite(Number(object.dec_deg)) ? `${Number(object.dec_deg).toFixed(4)}°` : '—'}</dd></div>${tracer}${Number.isFinite(cz) ? `<div><dt>cz</dt><dd>${formatVelocity(cz)}</dd></div>` : ''}${Number.isFinite(magnitude) ? `<div><dt>Magnitude</dt><dd>${magnitude.toFixed(3)}</dd></div>` : ''}</dl>`;
  }
}
