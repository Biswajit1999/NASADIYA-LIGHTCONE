# Data directories

- `raw/` is for source downloads and is excluded from Git.
- `processed/2mrs/2mrs_lightcone.json` is the browser product generated from 2MRS Table 3.
- `schemas/` documents the source-to-browser row contract.

Run `python scripts/download_2mrs.py` followed by `python scripts/build_2mrs_lightcone.py` to create the first real layer.
