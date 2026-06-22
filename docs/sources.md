# Sources and acknowledgement record

## 2MRS v0.1

- **Catalogue:** 2MASS Redshift Survey (2MRS), Table 3.
- **VizieR catalogue identifier:** `J/ApJS/199/26/table3`.
- **Catalogue access:** https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J/ApJS/199/26/table3
- **Source publication:** Huchra, J. P. et al. 2012, *The 2MASS Redshift Survey—Description and Data Release*, ApJS, 199, 26, doi:10.1088/0067-0049/199/2/26.
- **Catalogue-access acknowledgement:** “This research has made use of the VizieR catalogue access tool, CDS, Strasbourg, France (DOI: 10.26093/cds/vizier).”

The `source_manifest.json` written by the download script records the query endpoint, retrieval time, table identifier, and file hash. Use the original catalogue publication and VizieR acknowledgement in any public page or presentation that uses this data layer.

## Planned layers

- 2MPZ: whole-sky photometric-redshift layer; radial uncertainty is mandatory.
- DESI DR1: spectroscopic galaxies and quasars; include release, target class, redshift quality, completeness/footprint, and selection information.
- Gaia: treated as a separate Milky Way stellar layer, not mixed with extragalactic catalogue points.


## Multi-survey implementation references

- **2MPZ:** Bilicki et al. (2014), *2MASS Photometric Redshift catalog: a comprehensive three-dimensional census of the whole sky*, ApJS 210, 9; source paper: https://arxiv.org/abs/1311.5246. Its redshift estimates are photometric and must retain their radial uncertainty in every visual layer.
- **DESI DR1:** official release documentation: https://data.desi.lbl.gov/doc/releases/dr1/. DR1 is CC BY 4.0 and requires the official acknowledgement/citation text. The public DR1 page provides the data root and documented LSS catalogue paths.
- **Gaia:** any future Gaia integration is a Galactic context layer and must cite the relevant ESA Gaia data release separately.
