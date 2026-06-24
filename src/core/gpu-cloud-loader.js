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
