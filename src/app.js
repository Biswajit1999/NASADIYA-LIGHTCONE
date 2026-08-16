import * as THREE from 'three';

import { DESI_TRACERS, LIGHTCONE_CONFIG, SURVEY_LAYERS, TILE_STREAMING } from './config.js?v=20260816-v5';
import { FULL_DESI_GPU_CLOUD } from './full-cloud-config.js';
import { loadCatalog, loadTileStoreOverview } from './core/catalog-loader.js';
import { probeGpuCloud } from './core/gpu-cloud-loader.js';
import { fetchGpuCloud } from './core/gpu-cloud-binary.js';
import { CompositeFullCloud } from './core/composite-full-cloud.js?v=20260816-v5';
import { GpuSurveyCloud } from './core/gpu-survey-cloud.js?v=20260816-v5';
import { GuidedFlyby } from './core/guided-flyby.js';
import { LightconeScene } from './core/lightcone-scene.js?v=20260703-phase3';
import { SurveyReferenceFrame } from './core/reference-frame.js';
import { SurveyPoints } from './core/survey-points.js?v=20260816-v5';
import { TileStreamer } from './core/tile-streamer.js';
import { LightconeInterface } from './ui/lightcone-interface.js?v=20260816-v5';
import { ObservatoryConsole } from './ui/observatory-console.js?v=20260816-v5';
import { SurveyReadinessPanel } from './ui/survey-readiness.js?v=20260703-phase4';
import { AnalysisPanel } from './ui/analysis-panel.js?v=20260816-v5';

const state = {
  layerId: 'desi-dr1',
  maxRedshift: SURVEY_LAYERS['desi-dr1'].defaultMaxRedshift,
  pointBudget: SURVEY_LAYERS['desi-dr1'].defaultPointBudget,
  sliceThickness: 24,
  sliceOffset: 0,
  showGalaxies: true,
  showReference: true,
  showLegend: true,
  spatialMode: SURVEY_LAYERS['desi-dr1'].defaultSpatialMode,
  viewMode: 'tracer',
  tileStreaming: false,
  fullCatalogue: false,
  renderQuality: 'auto',
  tracerFilters: Object.fromEntries(DESI_TRACERS.map((tracer) => [tracer, true])),
};

const canvas = document.querySelector('#lightcone-canvas');
const scene = new LightconeScene(canvas);
const ui = new LightconeInterface();
const referenceFrame = new SurveyReferenceFrame(scene.world);
const flyby = new GuidedFlyby(scene);
const observatory = new ObservatoryConsole({ scene, canvas, getState: () => state });
const surveyReadiness = new SurveyReadinessPanel();
const analysisPanel = new AnalysisPanel();
const raycaster = new THREE.Raycaster();
raycaster.params.Points.threshold = 9;
const pointer = new THREE.Vector2();

let points = null;
let overviewObjects = [];
let activeMeta = null;
let tileStreamer = null;
let tileRefreshTimer = null;
let tileRefreshBusy = false;
let fullCloudProbe = null;
let fullCloudLoading = false;
let pointerStart = null;
let hoverTimer = null;
let loadSequence = 0;
let redshiftPlayback = null;

function maxField(objects, field) {
  return objects.reduce((maximum, object) => Math.max(maximum, Number(object[field]) || 0), 0);
}

function currentLayer() {
  return SURVEY_LAYERS[state.layerId];
}

function supportsFullCloud(layer = currentLayer()) {
  return ['desi-dr1', 'all-live'].includes(layer?.id);
}

function updateSpatialAids() {
  referenceFrame.setExtent(scene.datasetMaxDistanceMpc);
  const visible = state.showReference && state.spatialMode === 'lightcone';
  referenceFrame.setVisible(visible);
  ui.dom.spatialAnnotation.hidden = !visible;
  ui.dom.spatialCard.hidden = !visible;
  ui.dom.legendCard.hidden = !state.showLegend || !['desi-dr1', 'all-live'].includes(state.layerId);
}

function attachRenderable(next, extentMpc) {
  if (points) {
    scene.world.remove(points.points);
    points.dispose();
  }
  points = next;
  points.setCinematicBoost(flyby.active);
  scene.world.add(points.points);
  scene.setDatasetExtent(Math.max(1, Number(extentMpc) || 1));
  scene.setSelection(null);
  updateSpatialAids();
}

