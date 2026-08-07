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

    print("HARNESS_BLENDER_BACKGROUND_INTEGRATION_OK")


if __name__ == "__main__":
    main()
