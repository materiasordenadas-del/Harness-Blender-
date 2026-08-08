# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only V4 deterministic scene evaluation operations."""

from __future__ import annotations

from typing import Any

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


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
        bvh = BVHTree.FromBMesh(bm)
        self_pairs = 0
        for first, second in bvh.overlap(bvh):
            if first >= second:
                continue
            first_face, second_face = bm.faces[first], bm.faces[second]
            if not set(first_face.verts).isdisjoint(second_face.verts):
                continue
            self_pairs += 1
        inconsistent_normals = sum(edge.is_manifold and not edge.is_contiguous for edge in bm.edges)
        closed = boundary == 0 and loose_edges == 0 and non_manifold == 0
        coords = [obj.matrix_world @ vertex.co for vertex in bm.verts]
        minimum = [min(point[axis] for point in coords) for axis in range(3)] if coords else [0.0, 0.0, 0.0]
        maximum = [max(point[axis] for point in coords) for axis in range(3)] if coords else [0.0, 0.0, 0.0]
        area = sum(face.calc_area() for face in bm.faces)
        volume = abs(bm.calc_volume(signed=True)) if closed else None
        return {
            "name": obj.name, "vertices": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
            "boundary_edges": boundary, "non_manifold_edges": non_manifold, "loose_edges": loose_edges,
            "degenerate_faces": degenerate, "self_intersections": self_pairs,
            "inconsistent_normal_edges": inconsistent_normals, "is_closed_manifold": closed,
            "surface_area": float(area), "volume": float(volume) if volume is not None else None,
            "bounding_box": {"min": [float(value) for value in minimum], "max": [float(value) for value in maximum]},
        }
    finally:
        bm.free()


def evaluate_asset_readiness(params: dict[str, Any]) -> dict[str, Any]:
    """Assess production prerequisites without editing the named mesh."""
    obj = bpy.data.objects.get(params["object_name"])
    if obj is None or obj.type != "MESH":
        raise TypeError("evaluate_asset_readiness requires an existing MESH object")

    mesh = evaluate_mesh(params)
    blockers: list[str] = []
    review_items: list[str] = []
    for field in ("non_manifold_edges", "loose_edges", "degenerate_faces", "self_intersections", "inconsistent_normal_edges"):
        if mesh[field]:
            blockers.append(field)
    if mesh["boundary_edges"]:
        review_items.append("boundary_edges")
    if not obj.users_collection:
        review_items.append("collections")
    if not any(slot.material for slot in obj.material_slots):
        review_items.append("materials")
    else:
        materials = [slot.material for slot in obj.material_slots if slot.material]
        if any(not material.use_nodes or not material.node_tree or material.node_tree.nodes.get("Principled BSDF") is None for material in materials):
            review_items.append("principled_material")
    if not obj.data.uv_layers:
        review_items.append("uv_layers")
    if any(abs(value - 1.0) > 1e-6 for value in obj.scale):
        review_items.append("unapplied_scale")
    if any(abs(value) > 1e-6 for value in obj.rotation_euler):
        review_items.append("unapplied_rotation")

    status = "blocked" if blockers else "needs_review" if review_items else "ready"
    return {
        "object_name": obj.name,
        "status": status,
        "blockers": blockers,
        "needs_review": review_items,
        "mesh": mesh,
        "transform": {
            "location": [float(value) for value in obj.location],
            "rotation_euler": [float(value) for value in obj.rotation_euler],
            "scale": [float(value) for value in obj.scale],
        },
        "collections": [collection.name for collection in obj.users_collection],
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
    }


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


def evaluate_tubular(params: dict[str, Any]) -> dict[str, Any]:
    obj = bpy.data.objects.get(params["object_name"])
    if obj is None or obj.type != "CURVE":
        raise TypeError("evaluate_tubular requires an existing CURVE object")
    spline = obj.data.splines[params["spline_index"]]
    points = spline.bezier_points if spline.type == "BEZIER" else spline.points
    if len(points) < 2:
        raise ValueError("Tubular evaluation requires at least two points")
    centers = [Vector(point.co[:3]) for point in points]
    radii = [float(point.radius) * float(obj.data.bevel_depth) for point in points]
    diameters = [radius * 2 for radius in radii]
    jumps = [abs(radii[index + 1] - radii[index]) for index in range(len(radii) - 1)]
    curvature: list[float] = []
    for index in range(1, len(centers) - 1):
        left = centers[index] - centers[index - 1]
        right = centers[index + 1] - centers[index]
        curvature.append(float(left.angle(right)) if left.length > 1e-12 and right.length > 1e-12 else 0.0)
    return {
        "name": obj.name, "spline_index": params["spline_index"], "point_count": len(points),
        "radii": radii, "diameters": diameters, "minimum_thickness": min(diameters), "maximum_thickness": max(diameters),
        "radius_jumps": jumps, "max_radius_jump": max(jumps) if jumps else 0.0,
        "centerline": [[float(value) for value in center] for center in centers],
        "curvature_radians": curvature, "max_curvature_radians": max(curvature) if curvature else 0.0,
    }


def evaluate_penetration(params: dict[str, Any]) -> dict[str, Any]:
    first = bpy.data.objects.get(params["object_name"])
    second = bpy.data.objects.get(params["target_object_name"])
    if first is None or second is None or first.type != "MESH" or second.type != "MESH":
        raise TypeError("evaluate_penetration requires two MESH objects")

    def tree(obj: bpy.types.Object) -> BVHTree:
        vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        triangles = []
        for polygon in obj.data.polygons:
            indices = tuple(polygon.vertices)
            triangles.extend((indices[0], indices[index], indices[index + 1]) for index in range(1, len(indices) - 1))
        return BVHTree.FromPolygons(vertices, triangles, all_triangles=True)

    pairs = tree(first).overlap(tree(second))
    return {"object_name": first.name, "target_object_name": second.name, "intersecting_face_pairs": len(pairs), "penetrates": bool(pairs)}