function replacePoints(objects, meta) {
  state.fullCatalogue = false;
  attachRenderable(new SurveyPoints(objects, meta), maxField(objects, 'comoving_distance_mpc'));
}

function replaceGpuCloud(buffer, manifest, meta) {
  state.fullCatalogue = true;
  const renderable = state.layerId === 'all-live'
    ? new CompositeFullCloud(buffer, manifest, overviewObjects, meta)
    : new GpuSurveyCloud(buffer, manifest, meta);
  attachRenderable(renderable, renderable.maxDistanceMpc || maxField(overviewObjects, 'comoving_distance_mpc'));
}

function applyState({ scheduleTiles = true } = {}) {
  if (!points) return;
  const metrics = points.applyState(state);
  ui.updateTelemetry(metrics, state);
  scene.renderer.toneMappingExposure = metrics.fullCatalogue ? 0.94 : 1.08;
  scene.scene.fog.density = metrics.fullCatalogue ? 0.00023 : 0.00030;
  scene.setRenderQuality(state.renderQuality);
  updateSpatialAids();
  analysisPanel.update({ objects: overviewObjects, metrics, meta: activeMeta || {} });
  if (scheduleTiles && !state.fullCatalogue) scheduleAdaptiveTileRefresh();
}

function tileStreamingConfig() {
  return TILE_STREAMING[state.layerId] || null;
}

function scheduleAdaptiveTileRefresh(delay = null) {
  if (!tileStreamer || !state.tileStreaming || state.fullCatalogue || tileRefreshBusy) return;
  const config = tileStreamingConfig();
  if (!config) return;
  window.clearTimeout(tileRefreshTimer);
  tileRefreshTimer = window.setTimeout(() => refreshAdaptiveTiles(), delay ?? config.refreshDebounceMs);
}

async function refreshAdaptiveTiles() {
  if (!tileStreamer || !state.tileStreaming || state.fullCatalogue || tileRefreshBusy) return;
  const requestId = loadSequence;
  tileRefreshBusy = true;
  try {
    const result = await tileStreamer.update(scene.camera, state);
    if (requestId !== loadSequence || !tileStreamer || !state.tileStreaming || state.fullCatalogue) return;
    if (result.changed && result.objects?.length) {
      replacePoints(result.objects, activeMeta);
      applyState({ scheduleTiles: false });
    }
    ui.setTileStreamingStatus({ available: true, active: true, ...result });
  } catch (error) {
    state.tileStreaming = false;
    const delivery = { available: false, active: false, reason: error?.message || 'Adaptive tile loading failed.' };
    ui.setTileStreamingStatus(delivery);
    replacePoints(overviewObjects, activeMeta);
    applyState({ scheduleTiles: false });
  } finally {
    tileRefreshBusy = false;
  }
}

async function configureFullCloud(layer, requestId) {
  fullCloudProbe = null;
  if (!supportsFullCloud(layer)) {
    ui.setFullCloudStatus({ available: false, active: false, reason: 'Full observed-row mode is available for DESI DR1 and the comparison stack.' });
    return;
  }
  const probe = await probeGpuCloud(FULL_DESI_GPU_CLOUD.manifestPath, { remoteBaseUrl: FULL_DESI_GPU_CLOUD.remoteBaseUrl });
  if (requestId !== loadSequence || state.layerId !== layer.id) return;
  fullCloudProbe = probe;
  ui.setFullCloudStatus({
    available: probe.available,
    active: false,
    recordCount: Number(probe.manifest?.record_count || 0),
    reason: probe.reason,
    delivery: probe.delivery,
  });
}

