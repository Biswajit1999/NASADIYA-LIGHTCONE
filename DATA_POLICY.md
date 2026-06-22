# Data policy

NĀSADĪYA LIGHTCONE distinguishes source catalogues, locally processed browser products, and future hosted tiles.

- `data/raw/` contains source downloads and is ignored by Git.
- `data/processed/2mrs/` contains a compact browser product derived from 2MRS Table 3. It is allowed in Git only because it is small enough for a static first release and retains source metadata.
- Every processed object carries `source_survey`, `source_table`, `source_release`, `source_url`, `citation_key`, `measurement_kind`, and `is_synthetic=false`.
- No inferred filament, void, or density reconstruction may be mixed into an observed-object layer without a distinct layer identifier and method citation.
- A survey footprint, selection function, and spatial incompleteness are separate data products. Empty display regions do not establish low galaxy density.
- DESI, SDSS, Gaia, Euclid, Rubin, and other large releases will use a manifest plus tile-store strategy. Raw source files remain outside ordinary Git commits.
