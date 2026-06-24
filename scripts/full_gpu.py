#!/usr/bin/env python3
"""Build a packed full-catalogue DESI rendering cloud from Parquet.

The output is a rendering product for local or object-storage delivery. It is
not a row-level research table: individual source inspection remains available
through the provenance-preserving DESI tile store.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_COLUMNS = ("tracer", "x_mpc", "y_mpc", "z_mpc", "redshift")
TRACER_CODES = {"UNKNOWN": 0, "BGS": 1, "LRG": 2, "ELG": 3, "QSO": 4}
STRIDE_FLOATS = 5
