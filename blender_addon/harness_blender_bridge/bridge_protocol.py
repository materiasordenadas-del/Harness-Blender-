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
    "save_blend",
    "undo",
    "capture_screen",
    "create_curve",
    "inspect_curve",
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

    if operation in {"inspect_object", "delete_object", "validate_mesh"}:
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
