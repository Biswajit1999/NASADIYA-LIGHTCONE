# Observatory interface architecture

The explorer is a scientific instrument surface around a measured-catalogue WebGL viewport. Interface modes may change contrast, panel visibility and camera framing; they never modify catalogue positions, tracer identities, redshifts or provenance.

## Operating modes

- **Night observatory** is the default OLED-dark control-room theme.
- **Day research** provides a high-contrast publication and institute theme while retaining the dark astronomical viewport for point-cloud legibility.
- **Presentation focus** removes peripheral panels without changing the active survey, filters or display sample.
- The selected theme and one camera bookmark are stored locally in the browser.

## Instrumentation

The viewport instrument strip reports measured browser state: rendered frame rate, Three.js geometry and texture counts, and camera distance from its current target. These values are operational telemetry, not scientific measurements.

## Capture and bookmarks

Screenshot capture exports the current WebGL viewport. Camera bookmarks store only camera position, orbit target and view mode. Keyboard shortcuts are `T` for theme, `P` for presentation focus, `B` to save, `1` to restore and `S` to capture.

## Performance boundary

Instrumentation updates twice per second and reuses renderer counters already maintained by Three.js. It introduces no extra draw calls, catalogue buffers or particle motion. The underlying adaptive loading, deterministic display sampling and GPU-resident full-cloud modes remain unchanged.
