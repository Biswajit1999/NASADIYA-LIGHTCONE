import json

import pandas as pd

from nasadiya_lightcone.tiles import (
    SurveyDescriptor,
    canonicalise_survey_frame,
    write_tile_store,
)


def test_tile_store_requires_observed_rows_and_writes_manifest(tmp_path):
    source = pd.DataFrame(
        {
            "id": ["a", "b", "c"],
            "ra": [0.0, 90.0, 180.0],
            "dec": [0.0, 10.0, -10.0],
            "z": [0.01, 0.02, 0.03],
            "e_z": [0.001, 0.001, 0.001],
            "mag": [10.0, 11.0, 12.0],
        }
    )
    descriptor = SurveyDescriptor(
        dataset_id="test-photo",
        survey="Test Survey",
        release="test",
        source_url="https://example.invalid/source",
        citation_key="Test2026",
        measurement_kind="photometric",
    )
    frame = canonicalise_survey_frame(
        source,
        descriptor,
        id_column="id",
        ra_column="ra",
        dec_column="dec",
        redshift_column="z",
        redshift_error_column="e_z",
        magnitude_column="mag",
    )
    manifest = write_tile_store(
        frame,
        tmp_path / "tiles",
        descriptor=descriptor,
        radial_shell_mpc=100,
        ra_bins=4,
        dec_bins=2,
        overview_max_points=2,
    )
    assert manifest["record_count"] == 3
    assert manifest["tile_count"] >= 1
    index = json.loads((tmp_path / "tiles" / "index.json").read_text())
    assert index["dataset"]["is_synthetic"] is False
    assert index["dataset"]["radial_uncertainty_required"] is True
    overview = json.loads((tmp_path / "tiles" / "overview.json").read_text())
    assert len(overview["records"]) <= 2
