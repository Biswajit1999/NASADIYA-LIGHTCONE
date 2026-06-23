function fail(message) {
  throw new Error(message);
}

export const DESI_TRACERS = Object.freeze(['BGS', 'LRG', 'ELG', 'QSO']);

export function extractDesiTracer(objectId) {
  const parts = String(objectId ?? '').split(':');
  if (parts.length < 3 || parts[0].toLowerCase() !== 'desi-dr1') return null;
  const tracer = String(parts[1] ?? '').toUpperCase();
  return DESI_TRACERS.includes(tracer) ? tracer : null;
}

async function fetchJson(url, datasetLabel, options = {}) {
  const response = await fetch(url, { cache: 'no-cache', ...options });
  if (!response.ok) {
    if (response.status === 404) fail(`${datasetLabel} is not installed in this deployment.`);
    fail(`Could not load ${datasetLabel} (${response.status} ${response.statusText}).`);
  }
  return response.json();
}

function observedObjects(payload, datasetLabel) {
  if (!payload || payload.meta?.is_synthetic !== false) {
    fail(`Rejected ${datasetLabel}: explicit observed-data provenance is required.`);
  }
  if (!Array.isArray(payload.objects) || !payload.objects.length) {
    fail(`${datasetLabel} did not contain renderable observed objects.`);
  }
  const objects = payload.objects.filter((object) => {
    const required = ['x_mpc', 'y_mpc', 'z_mpc', 'redshift'];
    return object.is_synthetic === false && required.every((field) => Number.isFinite(Number(object[field])));
  });
  if (!objects.length) fail(`No observed ${datasetLabel} rows passed browser validation.`);
  return { meta: payload.meta, objects };
}

export async function loadCatalog(url, label = 'the browser catalogue') {
  const payload = await fetchJson(url, label);
  return observedObjects(payload, label);
}

function objectFromRecord(columns, values, dataset) {
  const record = Object.fromEntries(columns.map((column, index) => [column, values[index] ?? null]));
  return {
    ...record,
    name: record.object_id,
    tracer: record.tracer ?? extractDesiTracer(record.object_id),
    source_survey: dataset.survey,
    source_release: dataset.release,
    source_table: dataset.dataset_id,
    source_url: dataset.source_url,
    citation_key: dataset.citation_key,
    measurement_kind: dataset.measurement_kind,
    object_type: dataset.object_type,
    is_synthetic: false,
    distance_note: dataset.distance_note,
    magnitude: Number(record.magnitude),
  };
}

function validTileObject(object, kind) {
  const core = ['x_mpc', 'y_mpc', 'z_mpc', 'redshift'].every((field) => Number.isFinite(Number(object[field])));
  return core && (kind !== 'photometric' || (Number.isFinite(Number(object.redshift_error)) && Number(object.redshift_error) > 0));
}

function objectsFromRecords(records, columns, dataset, kind) {
  return records
    .map((values) => objectFromRecord(columns, values, dataset))
    .filter((object) => validTileObject(object, kind));
}

function asDirectoryUrl(url) {
  const value = String(url);
  return value.endsWith('/') ? value : `${value}/`;
}

export function resolveTileUrl(entry, indexUrl, remoteBaseUrl = null) {
  if (!entry?.path) fail('Tile metadata is missing its relative path.');
  const base = remoteBaseUrl
    ? new URL(asDirectoryUrl(remoteBaseUrl), window.location.href)
    : new URL('.', new URL(indexUrl, window.location.href));
  return new URL(entry.path, base).toString();
}

