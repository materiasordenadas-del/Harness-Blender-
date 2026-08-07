"""Pure report comparison helpers for the read-only V4 evaluator."""

from __future__ import annotations

from typing import Any


def _percent(before: float | int | None, after: float | int | None) -> float | None:
    if before is None or after is None or before == 0:
        return None
    return round((float(after) - float(before)) / abs(float(before)) * 100, 6)


def diff_reports(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("before and after must be JSON objects")
    result: dict[str, Any] = {}
    for key in ("vertices", "edges", "faces", "boundary_edges", "non_manifold_edges", "loose_edges", "degenerate_faces"):
        if key in before and key in after:
            result[f"{key}_delta"] = after[key] - before[key]
    for key in ("surface_area", "volume"):
        if key in before and key in after:
            result[f"{key}_delta_percent"] = _percent(before[key], after[key])
    if "radius" in before and "radius" in after:
        result["radius_delta_percent"] = _percent(before["radius"], after["radius"])
    return result
