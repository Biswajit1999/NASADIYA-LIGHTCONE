"""Observer-centred Planck18 coordinate transforms.

Large catalogue builds can use a dense, monotonic interpolation table rather than
calling the Astropy cosmology integrals once per source row.  The provenance manifest
records this choice so a visual navigation transform is never mistaken for a source
measurement.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from astropy.cosmology import Planck18

_GRID_CACHE: dict[tuple[int, float], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

COSMOLOGY_ID = "Planck18 (Astropy)"


def spherical_to_cartesian(ra_deg: np.ndarray, dec_deg: np.ndarray, distance_mpc: np.ndarray):
    """Convert ICRS spherical coordinates to an observer-centred Cartesian frame."""

    ra = np.deg2rad(np.asarray(ra_deg, dtype=float))
    dec = np.deg2rad(np.asarray(dec_deg, dtype=float))
    distance = np.asarray(distance_mpc, dtype=float)
    cos_dec = np.cos(dec)
    return (
        distance * cos_dec * np.cos(ra),
        distance * cos_dec * np.sin(ra),
        distance * np.sin(dec),
    )


def _validated_redshift(frame: pd.DataFrame) -> np.ndarray:
    required = {"ra_deg", "dec_deg", "redshift"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing transform fields: {', '.join(sorted(missing))}.")
    z = pd.to_numeric(frame["redshift"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(z).all():
        raise ValueError("redshift contains non-finite values.")
    return np.clip(z, 0.0, None)


def _append_coordinates(frame: pd.DataFrame, distance: np.ndarray, lookback: np.ndarray) -> pd.DataFrame:
    enriched = frame.copy()
    x, y, z_cart = spherical_to_cartesian(
        enriched["ra_deg"].to_numpy(dtype=float),
        enriched["dec_deg"].to_numpy(dtype=float),
        distance,
    )
    enriched["comoving_distance_mpc"] = np.asarray(distance, dtype=float)
    enriched["lookback_time_gyr"] = np.asarray(lookback, dtype=float)
    enriched["x_mpc"] = x
    enriched["y_mpc"] = y
    enriched["z_mpc"] = z_cart
    enriched["cosmology_id"] = COSMOLOGY_ID
    return enriched


def enrich_with_planck18(frame: pd.DataFrame) -> pd.DataFrame:
    """Add exact Planck18 distance, look-back time, and Cartesian columns."""

    display_z = _validated_redshift(frame)
    distance = Planck18.comoving_distance(display_z).value
    lookback = Planck18.lookback_time(display_z).value
    return _append_coordinates(frame, distance, lookback)


def enrich_with_planck18_interpolated(
    frame: pd.DataFrame,
    *,
    grid_size: int = 32769,
    z_max: float | None = None,
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    """Add Planck18-derived columns using a cached dense redshift grid.

    ``z_max`` keeps chunked catalogue builds on one common interpolation domain.
    It is a transform setting only; it does not clip the observed source redshift.
    """

    if grid_size < 1025:
        raise ValueError("grid_size must be at least 1025 for the interpolated transform.")
    display_z = _validated_redshift(frame)
    observed_max = float(np.max(display_z)) if len(display_z) else 0.0
    domain_max = max(observed_max, float(z_max or 0.0))
    if domain_max == 0.0:
        return _append_coordinates(frame, np.zeros_like(display_z), np.zeros_like(display_z)), {
            "method": "Planck18-interpolated",
            "grid_size": int(grid_size),
            "z_max": 0.0,
        }

    key = (int(grid_size), round(domain_max, 8))
    if key not in _GRID_CACHE:
        grid = np.linspace(0.0, domain_max, int(grid_size), dtype=float)
        _GRID_CACHE[key] = (
            grid,
            np.asarray(Planck18.comoving_distance(grid).value, dtype=float),
            np.asarray(Planck18.lookback_time(grid).value, dtype=float),
        )
    grid, distance_grid, lookback_grid = _GRID_CACHE[key]
    distance = np.interp(display_z, grid, distance_grid)
    lookback = np.interp(display_z, grid, lookback_grid)
    return _append_coordinates(frame, distance, lookback), {
        "method": "Planck18-interpolated",
        "grid_size": int(grid_size),
        "z_max": float(domain_max),
    }

