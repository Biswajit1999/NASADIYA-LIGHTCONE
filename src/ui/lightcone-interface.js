import {
  escapeHtml,
  formatDistance,
  formatLookback,
  formatNumber,
  formatRedshift,
  formatVelocity,
} from '../utils/format.js';

const EMPTY = '<p class="empty-state">Select a measured 2MRS point to open its source record.</p>';

const SPATIAL_COPY = Object.freeze({
  slice: {
    title: 'A slice through the observed galaxy field.',
    description: 'Real survey rows inside a finite observer-centred Cartesian slab. The view makes nearby structure legible without adding reconstructed filaments or simulated galaxies.',
    railMode: 'Local Cartesian slice',
  },
  lightcone: {
    title: 'The local Universe as a radial survey volume.',
    description: 'The complete active 2MRS selection is shown in observer-centred 3D. Distance increases outward through the measured radial volume.',
    railMode: 'Observer lightcone',
  },
});

const COLOUR_COPY = Object.freeze({
  catalog: 'Observed positions',
  time: 'Colour mapped by look-back time',
  uncertainty: 'Marker scale mapped by cz error',
});

export class LightconeInterface {
  constructor() {
    this.dom = {
      datasetStatus: document.querySelector('#dataset-status'),
      datasetDot: document.querySelector('#dataset-dot'),
      sceneTitle: document.querySelector('#scene-title'),
      sceneDescription: document.querySelector('#scene-description'),
      openingCount: document.querySelector('#opening-count'),
      controlToggle: document.querySelector('#control-toggle'),
      controlDrawer: document.querySelector('#control-drawer'),
      closeControls: document.querySelector('#close-controls'),
      maxRedshift: document.querySelector('#max-redshift'),
      maxRedshiftOutput: document.querySelector('#max-redshift-output'),
      sliceThickness: document.querySelector('#slice-thickness'),
      sliceThicknessOutput: document.querySelector('#slice-thickness-output'),
      sliceOffset: document.querySelector('#slice-offset'),
      sliceOffsetOutput: document.querySelector('#slice-offset-output'),
      sliceControls: document.querySelector('#slice-controls'),
      pointBudget: document.querySelector('#point-budget'),
      pointBudgetOutput: document.querySelector('#point-budget-output'),
      galaxies: document.querySelector('#toggle-galaxies'),
      reset: document.querySelector('#reset-view'),
      focusLocal: document.querySelector('#focus-local'),
      visibleCount: document.querySelector('#visible-count'),
      depth: document.querySelector('#depth-readout'),
      lookback: document.querySelector('#lookback-readout'),
      railMode: document.querySelector('#rail-mode'),
      railDetail: document.querySelector('#rail-detail'),
      objectInspector: document.querySelector('#object-inspector'),
      closeInspector: document.querySelector('#close-inspector'),
      inspector: document.querySelector('#inspector-content'),
      viewButtons: [...document.querySelectorAll('[data-spatial-mode]')],
      modeButtons: [...document.querySelectorAll('[data-view-mode]')],
      helpButton: document.querySelector('#help-button'),
      helpModal: document.querySelector('#help-modal'),
      closeHelp: document.querySelector('#close-help'),
      loadingScreen: document.querySelector('#loading-screen'),
      loadingTitle: document.querySelector('#loading-title'),
      loadingCopy: document.querySelector('#loading-copy'),
      loadingMeterBar: document.querySelector('#loading-meter-bar'),
      loadingDataset: document.querySelector('#loading-dataset'),
      loadingCount: document.querySelector('#loading-count'),
    };
  }

