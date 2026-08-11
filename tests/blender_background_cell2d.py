"""Run with Blender in background mode to validate the real Cell2D bridge operation."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "blender_addon"))

from harness_blender_bridge.operations import dispatch_operation  # noqa: E402


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = dispatch_operation("create_cell2d_symbol", {
        "object_name": "Cell2D_AQP2_001", "asset_id": "aqp2", "visual_category": "ion_channel",
        "domain": "apical", "anchor": "apical:u=0.4", "bounds": [1.0, 2.0, 3.0, 1.0], "shape_family": "membrane_capsule",
        "material": "membrane_protein", "color": "#F4C542", "z": 0.3,
        "reference_id": "ref_background", "source_observation_id": "observation_1",
    })
    obj = bpy.data.objects["Cell2D_AQP2_001"]
    assert result["collection"] == "Cell2D"
    assert obj.type == "MESH"
    assert obj["hb_asset_id"] == "aqp2"
    assert obj["hb_domain"] == "apical"
    assert obj["hb_anchor"] == "apical:u=0.4"
    assert obj.location.z == 0.0
    assert all(abs(vertex.co.z - 0.3) < 1e-6 for vertex in obj.data.vertices)
    dispatch_operation("undo", {})
    assert bpy.data.objects.get("Cell2D_AQP2_001") is None
    print("HARNESS_BLENDER_CELL2D_BACKGROUND_OK")


if __name__ == "__main__":
    main()
