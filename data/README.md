# Data directory

- `raw/` holds untouched public-survey downloads. It is ignored by Git.
- `processed/2mrs/` holds the compact public baseline derived from published 2MRS rows.
- `processed/2mpz/`, `processed/wise-sc/`, and `processed/desi-dr1/` are local chunked tile stores after a successful build. Only `.gitkeep` files are committed.
- `processed/gaia-dr3/` is a separate bounded local-star product. It is not an extragalactic layer.
- `registry/` states layer intent and build status without claiming that an unbuilt layer is live.
- `schemas/` specifies the serialisable browser and tile-store contracts.

No directory may contain synthetic galaxies presented as survey rows.
