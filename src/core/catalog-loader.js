export async function loadCatalog(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('The real 2MRS browser catalogue has not been built yet. Run the 2MRS download and build scripts, then refresh this page.');
    }
    throw new Error(`Could not load the 2MRS catalogue (${response.status} ${response.statusText}).`);
  }
  const payload = await response.json();
  if (!payload || payload.meta?.is_synthetic !== false) {
    throw new Error('Rejected a catalogue without explicit observed-data provenance.');
  }
  if (!Array.isArray(payload.objects) || !payload.objects.length) {
    throw new Error('The browser catalogue did not contain renderable observed objects.');
  }
  const objects = payload.objects.filter((object) => {
    const required = ['x_mpc', 'y_mpc', 'z_mpc', 'redshift'];
    return object.is_synthetic === false && required.every((field) => Number.isFinite(Number(object[field])));
  });
  if (!objects.length) throw new Error('No observed objects passed browser validation.');
  return { meta: payload.meta, objects };
}
