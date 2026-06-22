#!/usr/bin/env python3
"""Download selected official DESI DR1 LSS clustering catalogues.

This is a deliberate, source-preserving acquisition step. It requests only the
published BGS, LRG, ELG and/or QSO clustering products selected by ``--components``;
no rows are synthesised or cross-matched here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from nasadiya_lightcone.desi import DESI_COMPONENTS, DESI_DR1_LSS_BASE  # noqa: E402
from nasadiya_lightcone.http_download import download_file  # noqa: E402


def progress(label: str):
    last = {"value": -1}
    def report(done: int, total: int | None) -> None:
        if total:
            percent = int(done * 100 / total)
            if percent // 5 != last["value"] // 5:
                last["value"] = percent
                print(f"{label}: {percent}% ({done / 1e6:.1f}/{total / 1e6:.1f} MB)")
        elif done // (64 * 1024 * 1024) != last["value"]:
            last["value"] = done // (64 * 1024 * 1024)
            print(f"{label}: {done / 1e6:.1f} MB")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--components", default="bgs,lrg,elg,qso", help="Comma-separated: bgs,lrg,elg,qso")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "raw" / "desi-dr1")
    parser.add_argument("--max-gb", type=float, default=3.0, help="Hard per-file/total safety cap for this run.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Required to begin actual downloads.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    components = [item.strip().lower() for item in args.components.split(",") if item.strip()]
    unknown = sorted(set(components) - set(DESI_COMPONENTS))
    if unknown or not components:
        print(f"Unknown/empty components: {', '.join(unknown) or '(none)'}")
        return 2
    files = [(component, filename, f"{DESI_DR1_LSS_BASE}/{filename}") for component in components for filename in DESI_COMPONENTS[component]]
    print("DESI DR1 LSS request plan:")
    for component, filename, url in files:
        print(f"  {component.upper():3}  {filename}\n       {url}")
    print(f"Safety limit: {args.max_gb:.2f} GB across this command.")
    if args.dry_run:
        return 0
    if not args.yes:
        print("Review the plan then repeat with --yes.")
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    remaining = int(args.max_gb * 1024**3)
    manifest_files = []
    try:
        for component, filename, url in files:
            destination = args.output / filename
            result = download_file(
                url,
                destination,
                overwrite=args.overwrite,
                max_bytes=remaining,
                progress=progress(filename),
            )
            remaining -= result.bytes_written
            if remaining < 0:
                raise RuntimeError("Combined DESI acquisition exceeded --max-gb.")
            manifest_files.append({"component": component, "filename": filename, "url": url, "bytes": result.bytes_written, "sha256": result.sha256})
            print(f"Saved {filename}: {result.bytes_written / 1e6:.1f} MB")
    except Exception as exc:
        print(f"DESI DR1 download failed: {exc}")
        return 3

    payload = {"dataset_id": "desi-dr1", "release": "DESI DR1 LSS iron v1.2", "downloaded_utc": datetime.now(timezone.utc).isoformat(), "files": manifest_files, "is_synthetic": False}
    (args.output / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {len(manifest_files)} official DESI files to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
