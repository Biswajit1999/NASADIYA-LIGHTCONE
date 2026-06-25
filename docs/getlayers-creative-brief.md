# NĀSADĪYA LIGHTCONE — cinematic research-interface brief

Paste this brief into an AI design tool as a **design and implementation plan**, then adapt the useful ideas to this repository. Do not replace the existing data or static ES-module architecture with a React, Vite, or Next.js build.

```text
You are a senior Three.js creative developer and scientific-interface designer.

Redesign an existing browser-native astronomy application called NĀSADĪYA LIGHTCONE. It is not a generic landing page. It is a public research visualisation of real 2MRS and DESI DR1 spectroscopic catalogue rows. The experience must feel cinematic and premium, but every visual decision must preserve scientific honesty.

ARCHITECTURE — NON-NEGOTIABLE
- Keep a zero-dependency static website: plain HTML, CSS, and native ES modules.
- Keep the current Three.js scene, GitHub Pages deployment, and real catalogue products.
- Do not introduce React, Vite, npm build tooling, a backend, synthetic galaxies, fake filaments, or stock space imagery.
- The full DESI cloud contains 6,093,818 observed rows in GPU buffers. The browser must still orbit smoothly and respond immediately to mouse, wheel, touch, filters, and density controls.

SCIENTIFIC BOUNDARIES
- DESI has a real North/South footprint, targeting masks, and selection effects. Do not turn its gaps into a fake all-sky cosmic web.
- 2MRS + DESI is a comparison stack, not a merged or deduplicated master catalogue.
- In full-cloud mode, labels must distinguish GPU-resident rows, display sample, redshift limit, radial extent, and look-back time.

VISUAL DIRECTION
Create an 'Observatory Flight Deck' rather than a dashboard wall. Deep near-black midnight blue, restrained cyan navigation accents, warm amber only for DESI/source contrast, controlled glass panels, exact spacing, readable typography, cinematic motion that never fights manual controls.

LAYOUT
1. Canvas is the dominant subject. No panel may cover more than 30% of its width on a desktop.
2. A compact top command bar: survey status, Flythrough toggle, Data Lens.
3. A collapsible left mission briefing: title, one-paragraph scientific warning, survey selector. It should collapse automatically while the user explores the 3D field.
4. A floating upper-right spatial HUD: observer origin, 0–radial extent, redshift ceiling, look-back time, and a short selection-effect note.
5. Bottom telemetry rail: display sample, GPU-resident rows, radial extent, look-back window, current colour mode.
6. Data Lens is a single clean side drawer with visual sections: catalogue layer, display density, redshift, tracer classes, colour mode, and reset.

3D INTERACTION
- Left drag: orbit; mouse wheel: zoom; right drag: pan. The canvas must visibly indicate this with a grab cursor and no invisible overlays.
- Add subtle observer-centred X/Y/Z reference guides and radial distance rings. Put labels in an HTML HUD so they remain readable.
- Add a Flythrough toggle in the top command bar. Route: full footprint overview -> approach -> interior passage -> full overview. Any drag, scroll, or touch instantly returns manual control.
- Respect prefers-reduced-motion; do not autoplay a camera flight.

DENSITY AND FULL CLOUD
- When the 6.09M GPU cloud is active, all rows remain resident. The density slider controls a deterministic display sample: 125K, 250K, 500K, 1M, or 6.09M. Changing density must visibly update the canvas and telemetry immediately.
- In the 2MRS + DESI comparison stack, retain the local 2MRS anchor and show the full DESI GPU cloud alongside it. Source colour distinguishes the two surveys.

OUTPUT
Return a concrete file-by-file implementation plan for the existing static ES-module codebase. Include exact DOM hierarchy, CSS tokens, Three.js interaction settings, shader/BufferGeometry performance considerations, and acceptance tests. Do not output a generic marketing website.
```
