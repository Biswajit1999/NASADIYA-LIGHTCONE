import * as THREE from 'three';
import { LIGHTCONE_CONFIG } from './config.js';
import { loadCatalog } from './core/catalog-loader.js';
import { LightconeScene } from './core/lightcone-scene.js';
import { SurveyPoints } from './core/survey-points.js';
import { LightconeInterface } from './ui/lightcone-interface.js';

const state = {
  maxRedshift: LIGHTCONE_CONFIG.defaultMaxRedshift,
  pointBudget: LIGHTCONE_CONFIG.defaultPointBudget,
  sliceThickness: LIGHTCONE_CONFIG.defaultSliceThicknessMpc,
  sliceOffset: LIGHTCONE_CONFIG.defaultSliceOffsetMpc,
  showGalaxies: true,
  spatialMode: 'slice',
  viewMode: 'catalog',
};

const canvas = document.querySelector('#lightcone-canvas');
const scene = new LightconeScene(canvas);
const ui = new LightconeInterface();
const raycaster = new THREE.Raycaster();
raycaster.params.Points.threshold = 9;
const pointer = new THREE.Vector2();
let points = null;
let pointerStart = null;

function applyState() {
  if (!points) return;
  const metrics = points.applyState(state);
  ui.updateTelemetry(metrics, state);
}

function selectAtPointer(event) {
  if (!points) return;
  const bounds = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
  pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
  raycaster.setFromCamera(pointer, scene.camera);
  const match = points.selectFromRaycaster(raycaster);
  if (match) {
    const displayPosition = points.getDisplayPosition(match.index);
    scene.setSelection(displayPosition);
    ui.inspect(match.object);
  }
}

async function initialise() {
  ui.setLoadingState({
    title: 'Opening the observed local Universe',
    copy: 'Reading the 2MRS browser catalogue and its source provenance…',
    dataset: '2MRS Table 3',
    count: 'Preparing data layer',
    progress: 18,
  });

  try {
    const { meta, objects } = await loadCatalog(LIGHTCONE_CONFIG.dataUrl);
    ui.setLoadingState({
      title: 'Selecting the local galaxy field',
      copy: 'Placing real observed 2MRS rows in an observer-centred Cartesian slice…',
      dataset: meta.dataset_label || LIGHTCONE_CONFIG.dataLabel,
      count: `${new Intl.NumberFormat('en-GB').format(objects.length)} observed rows`,
      progress: 64,
    });

    points = new SurveyPoints(objects);
    scene.world.add(points.points);
    const maxRedshift = Math.max(...objects.map((object) => Number(object.redshift) || 0));

    ui.bind({
      getState: () => state,
      onStateChange: applyState,
      onSpatialModeChange: (mode) => {
        scene.setSpatialMode(mode);
        scene.setSelection(null);
      },
      onReset: () => {
        scene.resetView();
        scene.setSelection(null);
      },
      onFocusLocal: () => {
        scene.setSpatialMode('slice');
        scene.setSelection(null);
      },
      onCloseSelection: () => scene.setSelection(null),
    });

    ui.setDataReady(meta, maxRedshift);
    scene.setSpatialMode('slice', { immediate: true });
    ui.syncControlsFromState(state);
    applyState();
  } catch (error) {
    ui.showLoadError(error.message || 'Unknown catalogue-loading problem.');
  }

  canvas.addEventListener('pointerdown', (event) => {
    pointerStart = { x: event.clientX, y: event.clientY };
  });
  canvas.addEventListener('pointerup', (event) => {
    if (!pointerStart) return;
    const movement = Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y);
    if (movement < 5) selectAtPointer(event);
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
