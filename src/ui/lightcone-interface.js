import {
  escapeHtml,
  formatDistance,
  formatLookback,
  formatNumber,
  formatRedshift,
  formatVelocity,
} from '../utils/format.js';

const TRACERS = ['BGS', 'LRG', 'ELG', 'QSO'];
const TRACER_LABELS = Object.freeze({
  BGS: 'Bright Galaxy Survey',
  LRG: 'Luminous Red Galaxies',
  ELG: 'Emission-Line Galaxies',
  QSO: 'Quasars',
});

const SPATIAL_COPY = Object.freeze({
  slice: {
    title: 'Local observed galaxy field.',
    description: 'A finite Cartesian slice through real spectroscopic rows. It makes nearby structure legible without reconstructed filaments or simulated galaxies.',
    railMode: 'Local galaxy field',
  },
  lightcone: {
    title: 'Observed radial lightcone.',
    description: 'Measured source rows are positioned in an observer-centred radial volume. Distance increases outward through the active survey layer.',
    railMode: 'Observer lightcone',
  },
});

const COLOUR_COPY = Object.freeze({
  catalog: 'Observed positions',
  tracer: 'Colour mapped by DESI tracer class',
  time: 'Colour mapped by look-back time',
  uncertainty: 'Marker scale mapped by redshift uncertainty',
});

function copyForSurvey(meta, layer) {
  const photo = meta.measurement_kind === 'photometric';
  const survey = meta.source_survey || 'active survey';
  const isDesi = layer?.id === 'desi-dr1';
  return {
    photo,
    isDesi,
    intro: isDesi
      ? 'DESI DR1 LSS is a deep spectroscopic survey, not an all-sky reconstruction. The separated regions follow the observed North and South survey footprint; their edges reflect targeting and mask geometry, not disconnected Universes.'
      : photo
        ? `The full ${survey} tile store contains observed photometric-redshift rows. This browser view begins with a deterministic set of real source rows while preserving the layer’s total count and radial uncertainty.`
        : `Real ${survey} rows are shown as an observer-centred survey volume. Drag to orbit, scroll to move closer, and select a point for its source record.`,
    redshift: photo
      ? `${survey} uses photometric redshifts. Radial placement is a navigation convention; each accepted row retains its supplied photo-z uncertainty.`
      : `${survey} uses measured spectroscopic redshifts. Radial placement is a cosmological visual-navigation convention.`,
    footprint: isDesi
      ? 'DESI DR1 LSS does not observe the full sky. Separated point clouds follow the North and South Galactic Caps, targeting masks, and completeness cuts — they are not physical empty regions or isolated cosmic structures.'
      : photo
        ? `${survey} has a survey footprint, masking, and photo-z uncertainty. These are measurement properties, not empty physical regions.`
        : `${survey} has target selection and sky coverage limits. Gaps in the view are survey-selection effects, not physical empty space.`,
    empty: photo
      ? `<p class="empty-state">Select a rendered ${escapeHtml(survey)} overview row to open its photometric-redshift source record.</p>`
      : `<p class="empty-state">Select a measured ${escapeHtml(survey)} point to open its source record.</p>`,
  };
}

function enabledTracerNames(state) {
  return TRACERS.filter((tracer) => state.tracerFilters?.[tracer] !== false);
}

