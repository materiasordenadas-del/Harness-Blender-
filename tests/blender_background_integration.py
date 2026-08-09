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


def evaluated_coordinate(obj, vertex_index):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return list(mesh.vertices[vertex_index].co)
    finally:
        evaluated.to_mesh_clear()


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
    movable_before = dispatch_operation("inspect_movable_structure", {"object_name": "V1_Background_Curve"})
    assert movable_before["prepared"] is False
    movable = dispatch_operation("prepare_movable_structure", {"object_name": "V1_Background_Curve", "mode": "curve_guided"})
    assert movable["prepared"] is True and movable["parts"][1]["name"] == "Process_01"
    assert dispatch_operation("list_movable_parts", {"object_name": "V1_Background_Curve"})["prepared"] is True
    assert dispatch_operation("get_part_state", {"object_name": "V1_Background_Curve", "part_name": "Process_01"})["part"]["state"] == "neutral"
    curve_base = list(bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[0].co)
    curve_tip = list(bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[-1].co)
    curve_tip_tilt = bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[-1].tilt
    bent = dispatch_operation("bend_curve_part", {"object_name": "V1_Background_Curve", "part_name": "Process_01", "angle_degrees": -30})
    assert bent["base_protected"] is True
    assert_close(list(bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[0].co), curve_base)
    assert list(bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[-1].co) != curve_tip
    moved = dispatch_operation("move_curve_part", {"object_name": "V1_Background_Curve", "part_name": "Process_01", "offset": [0, 1, 0]})
    assert moved["base_protected"] is True
    twisted = dispatch_operation("twist_curve_part", {"object_name": "V1_Background_Curve", "part_name": "Process_01", "angle_degrees": 45})
    assert twisted["base_protected"] is True
    assert bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[-1].tilt != curve_tip_tilt
    assert dispatch_operation("reset_curve_part", {"object_name": "V1_Background_Curve", "part_name": "Process_01"})["reset"] is True
    assert_close(list(bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[-1].co), curve_tip)
    assert_close([bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[-1].tilt], [curve_tip_tilt])
    dispatch_operation("undo", {})  # restore the pose that existed before reset
    dispatch_operation("undo", {})  # undo twist
    assert_close([bpy.data.objects["V1_Background_Curve"].data.splines[0].bezier_points[-1].tilt], [curve_tip_tilt])
    dispatch_operation("undo", {})  # undo move
    dispatch_operation("undo", {})  # undo bend
    dispatch_operation("undo", {})  # undo preparation
    assert dispatch_operation("inspect_movable_structure", {"object_name": "V1_Background_Curve"})["prepared"] is False

    v8_data = bpy.data.meshes.new("V8_Mesh_Source_Data")
    v8_data.from_pydata([(0, 0, 0), (1, 0, 0), (2, 0, 1), (3, 0, 1)], [(0, 1), (1, 2), (2, 3)], [])
    v8_source = bpy.data.objects.new("V8_Mesh_Source", v8_data)
    bpy.context.scene.collection.objects.link(v8_source)
    v8_source.name = "V8_Mesh_Source"
    source_coordinates = [list(vertex.co) for vertex in v8_source.data.vertices]
    for vertex in v8_source.data.vertices: vertex.select = vertex.index >= 1
    prepared_mesh = dispatch_operation("prepare_selected_mesh_extension", {
        "object_name": v8_source.name, "part_name": "Process_01",
    })
    v8_copy = bpy.data.objects[prepared_mesh["copy_object"]]
    assert prepared_mesh["source_unchanged"] is True
    assert prepared_mesh["transition_vertex_count"] >= 0
    assert [list(vertex.co) for vertex in v8_source.data.vertices] == source_coordinates
    copy_base = evaluated_coordinate(v8_copy, 1)
    copy_tip = evaluated_coordinate(v8_copy, 3)
    bent_mesh = dispatch_operation("bend_mesh_part", {"object_name": v8_copy.name, "angle_degrees": 45, "bend_axis": "x"})
    assert bent_mesh["base_protected"] is True and bent_mesh["source_unchanged"] is True
    assert bent_mesh["bend_axis"] == "x"
    assert bent_mesh["maximum_edge_stretch"] <= 1.5
    assert_close(evaluated_coordinate(v8_copy, 1), copy_base)
    assert evaluated_coordinate(v8_copy, 3) != copy_tip
    assert [list(vertex.co) for vertex in v8_source.data.vertices] == source_coordinates
    assert dispatch_operation("reset_mesh_part", {"object_name": v8_copy.name})["reset"] is True
    assert_close(evaluated_coordinate(v8_copy, 3), copy_tip)
    try:
        dispatch_operation("bend_mesh_part", {"object_name": v8_copy.name, "angle_degrees": 180})
        raise AssertionError("unsafe mesh bend was not blocked")
    except ValueError as exc:
        assert "mesh bends are limited" in str(exc)
    assert_close(evaluated_coordinate(v8_copy, 3), copy_tip)
    dispatch_operation("undo", {})  # undo reset
    dispatch_operation("undo", {})  # undo bend
    assert_close(evaluated_coordinate(v8_copy, 3), copy_tip)
    dispatch_operation("undo", {})  # remove temporary copy
    assert bpy.data.objects.get(prepared_mesh["copy_object"]) is None

    bpy.ops.object.select_all(action="DESELECT")
    v8_source.select_set(True); bpy.context.view_layer.objects.active = v8_source
    v8_session = dispatch_operation("create_v8_session", {"session_name": "Background"})
    assert v8_session["state"] == "preview" and v8_session["source_unchanged"] is True
    assert len(v8_session["entries"]) == 1
    session_entry = v8_session["entries"][0]
    session_copy = bpy.data.objects[session_entry["copy_object"]]
    session_armature = bpy.data.objects[session_entry["armature_object"]]
    assert session_copy.data != v8_source.data and session_copy.find_armature() == session_armature
    auto_rig = dispatch_operation("create_v8_auto_rig", {"session_name": "Background", "copy_object": session_copy.name, "bone_count": 3})
    assert auto_rig["rig_mode"] == "automatic_chain" and len(auto_rig["control_bones"]) == 3
    handles = dispatch_operation("create_v8_independent_handles", {"session_name": "Background", "copy_object": session_copy.name})
    assert handles["rig_mode"] == "independent_handles" and len(handles["control_bones"]) == 4
    session_entry = dispatch_operation("inspect_v8_session", {"session_name": "Background"})["entries"][0]
    session_armature = bpy.data.objects[session_entry["armature_object"]]
    source_coordinates = [list(vertex.co) for vertex in v8_source.data.vertices]
    dispatch_operation("pose_v8_control", {"session_name": "Background", "copy_object": session_copy.name, "control_bone": session_entry["control_bones"][-1], "location": [0, 0, 0], "rotation_degrees": [0, 0, 25]})
    assert evaluated_coordinate(session_copy, 3) != evaluated_coordinate(v8_source, 3)
    assert [list(vertex.co) for vertex in v8_source.data.vertices] == source_coordinates
    assert dispatch_operation("reset_v8_session", {"session_name": "Background"})["reset"] is True
    assert_close(evaluated_coordinate(session_copy, 3), evaluated_coordinate(v8_source, 3))
    assert dispatch_operation("accept_v8_session", {"session_name": "Background"})["accepted"] is True
    assert dispatch_operation("inspect_v8_session", {"session_name": "Background"})["state"] == "accepted"
    v8_discard = dispatch_operation("create_v8_session", {"session_name": "Discard", "object_names": [v8_source.name]})
    assert dispatch_operation("discard_v8_session", {"session_name": "Discard"})["discarded"] is True
    assert bpy.data.objects.get(v8_discard["entries"][0]["copy_object"]) is None

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
    asset_readiness = dispatch_operation("evaluate_asset_readiness", {"object_name": evaluated_mesh.name})
    assert asset_readiness["status"] == "needs_review"
    assert asset_readiness["blockers"] == []
    assert "materials" in asset_readiness["needs_review"]
    rigging_structure = dispatch_operation("inspect_rigging_structure", {"object_name": evaluated_mesh.name})
    assert rigging_structure["object_type"] == "MESH"
    assert rigging_structure["connected_components"] == 1
    assert rigging_structure["bone_count"] == 0
    uv_report = dispatch_operation("inspect_uv", {"object_name": evaluated_mesh.name})
    assert uv_report["has_uv"] is True
    assert uv_report["active_layer"] is not None
    assert uv_report["layers"][0]["loop_count"] == len(evaluated_mesh.data.loops)
    assert dispatch_operation("evaluate_uv_layout", {"object_name": evaluated_mesh.name})["status"] == "ready"
    active_uv = evaluated_mesh.data.uv_layers.active
    second_polygon = evaluated_mesh.data.polygons[1]
    first_polygon = evaluated_mesh.data.polygons[0]
    saved_second_uv = [tuple(active_uv.data[index].uv) for index in second_polygon.loop_indices]
    for target, source in zip(second_polygon.loop_indices, first_polygon.loop_indices):
        active_uv.data[target].uv = active_uv.data[source].uv
    overlap_report = dispatch_operation("evaluate_uv_layout", {"object_name": evaluated_mesh.name})
    assert overlap_report["overlapping_triangle_pairs"] > 0
    assert "overlapping_uv_triangles" in overlap_report["issues"]
    for index, coordinate in zip(second_polygon.loop_indices, saved_second_uv):
        active_uv.data[index].uv = coordinate
    unwrapped = dispatch_operation("unwrap_uv", {"object_name": evaluated_mesh.name, "method": "ANGLE_BASED", "margin": 0.01})
    assert unwrapped["method"] == "ANGLE_BASED"
    assert unwrapped["uv"]["has_uv"] is True
    dispatch_operation("undo", {})
    assert dispatch_operation("inspect_uv", {"object_name": evaluated_mesh.name}) == uv_report
    before_sculpt = [tuple(vertex.co) for vertex in evaluated_mesh.data.vertices]
    sculpted = dispatch_operation("sculpt_smooth_region", {"object_name": evaluated_mesh.name, "vertex_indices": [0, 1], "factor": 0.4, "iterations": 1})
    assert sculpted["vertex_indices"] == [0, 1]
    dispatch_operation("undo", {})
    assert [tuple(vertex.co) for vertex in evaluated_mesh.data.vertices] == before_sculpt

    bpy.ops.mesh.primitive_plane_add(size=2, location=(8, 0, 0))
    solidify_surface = bpy.context.object
    solidify_surface.name = "V7_Solidify_Surface"
    solidified = dispatch_operation("solidify_mesh", {"object_name": solidify_surface.name, "thickness": 0.2, "fill_rim": True})
    assert solidified["applied"] is False
    assert solidify_surface.modifiers[solidified["modifier_name"]].use_rim is True
    dispatch_operation("undo", {})
    assert not solidify_surface.modifiers
    solid_copy = dispatch_operation("make_mesh_solid", {"object_name": solidify_surface.name, "output_name": "V7_Solidified_Copy", "thickness": 0.2, "voxel_size": 0.1})
    assert solid_copy["source_object"] == solidify_surface.name
    assert solid_copy["is_closed_manifold"] is True
    assert bpy.data.objects.get("V7_Solidified_Copy") is not None
    dispatch_operation("undo", {})
    assert bpy.data.objects.get("V7_Solidified_Copy") is None

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

    branch_main = dispatch_operation("create_curve", {"name": "V6_Branch_Main", "spline_type": "POLY", "points": [[0, 0, 0], [0, 0, 2]]})
    assert branch_main["name"] == "V6_Branch_Main"
    branch_one = dispatch_operation("create_curve", {"name": "V6_Branch_One", "spline_type": "POLY", "points": [[0, 0, 1], [1, 0, 2]]})
    branch_two = dispatch_operation("create_curve", {"name": "V6_Branch_Two", "spline_type": "POLY", "points": [[0, 0, 1], [-1, 0, 2]]})
    assert branch_one["name"] == "V6_Branch_One" and branch_two["name"] == "V6_Branch_Two"
    branching = dispatch_operation("create_procedural_branching_setup", {"main_curve_name": "V6_Branch_Main", "branch_curve_names": ["V6_Branch_One", "V6_Branch_Two"], "group_name": "V6_Background_Branching", "profile_radius": 0.1, "resample_length": 0.2})
    assert branching["group_name"] == "V6_Background_Branching"
    branching_tree = dispatch_operation("inspect_geometry_node_tree", {"object_name": "V6_Branch_Main"})
    assert {node["name"] for node in branching_tree["nodes"]} >= {"Main Curve Input", "Join Branch Curves", "Resample Branching", "Profile Circle", "Branching Curve to Mesh", "Geometry Output"}
    dispatch_operation("undo", {})
    assert not any(item.type == "NODES" for item in bpy.data.objects["V6_Branch_Main"].modifiers)

    bpy.ops.mesh.primitive_cube_add(size=2)
    split_source = bpy.context.object
    split_source.name = "V2_Split_Source"
    split = dispatch_operation("split_mesh_by_plane", {"object_name": split_source.name, "plane_point": [0, 0, 0], "plane_normal": [1, 0, 0], "positive_name": "V2_Split_Positive", "negative_name": "V2_Split_Negative", "cap": True})
    assert split["source_hidden"] is True
    assert split_source.hide_get() is True
    for name in ("V2_Split_Positive", "V2_Split_Negative"):
        report = dispatch_operation("evaluate_mesh", {"object_name": name})
        assert report["is_closed_manifold"] is True
    dispatch_operation("undo", {})
    assert bpy.data.objects.get("V2_Split_Positive") is None
    assert bpy.data.objects.get("V2_Split_Negative") is None
    assert split_source.hide_get() is False

    print("HARNESS_BLENDER_BACKGROUND_INTEGRATION_OK")


if __name__ == "__main__":
    main()
