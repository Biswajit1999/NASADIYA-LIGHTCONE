"""Conservative Gaia DR3 local-star sample utilities.

Gaia is kept separate from the extragalactic lightcone. This module produces a local
Milky-Way sample using explicit parallax-quality cuts, not a galaxy layer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_gaia_local_frame(source: pd.DataFrame) -> pd.DataFrame:
    required = {"source_id", "ra", "dec", "parallax", "parallax_error", "phot_g_mean_mag"}
    missing = required - set(source.columns)
    if missing:
        raise ValueError(f"Gaia source is missing: {', '.join(sorted(missing))}")
    frame = pd.DataFrame(index=source.index)
    frame["source_id"] = source["source_id"].astype(str).str.strip()
    frame["ra_deg"] = pd.to_numeric(source["ra"], errors="coerce")
    frame["dec_deg"] = pd.to_numeric(source["dec"], errors="coerce")
    frame["parallax_mas"] = pd.to_numeric(source["parallax"], errors="coerce")
    frame["parallax_error_mas"] = pd.to_numeric(source["parallax_error"], errors="coerce")
    frame["g_mag"] = pd.to_numeric(source["phot_g_mean_mag"], errors="coerce")
    finite = np.isfinite(frame[["ra_deg", "dec_deg", "parallax_mas", "parallax_error_mas", "g_mag"]]).all(axis=1)
    valid = finite & (frame["parallax_mas"] > 0) & (frame["parallax_error_mas"] > 0)
    frame = frame.loc[valid].copy()
    frame["distance_pc_naive"] = 1000.0 / frame["parallax_mas"]
    frame["distance_error_pc_naive"] = frame["distance_pc_naive"] * (frame["parallax_error_mas"] / frame["parallax_mas"])
    ra = np.deg2rad(frame["ra_deg"].to_numpy(float))
    dec = np.deg2rad(frame["dec_deg"].to_numpy(float))
    distance = frame["distance_pc_naive"].to_numpy(float)
    frame["x_pc"] = distance * np.cos(dec) * np.cos(ra)
    frame["y_pc"] = distance * np.cos(dec) * np.sin(ra)
    frame["z_pc"] = distance * np.sin(dec)
    frame["is_synthetic"] = False
    return frame.reset_index(drop=True)
