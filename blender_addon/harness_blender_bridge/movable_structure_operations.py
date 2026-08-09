# SPDX-License-Identifier: GPL-3.0-or-later
"""V8.0 reversible metadata for structures Harness can later move."""
from __future__ import annotations

import json
import heapq
import math
from typing import Any
import bpy
from mathutils import Matrix, Vector

_KEY = "harness_movable_structure_v8"
_CURVE_SNAPSHOT_KEY = "harness_curve_shape_v8"
_MESH_SOURCE_KEY = "harness_mesh_source_v8"
_MESH_PART_KEY = "harness_mesh_part_v8"
_MAX_SAFE_EDGE_STRETCH = 1.5
_MAX_SAFE_MESH_BEND_DEGREES = 90.0
_MAX_SAFE_HANDLE_STRETCH = 1.8
_WEIGHT_FALLOFF_RINGS = 4
_WEIGHT_FALLOFF_FACTOR = 0.55
_V8_SESSION_KEY = "harness_v8_session"
_V8_SOURCE_KEY = "harness_v8_source"
_V8_ROLE_KEY = "harness_v8_role"

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

def _smooth_influence_weights(mesh: bpy.types.Mesh, indices: list[int], base_indices: list[int]) -> dict[int, float]:
    base = Vector(_base_center(mesh, base_indices))
    distances = {index: (Vector(mesh.vertices[index].co) - base).length for index in indices}
    maximum = max(distances.values())
    if maximum <= 1e-6: raise ValueError("selected extension has no length beyond its base")
    weights = {index: distance / maximum for index, distance in distances.items()}
    selected_set = set(indices)
    adjacency: dict[int, set[int]] = {vertex.index: set() for vertex in mesh.vertices}
    for edge in mesh.edges:
        first, second = edge.vertices; adjacency[first].add(second); adjacency[second].add(first)
    frontier = set(indices)
    for _ in range(_WEIGHT_FALLOFF_RINGS):
        next_frontier: set[int] = set()
        for index in frontier:
            for neighbor in adjacency[index]:
                if neighbor in selected_set: continue
                candidate = weights[index] * _WEIGHT_FALLOFF_FACTOR
                if candidate > weights.get(neighbor, -1.0):
                    weights[neighbor] = candidate
                    next_frontier.add(neighbor)
        frontier = next_frontier
        if not frontier: break
    return weights

