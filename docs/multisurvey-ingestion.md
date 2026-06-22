# Multi-survey data architecture

NĀSADĪYA LIGHTCONE does not put multi-million-row catalogues into ordinary Git history. The repository stores source code, schemas, manifests, provenance documentation, and small test fixtures. Large public data products are transformed locally into a static tile store and then hosted separately as versioned release assets or object-storage files.

## Why a tile store

A one-million-row JSON file is too large for a smooth browser load; a DESI-scale single JSON file is impractical. The NĀSADĪYA tile-store format partitions observed rows by radial shell plus right-ascension and declination bins. Each store contains:

- `index.json`: layer metadata, provenance, tile bounds, tile counts, and partitioning rules;
- `overview.json`: deterministic lightweight point sample for an initial wide view;
- `tiles/*.json`: observed rows, fetched only as a required part of a view;
- an explicit `measurement_kind`, source URL, citation key, and cosmology convention.

The tiler rejects any source row that is not labelled `is_synthetic=false`.

## 2MPZ: one-million-galaxy all-sky layer

2MPZ is the planned wide shallow layer. The published catalogue contains about one million galaxies and uses photometric redshifts; the source paper reports an all-sky redshift accuracy of approximately `σz = 0.015`. Every 2MPZ rendering must retain and communicate the photo-z uncertainty as a radial uncertainty. A point plotted at one exact radius without its uncertainty is not an acceptable scientific representation.

Workflow after obtaining the source file from its official distribution:

```powershell
& .\.venv\Scripts\python.exe .\scripts\inspect_catalog.py .\data\raw\2mpz\catalogue.fits

& .\.venv\Scripts\python.exe .\scripts\build_survey_tile_store.py `
  --input .\data\raw\2mpz\catalogue.fits `
  --output .\data\processed\tiles\2mpz `
  --dataset-id 2mpz `
  --survey 2MPZ `
  --release "Bilicki et al. 2014" `
  --source-url "https://arxiv.org/abs/1311.5246" `
  --citation-key Bilicki2014_2MPZ `
  --measurement-kind photometric `
  --id-column <verified-id-column> `
  --ra-column <verified-ra-column> `
  --dec-column <verified-dec-column> `
  --redshift-column <verified-photoz-column> `
  --redshift-error-column <verified-photoz-error-column> `
  --magnitude-column <optional-magnitude-column>
```

The placeholders must be replaced only after checking the downloaded catalogue schema. Do not guess the meaning of a survey field.

## DESI DR1: deep spectroscopic layer

DESI DR1 provides more than 18 million unique Main Survey targets. Its official DR1 summary lists 13,049,402 galaxies and 1,553,713 quasars in the Main Survey, alongside stars and special-observation products. DR1 is released under CC BY 4.0 and requires the stated data citation and acknowledgement.

For a browser layer, begin from a documented, quality-controlled public DESI product. Preserve the source release, tracer class, footprint, and selection filters in the tile index. The DR1 documentation defines useful spectra using `ZCAT_PRIMARY==True`, `OBJTYPE=='TGT'`, and `ZWARN==0`; the Main Survey additionally excludes `PROGRAM=='other'`.

Inspect each supplied DESI file before tiling:

```powershell
& .\.venv\Scripts\python.exe .\scripts\inspect_catalog.py .\data\raw\desi-dr1\catalogue.fits
```

Then construct a tile store with explicitly confirmed mappings. Do not mix DESI stars into the extragalactic layer.

```powershell
& .\.venv\Scripts\python.exe .\scripts\build_survey_tile_store.py `
  --input .\data\raw\desi-dr1\quality_controlled_extragalactic.fits `
  --output .\data\processed\tiles\desi-dr1 `
  --dataset-id desi-dr1 `
  --survey DESI `
  --release "DR1" `
  --source-url "https://data.desi.lbl.gov/doc/releases/dr1/" `
  --citation-key DESI_DR1_2026 `
  --measurement-kind spectroscopic `
  --id-column <verified-targetid-column> `
  --ra-column <verified-ra-column> `
  --dec-column <verified-dec-column> `
  --redshift-column <verified-redshift-column>
```

## Hosting policy

Do not commit `data/processed/tiles/` to the main Git repository. Publish the resulting immutable tile-store directory to a release, object storage, or a dedicated data repository. Set CORS so the GitHub Pages frontend can fetch it. Record the exact tile-store URL and build manifest in the application layer registry.

## Gaia

Gaia is a Milky Way stellar survey, not an extragalactic redshift survey. It must be rendered as a separate Galactic context layer and never merged with 2MRS, 2MPZ, or DESI galaxy points.
