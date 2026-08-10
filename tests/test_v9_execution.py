import pytest

from harness_blender.v9_execution import validate_plan_steps


def test_v9_plan_accepts_only_packet_tools():
    assert validate_plan_steps([{"operation": "move_curve_point", "params": {"point_index": 1}}], ["move_curve_point"]) == [
        {"operation": "move_curve_point", "params": {"point_index": 1}}
    ]


def test_v9_plan_rejects_unreviewed_or_nested_operations():
    with pytest.raises(ValueError, match="TOOL_NOT_ALLOWED"):
        validate_plan_steps([{"operation": "voxel_remesh", "params": {}}], ["move_curve_point"])
    with pytest.raises(ValueError):
        validate_plan_steps([{"operation": "execute_batch", "params": {}}], ["execute_batch"])
