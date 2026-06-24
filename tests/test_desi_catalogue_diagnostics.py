from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "analyze_desi_catalogue.py"
SPEC = importlib.util.spec_from_file_location("desi_catalogue_diagnostics", MODULE_PATH)
assert SPEC and SPEC.loader
diagnostics = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = diagnostics
SPEC.loader.exec_module(diagnostics)


def test_hash_selection_is_chunk_invariant() -> None:
    first = pd.DataFrame({"object_id": ["a", "b", "c"], "tracer": ["BGS"] * 3})
    second = pd.DataFrame({"object_id": ["d", "e", "f"], "tracer": ["LRG"] * 3})
    selected = diagnostics.retain_lowest_hashes(None, first, 4)
    selected = diagnostics.retain_lowest_hashes(selected, second, 4)

    all_rows = pd.concat([first, second], ignore_index=True)
    all_rows["_stable_hash"] = diagnostics.stable_hashes(all_rows["object_id"])
    expected = all_rows.sort_values(
        ["_stable_hash", "object_id"], kind="mergesort", ignore_index=True
    ).head(4)

    assert selected["object_id"].tolist() == expected["object_id"].tolist()
    assert len(selected) == 4


def test_histogram_quantile_handles_empty_and_midpoint() -> None:
    edges = np.array([0.0, 1.0, 2.0])
    assert diagnostics.histogram_quantile(np.array([0, 0]), edges, 0.5) is None
    median = diagnostics.histogram_quantile(np.array([10, 0]), edges, 0.5)
    assert median is not None
    assert 0.0 <= median <= 1.0
