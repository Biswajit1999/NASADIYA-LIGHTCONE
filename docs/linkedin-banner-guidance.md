# LinkedIn sharing guidance

## Open Graph banner

`assets/nasadiya-lightcone-banner.png` is currently **2172 × 724 px** (≈3:1). LinkedIn's link-preview crop targets **1200 × 627 px** (≈1.91:1) and will centre-crop a wider image, which can cut the wordmark or provenance line at the edges. `index.html` now declares the real `og:image:width`/`og:image:height` (2172×724) so LinkedIn scales correctly, but for the sharpest crop on the feed:

1. Open the live explorer (or `?demo=linkedin`) at a 1200×627 (or any 1.91:1) browser viewport.
2. Let the boot sequence settle, then use the **Showcase** button (`#showcase-capture`) to export a branded PNG. It already composites the wordmark and the audited row-count line into the bottom of the frame.
3. Crop/resize that export to exactly 1200×627 (or keep native canvas resolution at that aspect ratio) and replace `assets/nasadiya-lightcone-banner.png`, or use it directly as a LinkedIn post image rather than relying on the link-preview crop.
4. Keep key text — the wordmark and stat line — inside the centre ~80% of the frame; LinkedIn's mobile crop trims more aggressively than desktop.

## Post copy checklist

- Lead with a real number from `SURVEY_INTEGRITY.md` (e.g. "6,093,818 observed DESI DR1 rows"), not a rounded or invented figure.
- Link to `https://biswajit1999.github.io/NASADIYA-LIGHTCONE/?demo=linkedin` so the click-through opens directly into the curated showcase route instead of the default interactive session.
- Credit Biswajit Jana as author; the project intentionally carries no AI/agent authorship metadata anywhere in its manifests or commit history.

## Regenerating the banner

There is no automated banner-generation script yet — regenerate it manually via Showcase Capture (above) whenever the boot sequence, palette, or hero framing changes materially enough that the committed banner no longer reflects the live explorer.
