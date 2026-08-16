import { formatLookback, formatNumber, formatRedshift } from '../utils/format.js';

const TRACER_COLOUR = Object.freeze({ BGS: '#ff6b5d', LRG: '#f2aa46', ELG: '#62def7', QSO: '#a681ed' });
const TRACER_ORDER = Object.freeze(['BGS', 'LRG', 'ELG', 'QSO']);
const SOURCE_COLOUR = Object.freeze({ '2mrs': '#62def7', 'desi-dr1': '#f2aa46' });
const SVG_NS = 'http://www.w3.org/2000/svg';

function svgEl(tag, attrs = {}) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  return el;
}

function emptyState(host, message) {
  host.replaceChildren();
  const p = document.createElement('p');
  p.className = 'analysis-empty';
  p.textContent = message;
  host.append(p);
}

/** Bins `values` into `bins` equal-width buckets across [0, max(values)]. */
function histogramBins(values, bins) {
  const max = values.reduce((m, v) => Math.max(m, v), 0);
  if (max <= 0) return { counts: [], max: 0, step: 0 };
  const step = max / bins;
  const counts = new Array(bins).fill(0);
  for (const value of values) {
    const index = Math.min(bins - 1, Math.floor(value / step));
    if (index >= 0) counts[index] += 1;
  }
  return { counts, max, step };
}

function renderHistogram(host, { values, color, formatX, xLabel, width = 100 }) {
  if (!values.length) return emptyState(host, 'No rows in the current view.');
  const bins = Math.min(24, Math.max(8, Math.round(Math.sqrt(values.length))));
  const { counts, max: xMax, step } = histogramBins(values, bins);
  const chartWidth = 100;
  const chartHeight = 46;
  const maxCount = counts.reduce((m, v) => Math.max(m, v), 1);
  const barWidth = chartWidth / bins;
  const svg = svgEl('svg', { viewBox: `0 0 ${chartWidth} ${chartHeight + 12}`, class: 'analysis-svg', role: 'img', 'aria-label': `${xLabel} histogram` });
  counts.forEach((count, index) => {
    const barHeight = (count / maxCount) * chartHeight;
    const rect = svgEl('rect', {
      x: (index * barWidth + 0.35).toFixed(2),
      y: (chartHeight - barHeight).toFixed(2),
      width: Math.max(0, barWidth - 0.7).toFixed(2),
      height: barHeight.toFixed(2),
      rx: 0.6,
      fill: color,
      opacity: count === 0 ? 0.08 : 0.88,
    });
    const binStart = index * step;
    const title = svgEl('title');
    title.textContent = `${formatX(binStart)} – ${formatX(binStart + step)}: ${formatNumber(count)} rows`;
    rect.append(title);
    svg.append(rect);
  });
  [0, 0.5, 1].forEach((fraction) => {
    const label = svgEl('text', { x: (fraction * chartWidth).toFixed(1), y: chartHeight + 9, class: 'analysis-axis-label', 'text-anchor': fraction === 0 ? 'start' : fraction === 1 ? 'end' : 'middle' });
    label.textContent = formatX(fraction * xMax);
    svg.append(label);
  });
  host.replaceChildren(svg);
}

function renderTracerChart(host, tracerCounts) {
  const entries = TRACER_ORDER.map((tracer) => [tracer, Number(tracerCounts?.[tracer]) || 0]).filter(([, count]) => count > 0);
  if (!entries.length) return emptyState(host, 'Tracer classes are only available for DESI layers.');
  const maxCount = entries.reduce((m, [, count]) => Math.max(m, count), 1);
  const chartWidth = 100;
  const chartHeight = 46;
  const barWidth = chartWidth / entries.length;
  const svg = svgEl('svg', { viewBox: `0 0 ${chartWidth} ${chartHeight + 12}`, class: 'analysis-svg', role: 'img', 'aria-label': 'Tracer class counts' });
  entries.forEach(([tracer, count], index) => {
    const barHeight = (count / maxCount) * chartHeight;
    const rect = svgEl('rect', {
      x: (index * barWidth + barWidth * 0.16).toFixed(2),
      y: (chartHeight - barHeight).toFixed(2),
      width: (barWidth * 0.68).toFixed(2),
      height: barHeight.toFixed(2),
      rx: 0.8,
      fill: TRACER_COLOUR[tracer],
    });
    const title = svgEl('title');
    title.textContent = `${tracer}: ${formatNumber(count)} rows`;
    rect.append(title);
    svg.append(rect);
    const label = svgEl('text', { x: (index * barWidth + barWidth / 2).toFixed(1), y: chartHeight + 9, class: 'analysis-axis-label', 'text-anchor': 'middle' });
    label.textContent = tracer;
    svg.append(label);
  });
  host.replaceChildren(svg);
}

