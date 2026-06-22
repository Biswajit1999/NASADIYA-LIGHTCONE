"""Observer-centred Planck18 coordinate transforms."""

from __future__ import annotations

import numpy as np
import pandas as pd
from astropy.cosmology import Planck18

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


def enrich_with_planck18(frame: pd.DataFrame) -> pd.DataFrame:
    """Add visual comoving-distance, look-back-time, and Cartesian columns.

    The 2MRS source velocity is retained. Negative nearby recession velocities are
    clipped only for the cosmological transform, because Planck18 distance is not
    defined for negative redshift in this use case.
    """

    required = {"ra_deg", "dec_deg", "redshift"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing transform fields: {', '.join(sorted(missing))}.")

    enriched = frame.copy()
    z = pd.to_numeric(enriched["redshift"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(z).all():
        raise ValueError("redshift contains non-finite values.")
    display_z = np.clip(z, 0.0, None)
    distance = Planck18.comoving_distance(display_z).value
    lookback = Planck18.lookback_time(display_z).value
    x, y, z_cart = spherical_to_cartesian(
        enriched["ra_deg"].to_numpy(dtype=float),
        enriched["dec_deg"].to_numpy(dtype=float),
        distance,
    )
    enriched["comoving_distance_mpc"] = distance
    enriched["lookback_time_gyr"] = lookback
    enriched["x_mpc"] = x
    enriched["y_mpc"] = y
    enriched["z_mpc"] = z_cart
    enriched["cosmology_id"] = COSMOLOGY_ID
    return enriched
