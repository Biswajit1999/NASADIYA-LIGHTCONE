"""Compact, serialisable browser-export utilities."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def _json_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    return str(value)


def write_browser_catalog(frame: pd.DataFrame, output: str | Path, *, input_sha256: str) -> dict:
    """Write a static browser payload and a small processing manifest."""

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "object_id", "name", "object_type", "measurement_kind", "source_survey",
        "source_release", "source_table", "source_url", "citation_key", "is_synthetic",
        "ra_deg", "dec_deg", "cz_km_s", "cz_error_km_s", "redshift", "redshift_error",
        "ks_mag", "morphology", "comoving_distance_mpc", "lookback_time_gyr", "x_mpc",
        "y_mpc", "z_mpc", "cosmology_id", "distance_note",
    ]
    present = [column for column in columns if column in frame.columns]
    objects = [
        {column: _json_value(row[column]) for column in present}
        for _, row in frame[present].iterrows()
    ]
    payload = {
        "meta": {
            "dataset_id": "2mrs-table3",
            "dataset_label": "2MRS Table 3 · real spectroscopic catalogue",
            "object_count": len(objects),
            "source_survey": "2MRS",
            "source_table": "J/ApJS/199/26/table3",
            "source_release": "Huchra et al. 2012",
            "source_url": "https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J/ApJS/199/26/table3",
            "citation_key": "Huchra2012_2MRS",
            "is_synthetic": False,
            "coordinate_frame": "ICRS/J2000; observer-centred Cartesian Mpc",
            "distance_convention": "Planck18 comoving distance evaluated at z≈cz/c",
            "nearby_universe_caution": "Individual nearby radial positions are not flow-corrected distances.",
            "source_file_sha256": input_sha256,
            "built_utc": datetime.now(timezone.utc).isoformat(),
        },
        "objects": objects,
    }
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    output.write_text(encoded, encoding="utf-8")
    output_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    manifest = {
        "dataset_id": payload["meta"]["dataset_id"],
        "object_count": len(objects),
        "browser_catalog": output.name,
        "browser_catalog_sha256": output_hash,
        "source_file_sha256": input_sha256,
        "is_synthetic": False,
    }
    (output.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
