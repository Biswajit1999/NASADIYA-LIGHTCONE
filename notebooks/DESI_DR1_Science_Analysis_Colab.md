# DESI DR1 science-first analysis — Google Colab cells

This is a science-first descriptive analysis of the supplied DESI DR1 LSS observed catalogue. It focuses on tracer populations, redshift distributions, look-back time, observed sky footprint, observer-centred Cartesian redshift slices and coordinate consistency.

It does **not** analyse CPU or GPU performance. It also does not claim a density field, BAO detection, correlation function, void catalogue or cosmological parameter constraint. Those analyses require the official DESI LSS masks, weights, random catalogues, covariance products and validated estimators.

## Cell 1 — clone the science-analysis branch and install dependencies

```python
from pathlib import Path
import os
import subprocess
import sys

repo = Path('/content/NASADIYA-LIGHTCONE')
if not repo.exists():
    subprocess.run([
        'git', 'clone', '--depth', '1', '--branch', 'science-first-desi-analysis-v1',
        'https://github.com/Biswajit1999/NASADIYA-LIGHTCONE.git',
        str(repo),
    ], check=True)

os.chdir(repo)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'], check=True)
print('Repository ready:', Path.cwd())
```

## Cell 2 — upload the Parquet bundle

```python
from google.colab import files

uploaded = files.upload()
assert uploaded, 'No file was uploaded.'

DATA_PATH = Path(next(iter(uploaded))).resolve()
assert DATA_PATH.exists(), f'Uploaded file was not found: {DATA_PATH}'

print('Input Parquet:', DATA_PATH)
print('Size [MB]:', round(DATA_PATH.stat().st_size / 1024**2, 2))
```

## Cell 3 — run the scientific analysis

```python
OUTPUT_DIR = Path('figures/desi_dr1_science')

subprocess.run([
    sys.executable,
    'scripts/analyze_desi_dr1_science.py',
    '--input', str(DATA_PATH),
    '--output-dir', str(OUTPUT_DIR),
    '--dpi', '300',
], check=True)

print('Outputs written to:', OUTPUT_DIR.resolve())
```

## Cell 4 — inspect the tracer and cosmic-epoch table

```python
import pandas as pd
from IPython.display import Markdown, display

summary = pd.read_csv(OUTPUT_DIR / 'tracer_cosmic_epoch_summary.csv')
display(summary.round(5))
display(Markdown((OUTPUT_DIR / 'science_summary.md').read_text(encoding='utf-8')))
```

## Cell 5 — display all scientific plots

```python
from PIL import Image
from IPython.display import display

for image_path in sorted(OUTPUT_DIR.glob('*.png')):
    print(image_path.name)
    display(Image.open(image_path))
```

## Cell 6 — create a ZIP archive

```python
import shutil

archive = shutil.make_archive('/content/desi_dr1_science_analysis', 'zip', OUTPUT_DIR)
print('Archive created:', archive)
```

Download `desi_dr1_science_analysis.zip` through the Colab Files sidebar.

## Outputs

```text
fig_01_redshift_population.png
fig_02_tracer_cosmic_epochs.png
fig_03_angular_footprint_by_redshift.png
fig_04_cartesian_redshift_slices.png
fig_05_observed_radial_selection.png
fig_06_coordinate_consistency.png
tracer_cosmic_epoch_summary.csv
science_analysis_manifest.json
science_summary.md
```