async function activateFullCloud() {
  if (!supportsFullCloud() || !fullCloudProbe?.available || fullCloudLoading) return;
  if (state.fullCatalogue) {
    state.pointBudget = Number(fullCloudProbe.manifest.record_count);
    applyState({ scheduleTiles: false });
    return;
  }
  const requestedLayerId = state.layerId;
  fullCloudLoading = true;
  ui.setLoadingState({
    title: requestedLayerId === 'all-live' ? 'Loading full comparison stack' : 'Loading full DESI GPU cloud',
    copy: requestedLayerId === 'all-live'
      ? 'Keeping the 2MRS nearby anchor while loading every accepted DESI row into GPU memory.'
      : 'Loading every accepted DESI row into GPU memory. Display density can then be changed without reloading the catalogue.',
    dataset: activeMeta?.dataset_label || 'DESI DR1 LSS',
    count: `${Number(fullCloudProbe.manifest.record_count).toLocaleString('en-GB')} DESI observed rows`,
    progress: 35,
  });
  try {
    const buffer = await fetchGpuCloud(fullCloudProbe);
    if (state.layerId !== requestedLayerId) return;
    window.clearTimeout(tileRefreshTimer);
    tileStreamer = null;
    state.tileStreaming = false;
    state.spatialMode = 'lightcone';
    replaceGpuCloud(buffer, fullCloudProbe.manifest, activeMeta);
    state.pointBudget = Number(fullCloudProbe.manifest.record_count);
    scene.setSpatialMode('lightcone', { immediate: true });
    ui.setFullCloudStatus({ available: true, active: true, recordCount: fullCloudProbe.manifest.record_count, delivery: fullCloudProbe.delivery });
    ui.setTileStreamingStatus({ available: true, active: true, fullCatalogue: true, streamedRows: fullCloudProbe.manifest.record_count, delivery: fullCloudProbe.delivery, totalTiles: activeMeta?.tile_count || 0 });
    applyState({ scheduleTiles: false });
    ui.hideLoading();
  } catch (error) {
    state.fullCatalogue = false;
    ui.setFullCloudStatus({ available: false, active: false, reason: error?.message || 'Full GPU cloud loading failed.' });
    ui.setLoadingState({ title: 'Full GPU cloud could not be loaded', copy: error?.message || 'The full cloud endpoint did not return a usable binary.', dataset: activeMeta?.dataset_label, count: 'The overview remains available', progress: 100 });
  } finally {
    fullCloudLoading = false;
  }
}

async function returnToAdaptiveCloud() {
  if (!state.fullCatalogue) return;
  replacePoints(overviewObjects, activeMeta);
  state.pointBudget = Math.min(1_000_000, Number(state.pointBudget) || 125_000);
  ui.setFullCloudStatus({ available: Boolean(fullCloudProbe?.available), active: false, recordCount: Number(fullCloudProbe?.manifest?.record_count || 0), reason: fullCloudProbe?.reason });
  await configureAdaptiveTiles(currentLayer(), activeMeta, loadSequence);
  applyState({ scheduleTiles: false });
}

function matchAtPointer(event) {
  if (!points || state.fullCatalogue) return;
  const bounds = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
  pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
  raycaster.setFromCamera(pointer, scene.camera);
  return points.selectFromRaycaster(raycaster);
}

function selectAtPointer(event) {
  const match = matchAtPointer(event);
  if (match) {
    scene.setSelection(points.getDisplayPosition(match.index));
    ui.inspect(match.object);
  }
}

async function loadSingleLayerPayload(layer) {
  return layer.dataKind === 'catalog' ? loadCatalog(layer.dataUrl, layer.label) : loadTileStoreOverview(layer.dataUrl, layer.label);
}

function annotateSourceLayer(objects, layerId) {
  return objects.map((object) => ({ ...object, source_layer: layerId }));
}

async function loadCompositeLayer(layer) {
  const memberIds = layer.memberLayerIds || [];
  if (memberIds.length < 2) throw new Error('Composite view requires at least two installed survey layers.');
  const members = await Promise.all(memberIds.map(async (memberId) => {
    const memberLayer = SURVEY_LAYERS[memberId];
    if (!memberLayer?.installed) throw new Error(`Composite member ${memberId} is not installed.`);
    return { id: memberId, result: await loadSingleLayerPayload(memberLayer) };
  }));
  const objects = members.flatMap(({ id, result }) => annotateSourceLayer(result.objects, id));
  const desi = members.find((member) => member.id === 'desi-dr1')?.result;
  const sourceRowCount = members.reduce((total, member) => total + Number(member.result.meta.object_count || member.result.objects.length), 0);
  return {
    meta: {
      dataset_id: 'all-live-observed-surveys',
      dataset_label: `2MRS + DESI DR1 LSS · ${sourceRowCount.toLocaleString('en-GB')} source rows (non-deduplicated)`,
      object_count: sourceRowCount,
      overview_count: objects.length,
      source_survey: '2MRS + DESI DR1 LSS',
      source_release: 'Huchra et al. 2012 + DESI DR1',
      source_url: 'docs/sources.md',
      citation_key: 'Huchra2012_2MRS;DESI_DR1',
      measurement_kind: 'spectroscopic',
      object_type: 'galaxies and quasars',
      distance_note: 'Non-deduplicated comparison stack. Individual records retain their original survey provenance and cosmological placement note.',
      radial_uncertainty_required: false,
      is_synthetic: false,
      composite: true,
      component_layers: members.map(({ id, result }) => ({ id, source_survey: result.meta.source_survey, source_rows: Number(result.meta.object_count || result.objects.length), overview_rows: Number(result.meta.overview_count || result.objects.length) })),
      overview_selection: { method: 'concatenate-installed-public-layers', non_deduplicated: true, note: 'Survey comparison stack, not a unified or completeness-corrected catalogue.' },
      tracer_counts: desi?.meta?.tracer_counts || {},
      tile_count: Number(desi?.meta?.tile_count || 0),
      tile_manifest: desi?.meta?.tile_manifest || null,
      tile_index_url: desi?.meta?.tile_index_url || null,
    },
    objects,
  };
}

