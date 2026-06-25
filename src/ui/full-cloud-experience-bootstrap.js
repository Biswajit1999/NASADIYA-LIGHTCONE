import { LightconeScene } from '../core/lightcone-scene.js';
import { GuidedFlyby } from '../core/guided-flyby.js';
import { SurveyReferenceFrame } from '../core/reference-frame.js';
import { LightconeInterface } from './lightcone-interface.js';
import { SceneHud } from './scene-hud.js';

function ensureExperience(scene) {
  if (scene.fullCloudExperience) return scene.fullCloudExperience;
  const reference = new SurveyReferenceFrame(scene.world);
  reference.setExtent(scene.datasetMaxDistanceMpc);
  reference.setVisible(scene.mode === 'lightcone');
  const hud = new SceneHud(document.querySelector('#explorer'));
  const flyby = new GuidedFlyby(scene);
  hud.bind({
    onFlybyToggle: () => {
      if (!flyby.active && scene.mode !== 'lightcone') scene.setSpatialMode('lightcone', { immediate: true });
      flyby.toggle();
    },
  });
  flyby.onChange((status) => hud.setFlyby(status));
  scene.fullCloudExperience = { reference, hud, flyby };
  return scene.fullCloudExperience;
}

const originalTick = LightconeScene.prototype.tick;
LightconeScene.prototype.tick = function calibratedTick(now) {
  window.__nasadiyaScene = this;
  const experience = ensureExperience(this);
  experience.flyby.tick(now);
  originalTick.call(this, now);
};

const originalSetExtent = LightconeScene.prototype.setDatasetExtent;
LightconeScene.prototype.setDatasetExtent = function calibratedExtent(maxDistanceMpc) {
  originalSetExtent.call(this, maxDistanceMpc);
  this.fullCloudExperience?.reference.setExtent(this.datasetMaxDistanceMpc);
};

const originalSpatialMode = LightconeScene.prototype.setSpatialMode;
LightconeScene.prototype.setSpatialMode = function calibratedSpatialMode(mode, options) {
  if (mode !== 'lightcone') this.fullCloudExperience?.flyby.stop('mode-change');
  originalSpatialMode.call(this, mode, options);
  this.fullCloudExperience?.reference.setVisible(mode === 'lightcone');
};

const originalTelemetry = LightconeInterface.prototype.updateTelemetry;
LightconeInterface.prototype.updateTelemetry = function calibratedTelemetry(metrics, state) {
  originalTelemetry.call(this, metrics, state);
  const scene = window.__nasadiyaScene;
  if (!scene) return;
  const experience = ensureExperience(scene);
  experience.hud.update({ metrics, state, layer: this.currentLayer });
  scene.renderer.toneMappingExposure = metrics?.fullCatalogue ? 0.93 : 1.08;
  scene.scene.fog.density = metrics?.fullCatalogue ? 0.00023 : 0.00030;
};
