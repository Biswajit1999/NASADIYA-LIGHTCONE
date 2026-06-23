import * as THREE from 'three';
import { DESI_TRACERS, SURVEY_LAYERS } from './config.js';
import { loadCatalog, loadTileStoreOverview } from './core/catalog-loader.js';
import { LightconeScene } from './core/lightcone-scene.js';
import { SurveyPoints } from './core/survey-points.js';
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
  tracerFilters: Object.fromEntries(DESI_TRACERS.map((tracer) => [tracer, true])),
};

const canvas = document.querySelector('#lightcone-canvas');
const scene = new LightconeScene(canvas);
const ui = new LightconeInterface();
const raycaster = new THREE.Raycaster();
raycaster.params.Points.threshold = 9;
const pointer = new THREE.Vector2();
let points = null;
let pointerStart = null;
let loadSequence = 0;

function maxField(objects, field) { return objects.reduce((maximum, object) => Math.max(maximum, Number(object[field]) || 0), 0); }
function currentLayer() { return SURVEY_LAYERS[state.layerId]; }
function applyState() { if (!points) return; ui.updateTelemetry(points.applyState(state), state); }
function selectAtPointer(event) {
  if (!points) return;
  const bounds = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
  pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
  raycaster.setFromCamera(pointer, scene.camera);
  const match = points.selectFromRaycaster(raycaster);
  if (match) { scene.setSelection(points.getDisplayPosition(match.index)); ui.inspect(match.object); }
}
async function loadLayerPayload(layer) { return layer.dataKind === 'catalog' ? loadCatalog(layer.dataUrl, layer.label) : loadTileStoreOverview(layer.dataUrl, layer.label); }
function loadingText(layer) {
  const tiled = layer.dataKind === 'tile-store';
  return { title: tiled ? `Opening ${layer.label.split(' · ')[0]}` : 'Opening the observed local Universe', copy: tiled ? 'Reading the tile-store index and deterministic overview of real observed source rows…' : 'Reading the 2MRS browser catalogue and its source provenance…' };
}
async function activateLayer(layerId, { initial = false } = {}) {
  const requestedLayer = SURVEY_LAYERS[layerId];
  const previousLayer = currentLayer();
  if (!requestedLayer) return;
  const requestId = ++loadSequence;
  const start = loadingText(requestedLayer);
  ui.setLoadingState({ ...start, dataset: requestedLayer.label, count: 'Preparing data layer', progress: 18 });
  try {
    const { meta, objects } = await loadLayerPayload(requestedLayer);
    if (requestId !== loadSequence) return;
    ui.setLoadingState({ title: `Selecting the ${meta.measurement_kind === 'photometric' ? 'wide photometric' : 'spectroscopic'} survey field`, copy: meta.measurement_kind === 'photometric' ? 'Placing real overview rows in an observer-centred lightcone; published radial uncertainty remains attached to every accepted source row.' : 'Placing real observed rows in an observer-centred survey volume…', dataset: meta.dataset_label || requestedLayer.label, count: `${new Intl.NumberFormat('en-GB').format(meta.object_count || objects.length)} observed source rows`, progress: 64 });
    const nextPoints = new SurveyPoints(objects, meta);
    const maxRedshift = maxField(objects, 'redshift');
    const maxDistance = maxField(objects, 'comoving_distance_mpc');
    if (points) { scene.world.remove(points.points); points.dispose(); }
    points = nextPoints;
    scene.world.add(points.points);
    state.layerId = requestedLayer.id;
    state.maxRedshift = Math.min(requestedLayer.defaultMaxRedshift, Math.max(0.003, maxRedshift));
    state.pointBudget = Math.min(requestedLayer.defaultPointBudget, objects.length);
    state.spatialMode = requestedLayer.defaultSpatialMode;
    state.sliceThickness = requestedLayer.supportsSlice ? 24 : state.sliceThickness;
    state.sliceOffset = requestedLayer.supportsSlice ? 0 : state.sliceOffset;
    scene.setDatasetExtent(maxDistance);
    scene.setSpatialMode(state.spatialMode, { immediate: true });
    scene.setSelection(null);
    ui.setDataReady(meta, maxRedshift, state, requestedLayer);
    applyState();
    document.title = `NĀSADĪYA LIGHTCONE — ${meta.source_survey || requestedLayer.id}`;
  } catch (error) {
    if (requestId !== loadSequence) return;
    if (initial) { ui.showLoadError(error.message || 'Unknown catalogue-loading problem.'); return; }
    ui.hideLoading();
    ui.showLayerUnavailable(requestedLayer, previousLayer);
  }
}
function initialise() {
  ui.bind({
    getState: () => state,
    onStateChange: applyState,
    onSpatialModeChange: (mode) => { scene.setSpatialMode(mode); scene.setSelection(null); },
    onReset: () => { scene.resetView(); scene.setSelection(null); },
    onFocusLocal: () => { scene.setSpatialMode('slice'); scene.setSelection(null); },
    onCloseSelection: () => scene.setSelection(null),
    onLayerChange: (layerId) => activateLayer(layerId),
  });
  document.querySelectorAll('[data-layer-shortcut]').forEach((button) => {
    button.addEventListener('click', () => activateLayer(button.dataset.layerShortcut));
  });
  activateLayer('2mrs', { initial: true });
  canvas.addEventListener('pointerdown', (event) => { pointerStart = { x: event.clientX, y: event.clientY }; });
  canvas.addEventListener('pointerup', (event) => {
    if (!pointerStart) return;
    if (Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) < 5) selectAtPointer(event);
    pointerStart = null;
  });
  const animate = (now) => { points?.updateTime(now * 0.001); scene.tick(now); requestAnimationFrame(animate); };
  requestAnimationFrame(animate);
}
initialise();
