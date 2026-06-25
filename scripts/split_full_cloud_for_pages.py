#!/usr/bin/env python3
"""Split a built DESI GPU cloud into GitHub Pages-safe static chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DEFAULT_CHUNK_MIB = 40
RECORD_BYTES = 20


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cloud-dir", type=Path, default=Path("data/processed/desi-dr1/full-cloud"))
    parser.add_argument("--chunk-mib", type=int, default=DEFAULT_CHUNK_MIB)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.chunk_mib < 1:
        raise ValueError("chunk_mib must be positive.")
    manifest_path = args.cloud_dir / "full-cloud.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    binary = manifest.get("binary", {})
    source_name = binary.get("path")
    if not source_name:
        raise ValueError("Manifest must contain binary.path from scripts/full_gpu.py before splitting.")
    source = args.cloud_dir / source_name
    if not source.exists():
        raise FileNotFoundError(f"Full cloud binary does not exist: {source}")
    expected = int(binary["byte_length"])
    if source.stat().st_size != expected:
        raise ValueError("Source cloud length does not match the manifest.")

    chunk_bytes = (args.chunk_mib * 1024 * 1024 // RECORD_BYTES) * RECORD_BYTES
    if chunk_bytes < RECORD_BYTES:
        raise ValueError("Chunk size is smaller than one packed record.")
    existing = list(args.cloud_dir.glob("desi-dr1-full-cloud.part-*.f32"))
    if existing and not args.overwrite:
        raise FileExistsError("Chunk files already exist; use --overwrite to replace them.")
    for path in existing:
        path.unlink()

    parts = []
    with source.open("rb") as input_handle:
        index = 0
        while True:
            block = input_handle.read(chunk_bytes)
            if not block:
                break
            if len(block) % RECORD_BYTES:
                raise RuntimeError("Chunk split would break packed record alignment.")
            path = args.cloud_dir / f"desi-dr1-full-cloud.part-{index:03d}.f32"
            path.write_bytes(block)
            parts.append({"path": path.name, "byte_length": len(block), "sha256": sha256(path)})
            index += 1

    if sum(part["byte_length"] for part in parts) != expected:
        raise RuntimeError("Split chunks do not sum to the declared cloud byte length.")
    binary["parts"] = parts
    binary.pop("path", None)
    binary.pop("sha256", None)
    manifest["binary"] = binary
    manifest["delivery"] = {"mode": "github-pages-static-chunks", "chunk_mib": args.chunk_mib, "part_count": len(parts)}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(parts)} chunks for GitHub Pages: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
