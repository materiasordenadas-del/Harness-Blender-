"""Verify that V5 visual capture refuses background mode."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "blender_addon"))

from harness_blender_bridge.operations import dispatch_operation  # noqa: E402


def main() -> None:
    assert bpy.app.background is True
    try:
        dispatch_operation(
            "capture_controlled_view",
            {"view": "front", "focus_object": None, "frame_selected": True},
        )
    except RuntimeError as exc:
        assert "GUI mode" in str(exc)
    else:
        raise AssertionError("capture_controlled_view must require Blender GUI mode")
    print("V5_BACKGROUND_GUI_GUARD_OK")


if __name__ == "__main__":
    main()
