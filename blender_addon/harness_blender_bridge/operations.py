# SPDX-License-Identifier: GPL-3.0-or-later
"""Closed Blender-side implementation of Harness Blender V0 operations."""

from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator

import bmesh
import bpy



@dataclass
class _UndoAction:
    label: str
    restore: Callable[[], None]


_UNDO_STACK: list[_UndoAction] = []
_MAX_UNDO_ACTIONS = 20


def _record_undo(label: str, restore: Callable[[], None]) -> None:
    _UNDO_STACK.append(_UndoAction(label=label, restore=restore))
    if len(_UNDO_STACK) > _MAX_UNDO_ACTIONS:
        del _UNDO_STACK[0]


from . import curve_operations
from . import mesh_operations
from . import evaluator_operations
from . import geometry_nodes_operations


def _object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")
    return obj


@contextmanager
def _operator_context() -> Iterator[None]:
    """Provide a VIEW_3D context for operators called by the bridge timer."""
    if bpy.app.background:
        yield
        return

    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((item for item in area.regions if item.type == "WINDOW"), None)
            if region is None:
                continue
            with bpy.context.temp_override(
                window=window,
                screen=screen,
                area=area,
                region=region,
                scene=window.scene,
                view_layer=window.view_layer,
            ):
                yield
                return
    raise RuntimeError("A Blender VIEW_3D window is required for this operation")


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
    with _operator_context():
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
        obj = bpy.context.view_layer.objects.active
        if obj is None:
            raise RuntimeError("Blender did not create an active object")
        obj.name = name
        obj.scale = tuple(params["scale"])
        bpy.context.view_layer.update()
    created_name = obj.name

    def restore() -> None:
        created = bpy.data.objects.get(created_name)
        if created is not None:
            bpy.data.objects.remove(created, do_unlink=True)

    _record_undo(f"create {created_name}", restore)
    return {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
    }


def _op_transform_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = _object(params["object_name"])
    previous_location = tuple(obj.location)
    previous_rotation = tuple(obj.rotation_euler)
    previous_scale = tuple(obj.scale)
    if "location" in params:
        obj.location = tuple(params["location"])
    if "rotation_degrees" in params:
        obj.rotation_euler = tuple(math.radians(v) for v in params["rotation_degrees"])
    if "scale" in params:
        obj.scale = tuple(params["scale"])
    bpy.context.view_layer.update()

    def restore() -> None:
        current = bpy.data.objects.get(obj.name)
        if current is None:
            return
        current.location = previous_location
        current.rotation_euler = previous_rotation
        current.scale = previous_scale
        bpy.context.view_layer.update()

    _record_undo(f"transform {obj.name}", restore)
    return {
        "name": obj.name,
        "location": list(obj.location),
        "rotation_euler": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
    }


def _op_delete_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = _object(params["object_name"])
    original_name = obj.name
    snapshot = obj.copy()
    if obj.data is not None and hasattr(obj.data, "copy"):
        snapshot.data = obj.data.copy()
    collections = tuple(obj.users_collection)
    parent = obj.parent
    parent_inverse = obj.matrix_parent_inverse.copy()
    bpy.data.objects.remove(obj, do_unlink=True)

    def restore() -> None:
        snapshot.name = original_name
        for collection in collections:
            collection.objects.link(snapshot)
        if not collections:
            bpy.context.scene.collection.objects.link(snapshot)
        snapshot.parent = parent
        snapshot.matrix_parent_inverse = parent_inverse
        bpy.context.view_layer.update()

    _record_undo(f"delete {snapshot.name}", restore)
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
    if not _UNDO_STACK:
        raise RuntimeError("Harness Blender has no reversible V0 action to undo")
    action = _UNDO_STACK.pop()
    action.restore()
    return {"status": ["FINISHED"], "undone": action.label}


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


