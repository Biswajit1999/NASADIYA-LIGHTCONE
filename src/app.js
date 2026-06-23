import * as THREE from 'three';

import { DESI_TRACERS, SURVEY_LAYERS, TILE_STREAMING } from './config.js';
import { loadCatalog, loadTileStoreOverview } from './core/catalog-loader.js';
import { LightconeScene } from './core/lightcone-scene.js';
import { SurveyPoints } from './core/survey-points.js';
import { TileStreamer } from './core/tile-streamer.js';
import { LightconeInterface } from './ui/lightcone-interface.js';

const state = {
  layerId: '2mrs',
  maxRedshift: SURVEY_LAYERS['2mrs'].defaultMaxRedshift,
  pointBudget: SURVEY_LAYERS['2mrs'].defaultPointBudget,
  sliceThickness: 24,
  sliceOffset: 0,
  showGalaxies: true,
  spatialMode: SURVEY_LAYERS['2mrs'].defaultSpatialMode,
  viewMode: 'catalog',
  tileStreaming: false,
  tracerFilters: Object.fromEntries(DESI_TRACERS.map((tracer) => [tracer, true])),
};

const canvas = document.querySelector('#lightcone-canvas');
const scene = new LightconeScene(canvas);
const ui = new LightconeInterface();
const raycaster = new THREE.Raycaster();
raycaster.params.Points.threshold = 9;
const pointer = new THREE.Vector2();

let points = null;
let overviewObjects = [];
let activeMeta = null;
let tileStreamer = null;
let tileRefreshTimer = null;
let tileRefreshBusy = false;
let pointerStart = null;
let loadSequence = 0;

function maxField(objects, field) {
  return objects.reduce((maximum, object) => Math.max(maximum, Number(object[field]) || 0), 0);
}

function currentLayer() {
  return SURVEY_LAYERS[state.layerId];
}

function replacePoints(objects, meta) {
  const nextPoints = new SurveyPoints(objects, meta);
  if (points) {
    scene.world.remove(points.points);
    points.dispose();
  }
  points = nextPoints;
  scene.world.add(points.points);
  scene.setDatasetExtent(maxField(objects, 'comoving_distance_mpc'));
  scene.setSelection(null);
}

function applyState({ scheduleTiles = true } = {}) {
  if (!points) return;
  ui.updateTelemetry(points.applyState(state), state);
  if (scheduleTiles) scheduleAdaptiveTileRefresh();
}

function tileStreamingConfig() {
  return TILE_STREAMING[state.layerId] || null;
}

function scheduleAdaptiveTileRefresh(delay = null) {
  if (!tileStreamer || !state.tileStreaming || tileRefreshBusy) return;
  const config = tileStreamingConfig();
  if (!config) return;
  window.clearTimeout(tileRefreshTimer);
  tileRefreshTimer = window.setTimeout(() => refreshAdaptiveTiles(), delay ?? config.refreshDebounceMs);
}

async function refreshAdaptiveTiles() {
  if (!tileStreamer || !state.tileStreaming || tileRefreshBusy) return;
  const requestId = loadSequence;
  tileRefreshBusy = true;
  try {
    const result = await tileStreamer.update(scene.camera, state);
    if (requestId !== loadSequence || !tileStreamer || !state.tileStreaming) return;
    if (result.changed && result.objects?.length) {
      replacePoints(result.objects, activeMeta);
      applyState({ scheduleTiles: false });
    }
    ui.setTileStreamingStatus({ available: true, active: true, ...result });
  } catch (error) {
    state.tileStreaming = false;
    ui.setTileStreamingStatus({ available: false, active: false, reason: error?.message || 'Adaptive tile loading failed.' });
    replacePoints(overviewObjects, activeMeta);
    applyState({ scheduleTiles: false });
  } finally {
    tileRefreshBusy = false;
  }
}

function selectAtPointer(event) {
  if (!points) return;
  const bounds = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
  pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
  raycaster.setFromCamera(pointer, scene.camera);
  const match = points.selectFromRaycaster(raycaster);
  if (match) {
    scene.setSelection(points.getDisplayPosition(match.index));
    ui.inspect(match.object);
  }
}

