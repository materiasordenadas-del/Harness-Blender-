# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only V4 deterministic scene evaluation operations."""

from __future__ import annotations

from typing import Any

import bpy


def inspect_scene_detailed(_params: dict[str, Any]) -> dict[str, Any]:
    objects: list[dict[str, Any]] = []
    for obj in bpy.context.scene.objects:
        item: dict[str, Any] = {
            "name": obj.name, "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "collections": [collection.name for collection in obj.users_collection],
            "location": [float(value) for value in obj.location],
            "dimensions": [float(value) for value in obj.dimensions],
            "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
            "modifiers": [{"name": modifier.name, "type": modifier.type} for modifier in obj.modifiers],
        }
        if obj.type == "MESH":
            item["mesh"] = {"vertices": len(obj.data.vertices), "edges": len(obj.data.edges), "faces": len(obj.data.polygons)}
        if obj.type == "CURVE":
            item["curve"] = {"splines": len(obj.data.splines), "bevel_depth": float(obj.data.bevel_depth)}
        objects.append(item)
    return {"scene": bpy.context.scene.name, "object_count": len(objects), "objects": objects}
