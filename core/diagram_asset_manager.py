"""Diagram asset selection for StudyPilot v3.1."""

from __future__ import annotations

import json
from pathlib import Path

from core.teaching_asset import TeachingAsset
from core.teaching_asset_manager import TeachingAssetManager


class DiagramAssetManager:
    def __init__(self, teaching_assets: TeachingAssetManager) -> None:
        self.teaching_assets = teaching_assets
        self.usage_log: list[dict] = []

    def select_diagram(
        self,
        concept_id: str,
        pdf_type: str,
        question_type: str = "",
        usage_context: str = "",
        avoid_used: bool = True,
    ) -> TeachingAsset | None:
        candidates = self.teaching_assets.candidates(concept_id, pdf_type, usage_context)
        if avoid_used:
            candidates = [asset for asset in candidates if asset.usage_count < asset.max_usage_per_run]
        if not candidates:
            candidates = self.teaching_assets.candidates(concept_id, pdf_type, "")
            if avoid_used:
                candidates = [asset for asset in candidates if asset.usage_count < asset.max_usage_per_run]
        if not candidates:
            return None
        asset = candidates[0]
        asset.usage_count += 1
        self.usage_log.append(
            {
                "asset_id": asset.id,
                "concept_id": concept_id,
                "pdf_type": pdf_type,
                "question_type": question_type,
                "usage_context": usage_context,
                "source": asset.source,
                "path": asset.path,
            }
        )
        return asset

    def export_usage_report(self, output_path: str | Path) -> Path:
        counts: dict[str, int] = {}
        for item in self.usage_log:
            counts[item["asset_id"]] = counts.get(item["asset_id"], 0) + 1
        duplicated = sorted([asset_id for asset_id, count in counts.items() if count > 1])
        data = {
            "usage_log": self.usage_log,
            "usage_count_by_asset": counts,
            "duplicated_diagram_asset_ids": duplicated,
            "image_reuse_count": sum(max(0, count - 1) for count in counts.values()),
        }
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
