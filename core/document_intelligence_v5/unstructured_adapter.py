"""Unstructured / MarkItDown optional adapter placeholder."""

from __future__ import annotations

import importlib.util


def unstructured_available() -> bool:
    return importlib.util.find_spec("unstructured") is not None


def markitdown_available() -> bool:
    return importlib.util.find_spec("markitdown") is not None
