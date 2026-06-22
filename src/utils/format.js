export function formatNumber(value) {
  return Number.isFinite(Number(value)) ? new Intl.NumberFormat('en-GB').format(Number(value)) : '—';
}

export function formatDistance(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return numeric >= 1000 ? `${(numeric / 1000).toFixed(2)} Gpc` : `${numeric.toFixed(1)} Mpc`;
}

export function formatLookback(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return numeric >= 1 ? `${numeric.toFixed(3)} Gyr` : `${(numeric * 1000).toFixed(1)} Myr`;
}

export function formatRedshift(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(5) : '—';
}

export function formatVelocity(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 }).format(numeric)} km/s` : '—';
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;',
  })[character]);
}
