# SPDX-License-Identifier: GPL-3.0-or-later
"""Typed V2 mesh inspection using Blender's BMesh API."""

from __future__ import annotations

from typing import Any

import bmesh
import bpy


def inspect_mesh_detailed(params: dict[str, Any]) -> dict[str, Any]:
    obj = bpy.data.objects.get(params["object_name"])
    if obj is None:
        raise ValueError(f"Object not found: {params['object_name']}")
    if obj.type != "MESH":
        raise TypeError(f"Object {obj.name} is {obj.type}, not MESH")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        boundary = sum(edge.is_boundary for edge in bm.edges)
        loose = sum(not edge.link_faces for edge in bm.edges)
        non_manifold = sum(not edge.is_manifold and not edge.is_boundary for edge in bm.edges)
        return {"name": obj.name, "vertices": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
                "triangles": sum(len(face.verts) == 3 for face in bm.faces),
                "quads": sum(len(face.verts) == 4 for face in bm.faces),
                "ngons": sum(len(face.verts) > 4 for face in bm.faces),
                "boundary_edges": boundary, "loose_edges": loose, "non_manifold_edges": non_manifold,
                "is_closed_manifold": boundary == 0 and loose == 0 and non_manifold == 0,
                "materials": [slot.material.name if slot.material else None for slot in obj.material_slots]}
    finally:
        bm.free()


def recalculate_normals(params: dict[str, Any]) -> dict[str, Any]:
    obj = bpy.data.objects.get(params["object_name"])
    if obj is None or obj.type != "MESH":
        raise TypeError("recalculate_normals requires an existing MESH object")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if not params["outward"]:
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    return {"name": obj.name, "orientation": "outside" if params["outward"] else "inside"}
