export const LIGHTCONE_CONFIG = Object.freeze({
  displayScale: 3.0,
  defaultSliceThicknessMpc: 24,
  defaultSliceOffsetMpc: 0,
});

export const DESI_TRACERS = Object.freeze(['BGS', 'LRG', 'ELG', 'QSO']);

/**
 * Adaptive tile delivery is intentionally opt-in. The public GitHub Pages build
 * begins from the committed 125k-row overview; full-resolution tiles can stream
 * from a local build or a separately configured object-store endpoint.
 */
export const TILE_STREAMING = Object.freeze({
  'desi-dr1': {
    enabled: true,
    remoteBaseUrl: null,
    maxTiles: 18,
    maxCachedTiles: 42,
    maxLoadedRows: 180_000,
    refreshDebounceMs: 550,
  },
  'all-live': {
    enabled: true,
    // Uses the DESI tile store for depth detail while preserving the full 2MRS
    // public layer as the nearby anchor in the composite view.
    remoteBaseUrl: null,
    maxTiles: 18,
    maxCachedTiles: 42,
    maxLoadedRows: 180_000,
    refreshDebounceMs: 550,
  },
});

export const SURVEY_LAYERS = Object.freeze({
  'all-live': {
    id: 'all-live',
    label: 'Available surveys · 2MRS + DESI DR1',
    eyebrow: 'AVAILABLE SURVEYS / OBSERVED STACK',
    dataKind: 'composite',
    memberLayerIds: ['2mrs', 'desi-dr1'],
    defaultMaxRedshift: 2.5,
    defaultPointBudget: 125_000,
    defaultSpatialMode: 'lightcone',
    supportsSlice: false,
    installed: true,
    localBuild: 'Included whenever the 2MRS and DESI browser layers are available.',
  },
  '2mrs': {
    id: '2mrs',
    label: '2MRS · 43,533 spectroscopic rows',
    eyebrow: 'LOCAL UNIVERSE / 2MRS',
    dataUrl: './data/processed/2mrs/2mrs_lightcone.json',
    dataKind: 'catalog',
    defaultMaxRedshift: 0.025,
    defaultPointBudget: 44_500,
    defaultSpatialMode: 'slice',
    supportsSlice: true,
    installed: true,
    localBuild: 'Included in the public baseline.',
  },
  '2mpz': {
    id: '2mpz',
    label: '2MPZ · ~1 million photo-z galaxies',
    eyebrow: 'WIDE UNIVERSE / 2MPZ',
    dataUrl: './data/processed/2mpz/index.json',
    dataKind: 'tile-store',
    defaultMaxRedshift: 0.24,
    defaultPointBudget: 100_000,
    defaultSpatialMode: 'lightcone',
    supportsSlice: false,
    installed: false,
    localBuild: 'Awaiting a corrected, validated official source endpoint before local ingestion is re-enabled.',
  },
  'wise-sc': {
    id: 'wise-sc',
    label: 'WISE × SuperCOSMOS · ~20 million photo-z galaxies',
    eyebrow: 'WIDE UNIVERSE / WISE × SUPERCOSMOS',
    dataUrl: './data/processed/wise-sc/index.json',
    dataKind: 'tile-store',
    defaultMaxRedshift: 0.45,
    defaultPointBudget: 125_000,
    defaultSpatialMode: 'lightcone',
    supportsSlice: false,
    installed: false,
    localBuild: 'Awaiting a corrected, validated official source endpoint before local ingestion is re-enabled.',
  },
  'desi-dr1': {
    id: 'desi-dr1',
    label: 'DESI DR1 LSS · spectroscopic galaxies and quasars',
    eyebrow: 'DEEP UNIVERSE / DESI DR1',
    dataUrl: './data/processed/desi-dr1/index.json',
    dataKind: 'tile-store',
    defaultMaxRedshift: 2.5,
    defaultPointBudget: 125_000,
    defaultSpatialMode: 'lightcone',
    supportsSlice: false,
    installed: true,
    localBuild: 'scripts\\download_desi_dr1_lss.py --yes then scripts\\build_desi_dr1_tile_store.py',
  },
});

export const PALETTE = Object.freeze({
  cyan: [0.30, 0.86, 1.0],
  violet: [0.73, 0.61, 1.0],
  amber: [1.0, 0.70, 0.41],
  green: [0.47, 0.93, 0.63],
});
