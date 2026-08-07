# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure-Python request validation for the Blender-side V0 bridge.

This module deliberately imports no ``bpy`` symbols so its security boundary can
be tested with normal Python. The network protocol accepts only a closed set of
semantic operations plus validated parameters; Python source code is never a
valid request field.
"""

from __future__ import annotations

import math
import os
import secrets
from typing import Any

ALLOWED_PRIMITIVES = {"cube", "uv_sphere", "cylinder", "cone", "torus"}
ALLOWED_OPERATIONS = {
    "ping",
    "inspect_scene",
    "inspect_object",
    "create_primitive",
    "transform_object",
    "delete_object",
    "validate_mesh",
    "inspect_mesh_detailed",
    "recalculate_normals",
    "flip_normals",
    "subdivide_mesh",
    "smooth_mesh",
    "create_material", "assign_material", "set_base_color", "set_roughness", "set_metallic", "set_alpha",
    "add_modifier",
    "save_blend",
    "undo",
    "capture_screen",
    "create_curve",
    "inspect_curve",
    "add_curve_point",
    "move_curve_point",
    "remove_curve_point",
    "set_curve_handle_type",
    "set_curve_handle_position",
    "subdivide_curve",
    "resample_curve",
    "convert_curve_to_mesh",
    "set_curve_point_radius",
    "set_curve_point_tilt",
    "set_curve_bevel_depth",
    "set_curve_bevel_resolution",
    "set_curve_resolution",
    "set_curve_cyclic",
}
MAX_NAME_LENGTH = 255
MAX_ABS_COORDINATE = 1_000_000.0
MAX_ABS_SCALE = 10_000.0
MAX_PATH_LENGTH = 4096


class ProtocolError(ValueError):
    """The request is malformed or outside the V0 contract."""


class AuthenticationError(PermissionError):
    """The request did not present the active bridge token."""


def _reject_unknown_keys(value: dict[str, Any], allowed: set[str], *, where: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ProtocolError(f"Unknown {where} field(s): {', '.join(sorted(unknown))}")


def _name(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ProtocolError(f"{field} must be a string")
    if not value or len(value) > MAX_NAME_LENGTH or "\0" in value:
        raise ProtocolError(f"{field} must contain 1-{MAX_NAME_LENGTH} characters and no NUL byte")
    return value


def _vec3(value: Any, field: str, *, scale: bool = False) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ProtocolError(f"{field} must contain exactly three numbers")
    limit = MAX_ABS_SCALE if scale else MAX_ABS_COORDINATE
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ProtocolError(f"{field} must contain only numbers")
        number = float(item)
        if not math.isfinite(number) or abs(number) > limit:
            raise ProtocolError(f"{field} values must be finite and within ±{limit:g}")
        result.append(number)
    return result


def _number(value: Any, field: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ProtocolError(f"{field} must be finite and between {minimum:g} and {maximum:g}")
    return number


def _integer(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ProtocolError(f"{field} must be an integer between {minimum} and {maximum}")
    return value


def _curve_point_target(params: dict[str, Any], operation: str, value_field: str) -> dict[str, Any]:
    allowed = {"object_name", "spline_index", "point_index", value_field}
    _reject_unknown_keys(params, allowed, where=f"{operation} parameter")
    if not all(key in params for key in allowed):
        raise ProtocolError(f"{operation} requires object_name, spline_index, point_index and {value_field}")
    return {
        "object_name": _name(params["object_name"], "object_name"),
        "spline_index": _integer(params["spline_index"], "spline_index", minimum=0, maximum=255),
        "point_index": _integer(params["point_index"], "point_index", minimum=0, maximum=4095),
    }


def _no_params(params: dict[str, Any], operation: str) -> dict[str, Any]:
    _reject_unknown_keys(params, set(), where=f"{operation} parameter")
    return {}


def validate_operation_params(operation: str, params: Any) -> dict[str, Any]:
    """Validate and normalize one V0 operation payload."""
    if operation not in ALLOWED_OPERATIONS:
        raise ProtocolError(f"Operation is not allowed in V0: {operation!r}")
    if not isinstance(params, dict):
        raise ProtocolError("params must be a JSON object")

    if operation in {"ping", "inspect_scene", "undo", "capture_screen"}:
        return _no_params(params, operation)

    if operation in {"inspect_object", "delete_object", "validate_mesh", "inspect_mesh_detailed"}:
        _reject_unknown_keys(params, {"object_name"}, where=f"{operation} parameter")
        if "object_name" not in params:
            raise ProtocolError(f"{operation} requires object_name")
        return {"object_name": _name(params["object_name"], "object_name")}

    if operation == "create_primitive":
        allowed = {"primitive", "name", "location", "scale"}
        _reject_unknown_keys(params, allowed, where="create_primitive parameter")
        if "primitive" not in params or "name" not in params:
            raise ProtocolError("create_primitive requires primitive and name")
        primitive = params["primitive"]
        if not isinstance(primitive, str) or primitive not in ALLOWED_PRIMITIVES:
            raise ProtocolError(f"Unsupported primitive: {primitive!r}")
        return {
            "primitive": primitive,
            "name": _name(params["name"], "name"),
            "location": _vec3(params.get("location", [0, 0, 0]), "location"),
            "scale": _vec3(params.get("scale", [1, 1, 1]), "scale", scale=True),
        }

    if operation == "transform_object":
        allowed = {"object_name", "location", "rotation_degrees", "scale"}
        _reject_unknown_keys(params, allowed, where="transform_object parameter")
        if "object_name" not in params:
            raise ProtocolError("transform_object requires object_name")
        if all(key not in params for key in ("location", "rotation_degrees", "scale")):
            raise ProtocolError("transform_object requires at least one transform field")
        normalized: dict[str, Any] = {"object_name": _name(params["object_name"], "object_name")}
        if "location" in params:
            normalized["location"] = _vec3(params["location"], "location")
        if "rotation_degrees" in params:
            normalized["rotation_degrees"] = _vec3(params["rotation_degrees"], "rotation_degrees")
        if "scale" in params:
            normalized["scale"] = _vec3(params["scale"], "scale", scale=True)
        return normalized

    if operation == "save_blend":
        _reject_unknown_keys(params, {"filepath"}, where="save_blend parameter")
        filepath = params.get("filepath")
        if filepath is None:
            return {"filepath": None}
        if not isinstance(filepath, str) or not filepath or len(filepath) > MAX_PATH_LENGTH:
            raise ProtocolError("filepath must be a non-empty absolute path")
        if not os.path.isabs(filepath):
            raise ProtocolError("filepath must be absolute")
        if not filepath.lower().endswith(".blend"):
            raise ProtocolError("filepath must end in .blend")
        return {"filepath": filepath}

    if operation == "create_curve":
        _reject_unknown_keys(params, {"name", "spline_type", "points"}, where="create_curve parameter")
        if not all(key in params for key in ("name", "spline_type", "points")):
            raise ProtocolError("create_curve requires name, spline_type and points")
        if params["spline_type"] not in {"BEZIER", "NURBS", "POLY"}:
            raise ProtocolError("spline_type must be BEZIER, NURBS or POLY")
        points = params["points"]
        if not isinstance(points, list) or not 2 <= len(points) <= 256:
            raise ProtocolError("points must contain 2-256 coordinates")
        return {"name": _name(params["name"], "name"), "spline_type": params["spline_type"],
                "points": [_vec3(point, "points item") for point in points]}

    if operation == "inspect_curve":
        _reject_unknown_keys(params, {"object_name"}, where="inspect_curve parameter")
        if "object_name" not in params:
            raise ProtocolError("inspect_curve requires object_name")
        return {"object_name": _name(params["object_name"], "object_name")}

    if operation == "recalculate_normals":
        _reject_unknown_keys(params, {"object_name", "outward"}, where="recalculate_normals parameter")
        if "object_name" not in params or not isinstance(params.get("outward", True), bool):
            raise ProtocolError("recalculate_normals requires object_name and boolean outward")
        return {"object_name": _name(params["object_name"], "object_name"), "outward": params.get("outward", True)}

    if operation == "flip_normals":
        _reject_unknown_keys(params, {"object_name"}, where="flip_normals parameter")
        if "object_name" not in params:
            raise ProtocolError("flip_normals requires object_name")
        return {"object_name": _name(params["object_name"], "object_name")}

    if operation == "subdivide_mesh":
        _reject_unknown_keys(params, {"object_name", "cuts"}, where="subdivide_mesh parameter")
        if "object_name" not in params or "cuts" not in params:
            raise ProtocolError("subdivide_mesh requires object_name and cuts")
        return {"object_name": _name(params["object_name"], "object_name"), "cuts": _integer(params["cuts"], "cuts", minimum=1, maximum=4)}

    if operation == "smooth_mesh":
        _reject_unknown_keys(params, {"object_name", "factor"}, where="smooth_mesh parameter")
        if "object_name" not in params or "factor" not in params:
            raise ProtocolError("smooth_mesh requires object_name and factor")
        return {"object_name": _name(params["object_name"], "object_name"), "factor": _number(params["factor"], "factor", minimum=0.0, maximum=1.0)}

    if operation == "create_material":
        _reject_unknown_keys(params, {"name"}, where="create_material parameter")
        return {"name": _name(params.get("name"), "name")}
    if operation == "assign_material":
        _reject_unknown_keys(params, {"object_name", "material_name"}, where="assign_material parameter")
        return {"object_name": _name(params.get("object_name"), "object_name"), "material_name": _name(params.get("material_name"), "material_name")}
    if operation == "set_base_color":
        _reject_unknown_keys(params, {"material_name", "base_color"}, where="set_base_color parameter")
        color = params.get("base_color")
        if not isinstance(color, list) or len(color) != 4:
            raise ProtocolError("base_color must contain four numbers")
        return {"material_name": _name(params.get("material_name"), "material_name"), "base_color": [_number(value, "base_color", minimum=0, maximum=1) for value in color]}
    if operation in {"set_roughness", "set_metallic", "set_alpha"}:
        field = operation.removeprefix("set_")
        _reject_unknown_keys(params, {"material_name", field}, where=f"{operation} parameter")
        return {"material_name": _name(params.get("material_name"), "material_name"), field: _number(params.get(field), field, minimum=0, maximum=1)}
    if operation == "add_modifier":
        _reject_unknown_keys(params, {"object_name", "name", "modifier_type"}, where="add_modifier parameter")
        allowed = {"SUBSURF", "SOLIDIFY", "SHRINKWRAP", "SMOOTH", "LAPLACIANSMOOTH", "DECIMATE", "REMESH", "BOOLEAN"}
        if params.get("modifier_type") not in allowed:
            raise ProtocolError("modifier_type is not in the V2 allowlist")
        return {"object_name": _name(params.get("object_name"), "object_name"), "name": _name(params.get("name"), "name"), "modifier_type": params["modifier_type"]}

    if operation in {"add_curve_point", "move_curve_point", "remove_curve_point"}:
        allowed = {"object_name", "spline_index", "point_index", "co"}
        if operation == "add_curve_point":
            allowed.remove("point_index")
        elif operation == "remove_curve_point":
            allowed.remove("co")
        _reject_unknown_keys(params, allowed, where=f"{operation} parameter")
        if not all(key in params for key in allowed):
            raise ProtocolError(f"{operation} requires {', '.join(sorted(allowed))}")
        normalized = {
            "object_name": _name(params["object_name"], "object_name"),
            "spline_index": _integer(params["spline_index"], "spline_index", minimum=0, maximum=255),
        }
        if operation != "add_curve_point":
            normalized["point_index"] = _integer(params["point_index"], "point_index", minimum=0, maximum=4095)
        if operation != "remove_curve_point":
            normalized["co"] = _vec3(params["co"], "co")
        return normalized

    if operation in {"set_curve_handle_type", "set_curve_handle_position"}:
        allowed = {"object_name", "spline_index", "point_index", "side"}
        allowed.add("handle_type" if operation == "set_curve_handle_type" else "co")
        _reject_unknown_keys(params, allowed, where=f"{operation} parameter")
        if not all(key in params for key in allowed):
            raise ProtocolError(f"{operation} requires {', '.join(sorted(allowed))}")
        if params["side"] not in {"left", "right"}:
            raise ProtocolError("side must be left or right")
        normalized = {
            "object_name": _name(params["object_name"], "object_name"),
            "spline_index": _integer(params["spline_index"], "spline_index", minimum=0, maximum=255),
            "point_index": _integer(params["point_index"], "point_index", minimum=0, maximum=4095),
            "side": params["side"],
        }
        if operation == "set_curve_handle_type":
            if params["handle_type"] not in {"AUTO", "ALIGNED", "FREE", "VECTOR"}:
                raise ProtocolError("handle_type must be AUTO, ALIGNED, FREE or VECTOR")
            normalized["handle_type"] = params["handle_type"]
        else:
            normalized["co"] = _vec3(params["co"], "co")
        return normalized

    if operation == "subdivide_curve":
        _reject_unknown_keys(params, {"object_name", "spline_index", "cuts"}, where="subdivide_curve parameter")
        if not all(key in params for key in ("object_name", "spline_index", "cuts")):
            raise ProtocolError("subdivide_curve requires object_name, spline_index and cuts")
        return {
            "object_name": _name(params["object_name"], "object_name"),
            "spline_index": _integer(params["spline_index"], "spline_index", minimum=0, maximum=255),
            "cuts": _integer(params["cuts"], "cuts", minimum=1, maximum=16),
        }

    if operation == "resample_curve":
        _reject_unknown_keys(params, {"object_name", "spline_index", "point_count"}, where="resample_curve parameter")
        if not all(key in params for key in ("object_name", "spline_index", "point_count")):
            raise ProtocolError("resample_curve requires object_name, spline_index and point_count")
        return {
            "object_name": _name(params["object_name"], "object_name"),
            "spline_index": _integer(params["spline_index"], "spline_index", minimum=0, maximum=255),
            "point_count": _integer(params["point_count"], "point_count", minimum=2, maximum=256),
        }

    if operation == "convert_curve_to_mesh":
        _reject_unknown_keys(params, {"object_name", "mesh_name"}, where="convert_curve_to_mesh parameter")
        if "object_name" not in params or "mesh_name" not in params:
            raise ProtocolError("convert_curve_to_mesh requires object_name and mesh_name")
        return {
            "object_name": _name(params["object_name"], "object_name"),
            "mesh_name": _name(params["mesh_name"], "mesh_name"),
        }

    if operation == "set_curve_point_radius":
        normalized = _curve_point_target(params, operation, "radius")
        normalized["radius"] = _number(params["radius"], "radius", minimum=0.0, maximum=MAX_ABS_SCALE)
        return normalized

    if operation == "set_curve_point_tilt":
        normalized = _curve_point_target(params, operation, "tilt")
        normalized["tilt"] = _number(
            params["tilt"], "tilt", minimum=-MAX_ABS_COORDINATE, maximum=MAX_ABS_COORDINATE
        )
        return normalized

    if operation == "set_curve_bevel_depth":
        _reject_unknown_keys(params, {"object_name", "bevel_depth"}, where="set_curve_bevel_depth parameter")
        if "object_name" not in params or "bevel_depth" not in params:
            raise ProtocolError("set_curve_bevel_depth requires object_name and bevel_depth")
        return {
            "object_name": _name(params["object_name"], "object_name"),
            "bevel_depth": _number(params["bevel_depth"], "bevel_depth", minimum=0.0, maximum=MAX_ABS_SCALE),
        }

    if operation == "set_curve_bevel_resolution":
        _reject_unknown_keys(params, {"object_name", "bevel_resolution"}, where="set_curve_bevel_resolution parameter")
        if "object_name" not in params or "bevel_resolution" not in params:
            raise ProtocolError("set_curve_bevel_resolution requires object_name and bevel_resolution")
        return {
            "object_name": _name(params["object_name"], "object_name"),
            "bevel_resolution": _integer(params["bevel_resolution"], "bevel_resolution", minimum=0, maximum=32),
        }

    if operation == "set_curve_resolution":
        _reject_unknown_keys(params, {"object_name", "spline_index", "resolution_u"}, where="set_curve_resolution parameter")
        if not all(key in params for key in ("object_name", "spline_index", "resolution_u")):
            raise ProtocolError("set_curve_resolution requires object_name, spline_index and resolution_u")
        return {
            "object_name": _name(params["object_name"], "object_name"),
            "spline_index": _integer(params["spline_index"], "spline_index", minimum=0, maximum=255),
            "resolution_u": _integer(params["resolution_u"], "resolution_u", minimum=1, maximum=1024),
        }

    if operation == "set_curve_cyclic":
        _reject_unknown_keys(params, {"object_name", "spline_index", "cyclic"}, where="set_curve_cyclic parameter")
        if not all(key in params for key in ("object_name", "spline_index", "cyclic")):
            raise ProtocolError("set_curve_cyclic requires object_name, spline_index and cyclic")
        if not isinstance(params["cyclic"], bool):
            raise ProtocolError("cyclic must be a boolean")
        return {
            "object_name": _name(params["object_name"], "object_name"),
            "spline_index": _integer(params["spline_index"], "spline_index", minimum=0, maximum=255),
            "cyclic": params["cyclic"],
        }

    raise ProtocolError(f"Unhandled V0 operation: {operation}")


def parse_operation_request(payload: Any, expected_token: str) -> tuple[str, dict[str, Any]]:
    """Authenticate and normalize one socket request."""
    if not expected_token:
        raise AuthenticationError("Bridge token is not initialized")
    if not isinstance(payload, dict):
        raise ProtocolError("Request must be a JSON object")
    _reject_unknown_keys(payload, {"type", "operation", "params", "token"}, where="request")
    if payload.get("type") != "operation":
        raise ProtocolError("Request type must be 'operation'")
    supplied_token = payload.get("token")
    if not isinstance(supplied_token, str) or not secrets.compare_digest(supplied_token, expected_token):
        raise AuthenticationError("Invalid Harness Blender bridge token")
    operation = payload.get("operation")
    if not isinstance(operation, str):
        raise ProtocolError("operation must be a string")
    return operation, validate_operation_params(operation, payload.get("params", {}))
