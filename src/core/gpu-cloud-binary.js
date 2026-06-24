export const GPU_BINARY_LAYOUT = 'interleaved-f32';

export async function fetchGpuCloud(probe) {
  if (!probe?.available || !probe.manifest?.binary) {
    throw new Error('Full GPU cloud is not available.');
  }
  const response = await fetch(probe.url, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Could not load full DESI GPU cloud (${response.status} ${response.statusText}).`);
  }
  return response.arrayBuffer();
}
