import json

import pandas as pd

from nasadiya_lightcone.desi import build_desi_frame
from nasadiya_lightcone.gaia import build_gaia_local_frame
from nasadiya_lightcone.photoz import (
    PHOTOZ_PROFILES,
    build_photoz_frame,
    infer_photoz_columns,
)
from nasadiya_lightcone.tiles import ChunkedTileStoreWriter


def test_photoz_profile_requires_real_error_and_maps_fixture() -> None:
    source = pd.DataFrame(
        {
            "objid": ["one", "two"],
            "ra": [10.0, 20.0],
            "dec": [2.0, -3.0],
            "zphot": [0.1, 0.2],
            "zerr": [0.01, 0.02],
            "w1mpro": [12.1, 13.2],
        }
    )
    mapping = infer_photoz_columns(source)
    assert mapping.redshift_error == "zerr"
    frame, _, descriptor = build_photoz_frame(
        source,
        PHOTOZ_PROFILES["wise-sc"],
        mapping=mapping,
    )
    assert len(frame) == 2
    assert descriptor.measurement_kind == "photometric"
    assert (frame["redshift_error"] > 0).all()


def test_chunked_writer_keeps_all_rows_and_bounded_real_overview(tmp_path) -> None:
    source = pd.DataFrame(
        {
            "objid": ["a", "b", "c", "d"],
            "ra": [1.0, 2.0, 3.0, 4.0],
            "dec": [0.0, 1.0, 2.0, 3.0],
            "zphot": [0.1, 0.2, 0.3, 0.4],
            "zerr": [0.01, 0.01, 0.02, 0.02],
        }
    )
    frame, mapping, descriptor = build_photoz_frame(
        source,
        PHOTOZ_PROFILES["2mpz"],
    )
    writer = ChunkedTileStoreWriter(
        tmp_path / "store",
        descriptor=descriptor,
        overview_max_points=2,
        radial_shell_mpc=100,
    )
    writer.ingest(frame.iloc[:2])
    writer.ingest(frame.iloc[2:])
    manifest = writer.finalise(extra_manifest={"column_mapping": mapping.as_dict()})
    assert manifest["record_count"] == 4
    overview = json.loads((tmp_path / "store" / "overview.json").read_text())
    assert len(overview["records"]) == 2
    assert overview["selection"]["not_a_scientific_selection"] is True


def test_desi_adapter_preserves_spectroscopic_provenance() -> None:
    source = pd.DataFrame(
        {
            "TARGETID": [11, 12],
            "RA": [11.0, 12.0],
            "DEC": [0.0, 1.0],
            "Z": [0.8, 1.1],
        }
    )
    frame, mapping, descriptor = build_desi_frame(
        source,
        component="lrg",
        source_file="LRG_NGC_clustering.dat.fits",
    )
    assert mapping["targetid"] == "TARGETID"
    assert descriptor.measurement_kind == "spectroscopic"
    assert frame["object_id"].str.contains("LRG:11").any()


def test_gaia_local_adapter_stays_galactic_and_observed() -> None:
    source = pd.DataFrame(
        {
            "source_id": [1, 2],
            "ra": [0.0, 90.0],
            "dec": [0.0, 0.0],
            "parallax": [10.0, 5.0],
            "parallax_error": [0.5, 0.5],
            "phot_g_mean_mag": [12.0, 15.0],
        }
    )
    frame = build_gaia_local_frame(source)
    assert len(frame) == 2
    assert (frame["is_synthetic"] == False).all()  # noqa: E712
    assert frame["distance_pc_naive"].tolist() == [100.0, 200.0]
