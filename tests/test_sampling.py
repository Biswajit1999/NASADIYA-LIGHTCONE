from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import pytest

from nasadiya_lightcone import sampling


def catalogue() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "object_id": [f"obj-{number:02d}" for number in range(20)],
            "tracer": ["BGS"] * 12 + ["LRG"] * 6 + ["QSO"] * 2,
            "sky_cell": ["a"] * 10 + ["b"] * 10,
            "redshift_bin": ["low"] * 8 + ["mid"] * 8 + ["high"] * 4,
            "redshift": [number / 100 for number in range(20)],
        }
    )


def test_stable_object_hash_matches_tile_store_contract() -> None:
    identifier = "desi-dr1-lss:123456"
    expected = int.from_bytes(
        hashlib.blake2b(identifier.encode("utf-8"), digest_size=8).digest(),
        "big",
    )
    assert int(sampling.stable_object_hash(identifier)) == expected


def test_lowest_hash_is_independent_of_parent_order() -> None:
    frame = catalogue()
    original = sampling.select_lowest_hash(frame, 8)
    shuffled = sampling.select_lowest_hash(frame.sample(frac=1.0, random_state=19), 8)
    assert original["object_id"].tolist() == shuffled["object_id"].tolist()
    assert original["object_id"].tolist() == sorted(original["object_id"].tolist())


def test_lowest_hash_matches_full_sort_reference() -> None:
    frame = catalogue()
    hashes = sampling.stable_object_hashes(frame["object_id"])
    order = np.lexsort((frame["object_id"].to_numpy(dtype=str), hashes))
    expected = sorted(frame.iloc[order[:7]]["object_id"].tolist())
    selected = sampling.select_lowest_hash(frame, 7)
    assert selected["object_id"].tolist() == expected


def test_seeded_random_is_reproducible() -> None:
    frame = catalogue()
    first = sampling.select_seeded_random(frame, 7, seed=42)
    second = sampling.select_seeded_random(frame, 7, seed=42)
    assert first["object_id"].tolist() == second["object_id"].tolist()


def test_largest_remainder_preserves_total_and_proportions() -> None:
    counts = pd.Series({"BGS": 12, "LRG": 6, "QSO": 2})
    quotas = sampling.largest_remainder_quotas(counts, 10)
    assert quotas.to_dict() == {"BGS": 6, "LRG": 3, "QSO": 1}
    assert int(quotas.sum()) == 10


def test_stratified_lowest_hash_respects_tracer_budget() -> None:
    selected = sampling.select_stratified_lowest_hash(
        catalogue(),
        10,
        group_columns=("tracer",),
    )
    assert len(selected) == 10
    assert selected["tracer"].value_counts().to_dict() == {"BGS": 6, "LRG": 3, "QSO": 1}


def test_sampling_metadata_rejects_non_parent_rows() -> None:
    frame = catalogue()
    outside = pd.DataFrame({"object_id": ["not-in-parent"]})
    with pytest.raises(ValueError, match="originate"):
        sampling.sampling_metadata(frame, outside, strategy="lowest-hash")
