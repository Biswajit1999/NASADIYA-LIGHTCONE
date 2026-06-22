#!/usr/bin/env python3
"""Build 2MPZ's chunked real-row tile store."""
from __future__ import annotations
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.argv[1:1] = ["--survey", "2mpz"]
exec(compile((PROJECT_ROOT / "scripts" / "build_photoz_tile_store.py").read_text(encoding="utf-8"), "build_photoz_tile_store.py", "exec"), {"__name__": "__main__", "__file__": str(PROJECT_ROOT / "scripts" / "build_photoz_tile_store.py"), "sys": sys})
