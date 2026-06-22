"""Adapters for DESI DR1 LSS clustering catalogues."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .tiles import SurveyDescriptor, canonicalise_survey_frame

DESI_DR1_LSS_BASE = (
    "https://data.desi.lbl.gov/public/dr1/survey/catalogs/dr1/LSS/iron/LSScats/v1.2"
)

DESI_COMPONENTS: dict[str, tuple[str, str]] = {
    "bgs": ("BGS_BRIGHT-21.5_NGC_clustering.dat.fits", "BGS_BRIGHT-21.5_SGC_clustering.dat.fits"),
    "elg": ("ELG_LOPnotqso_NGC_clustering.dat.fits", "ELG_LOPnotqso_SGC_clustering.dat.fits"),
    "lrg": ("LRG_NGC_clustering.dat.fits", "LRG_SGC_clustering.dat.fits"),
    "qso": ("QSO_NGC_clustering.dat.fits", "QSO_SGC_clustering.dat.fits"),
}


def infer_desi_columns(source: pd.DataFrame) -> dict[str, str]:
    normal = {"".join(ch.lower() for ch in str(name) if ch.isalnum()): str(name) for name in source.columns}

    def choose(label: str, aliases: tuple[str, ...]) -> str:
        for alias in aliases:
            result = normal.get("".join(ch.lower() for ch in alias if ch.isalnum()))
            if result:
                return result
        raise ValueError(f"DESI adapter could not resolve {label}. Available: {', '.join(map(str, source.columns))}")

    return {
        "targetid": choose("TARGETID", ("TARGETID", "target_id", "id")),
        "ra": choose("RA", ("RA", "ra")),
        "dec": choose("DEC", ("DEC", "dec")),
        "redshift": choose("Z", ("Z", "redshift")),
    }


def build_desi_frame(source: pd.DataFrame, *, component: str, source_file: str) -> tuple[pd.DataFrame, dict[str, str], SurveyDescriptor]:
    mapping = infer_desi_columns(source)
    working = source.copy()
    # The target identifier remains recoverable in the source record while the component
    # prefix protects the tile build from an accidental cross-tracer duplicate.
    working["_nasadiya_id"] = component.upper() + ":" + working[mapping["targetid"]].astype(str).str.strip()
    descriptor = SurveyDescriptor(
        dataset_id="desi-dr1",
        survey="DESI DR1 LSS clustering catalogues",
        release="DESI DR1 · iron · LSScats v1.2",
        source_url=DESI_DR1_LSS_BASE + "/",
        citation_key="DESI2026_DR1",
        measurement_kind="spectroscopic",
        object_type="mixed extragalactic target",
        distance_note="DESI spectroscopic-redshift Planck18 visual placement",
    )
    frame = canonicalise_survey_frame(
        working,
        descriptor,
        id_column="_nasadiya_id",
        ra_column=mapping["ra"],
        dec_column=mapping["dec"],
        redshift_column=mapping["redshift"],
        redshift_error_column=None,
        magnitude_column=None,
        cosmology_mode="interpolated",
        interpolation_z_max=5.0,
    )
    frame["name"] = frame["object_id"].str.replace("desi-dr1:", "", n=1, regex=False)
    frame["source_table"] = Path(source_file).name
    frame["tracer"] = component.upper()
    return frame, mapping, descriptor
