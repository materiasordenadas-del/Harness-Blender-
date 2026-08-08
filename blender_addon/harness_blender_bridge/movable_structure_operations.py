# SPDX-License-Identifier: GPL-3.0-or-later
"""V8.0 reversible metadata for structures Harness can later move."""
from __future__ import annotations

import json
import math
from typing import Any
import bpy
from mathutils import Vector

_KEY = "harness_movable_structure_v8"
_CURVE_SNAPSHOT_KEY = "harness_curve_shape_v8"
_MESH_SOURCE_KEY = "harness_mesh_source_v8"
_MESH_PART_KEY = "harness_mesh_part_v8"
_MAX_SAFE_EDGE_STRETCH = 1.5
_MAX_SAFE_MESH_BEND_DEGREES = 90.0

def _object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type not in {"MESH", "CURVE"}:
        raise TypeError("movable structure requires an existing MESH or CURVE object")
    return obj

def _default(obj: bpy.types.Object, mode: str | None = None) -> dict[str, Any]:
    mode = mode or ("curve_guided" if obj.type == "CURVE" else "mesh_guided")
    if (obj.type == "CURVE") != (mode == "curve_guided"):
        raise ValueError(f"{obj.type} objects require {'curve_guided' if obj.type == 'CURVE' else 'mesh_guided'} mode")
    parts = [{"name": "Core", "movable": False, "state": "fixed"}]
    if obj.type == "CURVE":
        parts += [{"name": f"Process_{i:02d}", "movable": True, "state": "neutral", "spline_index": i - 1} for i in range(1, len(obj.data.splines) + 1)]
    return {"version": "v8.0", "object": obj.name, "mode": mode, "parts": parts,
            "status": "prepared" if obj.type == "CURVE" else "needs_review",
            "notes": [] if obj.type == "CURVE" else ["mesh_segmentation_is_planned_for_v8_2"]}

def _stored(obj: bpy.types.Object) -> dict[str, Any] | None:
    raw = obj.get(_KEY)
    try: return json.loads(raw) if isinstance(raw, str) else None
    except json.JSONDecodeError: return None

def inspect(params: dict[str, Any]) -> dict[str, Any]:
    obj = _object(params["object_name"]); stored = _stored(obj)
    return {"prepared": stored is not None, **(stored or _default(obj))}