async function loadLayerPayload(layer) {
  return layer.dataKind === 'catalog'
    ? loadCatalog(layer.dataUrl, layer.label)
    : loadTileStoreOverview(layer.dataUrl, layer.label);
}

function loadingText(layer) {
  const tiled = layer.dataKind === 'tile-store';
  return {
    title: tiled ? `Opening ${layer.label.split(' · ')[0]}` : 'Opening the observed local Universe',
    copy: tiled
      ? 'Reading the tile-store index and deterministic overview of real observed source rows…'
      : 'Reading the 2MRS browser catalogue and its source provenance…',
  };
}

async function configureAdaptiveTiles(layer, meta, requestId) {
  tileStreamer = null;
  state.tileStreaming = false;
  const config = TILE_STREAMING[layer.id];
  if (!config?.enabled || !meta.tile_manifest || !meta.tile_index_url || !meta.tile_count) {
    ui.setTileStreamingStatus({ available: false, active: false, reason: 'This layer has no adaptive tile store.' });
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
  if (!requestedLayer) return;
  const requestId = ++loadSequence;
  window.clearTimeout(tileRefreshTimer);
  tileStreamer = null;
  state.tileStreaming = false;
  const start = loadingText(requestedLayer);
  ui.setLoadingState({ ...start, dataset: requestedLayer.label, count: 'Preparing data layer', progress: 18 });

  try {
    const { meta, objects } = await loadLayerPayload(requestedLayer);
    if (requestId !== loadSequence) return;
    ui.setLoadingState({
      title: `Selecting the ${meta.measurement_kind === 'photometric' ? 'wide photometric' : 'spectroscopic'} survey field`,
      copy: meta.measurement_kind === 'photometric'
        ? 'Placing real overview rows in an observer-centred lightcone; published radial uncertainty remains attached to every accepted source row.'
        : 'Placing real observed rows in an observer-centred survey volume…',
      dataset: meta.dataset_label || requestedLayer.label,
      count: `${new Intl.NumberFormat('en-GB').format(meta.object_count || objects.length)} observed source rows`,
      progress: 64,
    });

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
  } catch (error) {
    if (requestId !== loadSequence) return;
    if (initial) {
      ui.showLoadError(error.message || 'Unknown catalogue-loading problem.');
      return;
    }
    ui.hideLoading();
    ui.showLayerUnavailable(requestedLayer, previousLayer);
  }
}

function initialise() {
  ui.bind({
    getState: () => state,
    onStateChange: () => applyState(),
    onSpatialModeChange: (mode) => {
      scene.setSpatialMode(mode);
      scene.setSelection(null);
      scheduleAdaptiveTileRefresh(0);
    },
    onReset: () => {
      scene.resetView();
      scene.setSelection(null);
      scheduleAdaptiveTileRefresh(0);
    },
    onFocusLocal: () => {
      scene.setSpatialMode('slice');
      scene.setSelection(null);
      scheduleAdaptiveTileRefresh(0);
    },
    onCloseSelection: () => scene.setSelection(null),
    onLayerChange: (layerId) => activateLayer(layerId),
  });

  document.querySelectorAll('[data-layer-shortcut]').forEach((button) => {
    button.addEventListener('click', () => activateLayer(button.dataset.layerShortcut));
  });
  scene.onCameraChange(() => scheduleAdaptiveTileRefresh());
  activateLayer('2mrs', { initial: true });

  canvas.addEventListener('pointerdown', (event) => {
    pointerStart = { x: event.clientX, y: event.clientY };
  });
  canvas.addEventListener('pointerup', (event) => {
    if (!pointerStart) return;
    if (Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) < 5) selectAtPointer(event);
    pointerStart = null;
  });

  const animate = (now) => {
    points?.updateTime(now * 0.001);
    scene.tick(now);
    requestAnimationFrame(animate);
  };
  requestAnimationFrame(animate);
}

initialise();
