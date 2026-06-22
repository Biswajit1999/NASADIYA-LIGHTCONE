function fail(message) {
  throw new Error(message);
}

async function fetchJson(url, datasetLabel) {
  const response = await fetch(url, { cache: 'no-cache' });
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
  const objects = overview.records
    .map((values) => objectFromRecord(columns, values, manifest.dataset))
    .filter((object) => {
      const core = ['x_mpc', 'y_mpc', 'z_mpc', 'redshift'].every((field) => Number.isFinite(Number(object[field])));
      return core && (kind !== 'photometric' || (Number.isFinite(Number(object.redshift_error)) && Number(object.redshift_error) > 0));
    });
  if (!objects.length) fail(`No observed ${datasetLabel} overview rows passed browser validation.`);

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
    },
    objects,
  };
}
