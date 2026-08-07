# SPDX-License-Identifier: GPL-3.0-or-later
"""Typed V1 curve operations implemented with Blender's data API."""

from __future__ import annotations

from typing import Any

import bpy

from .operations import _record_undo


def _curve(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")
    if obj.type != "CURVE":
        raise TypeError(f"Object {name} is {obj.type}, not CURVE")
    return obj


def _spline(obj: bpy.types.Object, index: int) -> bpy.types.Spline:
    if index < 0 or index >= len(obj.data.splines):
        raise IndexError(f"Spline index out of range: {index}")
    return obj.data.splines[index]


def _points(spline: bpy.types.Spline):
    return spline.bezier_points if spline.type == "BEZIER" else spline.points


def _point(spline: bpy.types.Spline, index: int):
    points = _points(spline)
    if index < 0 or index >= len(points):
        raise IndexError(f"Point index out of range: {index}")
    return points[index]


def _point_info(point: Any, bezier: bool) -> dict[str, Any]:
    info = {
        "co": [float(v) for v in point.co],
        "radius": float(point.radius),
        "tilt": float(point.tilt),
    }
    if bezier:
        info.update({
            "handle_left": [float(v) for v in point.handle_left],
            "handle_right": [float(v) for v in point.handle_right],
            "handle_left_type": point.handle_left_type,
            "handle_right_type": point.handle_right_type,
        })
    return info


def _spline_state(spline: bpy.types.Spline) -> dict[str, Any]:
    return {
        "type": spline.type,
        "cyclic": bool(spline.use_cyclic_u),
        "resolution_u": int(spline.resolution_u),
        "points": [_point_info(point, spline.type == "BEZIER") for point in _points(spline)],
    }


def _replace_single_spline(obj: bpy.types.Object, state: dict[str, Any]) -> bpy.types.Spline:
    """Replace V1's single spline while preserving editable point attributes."""
    data = obj.data
    if len(data.splines) != 1:
        raise ValueError("Point insertion/removal currently requires a curve with one spline")
    data.splines.remove(data.splines[0])
    spline = data.splines.new(state["type"])
    points = spline.bezier_points if spline.type == "BEZIER" else spline.points
    points.add(len(state["points"]) - 1)
    for point, saved in zip(points, state["points"]):
        point.co = saved["co"] if spline.type == "BEZIER" else (*saved["co"][:3], 1.0)
        point.radius = saved["radius"]
        point.tilt = saved["tilt"]
        if spline.type == "BEZIER":
            point.handle_left = saved["handle_left"]
            point.handle_right = saved["handle_right"]
            point.handle_left_type = saved["handle_left_type"]
            point.handle_right_type = saved["handle_right_type"]
    spline.use_cyclic_u = state["cyclic"]
    spline.resolution_u = state["resolution_u"]
    return spline


def create_curve(params: dict[str, Any]) -> dict[str, Any]:
    name, spline_type, coordinates = params["name"], params["spline_type"], params["points"]
    if bpy.data.objects.get(name) is not None:
        raise ValueError(f"An object named {name!r} already exists")
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    spline = data.splines.new(spline_type)
    points = spline.bezier_points if spline_type == "BEZIER" else spline.points
    points.add(len(coordinates) - 1)
    for point, co in zip(points, coordinates):
        point.co = co if spline_type == "BEZIER" else (*co, 1.0)
        point.radius = 1.0
        if spline_type == "BEZIER":
            point.handle_left_type = "AUTO"
            point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)

    def restore() -> None:
        current = bpy.data.objects.get(name)
        if current is not None:
            bpy.data.objects.remove(current, do_unlink=True)

    _record_undo(f"create curve {name}", restore)
    return {"name": obj.name, "type": "CURVE", "spline_type": spline_type, "point_count": len(points)}


def inspect_curve(params: dict[str, Any]) -> dict[str, Any]:
    obj = _curve(params["object_name"])
    data = obj.data
    splines = []
    for spline in data.splines:
        points = _points(spline)
        splines.append({
            "type": spline.type,
            "point_count": len(points),
            "cyclic": bool(spline.use_cyclic_u),
            "resolution_u": int(spline.resolution_u),
            "points": [_point_info(point, spline.type == "BEZIER") for point in points],
        })
    return {"name": obj.name, "dimensions": data.dimensions, "spline_count": len(splines),
            "bevel_depth": float(data.bevel_depth), "bevel_resolution": int(data.bevel_resolution),
            "splines": splines}


