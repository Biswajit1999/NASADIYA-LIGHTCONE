const HUBBLE_TIME_GYR = 9.778 / 0.674;
const OMEGA_M = 0.315;
const OMEGA_L = 0.685;
const SPEED_OF_LIGHT_KM_S = 299792.458;
const HUBBLE_CONSTANT_KM_S_MPC = 67.4;
const HUBBLE_DISTANCE_MPC = SPEED_OF_LIGHT_KM_S / HUBBLE_CONSTANT_KM_S_MPC;

function inverseHubbleParameter(redshift) {
  const onePlusZ = 1 + redshift;
  return 1 / Math.sqrt(OMEGA_M * onePlusZ ** 3 + OMEGA_L);
}

function lookbackIntegrand(redshift) {
  return inverseHubbleParameter(redshift) / (1 + redshift);
}

function simpson(integrand, upperLimit) {
  const z = Math.max(0, Number(upperLimit) || 0);
  if (!z) return 0;
  let segments = Math.max(128, Math.ceil(z * 256));
  if (segments % 2) segments += 1;
  const step = z / segments;
  let sum = integrand(0) + integrand(z);
  for (let index = 1; index < segments; index += 1) {
    sum += (index % 2 ? 4 : 2) * integrand(index * step);
  }
  return step * sum / 3;
}

/** Approximate flat-LambdaCDM look-back time for navigation labels only. */
export function lookbackTimeGyr(redshift) {
  return HUBBLE_TIME_GYR * simpson(lookbackIntegrand, redshift);
}

/**
 * Approximate flat-LambdaCDM comoving distance, same cosmology as the
 * server-side Planck18 build (Ωm=0.315, ΩΛ=0.685, H0=67.4). For visual
 * navigation and uncertainty-shell thickness only, not a source measurement.
 */
export function comovingDistanceMpc(redshift) {
  return HUBBLE_DISTANCE_MPC * simpson(inverseHubbleParameter, redshift);
}

function effectiveRedshiftSigma(redshift, globalSigma, sigmaKind) {
  return sigmaKind === 'proportional_to_one_plus_z' ? globalSigma * (1 + Math.max(0, redshift)) : globalSigma;
}

/**
 * Half-thickness, in Mpc, of a survey-wide photometric-redshift uncertainty
 * shell centred on `redshift`. Used only to size the uncertainty-shell render
 * mode for layers with no per-object error (e.g. 2MPZ); it is never used to
 * move a catalogue point's best-estimate position.
 */
export function redshiftShellHalfThicknessMpc(redshift, globalSigma, sigmaKind = 'constant') {
  const z = Math.max(0, Number(redshift) || 0);
  const sigma = effectiveRedshiftSigma(z, Number(globalSigma) || 0, sigmaKind);
  if (!(sigma > 0)) return 0;
  const zLow = Math.max(0, z - sigma);
  const zHigh = z + sigma;
  return (comovingDistanceMpc(zHigh) - comovingDistanceMpc(zLow)) / 2;
}