export class LightconeInterface {
  constructor() {
    this.currentMeta = null;
    this.currentLayer = null;
    this.tileStreamStatus = null;
    this.dom = {
      datasetStatus: document.querySelector('#dataset-status'), datasetDot: document.querySelector('#dataset-dot'), surveyModeStatus: document.querySelector('#survey-mode-status'),
      sceneEyebrow: document.querySelector('#scene-eyebrow'), sceneTitle: document.querySelector('#scene-title'), sceneDescription: document.querySelector('#scene-description'), openingCount: document.querySelector('#opening-count'), summaryLayer: document.querySelector('#summary-layer'), summaryCount: document.querySelector('#summary-count'), footprintIndicator: document.querySelector('#footprint-indicator'), footprintIndicatorCopy: document.querySelector('#footprint-indicator-copy'),
      controlToggle: document.querySelector('#control-toggle'), controlDrawer: document.querySelector('#control-drawer'), closeControls: document.querySelector('#close-controls'),
      surveyLayer: document.querySelector('#survey-layer'), surveyLayerStatus: document.querySelector('#survey-layer-status'), surveyLayerNote: document.querySelector('#survey-layer-note'),
      maxRedshift: document.querySelector('#max-redshift'), maxRedshiftOutput: document.querySelector('#max-redshift-output'), redshiftNote: document.querySelector('#redshift-note'),
      sliceThickness: document.querySelector('#slice-thickness'), sliceThicknessOutput: document.querySelector('#slice-thickness-output'), sliceOffset: document.querySelector('#slice-offset'), sliceOffsetOutput: document.querySelector('#slice-offset-output'), sliceControls: document.querySelector('#slice-controls'),
      pointBudget: document.querySelector('#point-budget'), pointBudgetOutput: document.querySelector('#point-budget-output'), budgetNote: document.querySelector('#budget-note'), footprintNote: document.querySelector('#footprint-note'),
      tracerSection: document.querySelector('#desi-tracer-section'), tracerInputs: [...document.querySelectorAll('[data-desi-tracer]')], tracerCounts: [...document.querySelectorAll('[data-tracer-count]')],
      galaxies: document.querySelector('#toggle-galaxies'), reset: document.querySelector('#reset-view'), focusLocal: document.querySelector('#focus-local'),
      visibleCount: document.querySelector('#visible-count'), depth: document.querySelector('#depth-readout'), lookback: document.querySelector('#lookback-readout'), railMode: document.querySelector('#rail-mode'), railDetail: document.querySelector('#rail-detail'),
      sourceLink: document.querySelector('#source-link'), cornerNote: document.querySelector('#corner-note'), objectInspector: document.querySelector('#object-inspector'), closeInspector: document.querySelector('#close-inspector'), inspector: document.querySelector('#inspector-content'),
      viewButtons: [...document.querySelectorAll('[data-spatial-mode]')], modeButtons: [...document.querySelectorAll('[data-view-mode]')], tracerModeButton: document.querySelector('[data-view-mode="tracer"]'),
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

  hideLoading() {
    this.dom.loadingMeterBar.style.width = '100%';
    window.setTimeout(() => this.dom.loadingScreen.classList.add('is-hidden'), 280);
  }

  updateSpatialCopy(mode, state = null) {
    const defaultCopy = SPATIAL_COPY[mode] || SPATIAL_COPY.slice;
    const isDesi = this.currentLayer?.id === 'desi-dr1';
    const tracerText = state && isDesi ? enabledTracerNames(state).join(' · ') || 'no tracer classes' : null;
    const copy = isDesi && mode === 'lightcone'
      ? {
        title: 'DESI DR1 spectroscopic lightcone.',
        description: 'Six million measured redshifts underpin this view. The separated regions are the real North/South survey footprint — not a fabricated all-sky cosmic web.',
        railMode: 'DESI DR1 lightcone',
      }
      : defaultCopy;
    this.dom.sceneTitle.textContent = copy.title;
    this.dom.sceneDescription.textContent = copy.description;
    this.dom.railMode.textContent = copy.railMode;
    this.dom.sliceControls.hidden = mode !== 'slice';
    if (tracerText) this.dom.railMode.title = `Active DESI tracers: ${tracerText}`;
  }

  setTracerControls(meta, state, layer) {
    const available = layer?.id === 'desi-dr1' && Object.keys(meta.tracer_counts || {}).length > 0;
    this.dom.tracerSection.hidden = !available;
    if (this.dom.tracerModeButton) {
      this.dom.tracerModeButton.disabled = !available;
      if (!available && state.viewMode === 'tracer') state.viewMode = 'catalog';
    }
    this.dom.tracerInputs.forEach((input) => {
      input.disabled = !available;
      input.checked = state.tracerFilters?.[input.value] !== false;
    });
    this.dom.tracerCounts.forEach((countNode) => {
      const tracer = countNode.dataset.tracerCount;
      countNode.textContent = available ? formatNumber(meta.tracer_counts?.[tracer] || 0) : '—';
    });
  }

  setLayerControls(meta, state, layer) {
    const copy = copyForSurvey(meta, layer);
    this.currentMeta = meta;
    this.currentLayer = layer;
    this.tileStreamStatus = null;
    document.body.dataset.layer = layer.id;
    this.dom.surveyLayer.value = layer.id;
    this.dom.surveyLayerStatus.textContent = copy.photo ? 'photo-z' : 'spectroscopic';
    this.dom.surveyLayerNote.textContent = meta.overview_count
      ? `${formatNumber(meta.object_count)} observed rows; ${formatNumber(meta.overview_count)} real rows in the public browser overview. Full-resolution tiles remain outside Git history.`
      : `${formatNumber(meta.object_count)} observed rows are loaded from the browser catalogue.`;
    this.dom.sceneEyebrow.textContent = layer.eyebrow;
    this.dom.redshiftNote.textContent = copy.redshift;
    this.dom.footprintNote.textContent = copy.footprint;
    this.dom.datasetStatus.textContent = meta.dataset_label || layer.label;
    this.dom.summaryLayer.textContent = meta.source_survey || layer.label;
    this.dom.summaryCount.textContent = meta.overview_count ? `${formatNumber(meta.overview_count)} shown` : `${formatNumber(meta.object_count)} rows`;
    this.dom.footprintIndicator.hidden = !copy.isDesi;
    this.dom.footprintIndicatorCopy.textContent = copy.isDesi ? 'North/South Galactic Cap coverage and targeting geometry.' : 'Coverage is set by the active catalogue.';
    this.dom.surveyModeStatus.textContent = copy.photo ? 'photo-z uncertainty retained' : 'measured redshifts';
    this.dom.sourceLink.textContent = `${meta.source_survey || layer.id} source record ↗`;
    this.dom.sourceLink.href = 'docs/sources.md';
    this.dom.cornerNote.textContent = `${meta.source_survey || layer.id} · ${meta.source_release || 'source provenance in record'} · ${copy.isDesi ? 'survey footprint and tracer filters shown explicitly' : copy.photo ? 'photometric redshift with radial uncertainty' : 'spectroscopic survey placement'}`;
    this.dom.focusLocal.disabled = !layer.supportsSlice;
    this.dom.focusLocal.textContent = layer.supportsSlice ? 'Return to local slice' : 'Observer lightcone only';
    this.dom.viewButtons.forEach((button) => { button.disabled = button.dataset.spatialMode === 'slice' && !layer.supportsSlice; });
    if (!layer.supportsSlice && state.spatialMode === 'slice') state.spatialMode = 'lightcone';
    this.setTracerControls(meta, state, layer);
    this.dom.inspector.innerHTML = copy.empty;
  }

  setTileStreamingStatus({ available, active, totalTiles, requestedTiles, loadedTiles, streamedRows, delivery, reason } = {}) {
    if (this.currentLayer?.id !== 'desi-dr1') return;
    this.tileStreamStatus = { available, active, totalTiles, requestedTiles, loadedTiles, streamedRows, delivery, reason };
    const overview = formatNumber(this.currentMeta?.overview_count || 0);
    const full = formatNumber(this.currentMeta?.object_count || 0);
    const tiles = formatNumber(totalTiles || this.currentMeta?.tile_count || 0);
    if (available && active) {
      const loaded = Number.isFinite(Number(loadedTiles)) ? `${loadedTiles}/${requestedTiles || loadedTiles} active tiles` : 'adaptive tiles active';
      const rows = Number.isFinite(Number(streamedRows)) ? `${formatNumber(streamedRows)} streamed rows` : 'camera-selected observed rows';
      this.dom.surveyLayerNote.textContent = `Adaptive ${delivery || 'tile'} delivery is active: ${loaded}; ${rows}. The 125k overview remains the global context while detail follows the camera.`;
      this.dom.budgetNote.textContent = `Rendering is capped at the browser budget. Adaptive tiles add real camera-relevant rows without downloading all ${full} DESI rows at once.`;
      return;
    }
    this.dom.surveyLayerNote.textContent = `This deployment renders the ${overview}-row deterministic DESI overview. The full ${full}-row store is partitioned into ${tiles} tiles; ${reason || 'no local or remote tile endpoint is configured.'}`;
    this.dom.budgetNote.textContent = `The 125k overview gives an instant public load. Full-resolution tiles stream only from a local build or configured object-store endpoint.`;
  }

  syncControlsFromState(state) {
    this.dom.maxRedshift.value = String(state.maxRedshift);
    this.dom.maxRedshiftOutput.textContent = Number(state.maxRedshift).toFixed(4);
    this.dom.sliceThickness.value = String(state.sliceThickness);
    this.dom.sliceThicknessOutput.textContent = `${Math.round(Number(state.sliceThickness))} Mpc`;
    this.dom.sliceOffset.value = String(state.sliceOffset);
    this.dom.sliceOffsetOutput.textContent = `${Math.round(Number(state.sliceOffset))} Mpc`;
    this.dom.pointBudget.value = String(state.pointBudget);
    this.dom.pointBudgetOutput.textContent = formatNumber(state.pointBudget);
    this.dom.galaxies.checked = state.showGalaxies;
    this.dom.tracerInputs.forEach((input) => { input.checked = state.tracerFilters?.[input.value] !== false; });
    this.dom.viewButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.spatialMode === state.spatialMode));
    this.dom.modeButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.viewMode === state.viewMode));
    this.updateSpatialCopy(state.spatialMode, state);
  }

  bind({ getState, onStateChange, onSpatialModeChange, onReset, onFocusLocal, onCloseSelection, onLayerChange }) {
    [this.dom.surveyLayer, this.dom.maxRedshift, this.dom.sliceThickness, this.dom.sliceOffset, this.dom.pointBudget, this.dom.galaxies, this.dom.focusLocal, ...this.dom.viewButtons, ...this.dom.modeButtons].forEach((item) => { item.disabled = false; });
    const drawerOpen = (open) => {
      this.dom.controlDrawer.hidden = !open;
      document.body.classList.toggle('lens-open', open);
      this.dom.controlToggle.setAttribute('aria-expanded', String(open));
    };
    this.dom.controlToggle.addEventListener('click', () => drawerOpen(this.dom.controlDrawer.hidden));
    this.dom.closeControls.addEventListener('click', () => drawerOpen(false));
    const emit = () => {
      const state = getState();
      state.maxRedshift = Number(this.dom.maxRedshift.value);
      state.sliceThickness = Number(this.dom.sliceThickness.value);
      state.sliceOffset = Number(this.dom.sliceOffset.value);
      state.pointBudget = Number(this.dom.pointBudget.value);
      state.showGalaxies = this.dom.galaxies.checked;
      this.syncControlsFromState(state);
      onStateChange(state);
    };
    [this.dom.maxRedshift, this.dom.sliceThickness, this.dom.sliceOffset, this.dom.pointBudget, this.dom.galaxies].forEach((item) => item.addEventListener('input', emit));
    this.dom.tracerInputs.forEach((input) => input.addEventListener('change', () => {
      const state = getState();
      state.tracerFilters[input.value] = input.checked;
      this.syncControlsFromState(state);
      onStateChange(state);
    }));
    this.dom.surveyLayer.addEventListener('change', () => onLayerChange(this.dom.surveyLayer.value));
    this.dom.viewButtons.forEach((button) => button.addEventListener('click', () => {
      if (button.disabled) return;
      const state = getState();
      state.spatialMode = button.dataset.spatialMode;
      this.syncControlsFromState(state);
      onStateChange(state);
      onSpatialModeChange(state.spatialMode);
    }));
    this.dom.modeButtons.forEach((button) => button.addEventListener('click', () => {
      const state = getState();
      state.viewMode = button.dataset.viewMode;
      this.syncControlsFromState(state);
      onStateChange(state);
    }));
    this.dom.reset.addEventListener('click', () => { onReset(); this.dom.objectInspector.hidden = true; });
    this.dom.focusLocal.addEventListener('click', () => {
      if (this.dom.focusLocal.disabled) return;
      const state = getState();
      state.spatialMode = 'slice';
      state.sliceThickness = 24;
      state.sliceOffset = 0;
      state.maxRedshift = Math.min(0.025, Number(this.dom.maxRedshift.max));
      this.syncControlsFromState(state);
      onStateChange(state);
      onFocusLocal();
    });
    this.dom.closeInspector.addEventListener('click', () => { this.dom.objectInspector.hidden = true; onCloseSelection(); });
    const setHelp = (isOpen) => { this.dom.helpModal.hidden = !isOpen; if (isOpen) this.dom.closeHelp.focus(); };
    this.dom.helpButton.addEventListener('click', () => setHelp(true));
    this.dom.closeHelp.addEventListener('click', () => setHelp(false));
    this.dom.helpModal.addEventListener('click', (event) => { if (event.target === this.dom.helpModal) setHelp(false); });
    window.addEventListener('keydown', (event) => { if (event.key === 'Escape') { setHelp(false); drawerOpen(false); } });
  }

  setDataReady(meta, maxRedshift, state, layer) {
    const count = formatNumber(meta.object_count);
    const photo = meta.measurement_kind === 'photometric';
    this.setLayerControls(meta, state, layer);
    this.dom.datasetDot.classList.remove('status-dot--pending');
    this.dom.openingCount.textContent = meta.overview_count
      ? `${meta.source_survey} · ${count} observed ${photo ? 'photo-z ' : ''}rows · ${formatNumber(meta.overview_count)} real rows in this overview`
      : `${meta.source_survey} · ${count} observed rows`;
    this.dom.maxRedshift.max = Math.max(0.02, Math.ceil(maxRedshift * 10000) / 10000).toFixed(4);
    this.dom.pointBudget.max = String(Math.max(50_000, Number(meta.overview_count || meta.object_count || 50_000)));
    this.syncControlsFromState(state);
    this.setLoadingState({
      title: layer.id === 'desi-dr1' ? 'The DESI survey field is ready' : photo ? 'The wide photometric Universe is ready' : 'The observed survey volume is ready',
      copy: layer.id === 'desi-dr1'
        ? 'Real BGS, LRG, ELG and QSO rows are available as a deterministic browser overview. The footprint and tracer filters are visible in the Data Lens.'
        : photo
          ? 'Real photometric-redshift rows are displayed in an observer-centred lightcone with their published radial uncertainty retained.'
          : 'Real measured spectroscopic rows are now arranged in an observer-centred spatial view.',
      dataset: meta.dataset_label || layer.label,
      count: meta.overview_count ? `${count} source rows · ${formatNumber(meta.overview_count)} overview rows` : `${count} observed rows`,
      progress: 100,
    });
    this.hideLoading();
  }

  showLayerUnavailable(layer, previousLayer) {
    this.dom.surveyLayer.value = previousLayer.id;
    this.dom.surveyLayerNote.textContent = `${layer.label} is not installed in this deployment. Local build: ${layer.localBuild}`;
    this.dom.inspector.innerHTML = `<div class="object-tag object-tag--warning">LAYER NOT INSTALLED</div><h2>${escapeHtml(layer.label)}</h2><p class="empty-state">The code supports this survey layer, but its real source rows are not bundled with this deployment.</p><p class="empty-state"><code>${escapeHtml(layer.localBuild)}</code></p>`;
    this.dom.objectInspector.hidden = false;
  }

  updateTelemetry(metrics, state) {
    this.dom.visibleCount.textContent = formatNumber(metrics.visibleCount);
    this.dom.depth.textContent = formatDistance(metrics.maxDistance);
    this.dom.lookback.textContent = formatLookback(metrics.maxLookback);
    const activeTracers = enabledTracerNames(state);
    this.dom.tracerCounts.forEach((countNode) => {
      const tracer = countNode.dataset.tracerCount;
      const count = metrics.tracerCounts?.[tracer];
      if (count !== undefined) countNode.textContent = formatNumber(count);
    });
    if (this.currentLayer?.id === 'desi-dr1') {
      const stream = this.tileStreamStatus;
      const streamDetail = stream?.active
        ? ` · ${stream.loadedTiles || 0}/${stream.requestedTiles || 0} adaptive tiles`
        : ` · ${formatNumber(this.currentMeta?.overview_count || 0)}-row overview`;
      this.dom.railDetail.textContent = `${activeTracers.length}/4 tracer classes · z ≤ ${Number(state.maxRedshift).toFixed(4)} · real NGC/SGC footprint${streamDetail}`;
      this.dom.summaryCount.textContent = `${formatNumber(metrics.visibleCount)} drawn`;
      return;
    }
    this.dom.summaryCount.textContent = `${formatNumber(metrics.visibleCount)} drawn`;
    this.dom.railDetail.textContent = state.spatialMode === 'slice'
      ? `${Math.round(state.sliceThickness)} Mpc thickness · Cartesian Z = ${Math.round(state.sliceOffset)} Mpc · ${COLOUR_COPY[state.viewMode]}`
      : (this.currentMeta?.measurement_kind === 'photometric'
        ? `z ≤ ${Number(state.maxRedshift).toFixed(4)} · photo-z radial uncertainty retained`
        : `z ≤ ${Number(state.maxRedshift).toFixed(4)} · ${COLOUR_COPY[state.viewMode]}`);
  }

  inspect(object) {
    this.dom.objectInspector.hidden = false;
    const photo = object.measurement_kind === 'photometric';
    const magnitude = Number(object.magnitude ?? object.ks_mag);
    const uncertainty = Number(object.redshift_error);
    const hasCz = Number.isFinite(Number(object.cz_km_s));
    const tracer = object.tracer ? `<div><dt>DESI tracer</dt><dd>${escapeHtml(object.tracer)} · ${escapeHtml(TRACER_LABELS[object.tracer] || object.tracer)}</dd></div>` : '';
    const positional = `<div><dt>RA</dt><dd>${Number.isFinite(Number(object.ra_deg)) ? `${Number(object.ra_deg).toFixed(4)}°` : '—'}</dd></div><div><dt>Dec</dt><dd>${Number.isFinite(Number(object.dec_deg)) ? `${Number(object.dec_deg).toFixed(4)}°` : '—'}</dd></div>`;
    const values = photo
      ? `<div><dt>Photometric z</dt><dd>${formatRedshift(object.redshift)}</dd></div><div><dt>Photo-z uncertainty</dt><dd>±${formatRedshift(uncertainty)}</dd></div><div><dt>Comoving placement</dt><dd>${formatDistance(object.comoving_distance_mpc)}</dd></div><div><dt>Look-back placement</dt><dd>${formatLookback(object.lookback_time_gyr)}</dd></div>${positional}${tracer}<div><dt>Magnitude</dt><dd>${Number.isFinite(magnitude) ? magnitude.toFixed(3) : '—'}</dd></div><div><dt>Placement note</dt><dd>not exact radial distance</dd></div>`
      : `<div><dt>${hasCz ? 'cz' : 'Spectroscopic z'}</dt><dd>${hasCz ? formatVelocity(object.cz_km_s) : formatRedshift(object.redshift)}</dd></div><div><dt>Comoving distance</dt><dd>${formatDistance(object.comoving_distance_mpc)}</dd></div><div><dt>Look-back time</dt><dd>${formatLookback(object.lookback_time_gyr)}</dd></div>${positional}${tracer}<div><dt>Magnitude</dt><dd>${Number.isFinite(magnitude) ? magnitude.toFixed(3) : '—'}</dd></div>`;
    const tag = object.tracer ? `OBSERVED / DESI ${escapeHtml(object.tracer)}` : `OBSERVED / ${photo ? 'PHOTOMETRIC' : 'SPECTROSCOPIC'}`;
    this.dom.inspector.innerHTML = `<div class="object-tag">${tag}</div><h2>${escapeHtml(object.name || object.object_id)}</h2><p class="object-type">${escapeHtml(object.source_survey)} · ${escapeHtml(object.source_table)} · ${escapeHtml(object.object_id)}</p><dl class="object-metrics">${values}</dl><div class="provenance-block"><span>PROVENANCE</span><strong>${escapeHtml(object.source_release)}</strong><p>${escapeHtml(object.source_url)}</p><p>${escapeHtml(object.distance_note)}</p></div>`;
  }

  showLoadError(message) {
    this.dom.openingCount.textContent = 'Observed layer unavailable';
    this.setLoadingState({ title: 'Observed layer unavailable', copy: message, dataset: 'Survey browser', count: 'Check the local data pipeline, then refresh', progress: 100 });
  }
}
