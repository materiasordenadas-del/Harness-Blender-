"""Run with Blender 5.1+ in background mode.

Example:
    blender --background --factory-startup --python tests/blender_background_integration.py

This is intentionally not a pytest test because it requires Blender's Python
runtime. It exercises the actual V0 operation implementations, including delete
followed by Blender undo. GUI screenshot remains a manual acceptance test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "blender_addon"))

from harness_blender_bridge.operations import dispatch_operation  # noqa: E402


def assert_close(actual, expected, tolerance=1e-6):
    if len(actual) != len(expected):
        raise AssertionError((actual, expected))
    for left, right in zip(actual, expected):
        if abs(float(left) - float(right)) > tolerance:
            raise AssertionError((actual, expected))


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.use_global_undo = True

    ping = dispatch_operation("ping", {})
    assert ping["status"] == "ready"
    assert ping["background"] is True

    initial = dispatch_operation("inspect_scene", {})
    assert initial["object_count"] == 0

    created = dispatch_operation(
        "create_primitive",
        {
            "primitive": "cube",
            "name": "V0_Background_Test",
            "location": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
    )
    assert created["name"] == "V0_Background_Test"

    transformed = dispatch_operation(
        "transform_object",
        {
            "object_name": "V0_Background_Test",
            "location": [2.0, 0.0, 1.0],
            "rotation_degrees": [0.0, 0.0, 45.0],
            "scale": [1.0, 2.0, 1.0],
        },
    )
    assert_close(transformed["location"], [2.0, 0.0, 1.0])
    assert_close(transformed["scale"], [1.0, 2.0, 1.0])

    inspected = dispatch_operation("inspect_object", {"object_name": "V0_Background_Test"})
    assert_close(inspected["location"], [2.0, 0.0, 1.0])

    validation = dispatch_operation("validate_mesh", {"object_name": "V0_Background_Test"})
    assert validation["boundary_edges"] == 0
    assert validation["non_manifold_edges"] == 0
    assert validation["loose_edges"] == 0
    assert validation["is_closed_manifold"] is True

    deleted = dispatch_operation("delete_object", {"object_name": "V0_Background_Test"})
    assert deleted["undoable"] is True
    assert bpy.data.objects.get("V0_Background_Test") is None

    dispatch_operation("undo", {})
    restored = bpy.data.objects.get("V0_Background_Test")
    if restored is None:
        raise AssertionError("undo did not restore the object deleted by delete_object")

    curve = dispatch_operation(
        "create_curve",
        {
            "name": "V1_Background_Curve",
            "spline_type": "BEZIER",
            "points": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.5], [2.0, 1.0, 0.0]],
        },
    )
    assert curve == {"name": "V1_Background_Curve", "type": "CURVE", "spline_type": "BEZIER", "point_count": 3}
    changed_handle_type = dispatch_operation(
        "set_curve_handle_type",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "point_index": 1, "side": "right", "handle_type": "FREE"},
    )
    assert changed_handle_type == {"side": "right", "handle_type": "FREE"}
    changed_handle_position = dispatch_operation(
        "set_curve_handle_position",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "point_index": 1, "side": "right", "co": [1.5, 0.5, 0.5]},
    )
    assert_close(changed_handle_position["co"], [1.5, 0.5, 0.5])
    added = dispatch_operation(
        "add_curve_point",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "co": [3.0, 1.0, 0.0]},
    )
    assert added == {"point_index": 3, "point_count": 4}
    moved = dispatch_operation(
        "move_curve_point",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "point_index": 3, "co": [3.0, 2.0, 0.0]},
    )
    assert_close(moved["co"], [3.0, 2.0, 0.0])
    removed = dispatch_operation(
        "remove_curve_point",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "point_index": 3},
    )
    assert removed == {"removed_index": 3, "point_count": 3}
    dispatch_operation("undo", {})
    undo_removed_curve = dispatch_operation("inspect_curve", {"object_name": "V1_Background_Curve"})
    assert undo_removed_curve["splines"][0]["point_count"] == 4
    dispatch_operation("undo", {})
    undo_moved_curve = dispatch_operation("inspect_curve", {"object_name": "V1_Background_Curve"})
    assert_close(undo_moved_curve["splines"][0]["points"][3]["co"][:3], [3.0, 1.0, 0.0])
    dispatch_operation("undo", {})
    undo_added_curve = dispatch_operation("inspect_curve", {"object_name": "V1_Background_Curve"})
    assert undo_added_curve["splines"][0]["point_count"] == 3
    dispatch_operation(
        "set_curve_point_radius",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "point_index": 1, "radius": 0.4},
    )
    dispatch_operation(
        "set_curve_point_tilt",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "point_index": 1, "tilt": 0.25},
    )
    dispatch_operation("set_curve_bevel_depth", {"object_name": "V1_Background_Curve", "bevel_depth": 0.1})
    dispatch_operation("set_curve_bevel_resolution", {"object_name": "V1_Background_Curve", "bevel_resolution": 3})
    dispatch_operation(
        "set_curve_resolution",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "resolution_u": 16},
    )
    dispatch_operation(
        "set_curve_cyclic",
        {"object_name": "V1_Background_Curve", "spline_index": 0, "cyclic": True},
    )
    inspected_curve = dispatch_operation("inspect_curve", {"object_name": "V1_Background_Curve"})
    spline = inspected_curve["splines"][0]
    assert_close([inspected_curve["bevel_depth"]], [0.1])
    assert inspected_curve["bevel_resolution"] == 3
    assert spline["cyclic"] is True
    assert spline["resolution_u"] == 16
    assert_close([spline["points"][1]["radius"]], [0.4])
    assert_close([spline["points"][1]["tilt"]], [0.25])

    print("HARNESS_BLENDER_BACKGROUND_INTEGRATION_OK")


if __name__ == "__main__":
    main()
