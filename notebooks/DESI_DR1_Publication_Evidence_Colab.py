# %% [markdown]
# # DESI DR1 browser-representation evidence
#
# Run this file in Google Colab cell-by-cell, or upload it and use it as a
# notebook-style script. It generates reproducible figure outputs from the
# local DESI DR1 LSS research Parquet bundle.

# %%
# Clone the repository and install the declared environment.
!git clone --depth 1 https://github.com/Biswajit1999/NASADIYA-LIGHTCONE.git
%cd NASADIYA-LIGHTCONE
!pip -q install -r requirements.txt

# %% [markdown]
# ## Choose one source for the local Parquet bundle
#
# Option A: mount Drive and set `DATA_PATH` to the bundle.
# Option B: use `files.upload()` and set `DATA_PATH` to the uploaded filename.

# %%
# Option A — Google Drive
from google.colab import drive
drive.mount('/content/drive')
DATA_PATH = '/content/drive/MyDrive/desi_dr1_lss_research_bundle.parquet'
MANIFEST_PATH = 'data/processed/desi-dr1/full-cloud/full-cloud.json'

# %%
# Option B — direct upload. Comment out Option A if you use this.
# from google.colab import files
# uploaded = files.upload()
# DATA_PATH = '/content/' + next(iter(uploaded))
# MANIFEST_PATH = 'data/processed/desi-dr1/full-cloud/full-cloud.json'

# %%
from pathlib import Path
assert Path(DATA_PATH).exists(), f'Missing input: {DATA_PATH}'

# %%
!python scripts/build_desi_publication_figures.py \
  --input "$DATA_PATH" \
  --full-cloud-manifest "$MANIFEST_PATH" \
  --output-dir figures/publication_evidence \
  --budgets 125000,250000,500000,1000000 \
  --poster-budget 125000 \
  --dpi 300

# %%
import pandas as pd
from IPython.display import display

out = Path('figures/publication_evidence')
metrics = pd.read_csv(out / 'representation_fidelity_metrics.csv')
display(metrics.round(6))

# %%
from PIL import Image
for image_path in sorted(out.glob('*.png')):
    print(image_path.name)
    display(Image.open(image_path))

# %%
!zip -rq publication_evidence.zip figures/publication_evidence
from google.colab import files
files.download('publication_evidence.zip')
