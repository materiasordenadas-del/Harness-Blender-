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
