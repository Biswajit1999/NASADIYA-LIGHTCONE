#!/usr/bin/env python3
"""Download WISE × SuperCOSMOS through the strict published-source photo-z downloader."""
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Inject the profile flag before invoking the generic downloader.
sys.argv[1:1] = ["--survey", "wise-sc"]
exec(compile((PROJECT_ROOT / "scripts" / "download_vizier_photoz.py").read_text(encoding="utf-8"), "download_vizier_photoz.py", "exec"), {"__name__": "__main__", "__file__": str(PROJECT_ROOT / "scripts" / "download_vizier_photoz.py"), "sys": sys})
