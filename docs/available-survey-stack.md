# Available-survey comparison stack

## What is live together today

The `Available surveys · 2MRS + DESI DR1` layer renders the two deployed extragalactic catalogues together:

| Component | Public rows used by the stack | Underlying source rows |
|---|---:|---:|
| 2MRS Table 3 | 43,533 | 43,533 |
| DESI DR1 LSS deterministic overview | 125,000 | 6,093,818 |
| **Comparison stack** | **168,533** | **6,137,351 source rows before cross-survey matching** |

The source-row total is an arithmetic sum, **not** a unique-galaxy count. The two catalogues overlap on the sky and may contain records of the same astrophysical object.

## How to read the stack

- Select **Available surveys · 2MRS + DESI DR1** from the Data Lens.
- Select **Source** in Colour treatment: cyan is 2MRS, amber is DESI DR1.
- Inspect any point to see its original survey, object identifier, coordinates, redshift and source record.
- The rendering policy preserves the full 2MRS local anchor first, then uses the remaining browser budget for a deterministic DESI view.

## What this is not

This view is not a unified, cross-matched, completeness-corrected cosmology catalogue. It does not remove duplicated objects, homogenise magnitude limits, reconcile redshift conventions or infer missing footprint regions. It is an honest comparison layer for navigation between the local all-sky anchor and the deep DESI footprint.

## 2MPZ is now a standalone layer, not yet in the comparison stack

2MPZ (933,447 rows from the real `TWOMPZ..twompzPhotoz` SSA table) is deployed as its own selectable layer, but is **not** part of `all-live`. Its source table has no per-object redshift-uncertainty column — only a published survey-wide accuracy figure (σz = 0.015) — so every 2MPZ point is rendered at its exact measured position while that one real number drives the existing "Uncertainty" colour/size mode uniformly across the whole layer, never a fabricated per-row value. Folding it into the comparison stack is a separate decision, since it would mix a photometric, coarser-precision layer into a view currently built from two spectroscopic surveys.

## Future all-survey stack

WISE × SuperCOSMOS remains eligible only after:

1. a verified downloadable published source table (one exists at http://ssa.roe.ac.uk/cats/wiseScosPhotoz160708.csv.gz, confirmed reachable);
2. explicit object identifier, RA, Dec, photo-z and either a per-object photo-z uncertainty field or an accepted survey-wide-uncertainty treatment matching 2MPZ's;
3. provenance and selection/mask metadata; and
4. a layer-specific tile build.

After ingestion, it should be introduced as an optional overlay, not silently merged into a unique-object count. Gaia/GCNS remains a separate stellar Milky-Way mode.
