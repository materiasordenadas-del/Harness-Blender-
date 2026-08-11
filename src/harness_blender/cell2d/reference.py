"""Build deterministic Cell2D reconstruction plans from reviewed reference analysis."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .style import symbol_contract, validate_style_contract

_SUPPORTED_REFERENCE_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
_VALID_DOMAINS = {"apical", "basal", "lateral", "membrane", "cytoplasm", "nucleus", "extracellular", "unknown"}


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_reference(path: Path, *, source_url: str | None = None, rights_status: str = "user_supplied") -> dict[str, Any]:
    """Describe an immutable image/SVG reference without interpreting its pixels."""
    if not path.is_file():
        raise ValueError(f"reference file does not exist: {path}")
    if path.suffix.lower() not in _SUPPORTED_REFERENCE_SUFFIXES:
        raise ValueError("reference must be SVG, PNG, JPG, JPEG or WEBP")
    if rights_status not in {"user_supplied", "licensed", "reference_only"}:
        raise ValueError("rights_status is unknown")
    if source_url is not None and (not isinstance(source_url, str) or not source_url.startswith(("https://", "http://"))):
        raise ValueError("source_url must be an HTTP(S) URL")
    return {
        "reference_id": f"ref_{_sha256(path)[:16]}",
        "file_name": path.name,
        "format": path.suffix.lower()[1:],
        "sha256": _sha256(path),
        "source_url": source_url,
        "rights_status": rights_status,
    }


def load_asset_catalog(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("assets"), list):
        raise ValueError("asset catalog must contain an assets list")
    assets: dict[str, dict[str, Any]] = {}
    for asset in data["assets"]:
        if not isinstance(asset, dict) or not isinstance(asset.get("asset_id"), str):
            raise ValueError("each asset requires asset_id")
        if asset["asset_id"] in assets:
            raise ValueError(f"duplicate asset_id: {asset['asset_id']}")
        assets[asset["asset_id"]] = asset
    return assets


def build_reconstruction_plan(
    reference: dict[str, Any], observations: list[dict[str, Any]], asset_catalog: dict[str, dict[str, Any]], style: dict[str, Any],
) -> dict[str, Any]:
    """Translate reviewed observations into reusable canonical instances and review items.

    Pixel interpretation is intentionally outside this deterministic function. A vision-capable
    agent or a user supplies observations; this function never assigns biological identity by guesswork.
    """
    required_reference = {"reference_id", "file_name", "format", "sha256", "source_url", "rights_status"}
    if not isinstance(reference, dict) or set(reference) != required_reference:
        raise ValueError("reference record is incomplete")
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    normalized_style = validate_style_contract(style)
    instances: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []

    for index, observation in enumerate(observations, start=1):
        if not isinstance(observation, dict):
            raise ValueError(f"observations[{index - 1}] must be an object")
        required = {"observation_id", "visual_category", "domain", "anchor", "bounds", "confidence", "asset_id"}
        if set(observation) != required:
            raise ValueError(f"observations[{index - 1}] must match the reference analysis contract")
        observation_id = observation["observation_id"]
        category = observation["visual_category"]
        domain = observation["domain"]
        anchor = observation["anchor"]
        bounds = observation["bounds"]
        confidence = _number(observation["confidence"], f"observations[{index - 1}].confidence")
        if not isinstance(observation_id, str) or not observation_id:
            raise ValueError("observation_id must be a non-empty string")
        if domain not in _VALID_DOMAINS:
            raise ValueError(f"observations[{index - 1}].domain is unknown")
        if not isinstance(anchor, str) or not anchor.strip():
            raise ValueError(f"observations[{index - 1}].anchor must be a non-empty string")
        if not isinstance(bounds, list) or len(bounds) != 4:
            raise ValueError("bounds must contain x, y, width and height")
        normalized_bounds = [_number(value, "bounds") for value in bounds]
        if normalized_bounds[2] <= 0 or normalized_bounds[3] <= 0:
            raise ValueError("bounds width and height must be positive")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        try:
            visual_style = symbol_contract(normalized_style, category)
        except ValueError:
            review_items.append({"observation_id": observation_id, "reason": "unknown_visual_category", "proposed_value": category})
            continue
        asset_id = observation["asset_id"]
        if asset_id is not None and asset_id not in asset_catalog:
            review_items.append({"observation_id": observation_id, "reason": "unknown_asset_id", "proposed_value": asset_id})
            continue
        if confidence < 0.8:
            review_items.append({"observation_id": observation_id, "reason": "low_confidence", "proposed_value": confidence})
            continue
        instances.append({
            "instance_id": f"{asset_id or category}_{index:03d}",
            "source_observation_id": observation_id,
            "asset_id": asset_id,
            "visual_category": category,
            "domain": domain,
            "anchor": anchor,
            "bounds": normalized_bounds,
            "style": visual_style,
        })

    return {
        "reference": reference,
        "target_style_id": normalized_style["style_id"],
        "instances": instances,
        "review_items": review_items,
        "status": "needs_review" if review_items else "ready_for_blender",
    }
