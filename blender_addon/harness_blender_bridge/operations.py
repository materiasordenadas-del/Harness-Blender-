# SPDX-License-Identifier: GPL-3.0-or-later
"""Closed Blender-side implementation of Harness Blender V0 operations."""

from __future__ import annotations

import base64
import math
import tempfile
from pathlib import Path
from typing import Any, Callable

import bmesh
import bpy


def _object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")
    return obj


def _op_ping(_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ready",
        "blender_version": bpy.app.version_string,
        "file": bpy.data.filepath or None,
        "mode": bpy.context.mode,
        "background": bool(bpy.app.background),
    }


def _op_inspect_scene(_params: dict[str, Any]) -> dict[str, Any]:
    scene = bpy.context.scene
    objects: list[dict[str, Any]] = []
    for obj in scene.objects:
        item: dict[str, Any] = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(float(v), 6) for v in obj.location],
            "rotation_euler": [round(float(v), 6) for v in obj.rotation_euler],
            "scale": [round(float(v), 6) for v in obj.scale],
            "dimensions": [round(float(v), 6) for v in obj.dimensions],
            "visible": bool(obj.visible_get()),
        }
        if obj.type == "MESH":
            item["mesh"] = {
                "vertices": len(obj.data.vertices),
                "edges": len(obj.data.edges),
                "polygons": len(obj.data.polygons),
            }
        objects.append(item)
    active = bpy.context.view_layer.objects.active
    return {
        "scene": scene.name,
        "file": bpy.data.filepath or None,
        "active_object": active.name if active else None,
        "selected_objects": [obj.name for obj in bpy.context.selected_objects],
        "object_count": len(objects),
        "objects": objects,
    }


def _op_inspect_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = _object(params["object_name"])
    info: dict[str, Any] = {
        "name": obj.name,
        "type": obj.type,
        "location": [round(float(v), 6) for v in obj.location],
        "rotation_euler": [round(float(v), 6) for v in obj.rotation_euler],
        "rotation_mode": obj.rotation_mode,
        "scale": [round(float(v), 6) for v in obj.scale],
        "dimensions": [round(float(v), 6) for v in obj.dimensions],
        "parent": obj.parent.name if obj.parent else None,
        "modifiers": [{"name": modifier.name, "type": modifier.type} for modifier in obj.modifiers],
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
    }
    if obj.type == "MESH":
        mesh = obj.data
        info["mesh"] = {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "uv_layers": [layer.name for layer in mesh.uv_layers],
            "shape_keys": list(mesh.shape_keys.key_blocks.keys()) if mesh.shape_keys else [],
        }
    return info


def _op_create_primitive(params: dict[str, Any]) -> dict[str, Any]:
    name = params["name"]
    if bpy.data.objects.get(name) is not None:
        raise ValueError(f"An object named {name!r} already exists")

    primitive = params["primitive"]
    location = tuple(params["location"])
    if primitive == "cube":
        status = bpy.ops.mesh.primitive_cube_add(location=location)
    elif primitive == "uv_sphere":
        status = bpy.ops.mesh.primitive_uv_sphere_add(location=location)
    elif primitive == "cylinder":
        status = bpy.ops.mesh.primitive_cylinder_add(location=location)
    elif primitive == "cone":
        status = bpy.ops.mesh.primitive_cone_add(location=location)
    elif primitive == "torus":
        status = bpy.ops.mesh.primitive_torus_add(location=location)
    else:  # bridge_protocol should make this unreachable
        raise ValueError(f"Unsupported primitive: {primitive}")
    if "FINISHED" not in status:
        raise RuntimeError(f"Blender primitive operator returned {sorted(status)}")

    obj = bpy.context.active_object
    if obj is None:
        raise RuntimeError("Blender did not create an active object")
    obj.name = name
    obj.scale = tuple(params["scale"])
    bpy.context.view_layer.update()
    return {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
    }


def _op_transform_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = _object(params["object_name"])
    # Direct RNA assignments are not operators, so explicitly snapshot an undo
    # state before applying them. This keeps undo_last_action useful for V0.
    if bpy.ops.ed.undo_push.poll():
        bpy.ops.ed.undo_push(message=f"Harness Blender transform {obj.name}")
    if "location" in params:
        obj.location = tuple(params["location"])
    if "rotation_degrees" in params:
        obj.rotation_euler = tuple(math.radians(v) for v in params["rotation_degrees"])
    if "scale" in params:
        obj.scale = tuple(params["scale"])
    bpy.context.view_layer.update()
    return {
        "name": obj.name,
        "location": list(obj.location),
        "rotation_euler": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
    }


