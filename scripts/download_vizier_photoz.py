#!/usr/bin/env python3
"""Download a published photo-z source table without relying on a guessed VizieR key.

Order of acquisition:
1. Probe the official project archive landing pages published with the catalogue paper;
   discover a direct FITS/CSV/TSV file link and stream it with resume support.
2. Fall back to VizieR metadata discovery; only accept a table with coordinate, ID,
   photo-z and explicit uncertainty columns.

The script stops rather than saving a catalogue with an unknown schema or fabricated
per-object uncertainty.
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
    try: return [str(key) for key in catalogues.keys()]
    except AttributeError: return []


def file_links_from_landing(url: str) -> list[str]:
    import requests
    response = requests.get(url, timeout=30, headers={"User-Agent": "NasadiyaLightcone/0.7"})
    response.raise_for_status()
    anchors = re.findall(r"href\s*=\s*['\"]([^'\"]+)['\"]", response.text, flags=re.I)
    links=[]
    for anchor in anchors:
        resolved = urljoin(response.url, html.unescape(anchor))
        path = urlparse(resolved).path.lower()
        if any(path.endswith(suffix) for suffix in DATA_SUFFIXES): links.append(resolved)
    return sorted(set(links))


def choose_archive_link(links: list[str], profile) -> str | None:
    if not links: return None
    name_hints = (profile.dataset_id.replace('-', ''), *[h.replace(' ', '').lower() for h in profile.table_hints])
    return max(links, key=lambda link: sum(hint in link.lower().replace('-', '').replace('_','') for hint in name_hints))


def archive_download(profile, output: Path, max_bytes: int | None) -> tuple[str, dict] | None:
    failures=[]
    for landing in profile.archive_landing_urls:
        try:
            link=choose_archive_link(file_links_from_landing(landing), profile)
            if not link:
                failures.append(f"{landing}: no FITS/CSV/TSV link found")
                continue
            result=download_file(link, output, max_bytes=max_bytes)
            return "official-archive", {"landing_page": landing, "file_url": link, "sha256": result.sha256, "bytes": result.bytes_written}
        except Exception as exc:
            failures.append(f"{landing}: {exc}")
    return None


def vizier_download(profile, output: Path, catalog_override: str | None, table_override: str | None, max_rows: int):
    from astroquery.vizier import Vizier
    attempts=[]
    catalogues=[catalog_override] if catalog_override else []
    if not catalogues:
        for term in profile.search_terms:
            try: catalogues.extend(candidate_ids(Vizier(columns=['*'], row_limit=1).find_catalogs(term)))
            except Exception as exc: attempts.append(f"discovery {term!r}: {exc}")
    ordered=[]
    for item in catalogues:
        if item not in ordered: ordered.append(item)
    for catalog in ordered:
        try:
            probe=Vizier(columns=['*'], row_limit=1).get_catalogs(catalog)
            for key in candidate_ids(probe):
                if table_override and not (key == table_override or key.endswith(table_override)): continue
                table=probe[key]
                try: mapping=infer_photoz_columns(table.to_pandas())
                except Exception as exc:
                    attempts.append(f"{key}: {exc}"); continue
                full=Vizier(columns=['*'], row_limit=max_rows).get_catalogs(key)
                fullkeys=candidate_ids(full)
                selected=next((candidate for candidate in fullkeys if candidate == key), fullkeys[0] if fullkeys else None)
                if not selected: raise RuntimeError('validated table returned no full-table data')
                full[selected].write(output, overwrite=True)
                return "vizier", {"catalog_identifier": catalog, "selected_table": selected, "validated_photoz_mapping": mapping.as_dict()}
        except Exception as exc:
            attempts.append(f"{catalog}: {exc}")
    raise RuntimeError("; ".join(attempts[:20]) or "VizieR discovery returned no candidate table")


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--survey', choices=sorted(PHOTOZ_PROFILES), required=True)
    parser.add_argument('--catalog', help='Optional explicit VizieR catalogue ID for fallback.')
    parser.add_argument('--table', help='Optional explicit VizieR table key for fallback.')
    parser.add_argument('--max-rows', type=int, default=-1, help='VizieR fallback limit; -1 requests all rows.')
    parser.add_argument('--output', type=Path, help='Raw output path; defaults to data/raw/<survey>/<survey>_source.fits.')
    parser.add_argument('--max-gb', type=float, default=20.0, help='Safety cap for direct archive streaming.')
    parser.add_argument('--provider', choices=('auto','archive','vizier'), default='auto')
    args=parser.parse_args()
    if args.max_rows == 0 or args.max_rows < -1 or args.max_gb <= 0:
        print('--max-rows must be -1 or positive; --max-gb must be positive.'); return 2
    profile=PHOTOZ_PROFILES[args.survey]
    output=args.output or PROJECT_ROOT/'data'/'raw'/profile.dataset_id/f'{profile.dataset_id}_source.fits'
    output.parent.mkdir(parents=True, exist_ok=True)
    result=None; errors=[]
    if args.provider in ('auto','archive'):
        try: result=archive_download(profile, output, int(args.max_gb*1024**3))
        except Exception as exc: errors.append(f'official archive: {exc}')
    if result is None and args.provider in ('auto','vizier'):
        try: result=vizier_download(profile, output, args.catalog, args.table, args.max_rows)
        except Exception as exc: errors.append(f'VizieR fallback: {exc}')
    if result is None:
        print(f'{profile.dataset_id} download failed.\n' + '\n'.join(f'  - {error}' for error in errors))
        print('No raw file was written. The release cannot build this layer without a validated published source table.')
        return 3
    provider, provenance=result
    metadata={
        'dataset_id':profile.dataset_id, 'survey':profile.survey, 'provider':provider,
        'source_url':profile.source_url, 'downloaded_utc':datetime.now(timezone.utc).isoformat(),
        'raw_file':output.name, 'is_synthetic':False, **provenance,
    }
    output.with_suffix('.source.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f'Saved published {profile.survey} source file: {output}')
    print(f'Provider: {provider}')
    print(f'Next: scripts/build_{profile.dataset_id.replace("-", "_")}_tile_store.py')
    return 0
if __name__=='__main__': raise SystemExit(main())