function renderSkyFootprint(host, objects, composite) {
  if (!objects.length) return emptyState(host, 'No rows in the current view.');
  const chartWidth = 200;
  const chartHeight = 100;
  const svg = svgEl('svg', { viewBox: `0 0 ${chartWidth} ${chartHeight}`, class: 'analysis-svg analysis-svg--sky', role: 'img', 'aria-label': 'Sky footprint (RA vs Dec)' });
  svg.append(svgEl('rect', { x: 0, y: 0, width: chartWidth, height: chartHeight, class: 'analysis-sky-frame' }));
  [0.25, 0.5, 0.75].forEach((fraction) => svg.append(svgEl('line', { x1: 0, x2: chartWidth, y1: chartHeight * fraction, y2: chartHeight * fraction, class: 'analysis-gridline' })));
  const group = svgEl('g');
  const step = Math.max(1, Math.floor(objects.length / 6000));
  for (let index = 0; index < objects.length; index += step) {
    const object = objects[index];
    const ra = Number(object.ra_deg);
    const dec = Number(object.dec_deg);
    if (!Number.isFinite(ra) || !Number.isFinite(dec)) continue;
    const x = (ra / 360) * chartWidth;
    const y = ((90 - dec) / 180) * chartHeight;
    const color = composite ? (SOURCE_COLOUR[object.source_layer] || '#7dedad') : (TRACER_COLOUR[object.tracer] || '#62def7');
    group.append(svgEl('circle', { cx: x.toFixed(2), cy: y.toFixed(2), r: 0.55, fill: color, opacity: 0.55 }));
  }
  svg.append(group);
  host.replaceChildren(svg);
}

function legendFor(host, entries) {
  const legend = document.createElement('div');
  legend.className = 'analysis-legend';
  entries.forEach(([label, color]) => {
    const item = document.createElement('span');
    const dot = document.createElement('i');
    dot.style.background = color;
    item.append(dot, document.createTextNode(label));
    legend.append(item);
  });
  host.append(legend);
}

/**
 * Analysis panel driven entirely by rows already loaded in the browser (the
 * deterministic overview array, plus the true catalogue-wide tracer counts
 * from the active renderable's metrics). It never fetches or fabricates
 * additional rows; every plot states its sample size honestly.
 */
export class AnalysisPanel {
  constructor() {
    this.dom = {
      backdrop: document.querySelector('#analysis-modal'),
      close: document.querySelector('#close-analysis'),
      sampleNote: document.querySelector('#analysis-sample-note'),
      redshift: document.querySelector('#chart-redshift'),
      tracer: document.querySelector('#chart-tracer'),
      sky: document.querySelector('#chart-sky'),
      lookback: document.querySelector('#chart-lookback'),
      blocks: [...document.querySelectorAll('.analysis-block')],
    };
    this.lastPayload = null;
    this.dom.close?.addEventListener('click', () => this.close());
    this.dom.backdrop?.addEventListener('click', (event) => { if (event.target === this.dom.backdrop) this.close(); });
    window.addEventListener('keydown', (event) => { if (event.key === 'Escape' && this.isOpen()) this.close(); });
    this.dom.blocks.forEach((block) => {
      const toggle = block.querySelector('.analysis-block-toggle');
      toggle?.addEventListener('click', () => {
        const collapsed = block.classList.toggle('is-collapsed');
        toggle.setAttribute('aria-expanded', String(!collapsed));
        toggle.textContent = collapsed ? '+' : '−';
      });
    });
  }

  isOpen() { return this.dom.backdrop ? !this.dom.backdrop.hidden : false; }

  open() {
    if (!this.dom.backdrop) return;
    this.dom.backdrop.hidden = false;
    if (this.lastPayload) this.render(this.lastPayload);
  }

  close() { if (this.dom.backdrop) this.dom.backdrop.hidden = true; }
  toggle() { this.isOpen() ? this.close() : this.open(); }

  /** Call whenever the active layer, filters or display state change. */
  update(payload) {
    this.lastPayload = payload;
    if (this.isOpen()) this.render(payload);
  }

  render({ objects = [], metrics = {}, meta = {} }) {
    const composite = Boolean(meta.composite);
    const sampleIsFull = !metrics.fullCatalogue;
    if (this.dom.sampleNote) {
      this.dom.sampleNote.textContent = sampleIsFull
        ? `Computed from all ${formatNumber(objects.length)} rows in the loaded browser overview.`
        : `Redshift, sky and look-back plots use the ${formatNumber(objects.length)}-row browser overview (not all ${formatNumber(metrics.gpuResidentCount || 0)} GPU-resident rows). Tracer counts below are catalogue-wide.`;
    }
    if (this.dom.redshift) renderHistogram(this.dom.redshift, { values: objects.map((o) => Number(o.redshift) || 0), color: '#62def7', formatX: formatRedshift, xLabel: 'redshift' });
    if (this.dom.tracer) {
      this.dom.tracer.replaceChildren();
      renderTracerChart(this.dom.tracer, metrics.tracerCounts);
      if (Object.keys(metrics.tracerCounts || {}).length) legendFor(this.dom.tracer, TRACER_ORDER.filter((t) => metrics.tracerCounts?.[t]).map((t) => [t, TRACER_COLOUR[t]]));
    }
    if (this.dom.sky) {
      this.dom.sky.replaceChildren();
      renderSkyFootprint(this.dom.sky, objects, composite);
      if (composite) legendFor(this.dom.sky, [['2MRS', SOURCE_COLOUR['2mrs']], ['DESI DR1', SOURCE_COLOUR['desi-dr1']]]);
    }
    if (this.dom.lookback) renderHistogram(this.dom.lookback, { values: objects.map((o) => Number(o.lookback_time_gyr) || 0), color: '#a681ed', formatX: (v) => formatLookback(v), xLabel: 'look-back time' });
  }
}