def _op_delete_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = _object(params["object_name"])
    if bpy.context.mode != "OBJECT" and bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    status = bpy.ops.object.delete(use_global=False, confirm=False)
    if "FINISHED" not in status:
        raise RuntimeError(f"Blender delete operator returned {sorted(status)}")
    return {"deleted": params["object_name"], "undoable": True}


def _op_validate_mesh(params: dict[str, Any]) -> dict[str, Any]:
    obj = _object(params["object_name"])
    if obj.type != "MESH":
        raise TypeError(f"Object {obj.name} is {obj.type}, not MESH")

    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        boundary_edges = sum(1 for edge in bm.edges if edge.is_boundary)
        loose_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 0)
        # Boundary (1 face) and loose/wire (0 faces) edges are reported in their
        # own metrics. non_manifold_edges here means an edge with >2 linked faces.
        non_manifold_edges = sum(1 for edge in bm.edges if len(edge.link_faces) > 2)
        loose_vertices = sum(1 for vert in bm.verts if len(vert.link_edges) == 0)
        degenerate_faces = sum(1 for face in bm.faces if face.calc_area() <= 1e-12)
        return {
            "name": obj.name,
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": len(bm.faces),
            "boundary_edges": boundary_edges,
            "non_manifold_edges": non_manifold_edges,
            "loose_edges": loose_edges,
            "loose_vertices": loose_vertices,
            "degenerate_faces": degenerate_faces,
            "is_closed_manifold": (
                boundary_edges == 0
                and non_manifold_edges == 0
                and loose_edges == 0
                and loose_vertices == 0
            ),
        }
    finally:
        bm.free()


def _op_save_blend(params: dict[str, Any]) -> dict[str, Any]:
    filepath = params.get("filepath")
    if filepath:
        status = bpy.ops.wm.save_as_mainfile(filepath=filepath)
    else:
        if not bpy.data.filepath:
            raise ValueError("Current file has no path; provide filepath")
        status = bpy.ops.wm.save_mainfile()
    if "FINISHED" not in status:
        raise RuntimeError(f"Blender save operator returned {sorted(status)}")
    return {"filepath": bpy.data.filepath}


def _op_undo(_params: dict[str, Any]) -> dict[str, Any]:
    if not bpy.ops.ed.undo.poll():
        raise RuntimeError("Blender undo is not available in the current context")
    status = bpy.ops.ed.undo()
    if "FINISHED" not in status:
        raise RuntimeError(f"Blender undo operator returned {sorted(status)}")
    return {"status": sorted(status)}


def _op_capture_screen(_params: dict[str, Any]) -> dict[str, Any]:
    if bpy.app.background:
        raise RuntimeError("Screen capture requires Blender GUI mode")
    with tempfile.TemporaryDirectory(prefix="harness_blender_") as directory:
        target = Path(directory) / "screen.png"
        status = bpy.ops.screen.screenshot(filepath=str(target))
        if "FINISHED" not in status or not target.exists():
            raise RuntimeError(f"Blender screenshot operator returned {sorted(status)}")
        data = target.read_bytes()
    return {"format": "png", "png_base64": base64.b64encode(data).decode("ascii")}


Operation = Callable[[dict[str, Any]], dict[str, Any]]
OPERATIONS: dict[str, Operation] = {
    "ping": _op_ping,
    "inspect_scene": _op_inspect_scene,
    "inspect_object": _op_inspect_object,
    "create_primitive": _op_create_primitive,
    "transform_object": _op_transform_object,
    "delete_object": _op_delete_object,
    "validate_mesh": _op_validate_mesh,
    "save_blend": _op_save_blend,
    "undo": _op_undo,
    "capture_screen": _op_capture_screen,
}


def dispatch_operation(operation: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute one already-validated V0 operation on Blender's main thread."""
    handler = OPERATIONS.get(operation)
    if handler is None:
        raise ValueError(f"Operation is not implemented in V0: {operation!r}")
    result = handler(params)
    if not isinstance(result, dict):
        raise TypeError("V0 operations must return a JSON object")
    return result
