"""Small, resumable HTTP-download helpers for public survey products."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
from typing import Callable

import requests

CHUNK_BYTES = 1024 * 1024
USER_AGENT = "NasadiyaLightcone/0.7 (public-survey-ingestion)"


@dataclass(frozen=True)
class DownloadResult:
    url: str
    path: Path
    bytes_written: int
    sha256: str
    resumed: bool


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def download_file(
    url: str,
    destination: str | Path,
    *,
    timeout_seconds: int = 90,
    overwrite: bool = False,
    max_bytes: int | None = None,
    progress: Callable[[int, int | None], None] | None = None,
) -> DownloadResult:
    """Download one public file with a safe ``.part`` resume path.

    The helper never silently appends a full HTTP response to an existing partial
    file. If the host ignores a Range request, the partial file is restarted.
    """

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")

    if destination.exists() and not overwrite:
        return DownloadResult(
            url=url,
            path=destination,
            bytes_written=destination.stat().st_size,
            sha256=sha256_file(destination),
            resumed=False,
        )

    start_at = partial.stat().st_size if partial.exists() and not overwrite else 0
    headers = {"User-Agent": USER_AGENT}
    if start_at:
        headers["Range"] = f"bytes={start_at}-"

    with requests.get(url, headers=headers, stream=True, timeout=timeout_seconds) as response:
        response.raise_for_status()
        supports_resume = response.status_code == 206
        if start_at and not supports_resume:
            partial.unlink(missing_ok=True)
            start_at = 0

        expected = response.headers.get("Content-Length")
        total = (int(expected) + start_at) if expected and expected.isdigit() else None
        if max_bytes is not None and total is not None and total > max_bytes:
            raise RuntimeError(
                f"Refusing download of {total / 1e9:.2f} GB; allowed maximum is {max_bytes / 1e9:.2f} GB."
            )

        mode = "ab" if start_at and supports_resume else "wb"
        transferred = start_at
        with partial.open(mode) as handle:
            for block in response.iter_content(chunk_size=CHUNK_BYTES):
                if not block:
                    continue
                transferred += len(block)
                if max_bytes is not None and transferred > max_bytes:
                    raise RuntimeError(
                        f"Download exceeded the permitted maximum of {max_bytes / 1e9:.2f} GB."
                    )
                handle.write(block)
                if progress:
                    progress(transferred, total)

    os.replace(partial, destination)
    return DownloadResult(
        url=url,
        path=destination,
        bytes_written=destination.stat().st_size,
        sha256=sha256_file(destination),
        resumed=bool(start_at),
    )
