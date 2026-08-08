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
spec = importlib.util.spec_from_file_location("harness_bridge_protocol", MODULE_PATH)
assert spec and spec.loader
bridge_protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_protocol)

TOKEN = "a" * 43


def request(operation: str, params=None, **extra):
    payload = {
        "type": "operation",
        "operation": operation,
        "params": params or {},
        "token": TOKEN,
    }
    payload.update(extra)
    return payload


def test_wrong_token_is_rejected():
    payload = request("ping")
    payload["token"] = "wrong-token"
    with pytest.raises(bridge_protocol.AuthenticationError):
        bridge_protocol.parse_operation_request(payload, TOKEN)


def test_arbitrary_code_field_is_rejected_even_with_valid_token():
    payload = request("ping", code="import os; os.remove('anything')")
    with pytest.raises(bridge_protocol.ProtocolError, match="Unknown request field"):
        bridge_protocol.parse_operation_request(payload, TOKEN)


def test_unknown_operation_is_rejected():
    with pytest.raises(bridge_protocol.ProtocolError, match="not allowed"):
        bridge_protocol.parse_operation_request(request("execute_python"), TOKEN)


def test_create_primitive_is_normalized():
    operation, params = bridge_protocol.parse_operation_request(
        request("create_primitive", {"primitive": "cube", "name": "SafeCube"}),
        TOKEN,
    )
    assert operation == "create_primitive"
    assert params["location"] == [0.0, 0.0, 0.0]
    assert params["scale"] == [1.0, 1.0, 1.0]


@pytest.mark.parametrize(
    "bad_vector",
    ([1, 2], [1, 2, 3, 4], [1, float("inf"), 3], [1, True, 3], [1e20, 0, 0]),
)
def test_vector_limits_are_enforced(bad_vector):
    with pytest.raises(bridge_protocol.ProtocolError):
        bridge_protocol.parse_operation_request(
            request(
                "create_primitive",
                {"primitive": "cube", "name": "Cube", "location": bad_vector},
            ),
            TOKEN,
        )


def test_transform_requires_a_transform_field():
    with pytest.raises(bridge_protocol.ProtocolError, match="at least one"):
        bridge_protocol.parse_operation_request(
            request("transform_object", {"object_name": "Cube"}), TOKEN
        )


def test_unknown_operation_parameter_is_rejected():
    with pytest.raises(bridge_protocol.ProtocolError, match="Unknown create_primitive parameter"):
        bridge_protocol.parse_operation_request(
            request(
                "create_primitive",
                {"primitive": "cube", "name": "Cube", "shell_command": "whoami"},
            ),
            TOKEN,
        )


def test_save_requires_absolute_blend_path():
    with pytest.raises(bridge_protocol.ProtocolError, match="absolute"):
        bridge_protocol.parse_operation_request(
            request("save_blend", {"filepath": "relative/test.blend"}), TOKEN
        )


def test_all_declared_operations_have_validation_paths():
    simple = {"ping", "inspect_scene", "undo", "capture_screen"}
    for operation in simple:
        parsed, params = bridge_protocol.parse_operation_request(request(operation), TOKEN)
        assert parsed == operation
        assert params == {}


def test_controlled_view_is_closed_and_normalized():
    operation, params = bridge_protocol.parse_operation_request(
        request("capture_controlled_view", {"view": "top", "focus_object": "Vessel", "frame_selected": True}), TOKEN
    )
    assert operation == "capture_controlled_view"
    assert params == {"view": "top", "focus_object": "Vessel", "frame_selected": True}


def test_controlled_view_rejects_unknown_view_and_extra_fields():
    with pytest.raises(bridge_protocol.ProtocolError, match="view must be"):
        bridge_protocol.parse_operation_request(request("capture_controlled_view", {"view": "diagonal"}), TOKEN)
    with pytest.raises(bridge_protocol.ProtocolError, match="Unknown capture_controlled_view parameter"):
        bridge_protocol.parse_operation_request(request("capture_controlled_view", {"unsafe": True}), TOKEN)


def test_procedural_tube_setup_is_typed_and_bounded():
    operation, params = bridge_protocol.parse_operation_request(
        request("create_procedural_tube_setup", {
            "object_name": "Vessel", "group_name": "Vessel Tube", "profile_radius": 0.2, "resample_length": 0.5,
        }), TOKEN,
    )
    assert operation == "create_procedural_tube_setup"
    assert params["profile_radius"] == 0.2
    with pytest.raises(bridge_protocol.ProtocolError, match="between"):
        bridge_protocol.parse_operation_request(
            request("create_procedural_tube_setup", {"object_name": "Vessel", "group_name": "Bad", "profile_radius": 0, "resample_length": 0.5}), TOKEN,
        )


