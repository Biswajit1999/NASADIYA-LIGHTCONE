#!/usr/bin/env python3
"""Download 2MPZ through the strict published-source photo-z downloader."""
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.argv[1:1] = ["--survey", "2mpz"]
# Execute the generic CLI in-process so Windows users retain one stable command.
exec(compile((PROJECT_ROOT / "scripts" / "download_vizier_photoz.py").read_text(encoding="utf-8"), "download_vizier_photoz.py", "exec"), {"__name__": "__main__", "__file__": str(PROJECT_ROOT / "scripts" / "download_vizier_photoz.py"), "sys": sys})