def _create_mesh_rig(copy: bpy.types.Object, part_name: str, indices: list[int], base_indices: list[int], influence_weights: dict[int, float]) -> tuple[str, str, int]:
    base = Vector(_base_center(copy.data, base_indices))
    tip_index = max(indices, key=lambda index: (Vector(copy.data.vertices[index].co) - base).length)
    tip = Vector(copy.data.vertices[tip_index].co)
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
    for index, weight in influence_weights.items():
        base_group.add([index], 1.0 - weight, "REPLACE")
        segment_group.add([index], weight, "REPLACE")
    modifier = copy.modifiers.new(name="Harness_V8_Armature", type="ARMATURE")
    modifier.object = armature; modifier.use_deform_preserve_volume = True
    armature.show_in_front = True
    return armature.name, segment_name, tip_index

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
    influence_weights = _smooth_influence_weights(copy.data, indices, base_indices)
    armature_name, segment_bone, tip_index = _create_mesh_rig(copy, params["part_name"], indices, base_indices, influence_weights)
    part = json.loads(copy[_MESH_PART_KEY]); part.update({"armature_name": armature_name, "segment_bone": segment_bone, "tip_vertex_index": tip_index, "transition_vertex_count": len(influence_weights) - len(indices)})
    copy[_MESH_PART_KEY] = json.dumps(part, separators=(",", ":"))
    return {"object": source.name, "copy_object": copy.name, "armature_object": armature_name, "part": params["part_name"], "status": "prepared", "base_protected": True, "source_unchanged": True, "transition_vertex_count": len(influence_weights) - len(indices)}, copy.name

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
    positive_lengths = sorted(length for length in before if length > 1e-9)
    if not positive_lengths: return maximum
    typical_length = positive_lengths[len(positive_lengths) // 2]
    minimum_measured_length = max(1e-7, typical_length * 0.01)
    for original, current in zip(before, after):
        if original < minimum_measured_length:
            continue
        maximum = max(maximum, current / original, original / max(current, 1e-9))
    return maximum

def _evaluated_edge_lengths(obj: bpy.types.Object) -> list[float]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try: return _edge_lengths(mesh)
    finally: evaluated.to_mesh_clear()

def _evaluated_vertex_position(obj: bpy.types.Object, vertex_index: int) -> Vector:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try: return obj.matrix_world @ mesh.vertices[vertex_index].co
    finally: evaluated.to_mesh_clear()

def _active_view_matrix() -> Any:
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D": return area.spaces.active.region_3d.view_matrix.copy()
    raise ValueError("screen_direction requires a visible Blender 3D viewport")

def _screen_bend_rotation(copy: bpy.types.Object, pose_bone: Any, tip_vertex_index: int, angle_degrees: float, direction: str) -> tuple[list[float], str]:
    view_matrix = _active_view_matrix(); initial = view_matrix @ _evaluated_vertex_position(copy, tip_vertex_index)
    desired = {"left": Vector((-1.0, 0.0)), "right": Vector((1.0, 0.0)), "up": Vector((0.0, 1.0)), "down": Vector((0.0, -1.0))}[direction]
    candidates: list[tuple[float, list[float], str]] = []
    for axis, index in (("x", 0), ("z", 2)):
        for sign in (-1.0, 1.0):
            rotation = [0.0, 0.0, 0.0]; rotation[index] = sign * math.radians(abs(angle_degrees))
            pose_bone.rotation_mode = "XYZ"; pose_bone.rotation_euler = rotation; bpy.context.view_layer.update()
            moved = view_matrix @ _evaluated_vertex_position(copy, tip_vertex_index)
            displacement = Vector((moved.x - initial.x, moved.y - initial.y))
            score = displacement.normalized().dot(desired) if displacement.length > 1e-6 else -1.0
            candidates.append((score, rotation, axis))
    score, rotation, axis = max(candidates, key=lambda candidate: candidate[0])
    if score <= 0.0: raise ValueError("blocked: the selected part has no safe visible movement in that screen direction")
    return rotation, axis

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
    screen_direction = params.get("screen_direction")
    if screen_direction is not None:
        try:
            rotation, bend_axis = _screen_bend_rotation(copy, pose_bone, part["tip_vertex_index"], params["angle_degrees"], screen_direction)
            pose_bone.rotation_euler = rotation
        except Exception:
            pose_bone.rotation_mode = "XYZ"; pose_bone.rotation_euler = previous
            bpy.context.view_layer.update()
            raise
    else:
        bend_axis = params.get("bend_axis", "x")
        if bend_axis not in {"x", "z"}: raise ValueError("bend_axis must be x or z")
        axis_index = {"x": 0, "z": 2}[bend_axis]
        pose_bone.rotation_mode = "XYZ"; pose_bone.rotation_euler[axis_index] = math.radians(params["angle_degrees"])
    bpy.context.view_layer.update()
    stretch = _maximum_edge_stretch(edge_lengths, _evaluated_edge_lengths(copy))
    if stretch > _MAX_SAFE_EDGE_STRETCH:
        restore_mesh_part(copy.name, previous)
        raise ValueError(f"blocked: bend would stretch an edge {stretch:.2f}x (limit {_MAX_SAFE_EDGE_STRETCH:.2f}x)")
    return {"object": copy.name, "source_object": source.name, "part": part["name"], "angle_degrees": params["angle_degrees"], "bend_axis": bend_axis, "screen_direction": screen_direction, "base_protected": True, "source_unchanged": True, "maximum_edge_stretch": stretch}, previous

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


# V8.2 session controls deliberately bind each copied mesh to one visible
# controller.  Automatic multi-bone deformation is a later V8 milestone; this
# first session gives the user a safe, inspectable manual rig foundation.
def _session_collection_name(session_name: str) -> str:
    return f"Harness_V8_Preview_{session_name}"


def _session_payload(collection: bpy.types.Collection) -> dict[str, Any]:
    raw = collection.get(_V8_SESSION_KEY)
    try:
        payload = json.loads(raw) if isinstance(raw, str) else None
    except json.JSONDecodeError:
        payload = None
    if not isinstance(payload, dict):
        raise ValueError("V8 session metadata is unavailable")
    return payload


def _session_collection(session_name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(_session_collection_name(session_name)) or bpy.data.collections.get(f"Harness_V8_Accepted_{session_name}")
    if collection is None:
        raise ValueError("V8 session was not found")
    _session_payload(collection)
    return collection


def _unique_session_name(requested: str) -> str:
    base = requested.strip() or "Session"
    name = base
    suffix = 1
    while bpy.data.collections.get(_session_collection_name(name)) is not None:
        suffix += 1
        name = f"{base}_{suffix:02d}"
    return name


def _object_axis(obj: bpy.types.Object) -> Vector:
    dimensions = obj.dimensions
    axis = max(range(3), key=lambda index: dimensions[index])
    vector = Vector((0.0, 0.0, 0.0)); vector[axis] = max(float(dimensions[axis]) * 0.35, 0.1)
    return vector


def _deselect_armature_bones(armature: bpy.types.Object) -> None:
    prior_active = bpy.context.view_layer.objects.active; prior_selected = tuple(bpy.context.selected_objects)
    try:
        bpy.ops.object.select_all(action="DESELECT"); armature.select_set(True); bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="POSE"); bpy.ops.pose.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    finally:
        if armature.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for item in prior_selected:
            if item.name in bpy.data.objects: item.select_set(True)
        if prior_active is not None and prior_active.name in bpy.data.objects: bpy.context.view_layer.objects.active = prior_active


def _create_session_rig(copy: bpy.types.Object, collection: bpy.types.Collection, session_name: str) -> tuple[str, str]:
    data = bpy.data.armatures.new(f"{copy.name}_V8_Rig_Data")
    armature = bpy.data.objects.new(f"{copy.name}_V8_Rig", data)
    collection.objects.link(armature)
    armature.matrix_world = copy.matrix_world.copy()
    prior_active = bpy.context.view_layer.objects.active
    prior_selected = tuple(bpy.context.selected_objects)
    try:
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True); bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="EDIT")
        root = data.edit_bones.new("V8_Root")
        root.head = (0.0, 0.0, 0.0); root.tail = (0.0, 0.0, 0.25); root.use_deform = False
        control = data.edit_bones.new("V8_CTRL_Object")
        control.parent = root; control.head = root.head; control.tail = _object_axis(copy)
        control.use_deform = True
    finally:
        if armature.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for item in prior_selected:
            if item.name in bpy.data.objects: item.select_set(True)
        if prior_active is not None and prior_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = prior_active
    armature.show_in_front = True
    armature.display_type = "WIRE"
    group = copy.vertex_groups.new(name="V8_CTRL_Object")
    group.add(list(range(len(copy.data.vertices))), 1.0, "REPLACE")
    modifier = copy.modifiers.new(name="Harness_V8_Session_Armature", type="ARMATURE")
    modifier.object = armature
    modifier.use_deform_preserve_volume = True
    return armature.name, "V8_CTRL_Object"


