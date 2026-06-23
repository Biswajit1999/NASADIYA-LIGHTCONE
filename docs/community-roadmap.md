# Community roadmap

## Current milestone: v0.9 - Explorer foundation

- 2MRS nearby spectroscopic anchor
- DESI DR1 LSS deterministic public overview and local spatial tile store
- BGS / LRG / ELG / QSO filters parsed from retained identifiers
- Compact explorer-first interface with visible survey-footprint context
- Project report, community guide, issue template, and data-access model

## Next technical milestones

1. **DESI tile streaming:** camera-aware requests to an external static tile host, with a manifest and cache budget.
2. **Traceable survey endpoints:** restore 2MPZ and WISE × SuperCOSMOS only after validating the official published source table and per-object uncertainty columns.
3. **Survey comparison:** a clear deep-to-local transition between 2MRS and DESI, without implying common completeness or selection.
4. **Galactic mode:** Gaia DR3 as a wholly separate stellar context view.
5. **Accessibility:** keyboard navigation, reduced-motion support, high-contrast mode, and an alternative tabular record explorer.
6. **Reproducibility:** build manifests, deterministic release tags, checksum reporting, and archival release records.

## Non-goals

- A synthetic ``full Universe'' populated with invented galaxies.
- Mixing photometric and spectroscopic redshifts without explicit uncertainty treatment.
- Treating survey gaps as physical voids.
- Replacing survey-native provenance with decorative cosmic-web lines.
