# Getting started

## Requirements

- Python 3.11 or later
- A modern browser with WebGL
- Node.js only for the JavaScript syntax check; the runtime has no Node build step

## Windows quickstart

```cmd
cd /d "%USERPROFILE%\Documents\GitHub\NASADIYA-LIGHTCONE"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m http.server 8080
```

Open `http://localhost:8080`.

## Build the initial 2MRS layer

```cmd
.\.venv\Scripts\python.exe scripts\download_2mrs.py
.\.venv\Scripts\python.exe scripts\build_2mrs_lightcone.py
.\.venv\Scripts\python.exe scripts\verify_browser_catalog.py
```

## Build DESI DR1 LSS locally

```cmd
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --dry-run
.\.venv\Scripts\python.exe scripts\download_desi_dr1_lss.py --yes
.\.venv\Scripts\python.exe scripts\build_desi_dr1_tile_store.py
```

The final command produces `data/processed/desi-dr1/index.json`, `overview.json`, and `tiles/`. The full tile directory is intentionally excluded from Git.

## Validate before contributing

```cmd
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check pipeline scripts tests
npm run check:modules
```

## Common problems

| Symptom | Cause and action |
|---|---|
| Blank browser page | Start the local HTTP server rather than double-clicking `index.html`; then hard refresh with `Ctrl + Shift + R`. |
| DESI layer unavailable | Confirm both `data/processed/desi-dr1/index.json` and `overview.json` exist. |
| 2MPZ or WISE source retrieval refuses to build | This is deliberate until a validated official table with per-row photo-z uncertainty is wired in. Do not substitute a photometry-only table. |
| Git sees raw data | Do not force-add `data/raw/` or `data/processed/**/tiles/`. See [data access](data-access.md). |
