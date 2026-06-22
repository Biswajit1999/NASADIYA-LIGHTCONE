from pathlib import Path

from nasadiya_lightcone import build_2mrs_frame, enrich_with_planck18, parse_vizier_tsv, write_browser_catalog


def test_parse_and_build_2mrs_fixture(tmp_path):
    source = parse_vizier_tsv(Path("tests/fixtures/2mrs_short.tsv"))
    assert len(source) == 2
    frame = build_2mrs_frame(source)
    assert set(frame["source_survey"]) == {"2MRS"}
    assert not frame["is_synthetic"].any()

    enriched = enrich_with_planck18(frame)
    assert {"x_mpc", "y_mpc", "z_mpc", "comoving_distance_mpc"}.issubset(enriched.columns)
    assert (enriched["comoving_distance_mpc"] >= 0).all()

    output = tmp_path / "2mrs_lightcone.json"
    manifest = write_browser_catalog(enriched, output, input_sha256="test")
    assert manifest["object_count"] == 2
    assert output.exists()
