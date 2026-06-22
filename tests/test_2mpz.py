from pathlib import Path

import pandas as pd
import pytest

from nasadiya_lightcone.two_mpz import build_2mpz_frame, infer_2mpz_columns


def test_2mpz_adapter_requires_photoz_uncertainty_and_preserves_mapping():
    source = pd.read_csv(Path("tests/fixtures/2mpz_short.csv"))
    mapping = infer_2mpz_columns(source)
    assert mapping.redshift == "zphot"
    assert mapping.redshift_error == "e_zphot"

    frame, selected, descriptor = build_2mpz_frame(source)
    assert len(frame) == 2
    assert set(frame["measurement_kind"]) == {"photometric"}
    assert (frame["redshift_error"] > 0).all()
    assert (frame["is_synthetic"] == False).all()  # noqa: E712
    assert selected.as_dict()["object_id"] == "2MASS"
    assert descriptor.dataset_id == "2mpz"


def test_2mpz_adapter_rejects_missing_uncertainty_column():
    source = pd.read_csv(Path("tests/fixtures/2mpz_short.csv")).drop(columns=["e_zphot"])
    with pytest.raises(ValueError, match="photometric-redshift uncertainty"):
        infer_2mpz_columns(source)
