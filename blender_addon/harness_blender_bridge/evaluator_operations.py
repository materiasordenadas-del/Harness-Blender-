# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only V4 deterministic scene evaluation operations."""

from __future__ import annotations

from typing import Any

import bmesh
import bpy
from mathutils import Vector


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


def _world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(corner[axis] for corner in corners) for axis in range(3))),
        Vector((max(corner[axis] for corner in corners) for axis in range(3))),
    )


def evaluate_spatial(params: dict[str, Any]) -> dict[str, Any]:
    first = bpy.data.objects.get(params["object_name"])
    second = bpy.data.objects.get(params["target_object_name"])
    if first is None or second is None:
        raise ValueError("Both objects must exist")
    first_min, first_max = _world_bounds(first)
    second_min, second_max = _world_bounds(second)
    nearest_first_values = []
    nearest_second_values = []
    for axis in range(3):
        if first_max[axis] < second_min[axis]:
            nearest_first_values.append(first_max[axis])
            nearest_second_values.append(second_min[axis])
        elif second_max[axis] < first_min[axis]:
            nearest_first_values.append(first_min[axis])
            nearest_second_values.append(second_max[axis])
        else:
            shared = max(first_min[axis], second_min[axis])
            nearest_first_values.append(shared)
            nearest_second_values.append(shared)
    nearest_first = Vector(nearest_first_values)
    nearest_second = Vector(nearest_second_values)
    overlaps = all(first_min[axis] <= second_max[axis] and second_min[axis] <= first_max[axis] for axis in range(3))
    return {
        "object_name": first.name, "target_object_name": second.name,
        "bounding_box_overlap": overlaps,
        "distance": float((nearest_second - nearest_first).length),
        "nearest_points": {"object": [float(value) for value in nearest_first], "target": [float(value) for value in nearest_second]},
    }