async function loadLayerPayload(layer) {
  return layer.dataKind === 'composite' ? loadCompositeLayer(layer) : loadSingleLayerPayload(layer);
}

function loadingText(layer) {
  if (layer.dataKind === 'composite') {
    return { title: 'Building comparison stack', copy: 'Loading the 2MRS nearby anchor and the deterministic DESI overview while retaining separate survey identities.' };
  }
  return layer.dataKind === 'tile-store'
    ? { title: `Opening ${layer.label.split(' · ')[0]}`, copy: 'Reading the tile-store index and deterministic overview of observed source rows.' }
    : { title: 'Opening observed local field', copy: 'Reading the browser catalogue and source provenance.' };
}

async function configureAdaptiveTiles(layer, meta, requestId) {
  tileStreamer = null;
  state.tileStreaming = false;
  const config = TILE_STREAMING[layer.id];
  if (!config?.enabled || !meta.tile_manifest || !meta.tile_index_url || !meta.tile_count) {
    ui.setTileStreamingStatus({ available: false, active: false, reason: 'This layer has no adaptive tile delivery endpoint.' });
    return;
  }
  const streamer = new TileStreamer({
    manifest: meta.tile_manifest,
    indexUrl: meta.tile_index_url,
    overviewObjects,
    remoteBaseUrl: config.remoteBaseUrl,
    maxTiles: config.maxTiles,
    maxCachedTiles: config.maxCachedTiles,
    maxLoadedRows: config.maxLoadedRows,
    loadConcurrency: config.loadConcurrency,
    overviewReserveRows: config.overviewReserveRows,
    overviewReserveFraction: config.overviewReserveFraction,
    minOverviewRows: config.minOverviewRows,
  });
  const delivery = await streamer.probeDelivery();
  if (requestId !== loadSequence || state.layerId !== layer.id) return;
  tileStreamer = streamer;
  state.tileStreaming = delivery.available;
  ui.setTileStreamingStatus({ available: delivery.available, active: delivery.available, totalTiles: meta.tile_count, delivery: delivery.delivery, reason: delivery.reason });
  if (delivery.available) scheduleAdaptiveTileRefresh(0);
}

async function activateLayer(layerId, { initial = false } = {}) {
  const requestedLayer = SURVEY_LAYERS[layerId];
  const previousLayer = currentLayer();
  if (!requestedLayer || requestedLayer.installed === false) return;
  flyby.stop('layer-change');
  const requestId = ++loadSequence;
  window.clearTimeout(tileRefreshTimer);
  tileStreamer = null;
  state.tileStreaming = false;
  state.fullCatalogue = false;
  fullCloudProbe = null;
  ui.setFullCloudStatus({ available: false, active: false, recordCount: 0 });
  const start = loadingText(requestedLayer);
  ui.setLoadingState({ ...start, dataset: requestedLayer.label, count: 'Preparing observed rows', progress: 18 });
  try {
    const { meta, objects } = await loadLayerPayload(requestedLayer);
    if (requestId !== loadSequence) return;
    overviewObjects = objects;
    activeMeta = meta;
    state.layerId = requestedLayer.id;
    state.maxRedshift = Math.min(requestedLayer.defaultMaxRedshift, Math.max(0.003, maxField(objects, 'redshift')));
    state.pointBudget = Math.min(requestedLayer.defaultPointBudget, objects.length);
    state.spatialMode = requestedLayer.defaultSpatialMode;
    state.sliceThickness = requestedLayer.supportsSlice ? 24 : state.sliceThickness;
    state.sliceOffset = requestedLayer.supportsSlice ? 0 : state.sliceOffset;
    replacePoints(overviewObjects, meta);
    scene.setSpatialMode(state.spatialMode, { immediate: true });
    ui.setDataReady(meta, maxField(objects, 'redshift'), state, requestedLayer);
    applyState({ scheduleTiles: false });
    document.title = `NĀSADĪYA LIGHTCONE — ${meta.source_survey || requestedLayer.id}`;
    await configureAdaptiveTiles(requestedLayer, meta, requestId);
    await configureFullCloud(requestedLayer, requestId);
  } catch (error) {
    if (requestId !== loadSequence) return;
    if (initial) {
      ui.setLoadingState({ title: 'Catalogue loading failed', copy: error?.message || 'Unknown catalogue loading problem.', dataset: requestedLayer.label, count: 'Review the browser console and data path', progress: 100 });
      return;
    }
    ui.hideLoading();
    ui.showLayerUnavailable(requestedLayer, previousLayer);
  }
}