export async function probeTileStoreDelivery(manifest, indexUrl, { remoteBaseUrl = null } = {}) {
  const entry = manifest?.tiles?.find((tile) => Number(tile.count) > 0);
  if (!entry) return { available: false, reason: 'The tile manifest contains no non-empty tile entries.' };
  const url = resolveTileUrl(entry, indexUrl, remoteBaseUrl);
  try {
    let response = await fetch(url, { method: 'HEAD', cache: 'no-store' });
    if (response.status === 405) response = await fetch(url, { method: 'GET', cache: 'no-store', headers: { Range: 'bytes=0-0' } });
    if (!response.ok) {
      return { available: false, reason: `Tile endpoint returned ${response.status}.`, url };
    }
    return { available: true, url, delivery: remoteBaseUrl ? 'remote' : 'local' };
  } catch (error) {
    return { available: false, reason: error?.message || 'Tile endpoint could not be reached.', url };
  }
}

export async function loadTileRecords(entry, manifest, indexUrl, { remoteBaseUrl = null } = {}) {
  const url = resolveTileUrl(entry, indexUrl, remoteBaseUrl);
  const payload = await fetchJson(url, `tile ${entry.id || entry.path}`);
  if (payload?.format !== 'nasadiya-tile-store/v1' || !Array.isArray(payload.records)) {
    fail(`Rejected tile ${entry.id || entry.path}: record format is incomplete.`);
  }
  const columns = Array.isArray(payload.columns) ? payload.columns : manifest.record_columns;
  if (!Array.isArray(columns) || !columns.length) fail(`Rejected tile ${entry.id || entry.path}: columns are missing.`);
  const kind = manifest.dataset?.measurement_kind;
  return objectsFromRecords(payload.records, columns, manifest.dataset, kind);
}

export async function loadTileStoreOverview(indexUrl, datasetLabel = 'the survey tile store') {
  const manifest = await fetchJson(indexUrl, `${datasetLabel} manifest`);
  if (manifest?.format !== 'nasadiya-tile-store/v1') fail(`Rejected ${datasetLabel}: unknown tile-store format.`);
  const kind = manifest.dataset?.measurement_kind;
  if (manifest.dataset?.is_synthetic !== false || !['photometric', 'spectroscopic'].includes(kind)) {
    fail(`Rejected ${datasetLabel}: explicit observed photometric or spectroscopic provenance is required.`);
  }
  if (!manifest.overview?.path || !Array.isArray(manifest.record_columns)) {
    fail(`Rejected ${datasetLabel}: overview metadata is incomplete.`);
  }
  const overviewUrl = new URL(manifest.overview.path, new URL(indexUrl, window.location.href)).toString();
  const overview = await fetchJson(overviewUrl, `${datasetLabel} overview`);
  if (overview?.format !== 'nasadiya-tile-store/v1' || !Array.isArray(overview.records)) {
    fail(`Rejected ${datasetLabel}: overview record format is incomplete.`);
  }
  const columns = Array.isArray(overview.columns) ? overview.columns : manifest.record_columns;
  const objects = objectsFromRecords(overview.records, columns, manifest.dataset, kind);
  if (!objects.length) fail(`No observed ${datasetLabel} overview rows passed browser validation.`);

  const tracerCounts = objects.reduce((counts, object) => {
    if (object.tracer) counts[object.tracer] = (counts[object.tracer] || 0) + 1;
    return counts;
  }, {});

  return {
    meta: {
      dataset_id: manifest.dataset.dataset_id,
      dataset_label: `${manifest.dataset.survey} · ${Number(manifest.record_count).toLocaleString('en-GB')} observed ${kind === 'photometric' ? 'photo-z ' : ''}rows`,
      object_count: Number(manifest.record_count),
      overview_count: Number(manifest.overview.count),
      source_survey: manifest.dataset.survey,
      source_release: manifest.dataset.release,
      source_url: manifest.dataset.source_url,
      citation_key: manifest.dataset.citation_key,
      measurement_kind: kind,
      object_type: manifest.dataset.object_type,
      distance_note: manifest.dataset.distance_note,
      radial_uncertainty_required: kind === 'photometric',
      is_synthetic: false,
      overview_selection: overview.selection || null,
      tracer_counts: tracerCounts,
      tile_count: Number(manifest.tile_count || manifest.tiles?.length || 0),
      tile_manifest: manifest,
      tile_index_url: indexUrl,
    },
    objects,
  };
}
