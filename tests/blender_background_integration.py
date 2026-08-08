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
    subdivided = dispatch_operation(
        "subdivide_curve", {"object_name": "V1_Background_Curve", "spline_index": 0, "cuts": 1},
    )
    assert subdivided == {"point_count": 5, "cuts": 1}
    resampled = dispatch_operation(
        "resample_curve", {"object_name": "V1_Background_Curve", "spline_index": 0, "point_count": 4},
    )
    assert resampled == {"point_count": 4}
    converted = dispatch_operation(
        "convert_curve_to_mesh", {"object_name": "V1_Background_Curve", "mesh_name": "V1_Background_Mesh"},
    )
    assert converted["source"] == "V1_Background_Curve"
    assert converted["vertices"] > 0
    assert bpy.data.objects["V1_Background_Curve"].type == "CURVE"
    assert bpy.data.objects["V1_Background_Mesh"].type == "MESH"
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
    tubular = dispatch_operation("evaluate_tubular", {"object_name": "V1_Background_Curve", "spline_index": 0})
    assert tubular["point_count"] == 4
    assert tubular["maximum_thickness"] >= tubular["minimum_thickness"]

    bpy.ops.mesh.primitive_cube_add()
    merge_mesh = bpy.context.object
    merge_mesh.name = "V2_Merge_Test"
    original_vertex_count = len(merge_mesh.data.vertices)
    dispatch_operation("merge_vertices", {"object_name": merge_mesh.name, "vertex_indices": [0, 1]})
    assert len(merge_mesh.data.vertices) == original_vertex_count - 1
    dispatch_operation("undo", {})
    assert len(merge_mesh.data.vertices) == original_vertex_count

    loop_data = bpy.data.meshes.new("V2_Bridge_Test")
    loop_data.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
        [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4)],
        [],
    )
    loop_object = bpy.data.objects.new("V2_Bridge_Test", loop_data)
    bpy.context.scene.collection.objects.link(loop_object)
    bridged = dispatch_operation("bridge_edge_loops", {"object_name": loop_object.name, "edge_indices": list(range(8))})
    assert bridged["faces_created"] == 4
    dispatch_operation("undo", {})
    assert len(loop_data.polygons) == 0

    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    evaluated_mesh = bpy.context.object
    evaluated_mesh.name = "V4_Evaluated_Mesh"
    mesh_report = dispatch_operation("evaluate_mesh", {"object_name": evaluated_mesh.name})
    assert mesh_report["is_closed_manifold"] is True
    assert_close([mesh_report["surface_area"], mesh_report["volume"]], [24.0, 8.0])
    assert mesh_report["self_intersections"] == 0
    assert mesh_report["inconsistent_normal_edges"] == 0

    bpy.ops.mesh.primitive_cube_add(size=2, location=(4, 0, 0))
    target_mesh = bpy.context.object
    target_mesh.name = "V4_Penetration_Target"
    separated = dispatch_operation("evaluate_penetration", {"object_name": evaluated_mesh.name, "target_object_name": target_mesh.name})
    assert separated["penetrates"] is False
    target_mesh.location.x = 0.5
    bpy.context.view_layer.update()
    overlapping = dispatch_operation("evaluate_penetration", {"object_name": evaluated_mesh.name, "target_object_name": target_mesh.name})
    assert overlapping["penetrates"] is True
    spatial = dispatch_operation("evaluate_spatial", {"object_name": evaluated_mesh.name, "target_object_name": target_mesh.name})
    assert spatial["bounding_box_overlap"] is True
    assert_close([spatial["distance"]], [0.0])

    v6_setup = dispatch_operation("create_procedural_tube_setup", {
        "object_name": "V1_Background_Curve", "group_name": "V6_Background_Tube",
        "profile_radius": 0.15, "resample_length": 0.25,
    })
    assert v6_setup["group_name"] == "V6_Background_Tube"
    v6_tree = dispatch_operation("inspect_geometry_node_tree", {"object_name": "V1_Background_Curve"})
    assert {node["name"] for node in v6_tree["nodes"]} >= {"Curve Input", "Resample Curve", "Profile Circle", "Curve to Mesh", "Geometry Output"}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_curve = bpy.data.objects["V1_Background_Curve"].evaluated_get(depsgraph)
    generated_mesh = bpy.data.meshes.new_from_object(evaluated_curve, depsgraph=depsgraph)
    assert len(generated_mesh.vertices) > 0
    bpy.data.meshes.remove(generated_mesh)
    dispatch_operation("undo", {})
    assert not any(item.type == "NODES" for item in bpy.data.objects["V1_Background_Curve"].modifiers)

    bpy.ops.mesh.primitive_plane_add(size=4)
    scatter_surface = bpy.context.object
    scatter_surface.name = "V6_Scatter_Surface"
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.1, location=(0, 0, 2))
    scatter_instance = bpy.context.object
    scatter_instance.name = "V6_Scatter_Instance"
    scatter = dispatch_operation("create_surface_scatter_setup", {"surface_object_name": scatter_surface.name, "instance_object_name": scatter_instance.name, "group_name": "V6_Background_Scatter", "density": 2.0})
    assert scatter["group_name"] == "V6_Background_Scatter"
    scatter_tree = dispatch_operation("inspect_geometry_node_tree", {"object_name": scatter_surface.name})
    assert {node["name"] for node in scatter_tree["nodes"]} >= {"Surface Input", "Distribute Points on Faces", "Instance Object", "Instance on Points", "Join Surface and Instances", "Geometry Output"}
    dispatch_operation("undo", {})
    assert not any(item.type == "NODES" for item in scatter_surface.modifiers)

    print("HARNESS_BLENDER_BACKGROUND_INTEGRATION_OK")


if __name__ == "__main__":
    main()
