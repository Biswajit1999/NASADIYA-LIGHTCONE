#!/usr/bin/env python3
"""Download a validated published photo-z catalogue source table.

Acquisition order:
1. Probe bibliography-based VizieR catalogue identifiers embedded in the project profile.
2. Optionally use a user-supplied VizieR identifier.
3. Fall back to official project archive landing pages.
4. Use metadata discovery only when explicitly requested.

The downloader will not save a table unless it exposes coordinates, an object identifier,
a photometric redshift and a per-object photometric-redshift uncertainty.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from nasadiya_lightcone.http_download import download_file  # noqa: E402
from nasadiya_lightcone.photoz import PHOTOZ_PROFILES, infer_photoz_columns  # noqa: E402

DATA_SUFFIXES = (".fits", ".fit", ".fits.gz", ".fit.gz", ".csv", ".csv.gz", ".tsv", ".tsv.gz")


def candidate_ids(catalogues) -> list[str]:
    try:
        return [str(key) for key in catalogues.keys()]
    except AttributeError:
        return []


def file_links_from_landing(url: str) -> list[str]:
    import requests

    response = requests.get(url, timeout=30, headers={"User-Agent": "NasadiyaLightcone/1.1"})
    response.raise_for_status()
    anchors = re.findall(r"href\s*=\s*['\"]([^'\"]+)['\"]", response.text, flags=re.I)
    links = []
    for anchor in anchors:
        resolved = urljoin(response.url, html.unescape(anchor))
        path = urlparse(resolved).path.lower()
        if any(path.endswith(suffix) for suffix in DATA_SUFFIXES):
            links.append(resolved)
    return sorted(set(links))


def choose_archive_link(links: list[str], profile) -> str | None:
    if not links:
        return None
    name_hints = (profile.dataset_id.replace("-", ""), *[hint.replace(" ", "").lower() for hint in profile.table_hints])
    return max(links, key=lambda link: sum(hint in link.lower().replace("-", "").replace("_", "") for hint in name_hints))


def archive_download(profile, output: Path, max_bytes: int | None) -> tuple[str, dict] | None:
    failures = []
    for landing in profile.archive_landing_urls:
        try:
            link = choose_archive_link(file_links_from_landing(landing), profile)
            if not link:
                failures.append(f"{landing}: no FITS/CSV/TSV link found")
                continue
            result = download_file(link, output, max_bytes=max_bytes)
            return "official-archive", {"landing_page": landing, "file_url": link, "sha256": result.sha256, "bytes": result.bytes_written}
        except Exception as exc:
            failures.append(f"{landing}: {exc}")
    return None, {"failures": failures}


def probe_vizier_catalogue(catalogue: str) -> tuple[list[dict], list[str]]:
    """Return validated tables and rejection messages without fetching full rows."""
    from astroquery.vizier import Vizier

    rejections: list[str] = []
    valid: list[dict] = []
    tables = Vizier(columns=["*"], row_limit=1).get_catalogs(catalogue)
    keys = candidate_ids(tables)
    if not keys:
        return [], [f"{catalogue}: no VizieR tables returned"]
    for key in keys:
        table = tables[key]
        try:
            mapping = infer_photoz_columns(table.to_pandas())
            valid.append({"catalogue": catalogue, "table": key, "mapping": mapping.as_dict(), "columns": [str(column) for column in table.colnames]})
        except Exception as exc:
            rejections.append(f"{key}: {exc}")
    return valid, rejections


def catalogue_candidates(profile, catalog_override: str | None, *, discover: bool) -> tuple[list[str], list[str]]:
    candidates: list[str] = []
    messages: list[str] = []
    if catalog_override:
        candidates.append(catalog_override)
    else:
        candidates.extend(profile.vizier_catalog_ids)
    if discover:
        from astroquery.vizier import Vizier
        for term in profile.search_terms:
            try:
                candidates.extend(candidate_ids(Vizier(columns=["*"], row_limit=1).find_catalogs(term)))
            except Exception as exc:
                messages.append(f"discovery {term!r}: {exc}")
    ordered = []
    for candidate in candidates:
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ordered, messages


def vizier_download(profile, output: Path, catalog_override: str | None, table_override: str | None, max_rows: int, *, discover: bool):
    from astroquery.vizier import Vizier

    attempts: list[str] = []
    catalogues, discovery_messages = catalogue_candidates(profile, catalog_override, discover=discover)
    attempts.extend(discovery_messages)
    if not catalogues:
        raise RuntimeError("No bibliography-based or user-supplied VizieR catalogue ID is available")
    for catalogue in catalogues:
        try:
            valid, rejections = probe_vizier_catalogue(catalogue)
            attempts.extend(rejections)
            if table_override:
                valid = [item for item in valid if item["table"] == table_override or item["table"].endswith(table_override)]
            if not valid:
                attempts.append(f"{catalogue}: no table passed the required source-schema validation")
                continue
            selected = valid[0]
            table_key = selected["table"]
            full = Vizier(columns=["*"], row_limit=max_rows).get_catalogs(table_key)
            full_keys = candidate_ids(full)
            final_key = next((key for key in full_keys if key == table_key), full_keys[0] if full_keys else None)
            if not final_key:
                raise RuntimeError("validated VizieR table returned no full-table data")
            full[final_key].write(output, overwrite=True)
            return "vizier", {
                "catalog_identifier": catalogue,
                "selected_table": final_key,
                "validated_photoz_mapping": selected["mapping"],
                "schema_columns": selected["columns"],
            }
        except Exception as exc:
            attempts.append(f"{catalogue}: {exc}")
    raise RuntimeError("; ".join(attempts[:30]) or "No VizieR table passed photo-z schema validation")


def print_probe(profile, catalog_override: str | None, *, discover: bool) -> int:
    catalogues, messages = catalogue_candidates(profile, catalog_override, discover=discover)
    if messages:
        print("Discovery notes:")
        for message in messages:
            print(f"  - {message}")
    if not catalogues:
        print("No candidate VizieR catalogue IDs are configured.")
        return 3
    passed = 0
    for catalogue in catalogues:
        try:
            valid, rejected = probe_vizier_catalogue(catalogue)
            print(f"\n{catalogue}")
            for item in valid:
                passed += 1
                print(f"  PASS {item['table']}")
                print(f"    mapping: {json.dumps(item['mapping'], sort_keys=True)}")
            for message in rejected:
                print(f"  REJECT {message}")
        except Exception as exc:
            print(f"\n{catalogue}\n  ERROR {exc}")
    if passed:
        print("\nA validated table is available. Run the same command without --probe to download it.")
        return 0
    print("\nNo table passed: NĀSADĪYA will not construct a photo-z layer without explicit per-object uncertainty.")
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", choices=sorted(PHOTOZ_PROFILES), required=True)
    parser.add_argument("--catalog", help="Optional explicit VizieR catalogue ID.")
    parser.add_argument("--table", help="Optional explicit VizieR table key.")
    parser.add_argument("--max-rows", type=int, default=-1, help="VizieR limit; -1 requests all available rows.")
    parser.add_argument("--output", type=Path, help="Raw output path; defaults to data/raw/<survey>/<survey>_source.fits.")
    parser.add_argument("--max-gb", type=float, default=20.0, help="Safety cap for direct archive streaming.")
    parser.add_argument("--provider", choices=("auto", "vizier", "archive"), default="auto")
    parser.add_argument("--probe", action="store_true", help="Validate candidate source schemas only; do not download or write a raw source file.")
    parser.add_argument("--discover", action="store_true", help="Also try broad VizieR metadata discovery after explicit bibliography-based identifiers.")
    args = parser.parse_args()
    if args.max_rows == 0 or args.max_rows < -1 or args.max_gb <= 0:
        print("--max-rows must be -1 or positive; --max-gb must be positive.")
        return 2
    profile = PHOTOZ_PROFILES[args.survey]
    if args.probe:
        return print_probe(profile, args.catalog, discover=args.discover)
    output = args.output or PROJECT_ROOT / "data" / "raw" / profile.dataset_id / f"{profile.dataset_id}_source.fits"
    output.parent.mkdir(parents=True, exist_ok=True)
    result = None
    errors: list[str] = []
    # Prefer an explicit citation-linked catalogue record to archive-link scraping.
    if args.provider in ("auto", "vizier"):
        try:
            result = vizier_download(profile, output, args.catalog, args.table, args.max_rows, discover=args.discover)
        except Exception as exc:
            errors.append(f"VizieR source validation/download: {exc}")
    if result is None and args.provider in ("auto", "archive"):
        try:
            archive_result, archive_info = archive_download(profile, output, int(args.max_gb * 1024**3))
            result = archive_result, archive_info
            if archive_result is None:
                errors.extend(f"official archive: {message}" for message in archive_info.get("failures", []))
        except Exception as exc:
            errors.append(f"official archive: {exc}")
    if result is None or result[0] is None:
        print(f"{profile.dataset_id} download failed.\n" + "\n".join(f"  - {error}" for error in errors))
        print("No raw file was written. The release cannot build this layer without a validated published source table.")
        return 3
    provider, provenance = result
    metadata = {
        "dataset_id": profile.dataset_id,
        "survey": profile.survey,
        "provider": provider,
        "source_url": profile.source_url,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "raw_file": output.name,
        "is_synthetic": False,
        **provenance,
    }
    output.with_suffix(".source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved published {profile.survey} source file: {output}")
    print(f"Provider: {provider}")
    print(f"Next: scripts/build_{profile.dataset_id.replace('-', '_')}_tile_store.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
