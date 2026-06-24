"""Reproducible catalogue-sampling primitives for NĀSADĪYA validation.

These functions select real observed rows from a parent catalogue. They do not
apply survey completeness weights, infer a density field, or create a scientific
sample for clustering analysis. Their purpose is to build and compare
browser-level representations at a fixed point budget.

The ``lowest_hash`` strategy intentionally matches the BLAKE2b-64 object-ID
contract used by :class:`ChunkedTileStoreWriter`, making it possible to validate
the public overview against the full parent catalogue.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import hashlib
from typing import Any

import numpy as np
import pandas as pd

HASH_ALGORITHM = "blake2b-64"
HASH_DIGEST_SIZE = 8


@dataclass(frozen=True)
class SamplingMetadata:
    """Machine-readable description of a browser-representation selection."""

    strategy: str
    parent_rows: int
    selected_rows: int
    object_id_column: str
    group_columns: tuple[str, ...] = ()
    random_seed: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready record suitable for a manifest."""

        return {
            "strategy": self.strategy,
            "parent_rows": self.parent_rows,
            "selected_rows": self.selected_rows,
            "object_id_column": self.object_id_column,
            "group_columns": list(self.group_columns),
            "random_seed": self.random_seed,
            "hash_algorithm": HASH_ALGORITHM if self.strategy != "seeded-random" else None,
            "scientific_scope": (
                "Browser-representation selection only; not a completeness-corrected "
                "or clustering-ready scientific sample."
            ),
        }


def _require_valid_budget(frame: pd.DataFrame, n_rows: int) -> None:
    if not isinstance(n_rows, (int, np.integer)):
        raise TypeError("n_rows must be an integer.")
    if n_rows < 1:
        raise ValueError("n_rows must be positive.")
    if n_rows > len(frame):
        raise ValueError("n_rows cannot exceed the number of available rows.")


def _require_object_ids(frame: pd.DataFrame, object_id_column: str) -> pd.Series:
    if object_id_column not in frame.columns:
        raise ValueError(f"Missing object ID column: {object_id_column!r}.")
    values = frame[object_id_column].astype("string")
    if values.isna().any() or values.str.len().eq(0).any():
        raise ValueError("Object identifiers must be non-empty for deterministic sampling.")
    if values.duplicated().any():
        raise ValueError("Object identifiers must be unique for deterministic sampling.")
    return values


def stable_object_hash(value: object) -> np.uint64:
    """Return the tile-store-compatible deterministic 64-bit BLAKE2b hash."""

    digest = hashlib.blake2b(
        str(value).encode("utf-8"),
        digest_size=HASH_DIGEST_SIZE,
    ).digest()
    return np.uint64(int.from_bytes(digest, "big"))


def stable_object_hashes(values: Iterable[object]) -> np.ndarray:
    """Return deterministic BLAKE2b-64 hashes for an iterable of object IDs."""

    return np.fromiter(
        (stable_object_hash(value) for value in values),
        dtype=np.uint64,
    )


def select_lowest_hash(
    frame: pd.DataFrame,
    n_rows: int,
    *,
    object_id_column: str = "object_id",
) -> pd.DataFrame:
    """Select real rows using the lowest stable object-ID hashes.

    The returned frame is ordered by object ID so equivalent parent catalogues
    yield stable table ordering independent of input or chunk order.
    """

    _require_valid_budget(frame, n_rows)
    object_ids = _require_object_ids(frame, object_id_column)
    if n_rows == len(frame):
        return frame.sort_values(object_id_column, kind="mergesort").reset_index(drop=True)

    hashes = stable_object_hashes(object_ids)
    positions = np.arange(len(frame))
    order = np.lexsort((positions, object_ids.to_numpy(dtype=str), hashes))
    selected = frame.iloc[order[:n_rows]].copy()
    return selected.sort_values(object_id_column, kind="mergesort").reset_index(drop=True)


