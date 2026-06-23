from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "build_desi_research_bundle.py"
SPEC = importlib.util.spec_from_file_location("research_bundle", MODULE_PATH)
assert SPEC and SPEC.loader
research_bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research_bundle)


def test_hash_selection_is_deterministic() -> None:
    ids = pd.Series(["desi-dr1:BGS:1", "desi-dr1:LRG:2", "desi-dr1:QSO:3"])
    first = research_bundle.stable_hash_mask(ids, 0.5)
    second = research_bundle.stable_hash_mask(ids, 0.5)
    assert first.tolist() == second.tolist()
    assert research_bundle.stable_hash_mask(ids, 1.0).all()
    assert not research_bundle.stable_hash_mask(ids, 0.0).any()


def test_tile_normalisation_retains_observed_contract(tmp_path: Path) -> None:
    columns = [
        "object_id",
        "ra_deg",
        "dec_deg",
        "redshift",
        "redshift_error",
        "comoving_distance_mpc",
        "lookback_time_gyr",
        "x_mpc",
        "y_mpc",
        "z_mpc",
        "magnitude",
    ]
    payload = {
        "format": "nasadiya-tile-store/v1",
        "columns": columns,
        "records": [
            [
                "desi-dr1:ELG:42",
                12.5,
                -4.2,
                0.8,
                0.0002,
                2500.0,
                7.1,
                1.0,
                2.0,
                3.0,
                21.0,
            ]
        ],
    }
    path = tmp_path / "tile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    frame = research_bundle.normalise_tile_frame(path, columns)

    assert frame.columns.tolist() == list(research_bundle.OUTPUT_COLUMNS)
    assert frame.loc[0, "object_id"] == "desi-dr1:ELG:42"
    assert frame.loc[0, "tracer"] == "ELG"
    assert frame.loc[0, "x_mpc"] == 1.0
