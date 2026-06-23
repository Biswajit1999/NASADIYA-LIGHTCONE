# UI/UX and SEO audit — Explorer 1.0

## Hierarchy

Explorer 1.0 uses four durable layers: the observed field first, a concise survey briefing second, direct local/deep navigation third, and reversible controls plus source provenance fourth.

## Accessibility

- Public navigation reaches crawlable documents without JavaScript.
- Keyboard focus states are visible.
- `R` resets the current spatial frame when focus is not in an input.
- Reduced-motion preferences minimise non-essential transition timing.
- Layer, footprint and tracer context are stated in text rather than colour alone.

## Search delivery

The explorer includes canonical and Open Graph metadata plus JSON-LD. Public About, Data, Methods and Community pages make the project legible beyond the WebGL canvas.

## Architecture

The Three.js renderer remains native ES modules. A future Astro/React migration should use Astro for static page delivery and React for complex UI state only; the survey renderer remains a client island.
