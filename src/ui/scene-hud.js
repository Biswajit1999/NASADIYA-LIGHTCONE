const STYLE_ID = 'nasadiya-full-cloud-experience-styles';

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const link = document.createElement('link');
  link.id = STYLE_ID;
  link.rel = 'stylesheet';
  link.href = './styles/full-cloud-experience.css?v=1';
  document.head.append(link);
}

function formatDistance(value) {
  const distance = Math.max(0, Number(value) || 0);
  return distance >= 1000 ? `${(distance / 1000).toFixed(2)} Gpc` : `${Math.round(distance).toLocaleString('en-GB')} Mpc`;
}

function formatLookback(value) {
  const time = Math.max(0, Number(value) || 0);
  return time >= 1 ? `${time.toFixed(2)} Gyr` : `${Math.round(time * 1000)} Myr`;
}

function compactRows(value) {
  const rows = Math.max(0, Number(value) || 0);
  return rows >= 1_000_000 ? `${(rows / 1_000_000).toFixed(rows % 1_000_000 ? 2 : 0)}M` : `${Math.round(rows / 1000)}K`;
}

export class SceneHud {
  constructor(host) {
    ensureStyles();
    this.element = document.createElement('section');
    this.element.className = 'scene-hud';
    this.reference = document.createElement('aside');
    this.reference.className = 'scene-hud__reference';
    this.reference.innerHTML = '<span class="scene-hud__kicker">● SPATIAL REFERENCE</span><b data-frame>Observer-centred Cartesian view</b><dl><div><dt>Origin</dt><dd>Observer · z = 0</dd></div><div><dt>Radial extent</dt><dd data-scale>—</dd></div><div><dt>Redshift window</dt><dd data-redshift>—</dd></div><div><dt>Look-back ceiling</dt><dd data-lookback>—</dd></div></dl><p data-note>X / Y / Z are comoving visual coordinates in Mpc.</p>';
    this.flybyWrap = document.createElement('div');
    this.flybyWrap.className = 'scene-hud__flyby-wrap';
    this.flyby = document.createElement('button');
    this.flyby.type = 'button';
    this.flyby.className = 'scene-hud__flyby';
    this.flyby.innerHTML = '<span>GUIDED NAVIGATION</span><b data-flyby-label>Start flyby</b><em data-flyby-state>OFF</em>';
    this.flybyCopy = document.createElement('p');
    this.flybyCopy.className = 'scene-hud__flyby-copy';
    this.flybyCopy.textContent = 'Outer footprint → interior passage → full overview';
    this.flybyWrap.append(this.flyby, this.flybyCopy);
    this.element.append(this.reference, this.flybyWrap);
    host?.append(this.element);
    this.dom = {
      frame: this.reference.querySelector('[data-frame]'),
      scale: this.reference.querySelector('[data-scale]'),
      redshift: this.reference.querySelector('[data-redshift]'),
      lookback: this.reference.querySelector('[data-lookback]'),
      note: this.reference.querySelector('[data-note]'),
      flybyLabel: this.flyby.querySelector('[data-flyby-label]'),
      flybyState: this.flyby.querySelector('[data-flyby-state]'),
    };
    this.flyby.addEventListener('click', () => this.onFlybyToggle?.());
  }

  bind({ onFlybyToggle } = {}) { this.onFlybyToggle = onFlybyToggle; }

  update({ metrics = {}, state = {}, layer = null } = {}) {
    const full = Boolean(metrics.fullCatalogue);
    const rows = Number(metrics.gpuResidentCount || metrics.visibleCount || 0);
    this.reference.hidden = state.spatialMode !== 'lightcone';
    this.dom.frame.textContent = full ? `Full DESI GPU cloud · ${compactRows(rows)} resident rows` : `${layer?.label || 'Observed survey'} · observer-centred view`;
    this.dom.scale.textContent = metrics.maxDistance ? `0–${formatDistance(metrics.maxDistance)}` : 'Loading scale…';
    this.dom.redshift.textContent = `z = 0–${Number(state.maxRedshift || 0).toFixed(4)}`;
    this.dom.lookback.textContent = metrics.maxLookback ? formatLookback(metrics.maxLookback) : '—';
    this.dom.note.textContent = full
      ? 'All accepted DESI rows are resident in GPU buffers. Redshift and tracer filters change visibility without changing the catalogue.'
      : 'X / Y / Z are comoving visual coordinates in Mpc. Survey footprint is measurement geometry, not a reconstructed density field.';
  }

  setFlyby({ active = false, phase = 'overview', progress = 0, reason = null } = {}) {
    this.element.classList.toggle('is-flying', active);
    this.flyby.setAttribute('aria-pressed', String(active));
    this.dom.flybyLabel.textContent = active ? 'Stop flyby' : 'Start flyby';
    this.dom.flybyState.textContent = active ? 'ON' : 'OFF';
    if (active) this.flybyCopy.textContent = `${phase} · ${Math.round(progress * 100)}% · drag or scroll to take control`;
    else if (reason === 'manual') this.flybyCopy.textContent = 'Manual navigation restored. Use the switch to restart the guided route.';
    else this.flybyCopy.textContent = 'Outer footprint → interior passage → full overview';
  }
}
