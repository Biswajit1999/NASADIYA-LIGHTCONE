from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from nasadiya_lightcone.photoz import PHOTOZ_PROFILES


def test_photoz_profiles_have_explicit_vizier_catalogue_identifiers():
    for dataset_id in ("2mpz", "wise-sc"):
        profile = PHOTOZ_PROFILES[dataset_id]
        assert profile.vizier_catalog_ids
        assert all(identifier.startswith("J/") for identifier in profile.vizier_catalog_ids)


def test_photoz_profiles_are_explicit_about_expected_scale():
    assert PHOTOZ_PROFILES["2mpz"].expected_rows == 1_000_000
    assert PHOTOZ_PROFILES["wise-sc"].expected_rows == 20_000_000
