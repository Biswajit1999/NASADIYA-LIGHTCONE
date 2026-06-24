"""Command driver for DESI browser-sample evaluation."""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()