def create_v8_session(params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    requested = params.get("session_name", "Session")
    object_names = params.get("object_names")
    sources = list(bpy.context.selected_objects) if object_names is None else [bpy.data.objects.get(name) for name in object_names]
    sources = [item for item in sources if item is not None]
    if not sources:
        raise ValueError("select at least one object before creating a V8.2 session")
    session_name = _unique_session_name(requested)
    collection = bpy.data.collections.new(_session_collection_name(session_name))
    bpy.context.scene.collection.children.link(collection)
    entries: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    try:
        for source in sources:
            if source.type != "MESH":
                skipped.append({"object": source.name, "reason": f"{source.type} is not a deformable mesh in V8.2"})
                continue
            copy = source.copy(); copy.data = source.data.copy()
            copy.name = f"{source.name}_V8_{session_name}"
            collection.objects.link(copy)
            copy[_V8_SOURCE_KEY] = source.name; copy[_V8_ROLE_KEY] = "preview_mesh"
            rig_name, control_name = _create_session_rig(copy, collection, session_name)
            entries.append({"source_object": source.name, "copy_object": copy.name, "armature_object": rig_name, "control_bone": control_name})
        if not entries:
            raise ValueError("V8.2 currently requires at least one selected MESH object")
        collection[_V8_SESSION_KEY] = json.dumps({"version": "v8.2", "session": session_name, "state": "preview", "entries": entries}, separators=(",", ":"))
    except Exception:
        bpy.data.collections.remove(collection)
        raise
    return {"session": session_name, "collection": collection.name, "state": "preview", "entries": entries, "skipped": skipped, "source_unchanged": True, "requires_acceptance": True}, session_name


def inspect_v8_session(params: dict[str, Any]) -> dict[str, Any]:
    collection = _session_collection(params["session_name"])
    payload = _session_payload(collection)
    return {"collection": collection.name, **payload, "source_unchanged": True}


def _pose_snapshot(payload: dict[str, Any]) -> dict[str, list[float]]:
    snapshot: dict[str, list[float]] = {}
    for entry in payload["entries"]:
        armature = bpy.data.objects.get(entry["armature_object"])
        if armature is None or armature.type != "ARMATURE": continue
        for bone_name in entry.get("control_bones", [entry["control_bone"]]):
            control = armature.pose.bones.get(bone_name)
            if control is not None:
                snapshot[f"{armature.name}\0{bone_name}"] = [float(value) for row in control.matrix_basis for value in row]
    return snapshot


def restore_v8_session_pose(session_name: str, snapshot: dict[str, list[float]]) -> None:
    collection = bpy.data.collections.get(_session_collection_name(session_name))
    if collection is None: return
    for key, values in snapshot.items():
        armature_name, bone_name = key.split("\0", 1)
        armature = bpy.data.objects.get(armature_name)
        if armature is not None and armature.type == "ARMATURE":
            armature.pose.bones[bone_name].matrix_basis = Matrix((values[0:4], values[4:8], values[8:12], values[12:16]))
    bpy.context.view_layer.update()


def reset_v8_session(params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[float]]]:
    collection = _session_collection(params["session_name"]); payload = _session_payload(collection)
    previous = _pose_snapshot(payload)
    for entry in payload["entries"]:
        armature = bpy.data.objects.get(entry["armature_object"])
        if armature is not None and armature.type == "ARMATURE":
            for bone_name in entry.get("control_bones", [entry["control_bone"]]):
                armature.pose.bones[bone_name].matrix_basis.identity()
    bpy.context.view_layer.update()
    return {"session": payload["session"], "reset": True, "source_unchanged": True}, previous


