"""Static, provenance-preserving tile-store generation for large survey catalogues.

The browser must never load a multi-million row catalogue as one JSON document.  This
module converts canonical observed rows into a directory of spatial tiles plus a small
manifest and deterministic overview sample.  The tile store is designed to live on
object storage or release assets, not in normal Git history.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cosmology import COSMOLOGY_ID, enrich_with_planck18

TILE_STORE_FORMAT = "nasadiya-tile-store/v1"
TILE_COLUMNS = [
    "object_id",
    "ra_deg",
    "dec_deg",
    "redshift",
    "redshift_error",
    "comoving_distance_mpc",
    "x_mpc",
    "y_mpc",
    "z_mpc",
    "magnitude",
]


@dataclass(frozen=True)
class SurveyDescriptor:
    """Provenance required for every derived static survey layer."""

    dataset_id: str
    survey: str
    release: str
    source_url: str
    citation_key: str
    measurement_kind: str
    object_type: str = "galaxy"
    distance_note: str = "Planck18 comoving-distance placement for visual navigation"

    def __post_init__(self) -> None:
        if self.measurement_kind not in {"spectroscopic", "photometric"}:
            raise ValueError("measurement_kind must be 'spectroscopic' or 'photometric'.")
        for field in ("dataset_id", "survey", "release", "source_url", "citation_key"):
            if not getattr(self, field):
                raise ValueError(f"SurveyDescriptor.{field} must not be empty.")


def _as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def canonicalise_survey_frame(
    source: pd.DataFrame,
    descriptor: SurveyDescriptor,
    *,
    id_column: str,
    ra_column: str,
    dec_column: str,
    redshift_column: str,
    redshift_error_column: str | None = None,
    magnitude_column: str | None = None,
) -> pd.DataFrame:
    """Map one externally supplied catalogue into the tile-store row contract.

    The caller must explicitly name source columns.  This avoids silently guessing
    catalog-specific meanings, especially for photometric-redshift uncertainty fields.
    """

    required = {
        "id_column": id_column,
        "ra_column": ra_column,
        "dec_column": dec_column,
        "redshift_column": redshift_column,
    }
    missing = [label for label, column in required.items() if column not in source.columns]
    if missing:
        raise ValueError(
            "Source catalogue is missing requested column(s): "
            + ", ".join(f"{label}={required[label]!r}" for label in missing)
        )
    for label, column in {
        "redshift_error_column": redshift_error_column,
        "magnitude_column": magnitude_column,
    }.items():
        if column and column not in source.columns:
            raise ValueError(f"Source catalogue is missing requested {label}={column!r}.")

    frame = pd.DataFrame(index=source.index)
    raw_id = source[id_column].astype(str).str.strip()
    frame["object_id"] = descriptor.dataset_id + ":" + raw_id
    frame["ra_deg"] = _as_numeric(source[ra_column])
    frame["dec_deg"] = _as_numeric(source[dec_column])
    frame["redshift"] = _as_numeric(source[redshift_column])
    frame["redshift_error"] = (
        _as_numeric(source[redshift_error_column])
        if redshift_error_column
        else np.nan
    )
    frame["magnitude"] = _as_numeric(source[magnitude_column]) if magnitude_column else np.nan
    frame["source_survey"] = descriptor.survey
    frame["source_release"] = descriptor.release
    frame["source_url"] = descriptor.source_url
    frame["citation_key"] = descriptor.citation_key
    frame["measurement_kind"] = descriptor.measurement_kind
    frame["object_type"] = descriptor.object_type
    frame["is_synthetic"] = False
    frame["distance_note"] = descriptor.distance_note

    finite = np.isfinite(frame[["ra_deg", "dec_deg", "redshift"]]).all(axis=1)
    valid_sky = frame["ra_deg"].between(0, 360, inclusive="left") & frame["dec_deg"].between(-90, 90)
    valid_redshift = frame["redshift"].between(0, 10)
    nonempty_id = raw_id.ne("") & raw_id.str.lower().ne("nan")
    frame = frame.loc[finite & valid_sky & valid_redshift & nonempty_id].copy()

    if descriptor.measurement_kind == "photometric":
        if redshift_error_column is None:
            raise ValueError(
                "Photometric layers require an explicit redshift_error_column; "
                "do not render photo-z distances as exact radial positions."
            )
        frame = frame.loc[np.isfinite(frame["redshift_error"]) & (frame["redshift_error"] > 0)].copy()

    if frame.empty:
        raise ValueError("No valid observed rows remained after source-field validation.")
    if frame["object_id"].duplicated().any():
        duplicate_count = int(frame["object_id"].duplicated().sum())
        raise ValueError(f"Source ID collision: {duplicate_count} duplicate object identifier(s).")

    enriched = enrich_with_planck18(frame)
    enriched["cosmology_id"] = COSMOLOGY_ID
    return enriched.reset_index(drop=True)


def _json_number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _row_payload(row: pd.Series) -> list[Any]:
    return [
        str(row["object_id"]),
        _json_number(row["ra_deg"]),
        _json_number(row["dec_deg"]),
        _json_number(row["redshift"]),
        _json_number(row["redshift_error"]),
        _json_number(row["comoving_distance_mpc"]),
        _json_number(row["x_mpc"]),
        _json_number(row["y_mpc"]),
        _json_number(row["z_mpc"]),
        _json_number(row["magnitude"]),
    ]


def _tile_key(
    frame: pd.DataFrame,
    *,
    radial_shell_mpc: float,
    ra_bins: int,
    dec_bins: int,
) -> pd.Series:
    if radial_shell_mpc <= 0 or ra_bins <= 0 or dec_bins <= 0:
        raise ValueError("Tile dimensions must be positive.")
    distance_bin = np.floor(frame["comoving_distance_mpc"].to_numpy(dtype=float) / radial_shell_mpc).astype(int)
    ra_bin = np.floor((frame["ra_deg"].to_numpy(dtype=float) % 360) / 360 * ra_bins).astype(int)
    dec_fraction = np.clip((frame["dec_deg"].to_numpy(dtype=float) + 90) / 180, 0, 0.999999)
    dec_bin = np.floor(dec_fraction * dec_bins).astype(int)
    return pd.Series(
        [f"r{shell:03d}_a{ra:02d}_d{dec:02d}" for shell, ra, dec in zip(distance_bin, ra_bin, dec_bin)],
        index=frame.index,
        dtype="string",
    )


def _bounds(group: pd.DataFrame) -> dict[str, list[float]]:
    return {
        "x_mpc": [float(group["x_mpc"].min()), float(group["x_mpc"].max())],
        "y_mpc": [float(group["y_mpc"].min()), float(group["y_mpc"].max())],
        "z_mpc": [float(group["z_mpc"].min()), float(group["z_mpc"].max())],
        "redshift": [float(group["redshift"].min()), float(group["redshift"].max())],
    }


def write_tile_store(
    frame: pd.DataFrame,
    output_dir: str | Path,
    *,
    descriptor: SurveyDescriptor,
    radial_shell_mpc: float = 200.0,
    ra_bins: int = 24,
    dec_bins: int = 12,
    overview_max_points: int = 100_000,
) -> dict[str, Any]:
    """Write tiled observed rows plus a deterministic lightweight overview sample."""

    required = set(TILE_COLUMNS) - {"magnitude"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Tile frame is missing required field(s): {', '.join(sorted(missing))}.")
    if not (frame.get("is_synthetic") == False).all():  # noqa: E712
        raise ValueError("Tile stores reject synthetic or unlabelled rows.")

    output_dir = Path(output_dir)
    tiles_dir = output_dir / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    working = frame.copy()
    if "magnitude" not in working.columns:
        working["magnitude"] = np.nan
    working["tile_id"] = _tile_key(
        working,
        radial_shell_mpc=radial_shell_mpc,
        ra_bins=ra_bins,
        dec_bins=dec_bins,
    )

    tile_entries: list[dict[str, Any]] = []
    for tile_id, group in working.groupby("tile_id", sort=True):
        records = [_row_payload(row) for _, row in group.iterrows()]
        relative_path = Path("tiles") / f"{tile_id}.json"
        payload = {
            "format": TILE_STORE_FORMAT,
            "dataset_id": descriptor.dataset_id,
            "tile_id": str(tile_id),
            "columns": TILE_COLUMNS,
            "records": records,
        }
        (output_dir / relative_path).write_text(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        tile_entries.append(
            {
                "id": str(tile_id),
                "path": relative_path.as_posix(),
                "count": len(records),
                "bounds": _bounds(group),
            }
        )

    overview_stride = max(1, math.ceil(len(working) / max(1, overview_max_points)))
    overview = working.iloc[::overview_stride].head(overview_max_points)
    overview_payload = {
        "format": TILE_STORE_FORMAT,
        "dataset_id": descriptor.dataset_id,
        "columns": TILE_COLUMNS,
        "selection": {
            "method": "stable-input-stride",
            "stride": overview_stride,
            "max_points": overview_max_points,
            "not_a_scientific_selection": True,
        },
        "records": [_row_payload(row) for _, row in overview.iterrows()],
    }
    overview_path = output_dir / "overview.json"
    overview_path.write_text(
        json.dumps(overview_payload, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = {
        "format": TILE_STORE_FORMAT,
        "dataset": {
            "dataset_id": descriptor.dataset_id,
            "survey": descriptor.survey,
            "release": descriptor.release,
            "source_url": descriptor.source_url,
            "citation_key": descriptor.citation_key,
            "measurement_kind": descriptor.measurement_kind,
            "object_type": descriptor.object_type,
            "is_synthetic": False,
            "cosmology_id": COSMOLOGY_ID,
            "distance_note": descriptor.distance_note,
            "radial_uncertainty_required": descriptor.measurement_kind == "photometric",
        },
        "record_count": int(len(working)),
        "tile_count": len(tile_entries),
        "record_columns": TILE_COLUMNS,
        "overview": {"path": "overview.json", "count": int(len(overview))},
        "partition": {
            "method": "radial-shell-plus-sky-bin",
            "radial_shell_mpc": radial_shell_mpc,
            "ra_bins": ra_bins,
            "dec_bins": dec_bins,
        },
        "tiles": tile_entries,
    }
    (output_dir / "index.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
