#!/usr/bin/env python3
"""Strict metadata-only search for a genuine Gaia Catalogue of Nearby Stars source.

Generic Gaia EDR3/DR3 tables are intentionally not treated as GCNS. This command
writes no files and downloads no catalogue rows.
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


def normalise(value: str) -> str:
    return "".join(character.lower() for character in str(value) if character.isalnum())


def keys(table_list) -> list[str]:
    try:
        return [str(key) for key in table_list.keys()]
    except AttributeError:
        return []


def is_gcns_catalogue(identifier: str, descriptor) -> bool:
    text = " ".join(
        (
            identifier,
            str(getattr(descriptor, "description", "")),
            str(getattr(descriptor, "meta", {})),
        )
    ).lower()
    return (
        "gcns" in text
        or "catalogue of nearby stars" in text
        or "catalog of nearby stars" in text
    )


def match_column(columns: list[str], aliases: tuple[str, ...]) -> str | None:
    wanted = {normalise(alias) for alias in aliases}
    return next((column for column in columns if normalise(column) in wanted), None)


def main() -> int:
    try:
        from astroquery.vizier import Vizier
    except ImportError:
        print(
            "Missing astroquery. Run: "
            ".\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        )
        return 2

    finder = Vizier(columns=["*"], row_limit=1)
    candidates: dict[str, object] = {}
    print("Strict GCNS VizieR metadata probe — no data rows will be downloaded.\n")
    for term in SEARCH_TERMS:
        try:
            found = finder.find_catalogs(term)
            ids = keys(found)
            print(f"Search: {term!r} -> {len(ids)} catalogue record(s)")
            for identifier in ids:
                descriptor = found[identifier]
                if is_gcns_catalogue(identifier, descriptor):
                    candidates[identifier] = descriptor
        except Exception as exc:
            print(f"Search: {term!r} -> ERROR: {exc}")

    if not candidates:
        print("\nNo catalogue record identified itself as GCNS or Gaia Catalogue of Nearby Stars.")
        print(
            "Generic Gaia tables are intentionally rejected; they do not establish "
            "the GCNS 100-pc selection."
        )
        return 3

    required = {
        "object_id": ("Source", "source_id", "id"),
        "ra_deg": ("RA_ICRS", "RAJ2000", "ra"),
        "dec_deg": ("DE_ICRS", "DEJ2000", "dec"),
        "parallax_mas": ("Plx", "parallax"),
        "parallax_error_mas": ("e_Plx", "parallax_error"),
    }
    passed = 0
    for identifier in candidates:
        print(f"\nCATALOGUE {identifier} · GCNS CANDIDATE")
        try:
            tables = finder.get_catalogs(identifier)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            continue
        for key in keys(tables):
            columns = [str(column) for column in tables[key].colnames]
            mapping = {
                name: match_column(columns, aliases)
                for name, aliases in required.items()
            }
            valid = all(mapping.values())
            print(f"  {'PASS' if valid else 'REJECT'} {key}")
            print(f"    mapping: {mapping}")
            if valid:
                passed += 1

    if passed:
        print(
            "\nA verified GCNS-shaped schema is available. "
            "Paste this output before a downloader is added."
        )
        return 0
    print("\nNo self-identified GCNS candidate passed the required schema check.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
