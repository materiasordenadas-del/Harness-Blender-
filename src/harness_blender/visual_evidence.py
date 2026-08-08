"""Bounded metadata for reference-versus-result visual comparison."""

from __future__ import annotations

from typing import Any

from .visual_review import validate_visual_review

_VIEWS = ("front", "right", "perspective")


def _text(value: Any, field: str, maximum: int = 255) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field} must contain 1-{maximum} characters")
    return value.strip()


def validate_visual_comparison(packet: Any) -> dict[str, Any]:
    """Validate comparison metadata; image judgment stays with the calling model."""
    if not isinstance(packet, dict):
        raise ValueError("visual comparison must be a JSON object")
    expected = {"reference_id", "target_object", "views", "regions", "review"}
    if set(packet) != expected:
        raise ValueError("visual comparison must contain only the complete evidence schema")
    views = packet["views"]
    if not isinstance(views, list) or tuple(views) != _VIEWS:
        raise ValueError("views must be exactly front, right, perspective in that order")
    regions = packet["regions"]
    if not isinstance(regions, list) or not 1 <= len(regions) <= 12:
        raise ValueError("regions must contain 1-12 comparisons")
    normalized_regions = []
    for region in regions:
        if not isinstance(region, dict) or set(region) != {"reference_region", "result_region", "assessment"}:
            raise ValueError("each region must contain reference_region, result_region and assessment")
        normalized_regions.append({
            "reference_region": _text(region["reference_region"], "reference_region"),
            "result_region": _text(region["result_region"], "result_region"),
            "assessment": _text(region["assessment"], "assessment", 500),
        })
    return {
        "reference_id": _text(packet["reference_id"], "reference_id", 80),
        "target_object": _text(packet["target_object"], "target_object", 255),
        "views": list(_VIEWS),
        "regions": normalized_regions,
        "review": validate_visual_review(packet["review"]),
    }
