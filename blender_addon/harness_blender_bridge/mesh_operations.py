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


def flip_normals(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("flip mesh normals", lambda: _restore_topology(obj.data, snapshot))
    return {"name": obj.name, "faces": len(obj.data.polygons), "orientation": "flipped"}


def subdivide_mesh(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=params["cuts"], use_grid_fill=True)
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("subdivide mesh", lambda: _restore_topology(obj.data, snapshot))
    return {"name": obj.name, "vertices": len(obj.data.vertices), "faces": len(obj.data.polygons), "cuts": params["cuts"]}


def smooth_mesh(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.smooth_vert(bm, verts=list(bm.verts), factor=params["factor"], use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("smooth mesh", lambda: _restore_topology(obj.data, snapshot))
    return {"name": obj.name, "vertices": len(obj.data.vertices), "factor": params["factor"]}


def _material(name: str) -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if material is None:
        raise ValueError(f"Material not found: {name}")
    material.use_nodes = True
    return material


def _principled(material: bpy.types.Material):
    node = material.node_tree.nodes.get("Principled BSDF") if material.node_tree else None
    if node is None:
        raise RuntimeError("Material has no Principled BSDF node")
    return node


def create_material(params: dict[str, Any]) -> dict[str, Any]:
    name = params["name"]
    if bpy.data.materials.get(name) is not None:
        raise ValueError(f"Material already exists: {name}")
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    _record_undo("create material", lambda: bpy.data.materials.remove(material) if material.users == 0 else None)
    return {"name": material.name}


def assign_material(params: dict[str, Any]) -> dict[str, Any]:
    obj, material = _mesh_object(params["object_name"]), _material(params["material_name"])
    obj.data.materials.append(material)
    index = len(obj.data.materials) - 1
    _record_undo("assign material", lambda: obj.data.materials.pop(index=index))
    return {"object_name": obj.name, "material_name": material.name, "slot": index}


def set_material_value(params: dict[str, Any], input_name: str, response_name: str) -> dict[str, Any]:
    socket = _principled(_material(params["material_name"])).inputs[input_name]
    previous = socket.default_value[:]
    socket.default_value = params[response_name]
    _record_undo("set material value", lambda: setattr(socket, "default_value", previous))
    return {"material_name": params["material_name"], response_name: list(socket.default_value)}


def set_material_scalar(params: dict[str, Any], input_name: str, response_name: str) -> dict[str, Any]:
    socket = _principled(_material(params["material_name"])).inputs[input_name]
    previous = socket.default_value
    socket.default_value = params[response_name]
    _record_undo("set material value", lambda: setattr(socket, "default_value", previous))
    return {"material_name": params["material_name"], response_name: float(socket.default_value)}


def add_modifier(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    name, modifier_type = params["name"], params["modifier_type"]
    if obj.modifiers.get(name) is not None:
        raise ValueError(f"Modifier already exists: {name}")
    modifier = obj.modifiers.new(name, modifier_type)
    _record_undo("add modifier", lambda: obj.modifiers.remove(modifier) if modifier.name in obj.modifiers else None)
    return {"object_name": obj.name, "name": modifier.name, "modifier_type": modifier.type}


def set_modifier_parameter(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    modifier = obj.modifiers.get(params["modifier_name"])
    if modifier is None:
        raise ValueError(f"Modifier not found: {params['modifier_name']}")
    field, value = params["parameter"], params["value"]
    previous = getattr(modifier, field)
    setattr(modifier, field, value)
    _record_undo("set modifier parameter", lambda: setattr(modifier, field, previous))
    return {"object_name": obj.name, "modifier_name": modifier.name, "parameter": field, "value": getattr(modifier, field)}


def remove_modifier(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    modifier = obj.modifiers.get(params["modifier_name"])
    if modifier is None:
        raise ValueError(f"Modifier not found: {params['modifier_name']}")
    fields = {"SUBSURF": ("levels",), "SOLIDIFY": ("thickness",), "DECIMATE": ("ratio",)}.get(modifier.type, ())
    state = {field: getattr(modifier, field) for field in fields}
    name, modifier_type = modifier.name, modifier.type
    obj.modifiers.remove(modifier)

    def restore() -> None:
        restored = obj.modifiers.new(name, modifier_type)
        for field, value in state.items():
            setattr(restored, field, value)

    _record_undo("remove modifier", restore)
    return {"object_name": obj.name, "removed": name, "modifier_type": modifier_type}
