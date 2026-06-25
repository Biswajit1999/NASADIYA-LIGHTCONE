export const SCENE_HUD_VERSION = 2;

function formatDistance(value) {
  const distance = Math.max(0, Number(value) || 0);
  return distance >= 1000 ? `${(distance / 1000).toFixed(2)} Gpc` : `${Math.round(distance)} Mpc`;
}

export class SceneHud {
  constructor(host) {
    this.element = document.createElement('section');
    this.element.className = 'scene-hud';
    this.reference = document.createElement('aside');
    this.reference.className = 'scene-hud__reference';
    this.frame = document.createElement('b');
    this.scale = document.createElement('p');
    this.redshift = document.createElement('p');
    this.reference.append(this.frame, this.scale, this.redshift);
    this.flyby = document.createElement('button');
    this.flyby.type = 'button';
    this.flyby.className = 'scene-hud__flyby';
    this.flyby.textContent = 'Start guided flyby';
    this.element.append(this.reference, this.flyby);
    host?.append(this.element);
    this.flyby.addEventListener('click', () => this.onFlybyToggle?.());
  }

  bind({ onFlybyToggle } = {}) { this.onFlybyToggle = onFlybyToggle; }

  update({ metrics = {}, state = {}, layer = null } = {}) {
    this.reference.hidden = state.spatialMode !== 'lightcone';
    this.frame.textContent = metrics.fullCatalogue ? 'Full DESI GPU cloud · 6.09M observed rows' : `${layer?.label || 'Observed survey'} · observer-centred view`;
    this.scale.textContent = `Radial extent: 0–${formatDistance(metrics.maxDistance)}`;
    this.redshift.textContent = `Redshift window: z = 0–${Number(state.maxRedshift || 0).toFixed(4)}`;
  }

  setFlyby({ active = false } = {}) {
    this.element.classList.toggle('is-flying', active);
    this.flyby.textContent = active ? 'Stop guided flyby' : 'Start guided flyby';
    this.flyby.setAttribute('aria-pressed', String(active));
  }
}