function configureViewportTool(tool) {
  if (tool === 'pan') {
    scene.controls.mouseButtons.LEFT = THREE.MOUSE.PAN;
    return;
  }
  scene.controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
}

function toggleFullscreen() {
  const target = document.querySelector('#explorer');
  if (!document.fullscreenElement) target.requestFullscreen?.();
  else document.exitFullscreen?.();
}

function searchObservedObject(query) {
  const value = String(query || '').trim().toLowerCase();
  if (value.length < 3) return;
  const inspectable = points?.objects?.length ? points.objects : overviewObjects;
  const identifier = (object) => String(object.object_id || object.name || '').toLowerCase();
  let index = inspectable.findIndex((object) => identifier(object) === value);
  if (index < 0) index = inspectable.findIndex((object) => identifier(object).includes(value));
  if (index < 0) {
    observatory.notify('No matching object in the currently loaded inspectable rows');
    return;
  }
  const object = inspectable[index];
  const usesRenderableObjects = inspectable === points?.objects;
  const position = usesRenderableObjects
    ? points.getDisplayPosition(index)
    : new THREE.Vector3(Number(object.x_mpc), Number(object.y_mpc), Number(object.z_mpc)).multiplyScalar(LIGHTCONE_CONFIG.displayScale);
  scene.setSelection(position);
  scene.focusOn(position, 70);
  ui.inspect(object);
  observatory.notify(`Focused observed source ${object.object_id || object.name || ''}`.trim());
}

function applySharedView(shared) {
  if (!shared) return;
  const observedCeiling = Math.max(0.003, maxField(overviewObjects, 'redshift'));
  if (Number.isFinite(Number(shared.maxRedshift))) state.maxRedshift = Math.min(Number(shared.maxRedshift), observedCeiling);
  if (Number.isFinite(Number(shared.pointBudget))) state.pointBudget = Number(shared.pointBudget);
  if (typeof shared.viewMode === 'string') state.viewMode = shared.viewMode;
  if (['auto', 'performance', 'quality'].includes(shared.renderQuality)) state.renderQuality = shared.renderQuality;
  if (shared.tracerFilters && typeof shared.tracerFilters === 'object') state.tracerFilters = { ...state.tracerFilters, ...shared.tracerFilters };
  ui.syncControlsFromState(state);
  applyState({ scheduleTiles: false });
  if (Array.isArray(shared.camera) && Array.isArray(shared.target)) {
    const position = scene.camera.position.clone().fromArray(shared.camera);
    const target = scene.controls.target.clone().fromArray(shared.target);
    scene.animateCamera(position, target, 900);
  }
  if (shared.theme) observatory.applyTheme(shared.theme);
}

function toggleRedshiftPlayback() {
  if (redshiftPlayback) {
    redshiftPlayback = null;
    observatory.notify('Redshift scan paused');
    return;
  }
  const ceiling = Math.max(0.05, maxField(overviewObjects, 'redshift'));
  redshiftPlayback = { startedAt: performance.now(), start: 0.03, ceiling, duration: 12_000, lastUpdate: 0 };
  state.maxRedshift = redshiftPlayback.start;
  observatory.notify('Redshift scan active · visibility changes, catalogue positions remain fixed');
}

