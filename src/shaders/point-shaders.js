export const pointVertexShader = /* glsl */ `
  attribute vec3 color;
  attribute float aAlpha;
  attribute float aSize;
  attribute float aUncertainty;
  attribute float aTwinkle;
  uniform float uPointScale;
  uniform float uMode;
  uniform float uTime;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vHalo;
  void main() {
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    float perspective = clamp(1050.0 / max(1.0, -mvPosition.z), 0.25, 6.3);
    float uncertaintyBoost = mix(0.0, min(7.5, aUncertainty * 2300.0), step(0.5, uMode));
    float shimmer = 0.91 + 0.09 * sin(uTime * (0.38 + aTwinkle * 1.1) * 1.5 + aTwinkle * 6.28318);
    gl_PointSize = clamp((aSize + uncertaintyBoost) * uPointScale * perspective * shimmer, 1.0, 27.0);
    gl_Position = projectionMatrix * mvPosition;
    vColor = color;
    vAlpha = aAlpha;
    vHalo = shimmer;
  }
`;

export const pointFragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  varying float vHalo;
  void main() {
    vec2 uv = gl_PointCoord - vec2(0.5);
    float radius = length(uv);
    float core = 1.0 - smoothstep(0.0, 0.18, radius);
    float body = 1.0 - smoothstep(0.09, 0.33, radius);
    float halo = 1.0 - smoothstep(0.16, 0.50, radius);
    float alpha = max(core, body * 0.58 + halo * 0.20 * vHalo) * vAlpha;
    if (alpha < 0.012) discard;
    vec3 rgb = mix(vColor * 0.55, vec3(1.0), core * 0.60 + body * 0.17);
    gl_FragColor = vec4(rgb, alpha);
  }
`;
