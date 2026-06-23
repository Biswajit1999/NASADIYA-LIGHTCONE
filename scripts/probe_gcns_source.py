#!/usr/bin/env python3
"""Discover a downloadable Gaia Catalogue of Nearby Stars (GCNS) table via VizieR.

This performs metadata and one-row schema checks only. It does not download a source
catalogue or write derived data. The output identifies whether a VizieR-served GCNS
candidate exposes the fields needed for a separate Milky-Way layer.
"""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))


SEARCH_TERMS = (
    "Gaia Catalogue of Nearby Stars",
    "GCNS Gaia EDR3",
    "Smart Sarro Rybizki 2021 nearby stars",
)

ID_ALIASES = {"source", "sourceid", "source_id", "id", "name"}
RA_ALIASES = {"ra", "radeg", "raj2000", "raicrs"}
DEC_ALIASES = {"dec", "dedeg", "dej2000", "deicrs"}
PARALLAX_ALIASES = {"plx", "parallax"}
PARALLAX_ERROR_ALIASES = {"e_plx", "parallaxerror", "eparallax", "plxerror"}


def normalise(name: str) -> str:
    return "".join(character.lower() for character in str(name) if character.isalnum() or character == "_")


def matches(columns: list[str], aliases: set[str]) -> str | None:
    for column in columns:
        if normalise(column) in aliases:
            return column
    return None


def candidate_ids(table_list) -> list[str]:
    try:
        return [str(key) for key in table_list.keys()]
    except AttributeError:
        return []


def main() -> int:
    try:
        from astroquery.vizier import Vizier
    except ImportError:
        print("Missing astroquery. Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 2

    finder = Vizier(columns=["*"], row_limit=1)
    catalogue_ids: list[str] = []
    print("GCNS VizieR metadata probe — no survey rows will be downloaded.\n")
    for term in SEARCH_TERMS:
        try:
            found = finder.find_catalogs(term)
            ids = candidate_ids(found)
            print(f"Search: {term!r} -> {len(ids)} catalogue record(s)")
            for identifier in ids:
                if identifier not in catalogue_ids:
                    catalogue_ids.append(identifier)
        except Exception as exc:
            print(f"Search: {term!r} -> ERROR: {exc}")

    if not catalogue_ids:
        print("\nNo VizieR metadata results were returned. This is a network/source-access result, not a data failure.")
        return 3

    passed = 0
    for catalogue_id in catalogue_ids:
        print(f"\nCATALOGUE {catalogue_id}")
        try:
            tables = finder.get_catalogs(catalogue_id)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            continue
        keys = candidate_ids(tables)
        if not keys:
            print("  No tables returned.")
            continue
        for key in keys:
            table = tables[key]
            columns = [str(column) for column in table.colnames]
            mapping = {
                "object_id": matches(columns, ID_ALIASES),
                "ra_deg": matches(columns, RA_ALIASES),
                "dec_deg": matches(columns, DEC_ALIASES),
                "parallax_mas": matches(columns, PARALLAX_ALIASES),
                "parallax_error_mas": matches(columns, PARALLAX_ERROR_ALIASES),
            }
            complete = all(mapping.values())
            status = "PASS" if complete else "REJECT"
            print(f"  {status} {key}")
            print(f"    mapping: {mapping}")
            print(f"    columns: {', '.join(columns[:40])}{' …' if len(columns) > 40 else ''}")
            if complete:
                passed += 1

    if passed:
        print("\nA GCNS candidate schema is available. Paste this output before any download is implemented.")
        return 0
    print("\nNo candidate exposed the required identifier, sky position, parallax and parallax-error fields.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
