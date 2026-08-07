from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "blender_addon"
    / "harness_blender_bridge"
    / "bridge_protocol.py"
)
spec = importlib.util.spec_from_file_location("harness_curve_protocol", MODULE_PATH)
assert spec and spec.loader
bridge_protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_protocol)

TOKEN = "b" * 43


def request(operation: str, params: dict):
    return {"type": "operation", "operation": operation, "params": params, "token": TOKEN}


def parse(operation: str, params: dict):
    return bridge_protocol.parse_operation_request(request(operation, params), TOKEN)


def test_create_curve_normalizes_points():
    operation, params = parse(
        "create_curve",
        {"name": "Aorta", "spline_type": "BEZIER", "points": [[0, 0, 0], [1, 2, 3]]},
    )
    assert operation == "create_curve"
    assert params["points"] == [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]]


@pytest.mark.parametrize(
    ("operation", "params"),
    [
        ("create_curve", {"name": "Bad", "spline_type": "CATMULL", "points": [[0, 0, 0], [1, 0, 0]]}),
        ("create_curve", {"name": "Bad", "spline_type": "POLY", "points": [[0, 0, 0]]}),
        ("set_curve_point_radius", {"object_name": "Aorta", "spline_index": 0, "point_index": 0, "radius": -1}),
        ("set_curve_point_tilt", {"object_name": "Aorta", "spline_index": True, "point_index": 0, "tilt": 0}),
        ("set_curve_bevel_resolution", {"object_name": "Aorta", "bevel_resolution": 33}),
        ("set_curve_resolution", {"object_name": "Aorta", "spline_index": 0, "resolution_u": 0}),
        ("set_curve_cyclic", {"object_name": "Aorta", "spline_index": 0, "cyclic": 1}),
    ],
)
def test_curve_parameter_limits_are_enforced(operation, params):
    with pytest.raises(bridge_protocol.ProtocolError):
        parse(operation, params)


def test_curve_profile_and_geometry_settings_are_normalized():
    _, radius = parse(
        "set_curve_point_radius",
        {"object_name": "Aorta", "spline_index": 0, "point_index": 1, "radius": 0.25},
    )
    _, bevel = parse("set_curve_bevel_depth", {"object_name": "Aorta", "bevel_depth": 0.5})
    _, cyclic = parse("set_curve_cyclic", {"object_name": "Aorta", "spline_index": 0, "cyclic": True})
    assert radius["radius"] == 0.25
    assert bevel["bevel_depth"] == 0.5
    assert cyclic["cyclic"] is True


def test_curve_point_editing_is_normalized():
    _, added = parse("add_curve_point", {"object_name": "Aorta", "spline_index": 0, "co": [1, 2, 3]})
    _, moved = parse(
        "move_curve_point",
        {"object_name": "Aorta", "spline_index": 0, "point_index": 2, "co": [3, 2, 1]},
    )
    _, removed = parse(
        "remove_curve_point", {"object_name": "Aorta", "spline_index": 0, "point_index": 2},
    )
    assert added["co"] == [1.0, 2.0, 3.0]
    assert moved["co"] == [3.0, 2.0, 1.0]
    assert removed["point_index"] == 2


def test_bezier_handle_editing_is_normalized():
    _, handle_type = parse(
        "set_curve_handle_type",
        {"object_name": "Aorta", "spline_index": 0, "point_index": 1, "side": "left", "handle_type": "FREE"},
    )
    _, position = parse(
        "set_curve_handle_position",
        {"object_name": "Aorta", "spline_index": 0, "point_index": 1, "side": "right", "co": [2, 3, 4]},
    )
    assert handle_type["handle_type"] == "FREE"
    assert position["co"] == [2.0, 3.0, 4.0]


@pytest.mark.parametrize(
    ("operation", "params"),
    [
        ("set_curve_handle_type", {"object_name": "Aorta", "spline_index": 0, "point_index": 1, "side": "up", "handle_type": "FREE"}),
        ("set_curve_handle_type", {"object_name": "Aorta", "spline_index": 0, "point_index": 1, "side": "left", "handle_type": "BROKEN"}),
        ("set_curve_handle_position", {"object_name": "Aorta", "spline_index": 0, "point_index": 1, "side": "left", "co": [1, 2]}),
    ],
)
def test_bezier_handle_invalid_values_are_rejected(operation, params):
    with pytest.raises(bridge_protocol.ProtocolError):
        parse(operation, params)