def select_seeded_random(
    frame: pd.DataFrame,
    n_rows: int,
    *,
    seed: int,
    object_id_column: str = "object_id",
) -> pd.DataFrame:
    """Select a reproducible pseudo-random baseline without replacement."""

    _require_valid_budget(frame, n_rows)
    _require_object_ids(frame, object_id_column)
    generator = np.random.default_rng(seed)
    positions = np.sort(generator.choice(len(frame), size=n_rows, replace=False))
    selected = frame.iloc[positions].copy()
    return selected.sort_values(object_id_column, kind="mergesort").reset_index(drop=True)


def largest_remainder_quotas(counts: pd.Series, n_rows: int) -> pd.Series:
    """Allocate a point budget proportionally with deterministic tie-breaking."""

    if counts.empty:
        raise ValueError("Cannot allocate quotas for zero strata.")
    if (counts <= 0).any():
        raise ValueError("All stratum counts must be positive.")
    total = int(counts.sum())
    if n_rows < 1 or n_rows > total:
        raise ValueError("n_rows must lie between one and the total stratum count.")

    expected = counts.astype(float) * (float(n_rows) / total)
    quotas = np.floor(expected).astype(int)
    remaining = int(n_rows - quotas.sum())
    if remaining:
        ranking = sorted(
            counts.index,
            key=lambda key: (-(expected.loc[key] - quotas.loc[key]), str(key)),
        )
        for key in ranking[:remaining]:
            quotas.loc[key] += 1
    return quotas.astype(int)


def select_stratified_lowest_hash(
    frame: pd.DataFrame,
    n_rows: int,
    *,
    group_columns: Sequence[str],
    object_id_column: str = "object_id",
) -> pd.DataFrame:
    """Select a deterministic proportional sample within declared strata.

    Strata are representation-policy labels, not an observational selection
    correction. Typical use is ``("tracer",)`` or
    ``("tracer", "sky_cell", "redshift_bin")`` after those labels have been
    constructed from the observed parent catalogue.
    """

    _require_valid_budget(frame, n_rows)
    _require_object_ids(frame, object_id_column)
    columns = tuple(group_columns)
    if not columns:
        raise ValueError("At least one group column is required for stratified selection.")
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing group column(s): {', '.join(missing)}.")
    if frame.loc[:, list(columns)].isna().any(axis=None):
        raise ValueError("Stratified selection requires explicit non-null stratum labels.")

    groups = list(frame.groupby(list(columns), sort=False, observed=True, dropna=False))
    labels = [key if isinstance(key, tuple) else (key,) for key, _ in groups]
    counts = pd.Series([len(group) for _, group in groups], index=pd.Index(labels, dtype=object))
    quotas = largest_remainder_quotas(counts, n_rows)

    selected_groups: list[pd.DataFrame] = []
    for label, (_, group) in zip(labels, groups):
        quota = int(quotas.loc[label])
        if quota:
            selected_groups.append(
                select_lowest_hash(group, quota, object_id_column=object_id_column)
            )
    selected = pd.concat(selected_groups, ignore_index=True)
    return selected.sort_values(object_id_column, kind="mergesort").reset_index(drop=True)


def sampling_metadata(
    frame: pd.DataFrame,
    selected: pd.DataFrame,
    *,
    strategy: str,
    object_id_column: str = "object_id",
    group_columns: Sequence[str] = (),
    random_seed: int | None = None,
) -> SamplingMetadata:
    """Build manifest metadata after validating parent-row lineage."""

    _require_object_ids(frame, object_id_column)
    selected_ids = _require_object_ids(selected, object_id_column)
    parent_ids = set(frame[object_id_column].astype(str))
    if not set(selected_ids.astype(str)).issubset(parent_ids):
        raise ValueError("Selected rows must all originate in the declared parent catalogue.")
    return SamplingMetadata(
        strategy=strategy,
        parent_rows=len(frame),
        selected_rows=len(selected),
        object_id_column=object_id_column,
        group_columns=tuple(group_columns),
        random_seed=random_seed,
    )
