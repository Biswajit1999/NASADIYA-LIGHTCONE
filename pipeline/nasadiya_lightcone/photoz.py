"""Adapters for observed photometric-redshift catalogues.

The project never assigns an invented redshift error. A photo-z layer is rejected
unless the selected source table contains an explicit uncertainty column.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .tiles import SurveyDescriptor, canonicalise_survey_frame


@dataclass(frozen=True)
class PhotoZProfile:
    dataset_id: str
    survey: str
    release: str
    citation_key: str
    source_url: str
    search_terms: tuple[str, ...]
    table_hints: tuple[str, ...]
    expected_rows: int | None
    footprint_note: str
    archive_landing_urls: tuple[str, ...]
    vizier_catalog_ids: tuple[str, ...]


PHOTOZ_PROFILES: dict[str, PhotoZProfile] = {
    "2mpz": PhotoZProfile(
        dataset_id="2mpz",
        survey="2MASS Photometric Redshift Catalogue (2MPZ)",
        release="Bilicki et al. 2014",
        citation_key="Bilicki2014_2MPZ",
        source_url="https://arxiv.org/abs/1311.5246",
        search_terms=("2MPZ", "2MASS Photometric Redshift", "Bilicki 2014"),
        table_hints=("2mpz", "2mass", "photometric", "redshift"),
        expected_rows=1_000_000,
        footprint_note="All-sky photo-z layer; radial uncertainty is retained for every accepted row.",
        archive_landing_urls=(
            "https://surveys.roe.ac.uk/ssa/TWOMPZ/",
            "http://surveys.roe.ac.uk/ssa/TWOMPZ/",
            "https://ssa.roe.ac.uk/TWOMPZ/",
        ),
        # The paper reference is not itself a VizieR catalogue key. Keep this empty
        # until a maintained, verified public table endpoint is confirmed.
        vizier_catalog_ids=(),
    ),
    "wise-sc": PhotoZProfile(
        dataset_id="wise-sc",
        survey="WISE × SuperCOSMOS Photometric Redshift Catalogue",
        release="Bilicki et al. 2016",
        citation_key="Bilicki2016_WISESC",
        source_url="https://arxiv.org/abs/1607.01182",
        search_terms=("WISE SuperCOSMOS", "WISE x SuperCOSMOS", "SuperCOSMOS photometric redshift"),
        table_hints=("wise", "supercosmos", "photo", "redshift"),
        expected_rows=20_000_000,
        footprint_note="Wide photo-z layer; survey masking and radial uncertainty remain visible measurement properties.",
        archive_landing_urls=(
            "https://ssa.roe.ac.uk/WISExSCOS/",
            "http://ssa.roe.ac.uk/WISExSCOS/",
            "https://surveys.roe.ac.uk/ssa/WISExSCOS/",
        ),
        # No verified VizieR source key is configured. A user-supplied key must be
        # validated with --probe before a full download is allowed.
        vizier_catalog_ids=(),
    ),
}


@dataclass(frozen=True)
class PhotoZColumnMapping:
    object_id: str
    ra_deg: str
    dec_deg: str
    redshift: str
    redshift_error: str
    magnitude: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "object_id": self.object_id,
            "ra_deg": self.ra_deg,
            "dec_deg": self.dec_deg,
            "redshift": self.redshift,
            "redshift_error": self.redshift_error,
            "magnitude": self.magnitude,
        }


def _normalise(name: str) -> str:
    return "".join(char.lower() for char in str(name) if char.isalnum())


def _resolve(columns: Iterable[str], aliases: tuple[str, ...], label: str, *, required: bool = True) -> str | None:
    available = {_normalise(column): str(column) for column in columns}
    for alias in aliases:
        match = available.get(_normalise(alias))
        if match:
            return match
    if required:
        shown = ", ".join(map(str, columns))
        raise ValueError(f"Photo-z adapter could not resolve {label}. Available columns: {shown}")
    return None


def infer_photoz_columns(source: pd.DataFrame) -> PhotoZColumnMapping:
    columns = [str(column) for column in source.columns]
    return PhotoZColumnMapping(
        object_id=_resolve(columns, ("2MASS", "2MASX", "AllWISE", "WISE", "source_id", "objid", "ID", "Name", "Object"), "object identifier"),
        ra_deg=_resolve(columns, ("RAJ2000", "RAdeg", "RA", "RA_ICRS", "ra", "RAdegJ2000"), "right ascension"),
        dec_deg=_resolve(columns, ("DEJ2000", "DEdeg", "DEC", "DE_ICRS", "dec", "DEdegJ2000"), "declination"),
        redshift=_resolve(columns, ("zphot", "z_phot", "zPhoto", "zphoto", "zph", "zANN", "zmean", "z", "zphotANN"), "photometric redshift"),
        redshift_error=_resolve(columns, ("e_zphot", "e_z_phot", "e_zphoto", "e_zph", "zerr", "zphoterr", "zPhotoErr", "zsig", "sigma_z", "sigz", "zstd", "zerr68", "zerr_68", "zphot_sigma"), "photometric-redshift uncertainty"),
        magnitude=_resolve(columns, ("Kcmag", "Kmag", "Ks", "Ksmag", "K", "W1", "w1mpro", "rmag", "Rmag", "R1mag"), "representative magnitude", required=False),
    )


def build_photoz_frame(source: pd.DataFrame, profile: PhotoZProfile, *, mapping: PhotoZColumnMapping | None = None) -> tuple[pd.DataFrame, PhotoZColumnMapping, SurveyDescriptor]:
    mapping = mapping or infer_photoz_columns(source)
    descriptor = SurveyDescriptor(
        dataset_id=profile.dataset_id,
        survey=profile.survey,
        release=profile.release,
        source_url=profile.source_url,
        citation_key=profile.citation_key,
        measurement_kind="photometric",
        object_type="galaxy",
        distance_note="Photometric-redshift Planck18 visual placement; supplied radial uncertainty is retained and is not an exact distance measurement",
    )
    frame = canonicalise_survey_frame(
        source,
        descriptor,
        id_column=mapping.object_id,
        ra_column=mapping.ra_deg,
        dec_column=mapping.dec_deg,
        redshift_column=mapping.redshift,
        redshift_error_column=mapping.redshift_error,
        magnitude_column=mapping.magnitude,
        cosmology_mode="interpolated",
        interpolation_z_max=1.5,
    )
    frame["name"] = frame["object_id"].str.replace(f"{profile.dataset_id}:", "", n=1, regex=False)
    frame["source_table"] = profile.dataset_id
    return frame, mapping, descriptor