def pose_v8_control(params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[float]]]:
    collection = _session_collection(params["session_name"]); payload = _session_payload(collection)
    entry = next((item for item in payload["entries"] if item["copy_object"] == params["copy_object"]), None)
    if entry is None: raise ValueError("copy_object does not belong to this V8 session")
    armature = bpy.data.objects.get(entry["armature_object"])
    if armature is None or armature.type != "ARMATURE": raise ValueError("V8 session control armature is missing")
    bone_name = params.get("control_bone", entry["control_bone"])
    if bone_name not in entry.get("control_bones", [entry["control_bone"]]): raise ValueError("control_bone does not belong to this V8 rig")
    control = armature.pose.bones.get(bone_name)
    if control is None: raise ValueError("V8 session control bone is missing")
    previous = _pose_snapshot(payload)
    copy = bpy.data.objects.get(entry["copy_object"])
    if copy is None or copy.type != "MESH": raise ValueError("V8 session mesh copy is missing")
    before = _edge_lengths(copy.data)
    control.rotation_mode = "XYZ"
    control.location = params["location"]
    control.rotation_euler = [math.radians(value) for value in params["rotation_degrees"]]
    bpy.context.view_layer.update()
    stretch = _maximum_edge_stretch(before, _evaluated_edge_lengths(copy))
    if stretch > _MAX_SAFE_HANDLE_STRETCH:
        restore_v8_session_pose(payload["session"], previous)
        raise ValueError(f"blocked: handle pose would stretch an edge {stretch:.2f}x (limit {_MAX_SAFE_HANDLE_STRETCH:.2f}x)")
    return {"session": payload["session"], "copy_object": entry["copy_object"], "control_bone": bone_name, "location": params["location"], "rotation_degrees": params["rotation_degrees"], "maximum_edge_stretch": stretch, "source_unchanged": True}, previous