function updateRedshiftPlayback(now) {
  if (!redshiftPlayback || now - redshiftPlayback.lastUpdate < 90) return;
  redshiftPlayback.lastUpdate = now;
  const progress = Math.min(1, (now - redshiftPlayback.startedAt) / redshiftPlayback.duration);
  state.maxRedshift = redshiftPlayback.start + (redshiftPlayback.ceiling - redshiftPlayback.start) * progress;
  ui.syncControlsFromState(state);
  applyState({ scheduleTiles: false });
  if (progress >= 1) {
    redshiftPlayback = null;
    observatory.notify('Redshift scan complete');
  }
}

async function handleObservatoryCommand(command) {
  if (command.startsWith('destination-')) {
    flyby.stop('preset');
    scene.focusDestination(command.replace('destination-', ''));
    return;
  }
  if (command === 'redshift-play') return toggleRedshiftPlayback();
  const layers = { 'layer-local': '2mrs', 'layer-desi': 'desi-dr1', 'layer-comparison': 'all-live' };
  if (layers[command]) await activateLayer(layers[command]);
}

function initialise() {
  flyby.onChange((status) => { ui.setTourStatus(status); points?.setCinematicBoost(status.active); });
  ui.bind({
    getState: () => state,
    onStateChange: () => applyState(),
    onSpatialModeChange: (mode) => {
      flyby.stop('mode-change');
      scene.setSpatialMode(mode);
      scene.setSelection(null);
      updateSpatialAids();
      scheduleAdaptiveTileRefresh(0);
    },
    onReset: () => {
      flyby.stop('reset');
      scene.resetView();
      scene.setSelection(null);
      scheduleAdaptiveTileRefresh(0);
    },
    onFocusLocal: () => {
      flyby.stop('local');
      scene.setSpatialMode('slice');
      scene.setSelection(null);
      updateSpatialAids();
      scheduleAdaptiveTileRefresh(0);
    },
    onCloseSelection: () => scene.setSelection(null),
    onLayerChange: (layerId) => activateLayer(layerId),
    onReferenceChange: (visible) => { state.showReference = visible; updateSpatialAids(); },
    onLegendChange: (visible) => { state.showLegend = visible; updateSpatialAids(); },
    onTourToggle: () => flyby.toggle(),
    onViewportTool: configureViewportTool,
    onFullscreen: toggleFullscreen,
    onAnalysisOpen: () => analysisPanel.open(),
  });
  window.addEventListener('nasadiya:full-catalogue-request', () => activateFullCloud());
  window.addEventListener('nasadiya:adaptive-catalogue-request', () => returnToAdaptiveCloud());
  window.addEventListener('nasadiya:observatory-command', (event) => event.detail?.command === 'object-search' ? searchObservedObject(event.detail?.query) : handleObservatoryCommand(event.detail?.command));
  window.addEventListener('nasadiya:performance-sample', (event) => scene.samplePerformance(Number(event.detail?.fps)));
  scene.onCameraChange(() => scheduleAdaptiveTileRefresh());
  const sharedView = observatory.sharedViewFromLocation();
  const sharedLayer = SURVEY_LAYERS[sharedView?.layerId];
  const initialLayer = sharedLayer?.installed !== false && sharedLayer ? sharedView.layerId : 'desi-dr1';
  activateLayer(initialLayer, { initial: true }).then(() => applySharedView(sharedView));
  canvas.addEventListener('pointerdown', (event) => {
    flyby.stop('manual');
    ui.preview(null);
    pointerStart = { x: event.clientX, y: event.clientY };
  });
  canvas.addEventListener('pointermove', (event) => {
    window.clearTimeout(hoverTimer);
    const position = { clientX: event.clientX, clientY: event.clientY };
    hoverTimer = window.setTimeout(() => {
      const match = matchAtPointer(position);
      ui.preview(match?.object || null, position.clientX, position.clientY);
    }, 120);
  });
  canvas.addEventListener('pointerleave', () => { window.clearTimeout(hoverTimer); ui.preview(null); });
  canvas.addEventListener('pointerup', (event) => {
    if (!pointerStart) return;
    if (Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) < 5) selectAtPointer(event);
    pointerStart = null;
  });
  const animate = (now) => {
    updateRedshiftPlayback(now);
    flyby.tick(now);
    points?.updateTime(now * 0.001);
    scene.tick(now);
    observatory.tick(now);
    requestAnimationFrame(animate);
  };
  requestAnimationFrame(animate);
}

initialise();
