# SPDX-License-Identifier: GPL-3.0-or-later
"""V8.0 reversible metadata for structures Harness can later move."""
from __future__ import annotations

import json
from typing import Any
import bpy

_KEY = "harness_movable_structure_v8"
_CURVE_SNAPSHOT_KEY = "harness_curve_shape_v8"

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

def restore_metadata(object_name: str, previous: str | None) -> None:
    obj = bpy.data.objects.get(object_name)
    if obj is None: return
    if previous is None: obj.pop(_KEY, None)
    else: obj[_KEY] = previous