def propose_v8_photo_pose(params: dict[str, Any]) -> dict[str, Any]:
    """Combine annotated front and side image offsets into a reversible 3D pose proposal."""
    collection = _session_collection(params["session_name"]); payload = _session_payload(collection)
    entry = next((item for item in payload["entries"] if item["copy_object"] == params["copy_object"]), None)
    if entry is None or params["control_bone"] not in entry.get("control_bones", []): raise ValueError("photo proposal must target an existing V8 handle")
    front, side = params["front_offset"], params["side_offset"]
    # Front supplies X/Z, side supplies Y/Z.  Average Z so contradictory
    # annotations are visible to the caller rather than silently ignored.
    proposal = {"control_bone": params["control_bone"], "location": [front[0], side[0], (front[1] + side[1]) / 2.0], "rotation_degrees": [0.0, 0.0, 0.0]}
    payload["photo_proposal"] = proposal; collection[_V8_SESSION_KEY] = json.dumps(payload, separators=(",", ":"))
    return {"session": payload["session"], "copy_object": entry["copy_object"], "front_offset": front, "side_offset": side, "proposal": proposal, "requires_acceptance": True, "source_unchanged": True}


def _create_auto_chain_rig(copy: bpy.types.Object, collection: bpy.types.Collection, bone_count: int) -> tuple[str, list[str]]:
    vertices = copy.data.vertices
    adjacency: list[list[tuple[int, float]]] = [[] for _ in vertices]
    for edge in copy.data.edges:
        first, second = edge.vertices
        length = (vertices[first].co - vertices[second].co).length
        if length > 1e-9:
            adjacency[first].append((second, length)); adjacency[second].append((first, length))
    if not any(adjacency): raise ValueError("mesh has no usable connected path for an automatic V8.3 chain")
    def farthest(start: int) -> tuple[int, dict[int, int | None], dict[int, float]]:
        distances = {start: 0.0}; parents: dict[int, int | None] = {start: None}; queue = [(0.0, start)]
        while queue:
            distance, current = heapq.heappop(queue)
            if distance != distances[current]: continue
            for neighbor, cost in adjacency[current]:
                candidate = distance + cost
                if candidate < distances.get(neighbor, float("inf")):
                    distances[neighbor] = candidate; parents[neighbor] = current; heapq.heappush(queue, (candidate, neighbor))
        end = max(distances, key=distances.get)
        return end, parents, distances
    seed = next(index for index, links in enumerate(adjacency) if links)
    first, _, _ = farthest(seed); last, parents, distances = farthest(first)
    if distances[last] <= 1e-6: raise ValueError("mesh path is too short for an automatic V8.3 chain")
    path_indices = [last]
    while path_indices[-1] != first:
        parent = parents[path_indices[-1]]
        if parent is None: raise ValueError("automatic V8.3 chain could not reconstruct its mesh path")
        path_indices.append(parent)
    path_indices.reverse()
    path = [vertices[index].co.copy() for index in path_indices]
    cumulative = [0.0]
    for first_point, second_point in zip(path, path[1:]): cumulative.append(cumulative[-1] + (second_point - first_point).length)
    total_length = cumulative[-1]
    def point_at(distance: float) -> Vector:
        for index in range(1, len(cumulative)):
            if cumulative[index] >= distance:
                span = cumulative[index] - cumulative[index - 1]
                factor = 0.0 if span <= 1e-9 else (distance - cumulative[index - 1]) / span
                return path[index - 1].lerp(path[index], factor)
        return path[-1].copy()
    bone_points = [point_at(total_length * index / bone_count) for index in range(bone_count + 1)]
    data = bpy.data.armatures.new(f"{copy.name}_V8_Auto_Rig_Data")
    armature = bpy.data.objects.new(f"{copy.name}_V8_Auto_Rig", data); collection.objects.link(armature)
    armature.matrix_world = copy.matrix_world.copy()
    prior_active = bpy.context.view_layer.objects.active; prior_selected = tuple(bpy.context.selected_objects)
    controls: list[str] = []
    try:
        bpy.ops.object.select_all(action="DESELECT"); armature.select_set(True); bpy.context.view_layer.objects.active = armature; bpy.ops.object.mode_set(mode="EDIT")
        parent = None
        for index in range(bone_count):
            head = bone_points[index]; tail = bone_points[index + 1]
            bone = data.edit_bones.new(f"V8_CTRL_{index + 1:02d}"); bone.head = head; bone.tail = tail; bone.parent = parent
            if parent is not None: bone.use_connect = True
            parent = bone; controls.append(bone.name)
    finally:
        if armature.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for item in prior_selected:
            if item.name in bpy.data.objects: item.select_set(True)
        if prior_active is not None and prior_active.name in bpy.data.objects: bpy.context.view_layer.objects.active = prior_active
    for group in list(copy.vertex_groups): copy.vertex_groups.remove(group)
    for modifier in list(copy.modifiers):
        if modifier.type == "ARMATURE": copy.modifiers.remove(modifier)
    centers = [(bone_points[index] + bone_points[index + 1]) * 0.5 for index in range(bone_count)]
    for vertex in vertices:
        distances = [max((vertex.co - point).length, 1e-6) for point in centers]
        nearest = sorted(range(bone_count), key=lambda index: distances[index])[:2]
        weights = [0.0] * bone_count
        inverse = [1.0 / distances[index] for index in nearest]; total = sum(inverse)
        for index, value in zip(nearest, inverse): weights[index] = value / total
        for name, weight in zip(controls, weights):
            if weight > 0.0: copy.vertex_groups.new(name=name) if copy.vertex_groups.get(name) is None else None; copy.vertex_groups[name].add([vertex.index], weight / total, "REPLACE")
    modifier = copy.modifiers.new(name="Harness_V8_Auto_Armature", type="ARMATURE"); modifier.object = armature; modifier.use_deform_preserve_volume = True
    armature.show_in_front = True; armature.display_type = "WIRE"
    _deselect_armature_bones(armature)
    return armature.name, controls


