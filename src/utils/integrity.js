const REGISTRY_URL = './data/registry/survey_integrity.json';

let cachedSummary = null;

/**
 * Reads the audited row counts already committed by
 * scripts/audit_survey_integrity.mjs. Boot badges, the LinkedIn demo captions
 * and the Data Lens Pro panel all read the same file so a provenance number
 * shown anywhere in the UI can never drift from the machine-checked ledger.
 */
export async function loadIntegritySummary() {
  if (cachedSummary) return cachedSummary;
  try {
    const response = await fetch(REGISTRY_URL, { cache: 'no-store' });
    if (!response.ok) throw new Error(`Integrity registry returned ${response.status}.`);
    const registry = await response.json();
    cachedSummary = {
      available: true,
      fingerprint: registry.integrity_fingerprint || null,
      status: registry.status || null,
      twoMrsRows: Number(registry.products?.two_mrs?.object_count) || null,
      desiRows: Number(registry.products?.desi_index?.record_count) || null,
      desiTileCount: Number(registry.products?.desi_index?.tile_count) || null,
      desiOverviewRows: Number(registry.products?.desi_index?.overview_count) || null,
      fullCloudBytes: Number(registry.products?.full_cloud?.byte_length) || null,
      raw: registry,
    };
  } catch (error) {
    cachedSummary = { available: false, reason: error?.message || 'Integrity registry could not be loaded.' };
  }
  return cachedSummary;
}