def prepare(params: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    obj = _object(params["object_name"]); previous = obj.get(_KEY); structure = _default(obj, params.get("mode"))
    obj[_KEY] = json.dumps(structure, separators=(",", ":"))
    return {"prepared": True, **structure}, previous if isinstance(previous, str) else None

def list_parts(params: dict[str, Any]) -> dict[str, Any]:
    report = inspect(params)
    return {key: report[key] for key in ("object", "mode", "prepared", "parts")}

def get_part_state(params: dict[str, Any]) -> dict[str, Any]:
    report = inspect({"object_name": params["object_name"]})
    for part in report["parts"]:
        if part["name"] == params["part_name"]:
            return {"object": report["object"], "mode": report["mode"], "prepared": report["prepared"], "part": part}
    raise ValueError(f"part not found: {params['part_name']}")

def reset(params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    obj = _object(params["object_name"]); previous = obj.get(_KEY); structure = _stored(obj)
    if not isinstance(previous, str) or structure is None: raise ValueError("structure is not prepared")
    for part in structure["parts"]:
        if part["movable"]: part["state"] = "neutral"
    obj[_KEY] = json.dumps(structure, separators=(",", ":"))
    return {"object": obj.name, "reset": True, "parts": structure["parts"]}, previous

def _points(spline: Any) -> list[Any]:
    return list(spline.bezier_points) if spline.type == "BEZIER" else list(spline.points)

def _co(point: Any, bezier: bool) -> list[float]:
    value = point.co if bezier else point.co[:3]
    return [float(item) for item in value]

def _shape_snapshot(obj: bpy.types.Object) -> list[list[dict[str, Any]]]:
    return [[{"co": _co(point, spline.type == "BEZIER"), "tilt": float(point.tilt)}
             for point in _points(spline)] for spline in obj.data.splines]

def _restore_shape(obj: bpy.types.Object, snapshot: list[list[dict[str, Any]]]) -> None:
    for spline, saved_points in zip(obj.data.splines, snapshot):
        for point, saved in zip(_points(spline), saved_points):
            if spline.type == "BEZIER": point.co = saved["co"]
            else: point.co = [*saved["co"], point.co[3]]
            point.tilt = saved["tilt"]

def capture_curve_state(object_name: str) -> dict[str, Any]:
    obj = _object(object_name)
    return {
        "shape": _shape_snapshot(obj),
        "metadata": obj.get(_KEY),
        "original_shape": obj.get(_CURVE_SNAPSHOT_KEY),
    }

def restore_curve_state(object_name: str, state: dict[str, Any]) -> None:
    obj = bpy.data.objects.get(object_name)
    if obj is None or obj.type != "CURVE": return
    _restore_shape(obj, state["shape"])
    for key, value in ((_KEY, state["metadata"]), (_CURVE_SNAPSHOT_KEY, state["original_shape"])):
        if isinstance(value, str): obj[key] = value
        else: obj.pop(key, None)

def _save_original_shape(obj: bpy.types.Object) -> None:
    if not isinstance(obj.get(_CURVE_SNAPSHOT_KEY), str):
        obj[_CURVE_SNAPSHOT_KEY] = json.dumps(_shape_snapshot(obj), separators=(",", ":"))

def bend_curve_part(params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    obj = _object(params["object_name"])
    if obj.type != "CURVE": raise TypeError("bend_curve_part requires a CURVE object")
    structure = _stored(obj)
    if structure is None: raise ValueError("structure is not prepared")
    part = next((item for item in structure["parts"] if item["name"] == params["part_name"] and item["movable"]), None)
    if part is None: raise ValueError("part must be a prepared movable curve part")
    spline = obj.data.splines[part["spline_index"]]; points = _points(spline)
    if len(points) < 2: raise ValueError("curve part requires at least two points")
    previous = capture_curve_state(obj.name)
    _save_original_shape(obj)
    base = _co(points[0], spline.type == "BEZIER")
    import math
    radians = math.radians(params["angle_degrees"])
    for index, point in enumerate(points[1:], 1):
        factor = index / (len(points) - 1); angle = radians * factor; current = _co(point, spline.type == "BEZIER")
        x, z = current[0] - base[0], current[2] - base[2]
        rotated = [base[0] + x * math.cos(angle) + z * math.sin(angle), current[1], base[2] - x * math.sin(angle) + z * math.cos(angle)]
        if spline.type == "BEZIER": point.co = rotated
        else: point.co = [*rotated, point.co[3]]
    part["state"] = "bent"; part["angle_degrees"] = params["angle_degrees"]
    obj[_KEY] = json.dumps(structure, separators=(",", ":"))
    return {"object": obj.name, "part": part["name"], "angle_degrees": params["angle_degrees"], "base_protected": True}, previous

def move_curve_part(params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    obj = _object(params["object_name"])
    if obj.type != "CURVE": raise TypeError("move_curve_part requires a CURVE object")
    structure = _stored(obj)
    if structure is None: raise ValueError("structure is not prepared")
    part = next((item for item in structure["parts"] if item["name"] == params["part_name"] and item["movable"]), None)
    if part is None: raise ValueError("part must be a prepared movable curve part")
    spline = obj.data.splines[part["spline_index"]]; points = _points(spline); offset = params["offset"]
    if len(points) < 2: raise ValueError("curve part requires at least two points")
    previous = capture_curve_state(obj.name)
    _save_original_shape(obj)
    for index, point in enumerate(points[1:], 1):
        factor = index / (len(points) - 1); current = _co(point, spline.type == "BEZIER")
        moved = [current[axis] + offset[axis] * factor for axis in range(3)]
        if spline.type == "BEZIER": point.co = moved
        else: point.co = [*moved, point.co[3]]
    part["state"] = "moved"; part["offset"] = offset; obj[_KEY] = json.dumps(structure, separators=(",", ":"))
    return {"object": obj.name, "part": part["name"], "offset": offset, "base_protected": True}, previous

def twist_curve_part(params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    obj = _object(params["object_name"])
    if obj.type != "CURVE": raise TypeError("twist_curve_part requires a CURVE object")
    structure = _stored(obj)
    if structure is None: raise ValueError("structure is not prepared")
    part = next((item for item in structure["parts"] if item["name"] == params["part_name"] and item["movable"]), None)
    if part is None: raise ValueError("part must be a prepared movable curve part")
    spline = obj.data.splines[part["spline_index"]]; points = _points(spline)
    if len(points) < 2: raise ValueError("curve part requires at least two points")
    previous = capture_curve_state(obj.name)
    _save_original_shape(obj)
    import math
    for index, point in enumerate(points[1:], 1): point.tilt += math.radians(params["angle_degrees"]) * index / (len(points) - 1)
    part["state"] = "twisted"; part["twist_degrees"] = params["angle_degrees"]; obj[_KEY] = json.dumps(structure, separators=(",", ":"))
    return {"object": obj.name, "part": part["name"], "angle_degrees": params["angle_degrees"], "base_protected": True}, previous

def reset_curve_part(params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    obj = _object(params["object_name"])
    if obj.type != "CURVE": raise TypeError("reset_curve_part requires a CURVE object")
    snapshot = obj.get(_CURVE_SNAPSHOT_KEY); structure = _stored(obj)
    if not isinstance(snapshot, str) or structure is None: raise ValueError("curve has no saved original shape")
    part = next((item for item in structure["parts"] if item["name"] == params["part_name"] and item["movable"]), None)
    if part is None: raise ValueError("part must be a prepared movable curve part")
    previous = capture_curve_state(obj.name)
    saved_spline = json.loads(snapshot)[part["spline_index"]]
    spline = obj.data.splines[part["spline_index"]]
    for point, saved in zip(_points(spline), saved_spline):
        if spline.type == "BEZIER": point.co = saved["co"]
        else: point.co = [*saved["co"], point.co[3]]
        point.tilt = saved["tilt"]
    part["state"] = "neutral"
    part.pop("angle_degrees", None); part.pop("offset", None); part.pop("twist_degrees", None)
    obj[_KEY] = json.dumps(structure, separators=(",", ":"))
    return {"object": obj.name, "part": params["part_name"], "reset": True, "base_protected": True}, previous

def _mesh_part(obj: bpy.types.Object) -> dict[str, Any]:
    raw = obj.get(_MESH_PART_KEY)
    try: part = json.loads(raw) if isinstance(raw, str) else None
    except json.JSONDecodeError: part = None
    if not isinstance(part, dict): raise ValueError("mesh copy was not prepared by Harness V8.2")
    return part

def _unique_copy_name(obj: bpy.types.Object, part_name: str) -> str:
    base = f"{obj.name}_V8_{part_name}"
    return base if bpy.data.objects.get(base) is None else f"{base}_{len(bpy.data.objects):03d}"

def _create_mesh_rig(copy: bpy.types.Object, part_name: str, indices: list[int], base_indices: list[int]) -> tuple[str, str]:
    base = Vector(_base_center(copy.data, base_indices))
    tip = max((Vector(copy.data.vertices[index].co) for index in indices), key=lambda point: (point - base).length)
    direction = tip - base
    if direction.length <= 1e-6: raise ValueError("selected extension has no length beyond its base")
    armature_data = bpy.data.armatures.new(f"{copy.name}_Rig_Data")
    armature = bpy.data.objects.new(f"{copy.name}_Rig", armature_data)
    armature.matrix_world = copy.matrix_world.copy()
    for collection in copy.users_collection: collection.objects.link(armature)
    if not copy.users_collection: bpy.context.scene.collection.objects.link(armature)
    prior_active = bpy.context.view_layer.objects.active
    prior_selected = tuple(bpy.context.selected_objects)
    try:
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True); bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="EDIT")
        root = armature.data.edit_bones.new("Harness_Base")
        root.head = base - direction.normalized() * max(direction.length * 0.1, 0.001)
        root.tail = base
        segment = armature.data.edit_bones.new("Harness_Segment")
        segment.parent = root; segment.head = base; segment.tail = tip
        segment_name = segment.name
        bpy.ops.object.mode_set(mode="OBJECT")
    finally:
        if armature.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for item in prior_selected:
            if item.name in bpy.data.objects: item.select_set(True)
        if prior_active is not None and prior_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = prior_active
    base_group = copy.vertex_groups.new(name="Harness_Base")
    segment_group = copy.vertex_groups.new(name="Harness_Segment")
    distances = {index: (Vector(copy.data.vertices[index].co) - base).length for index in indices}
    maximum = max(distances.values())
    for index, distance in distances.items():
        weight = distance / maximum
        base_group.add([index], 1.0 - weight, "REPLACE")
        segment_group.add([index], weight, "REPLACE")
    modifier = copy.modifiers.new(name="Harness_V8_Armature", type="ARMATURE")
    modifier.object = armature; modifier.use_deform_preserve_volume = True
    armature.show_in_front = True
    return armature.name, segment_name

def prepare_mesh_extension(params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    source = _object(params["object_name"])
    if source.type != "MESH": raise TypeError("prepare_mesh_extension requires a MESH object")
    indices = params["vertex_indices"]; base_indices = params["base_vertex_indices"]
    if any(index >= len(source.data.vertices) for index in indices): raise ValueError("vertex_indices contains an index outside the mesh")
    if any(index >= len(source.data.vertices) for index in base_indices): raise ValueError("base_vertex_indices contains an index outside the mesh")
    if not set(base_indices).issubset(indices): raise ValueError("base_vertex_indices must belong to vertex_indices")
    if set(base_indices) == set(indices): raise ValueError("the base cannot contain every selected extension vertex")
    copy = source.copy(); copy.data = source.data.copy(); copy.name = _unique_copy_name(source, params["part_name"])
    for collection in source.users_collection: collection.objects.link(copy)
    if not source.users_collection: bpy.context.scene.collection.objects.link(copy)
    copy[_MESH_SOURCE_KEY] = source.name
    copy[_MESH_PART_KEY] = json.dumps({"name": params["part_name"], "vertex_indices": indices, "base_vertex_indices": base_indices}, separators=(",", ":"))
    armature_name, segment_bone = _create_mesh_rig(copy, params["part_name"], indices, base_indices)
    part = json.loads(copy[_MESH_PART_KEY]); part.update({"armature_name": armature_name, "segment_bone": segment_bone})
    copy[_MESH_PART_KEY] = json.dumps(part, separators=(",", ":"))
    return {"object": source.name, "copy_object": copy.name, "armature_object": armature_name, "part": params["part_name"], "status": "prepared", "base_protected": True, "source_unchanged": True}, copy.name

def prepare_selected_mesh_extension(params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    source = _object(params["object_name"])
    if source.type != "MESH": raise TypeError("prepare_selected_mesh_extension requires a MESH object")
    if source.mode == "EDIT": raise ValueError("finish the vertex selection and return to Object Mode before preparing the extension")
    selected = [vertex.index for vertex in source.data.vertices if vertex.select]
    selected_set = set(selected)
    if len(selected) < 2: raise ValueError("select at least two vertices for the extension")
    base = []
    for edge in source.data.edges:
        first, second = edge.vertices
        if (first in selected_set) != (second in selected_set): base.append(first if first in selected_set else second)
    base = sorted(set(base))
    if not base: raise ValueError("the selected extension needs a boundary connected to the unselected core")
    result, copy_name = prepare_mesh_extension({
        "object_name": source.name, "part_name": params["part_name"],
        "vertex_indices": selected, "base_vertex_indices": base,
    })
    result["selection_source"] = "Blender vertex selection"
    return result, copy_name

def propose_mesh_extension(params: dict[str, Any]) -> dict[str, Any]:
    source = _object(params["object_name"])
    if source.type != "MESH": raise TypeError("propose_mesh_extension requires a MESH object")
    return {
        "object": source.name, "mode": "mesh_guided", "status": "needs_review",
        "parts": [{"name": "Core", "movable": False, "state": "fixed"}],
        "proposal": {"requires_explicit_vertex_indices": True, "requires_explicit_base_vertex_indices": True},
        "source_unchanged": True,
    }

def remove_mesh_copy(copy_name: str) -> None:
    copy = bpy.data.objects.get(copy_name)
    armature_name = None
    if copy is not None:
        try: armature_name = _mesh_part(copy).get("armature_name")
        except ValueError: pass
        bpy.data.objects.remove(copy, do_unlink=True)
    armature = bpy.data.objects.get(armature_name) if isinstance(armature_name, str) else None
    if armature is not None: bpy.data.objects.remove(armature, do_unlink=True)

def _base_center(mesh: bpy.types.Mesh, indices: list[int]) -> list[float]:
    return [sum(mesh.vertices[index].co[axis] for index in indices) / len(indices) for axis in range(3)]

def _edge_lengths(mesh: bpy.types.Mesh) -> list[float]:
    return [math.dist(mesh.vertices[edge.vertices[0]].co, mesh.vertices[edge.vertices[1]].co) for edge in mesh.edges]

def _maximum_edge_stretch(before: list[float], after: list[float]) -> float:
    maximum = 1.0
    for original, current in zip(before, after):
        if original <= 1e-9:
            if current > 1e-9: return float("inf")
            continue
        maximum = max(maximum, current / original, original / max(current, 1e-9))
    return maximum

def _evaluated_edge_lengths(obj: bpy.types.Object) -> list[float]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try: return _edge_lengths(mesh)
    finally: evaluated.to_mesh_clear()

def bend_mesh_part(params: dict[str, Any]) -> tuple[dict[str, Any], list[float]]:
    copy = _object(params["object_name"])
    if copy.type != "MESH": raise TypeError("bend_mesh_part requires a prepared MESH copy")
    if abs(params["angle_degrees"]) > _MAX_SAFE_MESH_BEND_DEGREES:
        raise ValueError(f"blocked: mesh bends are limited to +/-{_MAX_SAFE_MESH_BEND_DEGREES:.0f} degrees")
    part = _mesh_part(copy)
    source_name = copy.get(_MESH_SOURCE_KEY); source = bpy.data.objects.get(source_name) if isinstance(source_name, str) else None
    if source is None or source.type != "MESH": raise ValueError("the original mesh is no longer available for this temporary copy")
    armature = bpy.data.objects.get(part.get("armature_name"))
    if armature is None or armature.type != "ARMATURE": raise ValueError("prepared mesh copy has no internal armature")
    pose_bone = armature.pose.bones.get(part.get("segment_bone"))
    if pose_bone is None: raise ValueError("prepared mesh copy has no segment control")
    previous = [float(value) for value in pose_bone.rotation_euler]
    edge_lengths = _edge_lengths(copy.data)
    bend_axis = params.get("bend_axis", "x")
    if bend_axis not in {"x", "z"}: raise ValueError("bend_axis must be x or z")
    axis_index = {"x": 0, "z": 2}[bend_axis]
    pose_bone.rotation_mode = "XYZ"; pose_bone.rotation_euler[axis_index] = math.radians(params["angle_degrees"])
    bpy.context.view_layer.update()
    stretch = _maximum_edge_stretch(edge_lengths, _evaluated_edge_lengths(copy))
    if stretch > _MAX_SAFE_EDGE_STRETCH:
        restore_mesh_part(copy.name, previous)
        raise ValueError(f"blocked: bend would stretch an edge {stretch:.2f}x (limit {_MAX_SAFE_EDGE_STRETCH:.2f}x)")
    return {"object": copy.name, "source_object": source.name, "part": part["name"], "angle_degrees": params["angle_degrees"], "bend_axis": bend_axis, "base_protected": True, "source_unchanged": True, "maximum_edge_stretch": stretch}, previous

def restore_mesh_part(object_name: str, previous: list[float]) -> None:
    copy = bpy.data.objects.get(object_name)
    if copy is None or copy.type != "MESH": return
    part = _mesh_part(copy)
    armature = bpy.data.objects.get(part.get("armature_name"))
    if armature is None: return
    pose_bone = armature.pose.bones.get(part.get("segment_bone"))
    if pose_bone is None: return
    pose_bone.rotation_mode = "XYZ"; pose_bone.rotation_euler = previous
    bpy.context.view_layer.update()

def reset_mesh_part(params: dict[str, Any]) -> tuple[dict[str, Any], list[float]]:
    copy = _object(params["object_name"])
    if copy.type != "MESH": raise TypeError("reset_mesh_part requires a prepared MESH copy")
    part = _mesh_part(copy); source_name = copy.get(_MESH_SOURCE_KEY)
    source = bpy.data.objects.get(source_name) if isinstance(source_name, str) else None
    if source is None or source.type != "MESH": raise ValueError("the original mesh is no longer available for this temporary copy")
    armature = bpy.data.objects.get(part.get("armature_name"))
    if armature is None: raise ValueError("prepared mesh copy has no internal armature")
    pose_bone = armature.pose.bones.get(part.get("segment_bone"))
    if pose_bone is None: raise ValueError("prepared mesh copy has no segment control")
    previous = [float(value) for value in pose_bone.rotation_euler]
    pose_bone.rotation_mode = "XYZ"; pose_bone.rotation_euler = [0.0, 0.0, 0.0]
    bpy.context.view_layer.update()
    return {"object": copy.name, "source_object": source.name, "part": part["name"], "reset": True, "base_protected": True, "source_unchanged": True}, previous

def restore_metadata(object_name: str, previous: str | None) -> None:
    obj = bpy.data.objects.get(object_name)
    if obj is None: return
    if previous is None: obj.pop(_KEY, None)
    else: obj[_KEY] = previous
