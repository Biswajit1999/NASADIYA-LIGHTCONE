import { RENDERING_LIMITS } from '../config.js';

const PROFILES = Object.freeze([
  { rows: 125_000, label: 'Overview', detail: '125K' },
  { rows: 250_000, label: 'Dense', detail: '250K' },
  { rows: 500_000, label: 'Deep', detail: '500K' },
  { rows: 1_000_000, label: 'Max detail', detail: '1M' },
  { rows: 6_093_818, label: 'Full DESI', detail: '6M+' },
]);

export const DENSITY_CONTROL_REVISION = 2;
