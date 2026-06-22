"""Static, provenance-preserving tile-store generation for large survey catalogues.

The browser must never load a multi-million row catalogue as one JSON document.  This
module converts canonical observed rows into a directory of spatial tiles plus a small
manifest and deterministic overview sample.  The tile store is designed to live on
object storage or release assets, not in normal Git history.
"""

from __future__ import annotations

import json
import math
import hashlib
import heapq
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cosmology import (
    COSMOLOGY_ID,
    enrich_with_planck18,
    enrich_with_planck18_interpolated,
)

TILE_STORE_FORMAT = "nasadiya-tile-store/v1"
TILE_COLUMNS = [
    "object_id",
    "ra_deg",
    "dec_deg",
    "redshift",
    "redshift_error",
    "comoving_distance_mpc",
    "lookback_time_gyr",
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
    cosmology_mode: str = "exact",
    interpolation_grid_size: int = 32769,
    interpolation_z_max: float | None = None,
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

    if cosmology_mode == "exact":
        enriched = enrich_with_planck18(frame)
        processing = {"method": "Planck18-exact"}
    elif cosmology_mode == "interpolated":
        enriched, processing = enrich_with_planck18_interpolated(
            frame,
            grid_size=interpolation_grid_size,
            z_max=interpolation_z_max,
        )
    else:
        raise ValueError("cosmology_mode must be 'exact' or 'interpolated'.")
    enriched["cosmology_id"] = COSMOLOGY_ID
    enriched.attrs["cosmology_processing"] = processing
    return enriched.reset_index(drop=True)


def _json_number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _record_payload(values: tuple[Any, ...]) -> list[Any]:
    """Serialise a canonical tile row without pandas ``iterrows`` overhead."""

    identifier, *numeric = values
    return [str(identifier), *[_json_number(value) for value in numeric]]


def _records_payload(frame: pd.DataFrame) -> list[list[Any]]:
    return [
        _record_payload(values)
        for values in frame[TILE_COLUMNS].itertuples(index=False, name=None)
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
    extra_manifest: dict[str, Any] | None = None,
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
        records = _records_payload(group)
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
        "records": _records_payload(overview),
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
        "processing": {
            "cosmology": frame.attrs.get("cosmology_processing", {"method": "Planck18-exact"}),
        },
        "partition": {
            "method": "radial-shell-plus-sky-bin",
            "radial_shell_mpc": radial_shell_mpc,
            "ra_bins": ra_bins,
            "dec_bins": dec_bins,
        },
        "tiles": tile_entries,
    }
    if extra_manifest:
        manifest["source_mapping"] = extra_manifest
    (output_dir / "index.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


class ChunkedTileStoreWriter:
    """Append canonical observed frames into a final static spatial tile store.

    It prevents a 20-million-row photo-z catalogue from being loaded as one pandas
    frame. Tile fragments are written as local NDJSON during ingestion and converted
    to browser JSON only at finalisation. Every retained record remains a real source
    row; the overview is a deterministic lowest-hash subset, never synthetic points.
    """

    def __init__(
        self,
        output_dir: str | Path,
        *,
        descriptor: SurveyDescriptor,
        radial_shell_mpc: float = 200.0,
        ra_bins: int = 24,
        dec_bins: int = 12,
        overview_max_points: int = 125_000,
    ) -> None:
        if overview_max_points < 1:
            raise ValueError("overview_max_points must be positive.")
        self.output_dir = Path(output_dir)
        self.descriptor = descriptor
        self.radial_shell_mpc = radial_shell_mpc
        self.ra_bins = ra_bins
        self.dec_bins = dec_bins
        self.overview_max_points = int(overview_max_points)
        self.stage_dir = self.output_dir / ".nasadiya_stage"
        self.fragments_dir = self.stage_dir / "fragments"
        self.tile_entries: dict[str, dict[str, Any]] = {}
        self.record_count = 0
        self._heap: list[tuple[int, int, list[Any]]] = []
        self._sequence = 0
        self._processing: dict[str, Any] | None = None

        if self.stage_dir.exists():
            shutil.rmtree(self.stage_dir)
        self.fragments_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _stable_hash(value: str) -> int:
        return int.from_bytes(hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest(), "big")

    def _consider_overview(self, record: list[Any]) -> None:
        # Max-heap emulation through negative hash: retain rows with the smallest hashes.
        score = self._stable_hash(str(record[0]))
        item = (-score, self._sequence, record)
        self._sequence += 1
        if len(self._heap) < self.overview_max_points:
            heapq.heappush(self._heap, item)
        elif item > self._heap[0]:
            heapq.heapreplace(self._heap, item)

    def ingest(self, frame: pd.DataFrame) -> None:
        required = set(TILE_COLUMNS) - {"magnitude"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Tile chunk is missing required fields: {', '.join(sorted(missing))}")
        if not (frame.get("is_synthetic") == False).all():  # noqa: E712
            raise ValueError("Tile stores reject synthetic or unlabelled rows.")
        if frame.empty:
            return

        working = frame.copy()
        if "magnitude" not in working.columns:
            working["magnitude"] = np.nan
        working["tile_id"] = _tile_key(
            working,
            radial_shell_mpc=self.radial_shell_mpc,
            ra_bins=self.ra_bins,
            dec_bins=self.dec_bins,
        )
        self._processing = frame.attrs.get("cosmology_processing", self._processing)

        for tile_id, group in working.groupby("tile_id", sort=False):
            records = _records_payload(group)
            fragment = self.fragments_dir / f"{tile_id}.jsonl"
            with fragment.open("a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False))
                    handle.write("\n")
                    self._consider_overview(record)
            current = self.tile_entries.get(str(tile_id))
            group_bounds = _bounds(group)
            if current is None:
                self.tile_entries[str(tile_id)] = {
                    "id": str(tile_id),
                    "path": (Path("tiles") / f"{tile_id}.json").as_posix(),
                    "count": len(records),
                    "bounds": group_bounds,
                }
            else:
                current["count"] += len(records)
                for field, bounds in group_bounds.items():
                    current["bounds"][field][0] = min(current["bounds"][field][0], bounds[0])
                    current["bounds"][field][1] = max(current["bounds"][field][1], bounds[1])
            self.record_count += len(records)

    def finalise(self, *, extra_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.record_count == 0:
            raise ValueError("No observed rows were accepted into the tile store.")
        tiles_dir = self.output_dir / "tiles"
        if tiles_dir.exists():
            shutil.rmtree(tiles_dir)
        tiles_dir.mkdir(parents=True, exist_ok=True)

        for tile_id, entry in sorted(self.tile_entries.items()):
            fragment = self.fragments_dir / f"{tile_id}.jsonl"
            output = self.output_dir / entry["path"]
            with output.open("w", encoding="utf-8") as handle:
                header = {
                    "format": TILE_STORE_FORMAT,
                    "dataset_id": self.descriptor.dataset_id,
                    "tile_id": tile_id,
                    "columns": TILE_COLUMNS,
                }
                prefix = json.dumps(header, separators=(",", ":"), ensure_ascii=False)[:-1]
                handle.write(prefix + ',"records":[')
                first = True
                with fragment.open("r", encoding="utf-8") as source:
                    for line in source:
                        if not first:
                            handle.write(",")
                        handle.write(line.rstrip("\n"))
                        first = False
                handle.write("]}")

        selected = [item[2] for item in sorted(self._heap, key=lambda item: (-item[0], item[1]))]
        overview = {
            "format": TILE_STORE_FORMAT,
            "dataset_id": self.descriptor.dataset_id,
            "columns": TILE_COLUMNS,
            "selection": {
                "method": "deterministic-lowest-object-hash",
                "max_points": self.overview_max_points,
                "not_a_scientific_selection": True,
            },
            "records": selected,
        }
        (self.output_dir / "overview.json").write_text(
            json.dumps(overview, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )

        manifest: dict[str, Any] = {
            "format": TILE_STORE_FORMAT,
            "dataset": {
                "dataset_id": self.descriptor.dataset_id,
                "survey": self.descriptor.survey,
                "release": self.descriptor.release,
                "source_url": self.descriptor.source_url,
                "citation_key": self.descriptor.citation_key,
                "measurement_kind": self.descriptor.measurement_kind,
                "object_type": self.descriptor.object_type,
                "is_synthetic": False,
                "cosmology_id": COSMOLOGY_ID,
                "distance_note": self.descriptor.distance_note,
                "radial_uncertainty_required": self.descriptor.measurement_kind == "photometric",
            },
            "record_count": int(self.record_count),
            "tile_count": len(self.tile_entries),
            "record_columns": TILE_COLUMNS,
            "overview": {"path": "overview.json", "count": len(selected)},
            "processing": {"cosmology": self._processing or {"method": "Planck18-interpolated"}},
            "partition": {
                "method": "radial-shell-plus-sky-bin",
                "radial_shell_mpc": self.radial_shell_mpc,
                "ra_bins": self.ra_bins,
                "dec_bins": self.dec_bins,
            },
            "tiles": [self.tile_entries[key] for key in sorted(self.tile_entries)],
        }
        if extra_manifest:
            manifest["source_mapping"] = extra_manifest
        (self.output_dir / "index.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        shutil.rmtree(self.stage_dir, ignore_errors=True)
        return manifest
