"""Convert reviewed Cell2D reconstruction plans into typed Blender scene packets."""
from __future__ import annotations

from typing import Any


def build_scene_packet(plan: dict[str, Any]) -> dict[str, Any]:
    """Return only explicit, validated operations for a review-ready reconstruction plan.

    The Blender bridge will later implement ``create_cell2d_symbol``. Keeping this packet
    separate makes the mapping reviewable and prevents free-form code from crossing the bridge.
    """
    if not isinstance(plan, dict):
        raise ValueError("reconstruction plan must be an object")
    required = {"reference", "target_style_id", "instances", "review_items", "status"}
    if set(plan) != required:
        raise ValueError("reconstruction plan has an unexpected shape")
    if plan["status"] != "ready_for_blender" or plan["review_items"]:
        raise ValueError("reconstruction plan must be reviewed before building a Blender packet")
    reference = plan["reference"]
    if not isinstance(reference, dict) or not isinstance(reference.get("reference_id"), str):
        raise ValueError("reconstruction plan reference is invalid")
    if not isinstance(plan["target_style_id"], str) or not plan["target_style_id"]:
        raise ValueError("target_style_id must be a non-empty string")
    if not isinstance(plan["instances"], list):
        raise ValueError("instances must be a list")

    operations: list[dict[str, Any]] = []
    names: set[str] = set()
    for instance in plan["instances"]:
        if not isinstance(instance, dict):
            raise ValueError("each instance must be an object")
        required_instance = {"instance_id", "source_observation_id", "asset_id", "visual_category", "domain", "anchor", "bounds", "style"}
        if set(instance) != required_instance:
            raise ValueError("instance has an unexpected shape")
        object_name = f"Cell2D_{instance['instance_id']}"
        if object_name in names:
            raise ValueError(f"duplicate object name: {object_name}")
        names.add(object_name)
        style = instance["style"]
        if not isinstance(style, dict) or set(style) != {"layer", "material", "shape_family", "z", "color"}:
            raise ValueError("instance style is invalid")
        operations.append({
            "operation": "create_cell2d_symbol",
            "params": {
                "object_name": object_name,
                "asset_id": instance["asset_id"],
                "visual_category": instance["visual_category"],
                "domain": instance["domain"],
                "anchor": instance["anchor"],
                "bounds": instance["bounds"],
                "shape_family": style["shape_family"],
                "material": style["material"],
                "color": style["color"],
                "z": style["z"],
                "reference_id": reference["reference_id"],
                "source_observation_id": instance["source_observation_id"],
            },
        })

    return {
        "packet_type": "harness-cell2d-scene",
        "version": "0.1.0",
        "target_style_id": plan["target_style_id"],
        "reference_id": reference["reference_id"],
        "operations": operations,
    }
