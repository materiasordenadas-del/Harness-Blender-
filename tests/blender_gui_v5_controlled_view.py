"""Run inside Blender GUI to prove V5 captures a real controlled PNG."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "blender_addon"))

from harness_blender_bridge.operations import dispatch_operation  # noqa: E402


def run() -> None:
    try:
        bpy.ops.mesh.primitive_cube_add(size=2)
        cube = bpy.context.object
        cube.name = "V5_GUI_Cube"
        previous_active = bpy.context.view_layer.objects.active
        previous_selected = tuple(bpy.context.selected_objects)
        result = dispatch_operation(
            "capture_controlled_view",
            {"view": "front", "focus_object": cube.name, "frame_selected": True},
        )
        image = base64.b64decode(result["png_base64"], validate=True)
        assert image.startswith(b"\x89PNG\r\n\x1a\n")
        assert result["view"] == "front"
        assert result["focus_object"] == cube.name
        assert tuple(bpy.context.selected_objects) == previous_selected
        assert bpy.context.view_layer.objects.active == previous_active
        print("V5_GUI_CONTROLLED_VIEW_OK")
    finally:
        bpy.ops.wm.quit_blender()


bpy.app.timers.register(run, first_interval=1.0)
