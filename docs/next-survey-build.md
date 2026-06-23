# Next survey build: validated photo-z layers

NĀSADĪYA adds new data layers one survey at a time. The first next layer is **2MPZ**; WISE × SuperCOSMOS follows only after the same schema gate passes.

## Why this order

- **2MPZ** provides the bridge between the nearby 2MRS anchor and the deeper DESI footprint. It is an approximately one-million-galaxy, almost-all-sky photometric-redshift catalogue.
- **WISE × SuperCOSMOS** is much larger and deeper, but its wide photo-z geometry and survey mask need the same explicit uncertainty validation before any tile store is produced.
- **Gaia DR3** remains a separate Milky Way mode, not an extragalactic lightcone layer.

## 1. Probe the cited source table first

Run this from the repository root after installing `requirements.txt`:

```cmd
.\.venv\Scripts\python.exe scripts\download_2mpz.py --probe
```

The probe does not download data. It prints each candidate VizieR table and only reports `PASS` when the source exposes:

1. object identifier;
2. right ascension and declination;
3. photometric redshift; and
4. a **per-object** redshift uncertainty.

A `REJECT` result is a scientific safeguard, not a build error. The project must not manufacture an uncertainty column from a survey-wide scatter value.

## 2. Download and tile 2MPZ only after a pass

```cmd
.\.venv\Scripts\python.exe scripts\download_2mpz.py
.\.venv\Scripts\python.exe scripts\build_2mpz_tile_store.py
```

The raw source file and full tiles remain local. The tile builder creates a deterministic browser overview plus `index.json` for a public layer of detail.

## 3. Validate WISE × SuperCOSMOS separately

```cmd
.\.venv\Scripts\python.exe scripts\download_wise_sc.py --probe
```

Only after a `PASS` should a full WISE build be attempted. Start with a bounded test request if the selected source is large, inspect the produced mapping, then build the full local tile store.

## No synthetic backfill

Do not add points to fill the Zone of Avoidance, DESI masks or any catalogue footprint. A dark region may be an observational limitation rather than a physical void.
