export const GPU_CLOUD_FORMAT = 'nasadiya-gpu-cloud/v1';

function asDirectoryUrl(url) {
  const value = String(url);
  return value.endsWith('/') ? value : `${value}/`;
}

function resolveCloudUrl(path, manifestUrl, remoteBaseUrl = null) {
  const base = remoteBaseUrl
    ? new URL(asDirectoryUrl(remoteBaseUrl), window.location.href)
    : new URL('.', new URL(manifestUrl, window.location.href));
  return new URL(path, base).toString();
}

export function validGpuCloudManifest(manifest) {
  const binary = manifest?.binary;
  return manifest?.format === GPU_CLOUD_FORMAT
    && Number.isInteger(Number(manifest.record_count))
    && Number(manifest.record_count) > 0
    && binary?.encoding === 'little-endian-float32-interleaved'
    && Number(binary.stride_floats) === 5
    && Number(binary.byte_length) === Number(manifest.record_count) * 20
    && Array.isArray(binary.fields)
    && binary.fields.join('|') === 'x_mpc|y_mpc|z_mpc|redshift|tracer_code';
}

export async function probeGpuCloud(manifestUrl, { remoteBaseUrl = null } = {}) {
  try {
    const manifestResponse = await fetch(manifestUrl, { cache: 'no-store' });
    if (!manifestResponse.ok) return { available: false, reason: `Full GPU cloud manifest returned ${manifestResponse.status}.` };
    const manifest = await manifestResponse.json();
    if (!validGpuCloudManifest(manifest)) return { available: false, reason: 'Full GPU cloud manifest is incomplete or incompatible.' };
    const url = resolveCloudUrl(manifest.binary.path, manifestUrl, remoteBaseUrl);
    let response = await fetch(url, { method: 'HEAD', cache: 'no-store' });
    if (response.status === 405) response = await fetch(url, { method: 'GET', cache: 'no-store', headers: { Range: 'bytes=0-0' } });
    if (!response.ok) return { available: false, reason: `Full GPU cloud endpoint returned ${response.status}.`, manifest, url };
    return { available: true, manifest, url, delivery: remoteBaseUrl ? 'remote' : 'local' };
  } catch (error) {
    return { available: false, reason: error?.message || 'Full GPU cloud could not be reached.' };
  }
}
