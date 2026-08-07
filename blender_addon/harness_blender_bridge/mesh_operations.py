# SPDX-License-Identifier: GPL-3.0-or-later
"""Typed V2 mesh inspection using Blender's BMesh API."""

from __future__ import annotations

from typing import Any

import bmesh
import bpy

from .operations import _record_undo


def _mesh_object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        raise TypeError("Operation requires an existing MESH object")
    return obj


def _topology_snapshot(mesh: bpy.types.Mesh) -> dict[str, Any]:
    return {
        "vertices": [tuple(vertex.co) for vertex in mesh.vertices],
        "faces": [tuple(polygon.vertices) for polygon in mesh.polygons],
        "materials": [polygon.material_index for polygon in mesh.polygons],
        "smooth": [polygon.use_smooth for polygon in mesh.polygons],
    }


def _restore_topology(mesh: bpy.types.Mesh, snapshot: dict[str, Any]) -> None:
    mesh.clear_geometry()
    mesh.from_pydata(snapshot["vertices"], [], snapshot["faces"])
    for polygon, material, smooth in zip(mesh.polygons, snapshot["materials"], snapshot["smooth"]):
        polygon.material_index, polygon.use_smooth = material, smooth
    mesh.update()


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
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
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
    _record_undo("recalculate mesh normals", lambda: _restore_topology(obj.data, snapshot))
    return {"name": obj.name, "orientation": "outside" if params["outward"] else "inside"}
