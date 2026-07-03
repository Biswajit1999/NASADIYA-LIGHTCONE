const STATUS_LABELS = Object.freeze({
  deployed: 'DEPLOYED',
  blocked: 'SOURCE GATE',
  planned: 'PLANNED',
});

function rowFor(layer) {
  const row = document.createElement('article');
  row.className = `mission-queue-row is-${layer.readiness}`;
  const status = document.createElement('span');
  status.textContent = STATUS_LABELS[layer.readiness] || 'REVIEW';
  const copy = document.createElement('div');
  const label = document.createElement('b');
  label.textContent = layer.label;
  const measurement = document.createElement('small');
  measurement.textContent = layer.measurement_kind.replaceAll('-', ' ');
  copy.append(label, measurement);
  row.append(status, copy);
  return row;
}

export class SurveyReadinessPanel {
  constructor({ url = './data/registry/surveys.json' } = {}) {
    this.url = url;
    this.toggle = document.querySelector('#mission-queue-toggle');
    this.list = document.querySelector('#mission-queue-list');
    this.toggle?.addEventListener('click', () => this.setOpen(this.list?.hidden));
    this.load();
  }

  setOpen(open) {
    if (!this.list) return;
    this.list.hidden = !open;
    this.toggle?.setAttribute('aria-expanded', String(open));
  }

  render(layers) {
    this.list.replaceChildren();
    const queued = layers.filter((layer) => layer.readiness !== 'deployed');
    if (!queued.length) {
      const empty = document.createElement('p');
      empty.className = 'mission-queue-state';
      empty.textContent = 'No future survey adapters are registered.';
      this.list.append(empty);
      return;
    }
    queued.forEach((layer) => this.list.append(rowFor(layer)));
    const note = document.createElement('p');
    note.className = 'mission-queue-note';
    note.textContent = 'Planned means architecture-ready, not data-ready. Every layer must pass its source and uncertainty contract.';
    this.list.append(note);
    const count = this.toggle?.querySelector('em');
    if (count) count.textContent = `${queued.length} adapters`;
  }

  showError(message) {
    this.list.replaceChildren();
    const error = document.createElement('p');
    error.className = 'mission-queue-state is-error';
    error.textContent = message;
    this.list.append(error);
  }

  async load() {
    if (!this.list) return;
    try {
      const response = await fetch(this.url, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Registry returned ${response.status}.`);
      const registry = await response.json();
      if (!Array.isArray(registry.layers)) throw new Error('Registry has no layer list.');
      this.render(registry.layers);
    } catch (error) {
      this.showError(error?.message || 'Survey registry could not be loaded.');
    } finally {
      this.list.setAttribute('aria-busy', 'false');
    }
  }
}
