"""Teaching asset pool management for StudyPilot v3.1."""

from __future__ import annotations

import json
from pathlib import Path

from core.teaching_asset import TeachingAsset


ASSET_ROOT = Path("data/teaching_assets/engineering/electromagnetic_static_chapter1")


class TeachingAssetManager:
    def __init__(self, assets: list[TeachingAsset] | None = None) -> None:
        self.assets = assets or []

    def add(self, asset: TeachingAsset) -> None:
        self.assets.append(asset)

    def reset_usage(self) -> None:
        for asset in self.assets:
            asset.usage_count = 0

    def export_manifest(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [asset.to_dict() for asset in self.assets]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def by_id(self, asset_id: str) -> TeachingAsset | None:
        for asset in self.assets:
            if asset.id == asset_id:
                return asset
        return None

    def candidates(self, concept_id: str, pdf_type: str, usage_context: str = "") -> list[TeachingAsset]:
        items = [
            asset
            for asset in self.assets
            if asset.concept_id == concept_id
            and pdf_type in asset.pdf_types
            and (not usage_context or asset.usage_context == usage_context)
        ]
        return sorted(items, key=_asset_priority)


def _asset_priority(asset: TeachingAsset) -> tuple[int, int, str]:
    source_rank = {
        "textbook": 0,
        "past_paper": 1,
        "ppt": 2,
        "programmatic": 3,
        "redraw": 4,
        "generated": 5,
    }.get(asset.source, 9)
    return (source_rank, asset.usage_count, asset.id)


def ensure_asset_dirs(root: str | Path = ASSET_ROOT) -> None:
    base = Path(root)
    for name in ["textbook", "past_paper", "ppt", "programmatic", "redraw"]:
        (base / name).mkdir(parents=True, exist_ok=True)