def create_v8_auto_rig(params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    collection = _session_collection(params["session_name"]); payload = _session_payload(collection)
    entry = next((item for item in payload["entries"] if item["copy_object"] == params["copy_object"]), None)
    if entry is None: raise ValueError("copy_object does not belong to this V8 session")
    old_armature = bpy.data.objects.get(entry["armature_object"])
    if old_armature is not None: bpy.data.objects.remove(old_armature, do_unlink=True)
    rig_name, controls = _create_auto_chain_rig(bpy.data.objects[entry["copy_object"]], collection, params["bone_count"])
    entry.update({"armature_object": rig_name, "control_bone": controls[0], "control_bones": controls, "rig_mode": "automatic_chain"})
    collection[_V8_SESSION_KEY] = json.dumps(payload, separators=(",", ":"))
    return {"session": payload["session"], "copy_object": entry["copy_object"], "armature_object": rig_name, "control_bones": controls, "rig_mode": "automatic_chain", "source_unchanged": True}, rig_name


def create_v8_independent_handles(params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    collection = _session_collection(params["session_name"]); payload = _session_payload(collection)
    entry = next((item for item in payload["entries"] if item["copy_object"] == params["copy_object"]), None)
    if entry is None: raise ValueError("copy_object does not belong to this V8 session")
    old_armature = bpy.data.objects.get(entry["armature_object"])
    if old_armature is None or old_armature.type != "ARMATURE": raise ValueError("create an automatic V8.3 chain before independent handles")
    old_bones = list(old_armature.data.bones)
    if len(old_bones) < 2: raise ValueError("automatic V8.3 chain needs at least two bones")
    anchors = [old_bones[0].head_local.copy()] + [bone.tail_local.copy() for bone in old_bones]
    copy = bpy.data.objects[entry["copy_object"]]
    data = bpy.data.armatures.new(f"{copy.name}_V8_Handles_Rig_Data")
    armature = bpy.data.objects.new(f"{copy.name}_V8_Handles_Rig", data); collection.objects.link(armature)
    armature.matrix_world = copy.matrix_world.copy()
    prior_active = bpy.context.view_layer.objects.active; prior_selected = tuple(bpy.context.selected_objects); controls: list[str] = []
    try:
        bpy.ops.object.select_all(action="DESELECT"); armature.select_set(True); bpy.context.view_layer.objects.active = armature; bpy.ops.object.mode_set(mode="EDIT")
        for index, anchor in enumerate(anchors):
            direction = (anchors[min(index + 1, len(anchors) - 1)] - anchors[max(index - 1, 0)]).normalized()
            if direction.length <= 1e-6: direction = Vector((0.0, 0.0, 0.05))
            bone = data.edit_bones.new(f"V8_HANDLE_{index + 1:02d}"); bone.head = anchor; bone.tail = anchor + direction * max(direction.length * 0.2, 0.03)
            controls.append(bone.name)
    finally:
        if armature.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for item in prior_selected:
            if item.name in bpy.data.objects: item.select_set(True)
        if prior_active is not None and prior_active.name in bpy.data.objects: bpy.context.view_layer.objects.active = prior_active
    for group in list(copy.vertex_groups): copy.vertex_groups.remove(group)
    for modifier in list(copy.modifiers):
        if modifier.type == "ARMATURE": copy.modifiers.remove(modifier)
    for name in controls: copy.vertex_groups.new(name=name)
    for vertex in copy.data.vertices:
        # Each handle remains independent, while the surface blends only between
        # its two closest handles.  This prevents the hard seams produced by a
        # one-handle-per-vertex assignment and behaves like a local elbow.
        distances = [max((vertex.co - anchor).length, 1e-6) for anchor in anchors]
        nearest = sorted(range(len(anchors)), key=lambda index: distances[index])[:2]
        inverse = [1.0 / distances[index] for index in nearest]; total = sum(inverse)
        for index, value in zip(nearest, inverse):
            copy.vertex_groups[controls[index]].add([vertex.index], value / total, "REPLACE")
    modifier = copy.modifiers.new(name="Harness_V8_Independent_Handles", type="ARMATURE"); modifier.object = armature; modifier.use_deform_preserve_volume = True
    armature.show_in_front = True; armature.display_type = "WIRE"
    _deselect_armature_bones(armature)
    bpy.data.objects.remove(old_armature, do_unlink=True)
    entry.update({"armature_object": armature.name, "control_bone": controls[0], "control_bones": controls, "rig_mode": "independent_handles"})
    collection[_V8_SESSION_KEY] = json.dumps(payload, separators=(",", ":"))
    return {"session": payload["session"], "copy_object": copy.name, "armature_object": armature.name, "control_bones": controls, "rig_mode": "independent_handles", "independent": True, "source_unchanged": True}, armature.name


def accept_v8_session(params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    collection = _session_collection(params["session_name"]); payload = _session_payload(collection)
    prior_name = collection.name
    collection.name = f"Harness_V8_Accepted_{payload['session']}"
    payload["state"] = "accepted"; collection[_V8_SESSION_KEY] = json.dumps(payload, separators=(",", ":"))
    return {"session": payload["session"], "collection": collection.name, "accepted": True, "source_unchanged": True}, prior_name


def restore_v8_session_acceptance(session_name: str, prior_name: str) -> None:
    collection = bpy.data.collections.get(f"Harness_V8_Accepted_{session_name}")
    if collection is None: return
    collection.name = prior_name
    payload = _session_payload(collection); payload["state"] = "preview"
    collection[_V8_SESSION_KEY] = json.dumps(payload, separators=(",", ":"))


def discard_v8_session(params: dict[str, Any]) -> dict[str, Any]:
    collection = _session_collection(params["session_name"]); payload = _session_payload(collection)
    for item in list(collection.objects):
        bpy.data.objects.remove(item, do_unlink=True)
    bpy.data.collections.remove(collection)
    return {"session": payload["session"], "discarded": True, "source_unchanged": True}