  setLoadingState({ title, copy, dataset, count, progress = 18 } = {}) {
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

  updateSpatialCopy(mode) {
    const copy = SPATIAL_COPY[mode] || SPATIAL_COPY.slice;
    this.dom.sceneTitle.textContent = copy.title;
    this.dom.sceneDescription.textContent = copy.description;
    this.dom.railMode.textContent = copy.railMode;
    this.dom.sliceControls.hidden = mode !== 'slice';
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
    this.dom.viewButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.spatialMode === state.spatialMode));
    this.dom.modeButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.viewMode === state.viewMode));
    this.updateSpatialCopy(state.spatialMode);
  }

  bind({ getState, onStateChange, onSpatialModeChange, onReset, onFocusLocal, onCloseSelection }) {
    const controlled = [
      this.dom.maxRedshift,
      this.dom.sliceThickness,
      this.dom.sliceOffset,
      this.dom.pointBudget,
      this.dom.galaxies,
      this.dom.focusLocal,
      ...this.dom.viewButtons,
      ...this.dom.modeButtons,
    ];
    controlled.forEach((item) => { item.disabled = false; });

    const drawerOpen = (open) => {
      this.dom.controlDrawer.hidden = !open;
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
    [this.dom.maxRedshift, this.dom.sliceThickness, this.dom.sliceOffset, this.dom.pointBudget, this.dom.galaxies]
      .forEach((item) => item.addEventListener('input', emit));

    this.dom.viewButtons.forEach((button) => button.addEventListener('click', () => {
      const state = getState();
      const mode = button.dataset.spatialMode;
      state.spatialMode = mode;
      if (mode === 'lightcone' && state.maxRedshift < 0.04) {
        state.maxRedshift = Math.min(0.05, Number(this.dom.maxRedshift.max));
      }
      if (mode === 'slice' && state.maxRedshift > 0.05) {
        state.maxRedshift = Math.min(0.025, Number(this.dom.maxRedshift.max));
      }
      this.syncControlsFromState(state);
      onStateChange(state);
      onSpatialModeChange(mode);
    }));

    this.dom.modeButtons.forEach((button) => button.addEventListener('click', () => {
      const state = getState();
      state.viewMode = button.dataset.viewMode;
      this.syncControlsFromState(state);
      onStateChange(state);
    }));

    this.dom.reset.addEventListener('click', () => {
      onReset();
      this.dom.objectInspector.hidden = true;
    });
    this.dom.focusLocal.addEventListener('click', () => {
      const state = getState();
      state.spatialMode = 'slice';
      state.sliceThickness = 24;
      state.sliceOffset = 0;
      state.maxRedshift = Math.min(0.025, Number(this.dom.maxRedshift.max));
      this.syncControlsFromState(state);
      onStateChange(state);
      onFocusLocal();
    });
    this.dom.closeInspector.addEventListener('click', () => {
      this.dom.objectInspector.hidden = true;
      onCloseSelection();
    });

    const setHelp = (isOpen) => {
      this.dom.helpModal.hidden = !isOpen;
      if (isOpen) this.dom.closeHelp.focus();
    };
    this.dom.helpButton.addEventListener('click', () => setHelp(true));
    this.dom.closeHelp.addEventListener('click', () => setHelp(false));
    this.dom.helpModal.addEventListener('click', (event) => { if (event.target === this.dom.helpModal) setHelp(false); });
    window.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        setHelp(false);
        drawerOpen(false);
      }
    });
  }

  setDataReady(meta, maxRedshift) {
    const count = formatNumber(meta.object_count);
    this.dom.datasetStatus.textContent = meta.dataset_label || '2MRS real spectroscopic catalogue';
    this.dom.datasetDot.classList.remove('status-dot--pending');
    this.dom.openingCount.textContent = `2MRS · ${count} observed galaxies · Huchra et al. 2012`;
    this.dom.maxRedshift.max = Math.max(0.02, Math.ceil(maxRedshift * 10000) / 10000).toFixed(4);
    this.dom.inspector.innerHTML = EMPTY;
    this.setLoadingState({
      title: 'The observed local Universe is ready',
      copy: 'Real 2MRS spectroscopic rows are now arranged in an observer-centred spatial view.',
      dataset: meta.dataset_label || '2MRS Table 3',
      count: `${count} observed rows`,
      progress: 100,
    });
    this.hideLoading();
  }

  updateTelemetry(metrics, state) {
    this.dom.visibleCount.textContent = formatNumber(metrics.visibleCount);
    this.dom.depth.textContent = formatDistance(metrics.maxDistance);
    this.dom.lookback.textContent = formatLookback(metrics.maxLookback);
    if (state.spatialMode === 'slice') {
      this.dom.railDetail.textContent = `${Math.round(state.sliceThickness)} Mpc thickness · Cartesian Z = ${Math.round(state.sliceOffset)} Mpc · ${COLOUR_COPY[state.viewMode]}`;
    } else {
      this.dom.railDetail.textContent = `z ≤ ${Number(state.maxRedshift).toFixed(4)} · ${COLOUR_COPY[state.viewMode]}`;
    }
  }

  inspect(object) {
    this.dom.objectInspector.hidden = false;
    this.dom.inspector.innerHTML = `
      <div class="object-tag">OBSERVED / SPECTROSCOPIC</div>
      <h2>${escapeHtml(object.name || object.object_id)}</h2>
      <p class="object-type">${escapeHtml(object.source_survey)} · ${escapeHtml(object.source_table)} · ${escapeHtml(object.object_id)}</p>
      <dl class="object-metrics">
        <div><dt>cz</dt><dd>${formatVelocity(object.cz_km_s)}</dd></div>
        <div><dt>z ≈ cz/c</dt><dd>${formatRedshift(object.redshift)}</dd></div>
        <div><dt>Comoving distance</dt><dd>${formatDistance(object.comoving_distance_mpc)}</dd></div>
        <div><dt>Look-back time</dt><dd>${formatLookback(object.lookback_time_gyr)}</dd></div>
        <div><dt>RA</dt><dd>${Number.isFinite(Number(object.ra_deg)) ? `${Number(object.ra_deg).toFixed(4)}°` : '—'}</dd></div>
        <div><dt>Dec</dt><dd>${Number.isFinite(Number(object.dec_deg)) ? `${Number(object.dec_deg).toFixed(4)}°` : '—'}</dd></div>
        <div><dt>cz uncertainty</dt><dd>±${formatVelocity(object.cz_error_km_s)}</dd></div>
        <div><dt>K<sub>s</sub> magnitude</dt><dd>${Number.isFinite(Number(object.ks_mag)) ? Number(object.ks_mag).toFixed(3) : '—'}</dd></div>
      </dl>
      <div class="provenance-block"><span>PROVENANCE</span><strong>${escapeHtml(object.source_release)}</strong><p>${escapeHtml(object.source_url)}</p><p>${escapeHtml(object.distance_note)}</p></div>`;
  }

  showLoadError(message) {
    this.dom.openingCount.textContent = '2MRS browser layer unavailable';
    this.setLoadingState({
      title: 'Observed layer unavailable',
      copy: message,
      dataset: '2MRS Table 3',
      count: 'Run the local data pipeline, then refresh',
      progress: 100,
    });
  }
}
