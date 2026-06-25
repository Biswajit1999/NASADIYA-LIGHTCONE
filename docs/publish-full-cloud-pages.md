# Publish the full DESI cloud on GitHub Pages

The explorer code is already served from `main`. The optional 6M+ payload must
be built on the computer holding `data/research/desi_dr1_lss_research_bundle.parquet`.

1. Build the original packed cloud with `scripts/full_gpu.py`.
2. Run `scripts/split_full_cloud_for_pages.py --cloud-dir data/processed/desi-dr1/full-cloud --chunk-mib 40 --overwrite`.
3. Commit only `full-cloud.json` and `desi-dr1-full-cloud.part-*.f32` files:

```bat
git add -f data\processed\desi-dr1\full-cloud\full-cloud.json
git add -f data\processed\desi-dr1\full-cloud\desi-dr1-full-cloud.part-*.f32
git commit -m "data: publish full DESI GPU cloud"
git push origin main
```

The browser detects `full-cloud.json` on GitHub Pages and enables the **Full
DESI 6M+** profile. The three ~40 MiB parts are record-aligned and fetched
sequentially, so the renderer never creates millions of JavaScript objects.

Do not commit the monolithic `desi-dr1-full-cloud.f32` file: GitHub blocks
single files larger than 100 MiB. Keep it locally as a source artifact.