def _op_capture_controlled_view(params: dict[str, Any]) -> dict[str, Any]:
    """Capture a fixed GUI viewport view and restore the user's view afterward."""
    if bpy.app.background:
        raise RuntimeError("Controlled view capture requires Blender GUI mode")
    temp_root = os.getenv("HARNESS_BLENDER_TEMP_DIR")
    if not temp_root:
        raise RuntimeError("Set HARNESS_BLENDER_TEMP_DIR to a writable directory before visual capture")
    directory = Path(temp_root)
    if not directory.is_absolute() or not directory.is_dir():
        raise RuntimeError("HARNESS_BLENDER_TEMP_DIR must be an existing absolute directory")
    focus = _object(params["focus_object"]) if params["focus_object"] else None
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((item for item in area.regions if item.type == "WINDOW"), None)
            if region is None:
                continue
            space = area.spaces.active
            region_3d = space.region_3d
            saved_view = (region_3d.view_distance, region_3d.view_location.copy(), region_3d.view_rotation.copy(), region_3d.view_perspective)
            saved_active = window.view_layer.objects.active
            saved_selected = tuple(item for item in window.view_layer.objects if item.select_get())
            try:
                with bpy.context.temp_override(window=window, screen=screen, area=area, region=region, scene=window.scene, view_layer=window.view_layer):
                    if focus is not None:
                        for item in bpy.context.selected_objects:
                            item.select_set(False)
                        focus.select_set(True)
                        bpy.context.view_layer.objects.active = focus
                    view = params["view"]
                    if view != "perspective":
                        status = bpy.ops.view3d.view_axis(type=view.upper(), align_active=False, relative=False)
                        if "FINISHED" not in status:
                            raise RuntimeError(f"Blender could not set {view} view")
                    if focus is not None and params["frame_selected"]:
                        status = bpy.ops.view3d.view_selected(use_all_regions=False)
                        if "FINISHED" not in status:
                            raise RuntimeError("Blender could not frame the focused object")
                    with tempfile.TemporaryDirectory(prefix="harness_blender_", dir=directory) as temporary:
                        target = Path(temporary) / "controlled_view.png"
                        status = bpy.ops.screen.screenshot(filepath=str(target))
                        if "FINISHED" not in status or not target.exists():
                            raise RuntimeError(f"Blender screenshot operator returned {sorted(status)}")
                        data = target.read_bytes()
                return {"format": "png", "png_base64": base64.b64encode(data).decode("ascii"), "view": view, "focus_object": focus.name if focus else None, "framed": bool(focus and params["frame_selected"])}
            finally:
                region_3d.view_distance, region_3d.view_location, region_3d.view_rotation, region_3d.view_perspective = saved_view
                for item in window.view_layer.objects:
                    item.select_set(False)
                for item in saved_selected:
                    item.select_set(True)
                window.view_layer.objects.active = saved_active
    raise RuntimeError("A Blender VIEW_3D window is required for controlled view capture")


def _op_create_procedural_tube_setup(params: dict[str, Any]) -> dict[str, Any]:
    result = geometry_nodes_operations.create_procedural_tube_setup(params)
    object_name = result["object_name"]
    modifier_name = result["modifier_name"]
    group_name = result["group_name"]

    def restore() -> None:
        obj = bpy.data.objects.get(object_name)
        modifier = obj.modifiers.get(modifier_name) if obj else None
        if modifier is not None:
            obj.modifiers.remove(modifier)
        group = bpy.data.node_groups.get(group_name)
        if group is not None and group.users == 0:
            bpy.data.node_groups.remove(group)
        bpy.context.view_layer.update()

    _record_undo(f"create Geometry Nodes tube {group_name}", restore)
    return result


def _op_create_surface_scatter_setup(params: dict[str, Any]) -> dict[str, Any]:
    result = geometry_nodes_operations.create_surface_scatter_setup(params)
    surface_name, modifier_name, group_name = result["surface_object_name"], result["modifier_name"], result["group_name"]

    def restore() -> None:
        surface = bpy.data.objects.get(surface_name)
        modifier = surface.modifiers.get(modifier_name) if surface else None
        if modifier is not None:
            surface.modifiers.remove(modifier)
        group = bpy.data.node_groups.get(group_name)
        if group is not None and group.users == 0:
            bpy.data.node_groups.remove(group)
        bpy.context.view_layer.update()

    _record_undo(f"create Geometry Nodes scatter {group_name}", restore)
    return result


def _op_create_procedural_branching_setup(params: dict[str, Any]) -> dict[str, Any]:
    result = geometry_nodes_operations.create_procedural_branching_setup(params)
    def restore() -> None:
        obj=bpy.data.objects.get(result["main_curve_name"]); mod=obj.modifiers.get(result["modifier_name"]) if obj else None
        if mod: obj.modifiers.remove(mod)
        group=bpy.data.node_groups.get(result["group_name"])
        if group and group.users == 0: bpy.data.node_groups.remove(group)
    _record_undo(f"create Geometry Nodes branching {result['group_name']}", restore)
    return result


def _op_inspect_active_selection(_params: dict[str, Any]) -> dict[str, Any]:
    active = bpy.context.view_layer.objects.active
    return {"active_object": active.name if active else None, "active_type": active.type if active else None, "selected_objects": [obj.name for obj in bpy.context.selected_objects]}


