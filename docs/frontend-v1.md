# Explorer v1 design note

The v1 explorer treats the survey field as the primary visual object. Narrative, controls and provenance remain visible without competing with it.

A future Astro/React migration should use Astro for static public pages and React only for client-side control islands. The existing Three.js renderer remains in native ES modules.