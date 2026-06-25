# Dashboard explorer controls

The NĀSADĪYA LIGHTCONE explorer uses a command-centre layout for survey navigation.

## Viewport controls

- **Left mouse drag:** orbit around the current observer-centred reference frame.
- **Right mouse drag:** pan.
- **Mouse wheel / trackpad pinch:** zoom.
- **Flythrough:** runs an optional overview → interior → overview route. Any manual interaction stops the route.
- **Reset frame:** returns to the intended frame for the active survey and spatial mode.

## Display density

For the public DESI overview, density controls determine the number of rendered observed rows available from the current delivery path.

When **Full DESI** is active, all accepted DESI DR1 LSS rows are resident in the GPU buffer. The density controls select a deterministic display sample of 125K, 250K, 500K, 1M, or all 6.09M rows. This affects visual density only; it does not change catalogue records, target selection, masks, weights, or completeness.

## Telemetry definitions

- **Visible / displayed:** current visual sample drawn by the renderer.
- **GPU-resident rows:** accepted full-cloud DESI records held in the browser GPU buffer.
- **Radial extent:** largest observer-centred comoving radius present in the active rendering layer.
- **Look-back time:** approximate flat ΛCDM look-back time at the selected redshift ceiling, using the Planck 2018 parameters displayed in the status strip.
- **Sky coverage:** survey footprint, not a physical boundary of galaxy structure.

## Comparison stack

The `2MRS + DESI DR1` layer is a comparison stack. It retains the nearby 2MRS anchor and DESI DR1 independently. It is not cross-matched, deduplicated, or converted into a unified completeness-corrected catalogue.