Operation = Callable[[dict[str, Any]], dict[str, Any]]
OPERATIONS: dict[str, Operation] = {
    "ping": _op_ping,
    "inspect_scene": _op_inspect_scene,
    "inspect_scene_detailed": evaluator_operations.inspect_scene_detailed,
    "inspect_active_selection": _op_inspect_active_selection,
    "evaluate_mesh": evaluator_operations.evaluate_mesh,
    "evaluate_spatial": evaluator_operations.evaluate_spatial,
    "evaluate_tubular": evaluator_operations.evaluate_tubular,
    "evaluate_penetration": evaluator_operations.evaluate_penetration,
    "inspect_object": _op_inspect_object,
    "create_primitive": _op_create_primitive,
    "transform_object": _op_transform_object,
    "delete_object": _op_delete_object,
    "validate_mesh": _op_validate_mesh,
    "inspect_mesh_detailed": mesh_operations.inspect_mesh_detailed,
    "recalculate_normals": mesh_operations.recalculate_normals,
    "flip_normals": mesh_operations.flip_normals,
    "subdivide_mesh": mesh_operations.subdivide_mesh,
    "smooth_mesh": mesh_operations.smooth_mesh,
    "create_material": mesh_operations.create_material,
    "assign_material": mesh_operations.assign_material,
    "set_base_color": lambda params: mesh_operations.set_material_value(params, "Base Color", "base_color"),
    "set_roughness": lambda params: mesh_operations.set_material_scalar(params, "Roughness", "roughness"),
    "set_metallic": lambda params: mesh_operations.set_material_scalar(params, "Metallic", "metallic"),
    "set_alpha": lambda params: mesh_operations.set_material_scalar(params, "Alpha", "alpha"),
    "add_modifier": mesh_operations.add_modifier,
    "set_modifier_parameter": mesh_operations.set_modifier_parameter,
    "remove_modifier": mesh_operations.remove_modifier,
    "apply_modifier": mesh_operations.apply_modifier,
    "merge_vertices": mesh_operations.merge_vertices,
    "bridge_edge_loops": mesh_operations.bridge_edge_loops,
    "split_mesh_by_plane": mesh_operations.split_mesh_by_plane,
    "split_selected_mesh_by_view_line": mesh_operations.split_selected_mesh_by_view_line,
    "fill_hole": mesh_operations.fill_hole,
    "boolean_union": lambda params: mesh_operations.boolean_operation(params, "UNION"),
    "boolean_difference": lambda params: mesh_operations.boolean_operation(params, "DIFFERENCE"),
    "boolean_intersection": lambda params: mesh_operations.boolean_operation(params, "INTERSECT"),
    "decimate_mesh": mesh_operations.decimate_mesh,
    "voxel_remesh": mesh_operations.voxel_remesh,
    "save_blend": _op_save_blend,
    "undo": _op_undo,
    "capture_screen": _op_capture_screen,
    "capture_controlled_view": _op_capture_controlled_view,
    "create_procedural_tube_setup": _op_create_procedural_tube_setup,
    "create_surface_scatter_setup": _op_create_surface_scatter_setup,
    "create_procedural_branching_setup": _op_create_procedural_branching_setup,
    "inspect_geometry_node_tree": geometry_nodes_operations.inspect_geometry_node_tree,
    "create_curve": curve_operations.create_curve,
    "inspect_curve": curve_operations.inspect_curve,
    "add_curve_point": curve_operations.add_point,
    "move_curve_point": curve_operations.move_point,
    "remove_curve_point": curve_operations.remove_point,
    "set_curve_handle_type": curve_operations.set_handle_type,
    "set_curve_handle_position": curve_operations.set_handle_position,
    "subdivide_curve": curve_operations.subdivide_curve,
    "resample_curve": curve_operations.resample_curve,
    "convert_curve_to_mesh": curve_operations.convert_curve_to_mesh,
    "set_curve_point_radius": lambda params: curve_operations.set_point_profile(params, "radius"),
    "set_curve_point_tilt": lambda params: curve_operations.set_point_profile(params, "tilt"),
    "set_curve_bevel_depth": lambda params: curve_operations.set_curve_property(params, "bevel_depth"),
    "set_curve_bevel_resolution": lambda params: curve_operations.set_curve_property(params, "bevel_resolution"),
    "set_curve_resolution": lambda params: curve_operations.set_spline_property(params, "resolution_u"),
    "set_curve_cyclic": lambda params: curve_operations.set_spline_property(
        params, "use_cyclic_u", param_field="cyclic"
    ),
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
