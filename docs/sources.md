# Data sources and citation record

## 2MRS Table 3

- **Survey:** 2MASS Redshift Survey (2MRS)
- **Published source table:** VizieR `J/ApJS/199/26/table3`
- **Measurement:** spectroscopic recession velocity (`cz`) and uncertainty where supplied
- **Browser treatment:** `z ≈ cz/c`; Planck18 comoving distance used for spatial navigation only
- **Citation key:** `Huchra2012_2MRS`

## 2MPZ

- **Survey:** 2MASS Photometric Redshift Catalogue (2MPZ)
- **Publication record:** Bilicki et al. (2014)
- **Measurement:** photometric redshift with published source-table uncertainty required by the ingestion client
- **Browser treatment:** observer lightcone only; uncertainty is retained and not presented as exact radial position
- **Citation key:** `Bilicki2014_2MPZ`

## WISE × SuperCOSMOS

- **Survey:** WISE × SuperCOSMOS Photometric Redshift Catalogue
- **Publication record:** Bilicki et al. (2016)
- **Measurement:** photometric redshift with published source-table uncertainty required by the ingestion client
- **Browser treatment:** observer lightcone only; footprint/masking and uncertainty remain visible measurement properties
- **Citation key:** `Bilicki2016_WISESC`

## DESI DR1 LSS

- **Survey:** Dark Energy Spectroscopic Instrument Data Release 1 LSS clustering catalogues
- **Current local build:** BGS, LRG, ELG and QSO NGC/SGC clustering files; 6,093,818 accepted source rows and 4,205 local spatial tiles
- **Public browser product:** deterministic 125,000-row overview with an explicit non-scientific-selection flag
- **Measurement:** spectroscopic redshift
- **Browser treatment:** observer lightcone; tracer class retained in the source identifier; separated NGC/SGC regions are footprint and selection geometry
- **Citation key:** `DESI_DR1`

## Gaia DR3 local stellar context

- **Survey:** Gaia DR3
- **Measurement:** astrometry/parallax; a bounded public-TAP sample only
- **Browser treatment:** separate Galactic context product; never combined with extragalactic galaxy counts
- **Citation key:** `GaiaCollaboration2023_DR3`

Every data product retains its catalogue-specific acknowledgement and reuse terms. NĀSADĪYA code is MIT licensed; survey data are not relicensed by this repository.