def test_surface_scatter_setup_requires_distinct_objects_and_bounded_density():
    operation, params = bridge_protocol.parse_operation_request(
        request("create_surface_scatter_setup", {"surface_object_name": "Surface", "instance_object_name": "Pebble", "group_name": "Scatter", "density": 2.5}), TOKEN
    )
    assert operation == "create_surface_scatter_setup"
    assert params["density"] == 2.5
    with pytest.raises(bridge_protocol.ProtocolError, match="must differ"):
        bridge_protocol.parse_operation_request(request("create_surface_scatter_setup", {"surface_object_name": "Surface", "instance_object_name": "Surface", "group_name": "Scatter", "density": 2.5}), TOKEN)


def test_procedural_branching_requires_distinct_curve_names():
    operation, params = bridge_protocol.parse_operation_request(request("create_procedural_branching_setup", {"main_curve_name": "Main", "branch_curve_names": ["Branch"], "group_name": "Branches", "profile_radius": 0.1, "resample_length": 0.2}), TOKEN)
    assert operation == "create_procedural_branching_setup"
    assert params["branch_curve_names"] == ["Branch"]


def test_plane_split_is_typed_and_rejects_zero_normal():
    operation, params = bridge_protocol.parse_operation_request(request("split_mesh_by_plane", {"object_name": "Source", "plane_point": [0, 0, 0], "plane_normal": [1, 0, 0], "positive_name": "Left", "negative_name": "Right"}), TOKEN)
    assert operation == "split_mesh_by_plane"
    assert params["cap"] is True
    with pytest.raises(bridge_protocol.ProtocolError, match="must not be zero"):
        bridge_protocol.parse_operation_request(request("split_mesh_by_plane", {"object_name": "Source", "plane_point": [0, 0, 0], "plane_normal": [0, 0, 0], "positive_name": "Left", "negative_name": "Right"}), TOKEN)


def test_asset_readiness_is_typed_and_rejects_extra_fields():
    operation, params = bridge_protocol.parse_operation_request(
        request("evaluate_asset_readiness", {"object_name": "Asset"}), TOKEN
    )
    assert operation == "evaluate_asset_readiness"
    assert params == {"object_name": "Asset"}
    with pytest.raises(bridge_protocol.ProtocolError, match="Unknown evaluate_asset_readiness parameter"):
        bridge_protocol.parse_operation_request(
            request("evaluate_asset_readiness", {"object_name": "Asset", "apply": True}), TOKEN
        )


def test_uv_inspection_is_typed_and_read_only():
    operation, params = bridge_protocol.parse_operation_request(
        request("inspect_uv", {"object_name": "Asset"}), TOKEN
    )
    assert operation == "inspect_uv"
    assert params == {"object_name": "Asset"}
    with pytest.raises(bridge_protocol.ProtocolError, match="Unknown inspect_uv parameter"):
        bridge_protocol.parse_operation_request(
            request("inspect_uv", {"object_name": "Asset", "create": True}), TOKEN
        )


def test_uv_layout_evaluation_is_typed_and_read_only():
    assert bridge_protocol.parse_operation_request(request("evaluate_uv_layout", {"object_name": "Asset"}), TOKEN) == ("evaluate_uv_layout", {"object_name": "Asset"})


def test_uv_unwrap_has_bounded_typed_parameters():
    operation, params = bridge_protocol.parse_operation_request(
        request("unwrap_uv", {"object_name": "Asset", "method": "CONFORMAL", "margin": 0.02}), TOKEN
    )
    assert operation == "unwrap_uv"
    assert params == {"object_name": "Asset", "method": "CONFORMAL", "margin": 0.02}
    with pytest.raises(bridge_protocol.ProtocolError, match="ANGLE_BASED or CONFORMAL"):
        bridge_protocol.parse_operation_request(request("unwrap_uv", {"object_name": "Asset", "method": "SMART_PROJECT"}), TOKEN)


def test_sculpt_smooth_region_is_bounded_and_explicit():
    operation, params = bridge_protocol.parse_operation_request(request("sculpt_smooth_region", {"object_name": "Asset", "vertex_indices": [0, 1], "factor": 0.4, "iterations": 2}), TOKEN)
    assert operation == "sculpt_smooth_region"
    assert params["vertex_indices"] == [0, 1]
    with pytest.raises(bridge_protocol.ProtocolError, match="distinct"):
        bridge_protocol.parse_operation_request(request("sculpt_smooth_region", {"object_name": "Asset", "vertex_indices": [0, 0]}), TOKEN)
