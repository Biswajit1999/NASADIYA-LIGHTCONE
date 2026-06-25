const HUBBLE_TIME_GYR = 9.778 / 0.674;
const OMEGA_M = 0.315;
const OMEGA_L = 0.685;

function integrand(redshift) {
  const onePlusZ = 1 + redshift;
  return 1 / (onePlusZ * Math.sqrt(OMEGA_M * onePlusZ ** 3 + OMEGA_L));
}

/** Approximate flat-LambdaCDM look-back time for navigation labels only. */
export function lookbackTimeGyr(redshift) {
  const z = Math.max(0, Number(redshift) || 0);
  if (!z) return 0;
  let segments = Math.max(128, Math.ceil(z * 256));
  if (segments % 2) segments += 1;
  const step = z / segments;
  let sum = integrand(0) + integrand(z);
  for (let index = 1; index < segments; index += 1) {
    sum += (index % 2 ? 4 : 2) * integrand(index * step);
  }
  return HUBBLE_TIME_GYR * step * sum / 3;
}
