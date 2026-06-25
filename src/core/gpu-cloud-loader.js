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

function validParts(parts, totalBytes) {
  return Array.isArray(parts)
    && parts.length > 0
    && parts.every((part) => typeof part?.path === 'string' && Number.isInteger(Number(part.byte_length)) && Number(part.byte_length) > 0)
    && parts.reduce((sum, part) => sum + Number(part.byte_length), 0) === totalBytes;
}

export function validGpuCloudManifest(manifest) {
  const binary = manifest?.binary;
  const recordCount = Number(manifest?.record_count);
  const totalBytes = Number(binary?.byte_length);
  const hasSingleBinary = typeof binary?.path === 'string' && binary.path.length > 0;
  const hasParts = validParts(binary?.parts, totalBytes);
  return manifest?.format === GPU_CLOUD_FORMAT
    && Number.isInteger(recordCount)
    && recordCount > 0
    && binary?.encoding === 'little-endian-float32-interleaved'
    && Number(binary.stride_floats) === 5
    && totalBytes === recordCount * 20
    && Array.isArray(binary.fields)
    && binary.fields.join('|') === 'x_mpc|y_mpc|z_mpc|redshift|tracer_code'
    && (hasSingleBinary || hasParts);
}

async function probeUrl(url) {
  let response = await fetch(url, { method: 'HEAD', cache: 'no-store' });
  if (response.status === 405) response = await fetch(url, { method: 'GET', cache: 'no-store', headers: { Range: 'bytes=0-0' } });
  return response;
}

export async function probeGpuCloud(manifestUrl, { remoteBaseUrl = null } = {}) {
  try {
    const manifestResponse = await fetch(manifestUrl, { cache: 'no-store' });
    if (!manifestResponse.ok) return { available: false, reason: `Full GPU cloud manifest returned ${manifestResponse.status}.` };
    const manifest = await manifestResponse.json();
    if (!validGpuCloudManifest(manifest)) return { available: false, reason: 'Full GPU cloud manifest is incomplete or incompatible.' };
    const paths = manifest.binary.parts?.map((part) => part.path) || [manifest.binary.path];
    const urls = paths.map((path) => resolveCloudUrl(path, manifestUrl, remoteBaseUrl));
    const probes = await Promise.all(urls.map((url) => probeUrl(url)));
    const failed = probes.find((response) => !response.ok);
    if (failed) return { available: false, reason: `Full GPU cloud endpoint returned ${failed.status}.`, manifest, urls };
    return { available: true, manifest, urls, url: urls[0], delivery: remoteBaseUrl ? 'remote' : 'local' };
  } catch (error) {
    return { available: false, reason: error?.message || 'Full GPU cloud could not be reached.' };
  }
}
