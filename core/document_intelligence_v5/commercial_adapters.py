"""Reserved commercial parser adapter interfaces for v5.

Mathpix and LlamaParse are intentionally not integrated in this repository.
They remain external/optional because they may require paid services, API keys,
and separate license review.
"""

from __future__ import annotations


class MathpixAdapterV5:
    name = "mathpix"

    def available(self) -> bool:
        return False

    def missing_dependency(self) -> str:
        return "Mathpix is a reserved commercial adapter; no API key or SDK is configured."


class LlamaParseAdapterV5:
    name = "llamaparse"

    def available(self) -> bool:
        return False

    def missing_dependency(self) -> str:
        return "LlamaParse is a reserved commercial adapter; no API key or SDK is configured."
