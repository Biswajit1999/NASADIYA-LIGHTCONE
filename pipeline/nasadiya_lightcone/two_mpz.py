"""Curated adapter for the published 2MPZ all-sky photo-z catalogue.

The adapter does not invent source columns.  It resolves only known aliases and
records the selected mappings in the resulting tile-store manifest.  Photometric
redshift uncertainty is mandatory: a 2MPZ layer cannot be built without it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .tiles import SurveyDescriptor, canonicalise_survey_frame

TWO_MPZ_CATALOG_ID = "2MPZ-published-release"
TWO_MPZ_SOURCE_URL = "https://arxiv.org/abs/1311.5246"


@dataclass(frozen=True)
class ColumnMapping:
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
    return "".join(character.lower() for character in str(name) if character.isalnum())


def _resolve(columns: Iterable[str], aliases: tuple[str, ...], label: str, *, required: bool = True) -> str | None:
    available = { _normalise(column): str(column) for column in columns }
    for alias in aliases:
        match = available.get(_normalise(alias))
        if match:
            return match
    if required:
        choices = ", ".join(map(str, columns))
        raise ValueError(
            f"2MPZ adapter could not resolve {label}. Available source columns: {choices}"
        )
    return None


def infer_2mpz_columns(source: pd.DataFrame) -> ColumnMapping:
    """Resolve a published 2MPZ-like table while rejecting missing required fields."""

    columns = [str(column) for column in source.columns]
    return ColumnMapping(
        object_id=_resolve(columns, ("2MASS", "2MASX", "_2MASS", "ID", "Name"), "object identifier"),
        ra_deg=_resolve(columns, ("RAJ2000", "RAdeg", "RA", "RA_ICRS"), "right ascension"),
        dec_deg=_resolve(columns, ("DEJ2000", "DEdeg", "DEC", "DE_ICRS"), "declination"),
        redshift=_resolve(columns, ("zphot", "z_phot", "zph", "zANN", "z"), "photometric redshift"),
        redshift_error=_resolve(
            columns,
            ("e_zphot", "e_z_phot", "zerr", "zphoterr", "zsig", "sigma_z", "sigz"),
            "photometric-redshift uncertainty",
        ),
        magnitude=_resolve(
            columns,
            ("Kcmag", "Kmag", "Ks", "Ksmag", "K"),
            "K-band magnitude",
            required=False,
        ),
    )


def build_2mpz_frame(
    source: pd.DataFrame,
    *,
    release: str = "Bilicki et al. 2014",
    source_url: str = TWO_MPZ_SOURCE_URL,
) -> tuple[pd.DataFrame, ColumnMapping, SurveyDescriptor]:
    """Canonicalise 2MPZ rows using explicit, recorded source-column mappings."""

    mapping = infer_2mpz_columns(source)
    descriptor = SurveyDescriptor(
        dataset_id="2mpz",
        survey="2MPZ",
        release=release,
        source_url=source_url,
        citation_key="Bilicki2014_2MPZ",
        measurement_kind="photometric",
        object_type="galaxy",
        distance_note=(
            "Photometric-redshift Planck18 visual placement; radial uncertainty must be retained "
            "and is not an exact distance measurement"
        ),
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
    )
    frame["name"] = frame["object_id"].str.replace("2mpz:", "", n=1, regex=False)
    frame["source_table"] = TWO_MPZ_CATALOG_ID
    return frame, mapping, descriptor
