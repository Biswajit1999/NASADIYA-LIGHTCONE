from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "plot_desi_research_figure.py"
SPEC = importlib.util.spec_from_file_location("research_figures", MODULE_PATH)
assert SPEC and SPEC.loader
research_figures = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = research_figures
SPEC.loader.exec_module(research_figures)


def test_exact_hash_reduction_is_chunk_invariant() -> None:
    first = pd.DataFrame(
        {
            "object_id": ["desi-dr1:LRG:4", "desi-dr1:BGS:1", "desi-dr1:QSO:7"],
            "tracer": ["LRG", "BGS", "QSO"],
        }
    )
    second = pd.DataFrame(
        {
            "object_id": ["desi-dr1:ELG:2", "desi-dr1:LRG:5", "desi-dr1:QSO:9"],
            "tracer": ["ELG", "LRG", "QSO"],
        }
    )
    candidates = research_figures.retain_lowest_hashes(None, first, 3)
    candidates = research_figures.retain_lowest_hashes(candidates, second, 3)

    expected = pd.concat([first, second], ignore_index=True)
    expected["_stable_hash"] = research_figures.stable_hashes(expected["object_id"])
    expected = expected.sort_values(
        ["_stable_hash", "object_id"],
        kind="mergesort",
        ignore_index=True,
    ).head(3)

    assert candidates["object_id"].tolist() == expected["object_id"].tolist()
    assert len(candidates) == 3


def test_sky_histogram_counts_valid_coordinates() -> None:
    histogram = research_figures.np.zeros((2, 2), dtype=research_figures.np.int64)
    group = pd.DataFrame(
        {
            "ra_deg": [10.0, 190.0, None],
            "dec_deg": [-45.0, 45.0, 0.0],
        }
    )
    research_figures.update_sky_histogram(
        histogram,
        group,
        research_figures.np.array([-90.0, 0.0, 90.0]),
        research_figures.np.array([0.0, 180.0, 360.0]),
    )

    assert histogram.sum() == 2