def add_point(params: dict[str, Any]) -> dict[str, Any]:
    obj = _curve(params["object_name"])
    spline = _spline(obj, params["spline_index"])
    points = _points(spline)
    if len(points) >= 256:
        raise ValueError("A V1 spline cannot contain more than 256 points")
    initial_state = _spline_state(spline)
    state = _spline_state_from_points(spline.type, initial_state)
    state["points"].append({"co": params["co"], "radius": 1.0, "tilt": 0.0})
    if spline.type == "BEZIER":
        state["points"][-1].update({
            "handle_left": params["co"], "handle_right": params["co"],
            "handle_left_type": "AUTO", "handle_right_type": "AUTO",
        })
    _replace_single_spline(obj, state)

    def restore() -> None:
        _replace_single_spline(obj, initial_state)

    _record_undo("add curve point", restore)
    return {"point_index": len(state["points"]) - 1, "point_count": len(state["points"])}


def _spline_state_from_points(
    spline_type: str, state: dict[str, Any], *, remove_last: bool = False, removed_index: int | None = None,
) -> dict[str, Any]:
    """Copy a saved state for a reversible add/remove mutation."""
    copied = {**state, "type": spline_type, "points": list(state["points"])}
    if remove_last:
        copied["points"] = copied["points"][:-1]
    if removed_index is not None:
        copied["points"] = copied["points"][:removed_index] + copied["points"][removed_index + 1:]
    return copied


def move_point(params: dict[str, Any]) -> dict[str, Any]:
    obj = _curve(params["object_name"])
    point = _point(_spline(obj, params["spline_index"]), params["point_index"])
    previous = tuple(point.co)
    point.co = params["co"] if len(previous) == 3 else (*params["co"], 1.0)

    def restore() -> None:
        point.co = previous

    _record_undo("move curve point", restore)
    return {"co": [float(v) for v in point.co][:3]}


def remove_point(params: dict[str, Any]) -> dict[str, Any]:
    obj = _curve(params["object_name"])
    spline = _spline(obj, params["spline_index"])
    state = _spline_state(spline)
    index = params["point_index"]
    if len(state["points"]) <= 2:
        raise ValueError("A V1 spline must retain at least two points")
    if index >= len(state["points"]):
        raise IndexError(f"Point index out of range: {index}")
    new_state = _spline_state_from_points(spline.type, state, removed_index=index)
    _replace_single_spline(obj, new_state)

    def restore() -> None:
        _replace_single_spline(obj, state)

    _record_undo("remove curve point", restore)
    return {"removed_index": index, "point_count": len(new_state["points"])}


def set_point_profile(params: dict[str, Any], field: str) -> dict[str, Any]:
    obj = _curve(params["object_name"])
    point = _point(_spline(obj, params["spline_index"]), params["point_index"])
    previous = getattr(point, field)
    setattr(point, field, params[field])

    def restore() -> None:
        setattr(point, field, previous)

    _record_undo(f"set curve {field}", restore)
    return {field: float(getattr(point, field))}


def set_curve_property(params: dict[str, Any], field: str) -> dict[str, Any]:
    obj = _curve(params["object_name"])
    previous = getattr(obj.data, field)
    setattr(obj.data, field, params[field])

    def restore() -> None:
        setattr(obj.data, field, previous)

    _record_undo(f"set curve {field}", restore)
    return {field: getattr(obj.data, field)}


def set_spline_property(params: dict[str, Any], field: str, *, param_field: str | None = None) -> dict[str, Any]:
    spline = _spline(_curve(params["object_name"]), params["spline_index"])
    previous = getattr(spline, field)
    public_field = param_field or field
    setattr(spline, field, params[public_field])

    def restore() -> None:
        setattr(spline, field, previous)

    _record_undo(f"set spline {field}", restore)
    return {public_field: getattr(spline, field)}
