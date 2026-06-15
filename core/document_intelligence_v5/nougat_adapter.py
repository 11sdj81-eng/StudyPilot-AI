"""Nougat optional adapter placeholder."""

from __future__ import annotations

import importlib.util


def available() -> bool:
    return importlib.util.find_spec("nougat") is not None
