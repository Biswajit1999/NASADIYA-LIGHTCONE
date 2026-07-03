from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from astropy.cosmology import Planck18
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "analyze_desi_dr1_science.py"
SPEC = importlib.util.spec_from_file_location("desi_dr1_science", MODULE_PATH)
assert SPEC and SPEC.loader
desi_dr1_science = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = desi_dr1_science
SPEC.loader.exec_module(desi_dr1_science)


def catalogue_rows() -> pd.DataFrame:
    redshift = np.array([0.1, 0.3, 0.7, 1.2, 2.0])
    distance = Planck18.comoving_distance(redshift).value
    ra = np.array([10.0, 40.0, 80.0, 160.0, 280.0])
    dec = np.array([-30.0, -10.0, 0.0, 20.0, 45.0])
    cos_dec = np.cos(np.deg2rad(dec))
    return pd.DataFrame(
        {
            "object_id": [f"desi-dr1:LRG:{index}" for index in range(len(redshift))],
            "tracer": ["LRG"] * len(redshift),
            "ra_deg": ra,
            "dec_deg": dec,
            "redshift": redshift,
            "x_mpc": distance * cos_dec * np.cos(np.deg2rad(ra)),
            "y_mpc": distance * cos_dec * np.sin(np.deg2rad(ra)),
            "z_mpc": distance * np.sin(np.deg2rad(dec)),
        }
    )


def test_load_catalogue_rejects_invalid_coordinates_and_blank_ids(tmp_path: Path) -> None:
    frame = catalogue_rows()
    invalid = frame.iloc[[0, 1]].copy()
    invalid["object_id"] = ["   ", "bad-ra"]
    invalid["ra_deg"] = [10.0, 360.0]
    path = tmp_path / "catalogue.parquet"
    pd.concat([frame, invalid], ignore_index=True).to_parquet(path, index=False)

    loaded = desi_dr1_science.load_catalogue(path)

    assert len(loaded) == len(frame)
    assert loaded["ra_deg"].between(0.0, 360.0, inclusive="left").all()


def test_redshift_slice_edges_always_define_four_panels() -> None:
    low_redshift = pd.DataFrame({"redshift": [0.0, 0.8]})
    full_lightcone = pd.DataFrame({"redshift": [0.0, 2.5]})

    low_edges = desi_dr1_science.redshift_slice_edges(low_redshift)
    full_edges = desi_dr1_science.redshift_slice_edges(full_lightcone)

    assert len(low_edges) == 5
    assert len(full_edges) == 5
    assert np.all(np.diff(low_edges) > 0)
    assert np.all(np.diff(full_edges) > 0)
    assert full_edges.tolist() == [0.0, 0.4, 0.8, 1.4, 2.5]


def test_final_redshift_interval_is_labelled_inclusive() -> None:
    assert desi_dr1_science.redshift_interval_label(0.4, 0.8, final=False) == "0.4 ≤ z < 0.8"
    assert desi_dr1_science.redshift_interval_label(1.4, 2.5, final=True) == "1.4 ≤ z ≤ 2.5"
