# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only V4 deterministic scene evaluation operations."""

from __future__ import annotations

from typing import Any

import bmesh
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


def evaluate_mesh(params: dict[str, Any]) -> dict[str, Any]:
    obj = bpy.data.objects.get(params["object_name"])
    if obj is None or obj.type != "MESH":
        raise TypeError("evaluate_mesh requires an existing MESH object")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.normal_update()
        boundary = sum(edge.is_boundary for edge in bm.edges)
        loose_edges = sum(not edge.link_faces for edge in bm.edges)
        non_manifold = sum(not edge.is_manifold and not edge.is_boundary for edge in bm.edges)
        degenerate = sum(face.calc_area() <= 1e-12 for face in bm.faces)
        closed = boundary == 0 and loose_edges == 0 and non_manifold == 0
        coords = [obj.matrix_world @ vertex.co for vertex in bm.verts]
        minimum = [min(point[axis] for point in coords) for axis in range(3)] if coords else [0.0, 0.0, 0.0]
        maximum = [max(point[axis] for point in coords) for axis in range(3)] if coords else [0.0, 0.0, 0.0]
        area = sum(face.calc_area() for face in bm.faces)
        volume = abs(bm.calc_volume(signed=True)) if closed else None
        return {
            "name": obj.name, "vertices": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
            "boundary_edges": boundary, "non_manifold_edges": non_manifold, "loose_edges": loose_edges,
            "degenerate_faces": degenerate, "is_closed_manifold": closed,
            "surface_area": float(area), "volume": float(volume) if volume is not None else None,
            "bounding_box": {"min": [float(value) for value in minimum], "max": [float(value) for value in maximum]},
        }
    finally:
        bm.free()
