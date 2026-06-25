export const GPU_BINARY_LAYOUT = 'interleaved-f32';

/**
 * Fetch one or more validated cloud parts sequentially into one GPU-ready
 * ArrayBuffer. Sequential transfer keeps peak browser memory lower than a
 * Promise.all download of every part.
 */
export async function fetchGpuCloud(probe) {
  if (!probe?.available || !probe.manifest?.binary) {
    throw new Error('Full GPU cloud is not available.');
  }
  const binary = probe.manifest.binary;
  const urls = Array.isArray(probe.urls) && probe.urls.length ? probe.urls : [probe.url];
  const parts = binary.parts || [{ path: binary.path, byte_length: binary.byte_length }];
  if (urls.length !== parts.length) throw new Error('Full GPU cloud part metadata does not match delivery URLs.');

  const destination = new Uint8Array(Number(binary.byte_length));
  let offset = 0;
  for (let index = 0; index < urls.length; index += 1) {
    const response = await fetch(urls[index], { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Could not load full DESI GPU cloud part ${index + 1} (${response.status} ${response.statusText}).`);
    }
    const source = new Uint8Array(await response.arrayBuffer());
    if (source.byteLength !== Number(parts[index].byte_length)) {
      throw new Error(`Full DESI GPU cloud part ${index + 1} length does not match the manifest.`);
    }
    destination.set(source, offset);
    offset += source.byteLength;
  }
  if (offset !== destination.byteLength) throw new Error('Full DESI GPU cloud assembly length mismatch.');
  return destination.buffer;
}
