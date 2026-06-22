#!/usr/bin/env python3
"""Download the published 2MRS Table 3 source file from VizieR."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"
TABLE_ID = "J/ApJS/199/26/table3"
COLUMNS = "ID,RAJ2000,DEJ2000,cz,e_cz,type,Kcmag"


def build_url(limit: int | None) -> str:
    params = {
        "-source": TABLE_ID,
        "-out": COLUMNS,
        "-out.max": str(limit) if limit else "unlimited",
    }
    return f"{BASE_URL}?{urlencode(params)}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/2mrs/2mrs_table3.tsv"))
    parser.add_argument("--limit", type=int, default=None, help="Optional row cap for a quick smoke test.")
    parser.add_argument("--force", action="store_true", help="Replace an existing source file.")
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive.")
    if args.output.exists() and not args.force:
        print(f"Source file already exists: {args.output}")
        print("Use --force to download it again.")
        return 0

    url = build_url(args.limit)
    request = Request(url, headers={"User-Agent": "Nasadiya-Lightcone/0.1 (+GitHub project)"})
    print(f"Requesting {TABLE_ID} from VizieR…")
    try:
        with urlopen(request, timeout=120) as response:
            content = response.read()
    except OSError as exc:
        print(f"Download failed: {exc}")
        return 2

    if b"RAJ2000" not in content or b"DEJ2000" not in content or b"cz" not in content:
        print("Download did not look like the expected 2MRS TSV response.")
        return 3

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    manifest = {
        "dataset_id": "2mrs-table3",
        "catalogue": TABLE_ID,
        "query_url": url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": digest,
        "bytes": len(content),
        "is_synthetic": False,
        "citation": "Huchra et al. 2012, ApJS 199, 26; VizieR catalogue access tool, CDS.",
    }
    manifest_path = args.output.parent / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved {args.output} ({len(content):,} bytes)")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
