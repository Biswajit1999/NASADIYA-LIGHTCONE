"""Source-table parsing and canonicalisation for the 2MRS first-release layer."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

C_KM_S = 299_792.458
TWO_MRS_TABLE = "J/ApJS/199/26/table3"
TWO_MRS_URL = "https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J/ApJS/199/26/table3"


def parse_vizier_tsv(path: str | Path) -> pd.DataFrame:
    """Read VizieR ASU TSV output while retaining only tabular source rows.

    ASU TSV includes comment metadata, a column header, a units row, and a separator
    row. This parser identifies the source header by its required `ID` field and
    discards non-data rows without inventing fields.
    """

    text = Path(path).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    try:
        header_index = next(
            index for index, line in enumerate(lines) if line.split("\t")[0].strip() == "ID"
        )
    except StopIteration as exc:
        raise ValueError("Could not find a VizieR TSV header beginning with ID.") from exc

    reader = csv.DictReader(StringIO("\n".join(lines[header_index:])), delimiter="\t")
    records = []
    for row in reader:
        identifier = (row.get("ID") or "").strip()
        if not identifier or identifier.startswith("-") or identifier.lower() in {"unit", "null"}:
            continue
        records.append({key.strip(): (value.strip() if value else "") for key, value in row.items()})
    if not records:
        raise ValueError("VizieR TSV did not contain 2MRS data rows.")
    return pd.DataFrame.from_records(records)


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace({"": np.nan, "---": np.nan}), errors="coerce")


def build_2mrs_frame(source: pd.DataFrame) -> pd.DataFrame:
    """Map the published 2MRS table into NĀSADĪYA's browser contract."""

    required = {"ID", "RAJ2000", "DEJ2000", "cz"}
    missing = required - set(source.columns)
    if missing:
        raise ValueError(f"2MRS source table is missing: {', '.join(sorted(missing))}.")

    frame = pd.DataFrame()
    frame["object_id"] = "2MRS:" + source["ID"].astype(str).str.strip()
    frame["name"] = source["ID"].astype(str).str.strip()
    frame["ra_deg"] = _numeric(source["RAJ2000"])
    frame["dec_deg"] = _numeric(source["DEJ2000"])
    frame["cz_km_s"] = _numeric(source["cz"])
    frame["cz_error_km_s"] = _numeric(source.get("e_cz", pd.Series(np.nan, index=source.index)))
    frame["redshift"] = frame["cz_km_s"] / C_KM_S
    frame["redshift_error"] = frame["cz_error_km_s"] / C_KM_S
    frame["morphology"] = source.get("type", pd.Series("", index=source.index)).replace("", np.nan)
    frame["ks_mag"] = _numeric(source.get("Kcmag", pd.Series(np.nan, index=source.index)))
    frame["source_survey"] = "2MRS"
    frame["source_release"] = "Huchra et al. 2012"
    frame["source_table"] = TWO_MRS_TABLE
    frame["source_url"] = TWO_MRS_URL
    frame["citation_key"] = "Huchra2012_2MRS"
    frame["measurement_kind"] = "spectroscopic"
    frame["object_type"] = "galaxy"
    frame["is_synthetic"] = False
    frame["distance_note"] = "z≈cz/c; visual cosmological distance is not flow-corrected"

    finite = np.isfinite(frame[["ra_deg", "dec_deg", "cz_km_s"]]).all(axis=1)
    valid_sky = frame["ra_deg"].between(0, 360, inclusive="left") & frame["dec_deg"].between(-90, 90)
    valid_velocity = frame["redshift"].between(-0.02, 0.20)
    frame = frame.loc[finite & valid_sky & valid_velocity].copy()

    if frame.empty:
        raise ValueError("No valid 2MRS rows remained after source-field validation.")
    if frame["object_id"].duplicated().any():
        duplicates = int(frame["object_id"].duplicated().sum())
        raise ValueError(f"2MRS ID collision: {duplicates} duplicate object ID(s).")
    return frame.reset_index(drop=True)
