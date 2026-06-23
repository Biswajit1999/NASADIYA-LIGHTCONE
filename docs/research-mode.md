# Research-resolution DESI workflow

## Why this is separate from the live explorer

The public browser begins from a compact observed overview so it can open quickly on
ordinary laptops and phones. The locally built DESI DR1 LSS store contains
6,093,818 observed rows across 4,205 spatial tiles; loading every row into one WebGL
buffer would make the initial site slow and memory-heavy.

Research mode uses Python and Parquet instead. It scans the complete observed bundle
for quantitative summaries while drawing an exact bounded deterministic subset in 3D.
The live explorer and the Python workflow are complementary, not competing products.

## Validated full-catalogue bundle

The first validated full-bundle build retained all **6,093,818 observed DESI DR1 LSS
rows** in a **185.12 MiB** compressed Parquet file, below the 480 MiB release target.
Read the [release record](desi-dr1-research-bundle-v1.md) for the file checksum,
tracer counts and release-asset contents.

## Build a capped research bundle

A full local DESI tile build is required first. Then run:

```cmd
.\.venv\Scripts\python.exe scripts\build_desi_research_bundle.py --target-mb 480 --overwrite
```

The builder writes:

```text
data/research/desi_dr1_lss_research_bundle.parquet
data/research/desi_dr1_lss_research_bundle.manifest.json
```

It first writes a compressed Parquet candidate using all observed DESI tile rows. If
that candidate is within the requested cap, the final bundle retains every available
row. If it is too large, the builder creates a deterministic object-ID-hash sample and
records the exact fraction, input count, output count, file hash and tracer counts in
the manifest.

The bundle is ignored by normal Git history. Publish it as a GitHub Release asset or
another versioned data release, not as a repository file.

## Generate reproducible figures

```cmd
.\.venv\Scripts\python.exe scripts\plot_desi_research_figure.py --input data\research\desi_dr1_lss_research_bundle.parquet --output-dir figures --render-rows 120000
```

This creates small, versionable outputs:

```text
figures/desi_dr1_lss_3d_research_view.png
figures/desi_dr1_lss_redshift_summary.png
figures/desi_dr1_lss_sky_footprint.png
figures/desi_dr1_lss_research_summary.json
```

The redshift and sky-footprint figures scan the complete research bundle. The 3D plot
uses exactly the requested number of rows: it retains the global lowest object-ID
hashes, with object ID as the deterministic tie-breaker. This is a visual and
computational level of detail, not a completeness correction or a unique-object
catalogue.

## Google Colab

Open the notebook from GitHub:

```text
https://colab.research.google.com/github/Biswajit1999/NASADIYA-LIGHTCONE/blob/main/notebooks/DESI_DR1_LSS_3D_Colab.ipynb
```

Set a future GitHub Release asset URL in `BUNDLE_URL`, or upload the Parquet bundle to
the Colab session. The notebook downloads the repository plotting script and produces
the same reproducible PNG outputs.

## Scientific scope

- Rows originate only in the locally built observed DESI DR1 LSS tile store.
- No synthetic galaxies, reconstructed filaments, interpolation or survey cross-match
  are created.
- Survey footprint, targeting and completeness are measurement properties. A dark sky
  region in the footprint map does not establish a physical underdensity.
- Cite the relevant DESI DR1 source products alongside this software and its bundle
  manifest when sharing a result.
