# SPDX-License-Identifier: GPL-3.0-or-later
"""Typed V6 Geometry Nodes recipes built against Blender 5.2's node API."""

from __future__ import annotations

from typing import Any

import bpy


def create_procedural_tube_setup(params: dict[str, Any]) -> dict[str, Any]:
    obj = bpy.data.objects.get(params["object_name"])
    if obj is None or obj.type != "CURVE":
        raise TypeError("create_procedural_tube_setup requires an existing CURVE object")
    group_name = params["group_name"]
    if bpy.data.node_groups.get(group_name) is not None:
        raise ValueError(f"A node group named {group_name!r} already exists")
    modifier_name = f"Harness {group_name}"
    if obj.modifiers.get(modifier_name) is not None:
        raise ValueError(f"Object already has modifier {modifier_name!r}")
    group = bpy.data.node_groups.new(group_name, "GeometryNodeTree")
    modifier = None
    try:
        group.is_modifier = True
        interface = group.interface
        interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        interface.new_socket(name="Profile Radius", in_out="INPUT", socket_type="NodeSocketFloat").default_value = params["profile_radius"]
        interface.new_socket(name="Resample Length", in_out="INPUT", socket_type="NodeSocketFloat").default_value = params["resample_length"]
        interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        nodes = group.nodes
        links = group.links
        group_input = nodes.new("NodeGroupInput")
        group_input.name = "Curve Input"
        resample = nodes.new("GeometryNodeResampleCurve")
        resample.name = "Resample Curve"
        resample.inputs["Mode"].default_value = "Length"
        circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
        circle.name = "Profile Circle"
        circle.inputs["Resolution"].default_value = 12
        curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
        curve_to_mesh.name = "Curve to Mesh"
        curve_to_mesh.inputs["Fill Caps"].default_value = True
        group_output = nodes.new("NodeGroupOutput")
        group_output.name = "Geometry Output"
        links.new(group_input.outputs["Geometry"], resample.inputs["Curve"])
        links.new(group_input.outputs["Resample Length"], resample.inputs["Length"])
        links.new(group_input.outputs["Profile Radius"], circle.inputs["Radius"])
        links.new(resample.outputs["Curve"], curve_to_mesh.inputs["Curve"])
        links.new(circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])
        links.new(curve_to_mesh.outputs["Mesh"], group_output.inputs["Geometry"])
        modifier = obj.modifiers.new(name=modifier_name, type="NODES")
        modifier.node_group = group
        bpy.context.view_layer.update()
        return {
            "object_name": obj.name, "modifier_name": modifier.name, "group_name": group.name,
            "nodes": [node.name for node in nodes], "profile_radius": params["profile_radius"],
            "resample_length": params["resample_length"],
        }
    except Exception:
        if modifier is not None:
            obj.modifiers.remove(modifier)
        bpy.data.node_groups.remove(group)
        raise


def inspect_geometry_node_tree(params: dict[str, Any]) -> dict[str, Any]:
    obj = bpy.data.objects.get(params["object_name"])
    if obj is None:
        raise ValueError("Object must exist")
    modifier = next((item for item in obj.modifiers if item.type == "NODES" and item.node_group), None)
    if modifier is None or modifier.node_group is None:
        raise ValueError("Object has no Geometry Nodes modifier with a node group")
    group = modifier.node_group
    sockets = [
        {"name": item.name, "direction": item.in_out, "socket_type": item.socket_type}
        for item in group.interface.items_tree if item.item_type == "SOCKET"
    ]
    return {
        "object_name": obj.name, "modifier_name": modifier.name, "group_name": group.name,
        "nodes": [{"name": node.name, "type": node.bl_idname} for node in group.nodes],
        "links": [{"from": link.from_node.name, "to": link.to_node.name} for link in group.links],
        "interface": sockets,
    }


def create_surface_scatter_setup(params: dict[str, Any]) -> dict[str, Any]:
    """Attach a reversible points-on-faces instancing recipe to one mesh surface."""
    surface = bpy.data.objects.get(params["surface_object_name"])
    instance = bpy.data.objects.get(params["instance_object_name"])
    if surface is None or surface.type != "MESH":
        raise TypeError("create_surface_scatter_setup requires a MESH surface object")
    if instance is None:
        raise ValueError("Instance object must exist")
    group_name = params["group_name"]
    if bpy.data.node_groups.get(group_name) is not None:
        raise ValueError(f"A node group named {group_name!r} already exists")
    modifier_name = f"Harness {group_name}"
    if surface.modifiers.get(modifier_name) is not None:
        raise ValueError(f"Surface already has modifier {modifier_name!r}")
    group = bpy.data.node_groups.new(group_name, "GeometryNodeTree")
    modifier = None
    try:
        group.is_modifier = True
        group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        group.interface.new_socket(name="Density", in_out="INPUT", socket_type="NodeSocketFloat").default_value = params["density"]
        group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        nodes, links = group.nodes, group.links
        group_input = nodes.new("NodeGroupInput"); group_input.name = "Surface Input"
        distribute = nodes.new("GeometryNodeDistributePointsOnFaces"); distribute.name = "Distribute Points on Faces"
        object_info = nodes.new("GeometryNodeObjectInfo"); object_info.name = "Instance Object"; object_info.transform_space = "ORIGINAL"; object_info.inputs["Object"].default_value = instance
        instance_on_points = nodes.new("GeometryNodeInstanceOnPoints"); instance_on_points.name = "Instance on Points"
        join = nodes.new("GeometryNodeJoinGeometry"); join.name = "Join Surface and Instances"
        group_output = nodes.new("NodeGroupOutput"); group_output.name = "Geometry Output"
        links.new(group_input.outputs["Geometry"], distribute.inputs["Mesh"])
        links.new(group_input.outputs["Density"], distribute.inputs["Density"])
        links.new(distribute.outputs["Points"], instance_on_points.inputs["Points"])
        links.new(object_info.outputs["Geometry"], instance_on_points.inputs["Instance"])
        links.new(group_input.outputs["Geometry"], join.inputs["Geometry"])
        links.new(instance_on_points.outputs["Instances"], join.inputs["Geometry"])
        links.new(join.outputs["Geometry"], group_output.inputs["Geometry"])
        modifier = surface.modifiers.new(name=modifier_name, type="NODES")
        modifier.node_group = group
        bpy.context.view_layer.update()
        return {"surface_object_name": surface.name, "instance_object_name": instance.name, "modifier_name": modifier.name, "group_name": group.name, "density": params["density"], "nodes": [node.name for node in nodes]}
    except Exception:
        if modifier is not None:
            surface.modifiers.remove(modifier)
        bpy.data.node_groups.remove(group)
        raise


def create_procedural_branching_setup(params: dict[str, Any]) -> dict[str, Any]:
    main = bpy.data.objects.get(params["main_curve_name"])
    branches = [bpy.data.objects.get(name) for name in params["branch_curve_names"]]
    if main is None or main.type != "CURVE" or any(item is None or item.type != "CURVE" for item in branches):
        raise TypeError("procedural branching requires existing CURVE main and branch objects")
    name = params["group_name"]
    if bpy.data.node_groups.get(name) or main.modifiers.get(f"Harness {name}"):
        raise ValueError("Branching group or modifier name already exists")
    group = bpy.data.node_groups.new(name, "GeometryNodeTree"); modifier = None
    try:
        group.is_modifier = True
        group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        group.interface.new_socket(name="Profile Radius", in_out="INPUT", socket_type="NodeSocketFloat").default_value = params["profile_radius"]
        group.interface.new_socket(name="Resample Length", in_out="INPUT", socket_type="NodeSocketFloat").default_value = params["resample_length"]
        group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        n, l = group.nodes, group.links
        inp=n.new("NodeGroupInput"); inp.name="Main Curve Input"
        join=n.new("GeometryNodeJoinGeometry"); join.name="Join Branch Curves"
        for index, branch in enumerate(branches, 1):
            info=n.new("GeometryNodeObjectInfo"); info.name=f"Branch {index}: {branch.name}"; info.transform_space="ORIGINAL"; info.inputs["Object"].default_value=branch; l.new(info.outputs["Geometry"], join.inputs["Geometry"])
        l.new(inp.outputs["Geometry"], join.inputs["Geometry"])
        resample=n.new("GeometryNodeResampleCurve"); resample.name="Resample Branching"; resample.inputs["Mode"].default_value="Length"
        circle=n.new("GeometryNodeCurvePrimitiveCircle"); circle.name="Profile Circle"; circle.inputs["Resolution"].default_value=12
        tube=n.new("GeometryNodeCurveToMesh"); tube.name="Branching Curve to Mesh"; tube.inputs["Fill Caps"].default_value=True
        out=n.new("NodeGroupOutput"); out.name="Geometry Output"
        l.new(join.outputs["Geometry"],resample.inputs["Curve"]); l.new(inp.outputs["Resample Length"],resample.inputs["Length"]); l.new(inp.outputs["Profile Radius"],circle.inputs["Radius"]); l.new(resample.outputs["Curve"],tube.inputs["Curve"]); l.new(circle.outputs["Curve"],tube.inputs["Profile Curve"]); l.new(tube.outputs["Mesh"],out.inputs["Geometry"])
        modifier=main.modifiers.new(name=f"Harness {name}",type="NODES"); modifier.node_group=group; bpy.context.view_layer.update()
        return {"main_curve_name":main.name,"branch_curve_names":[item.name for item in branches],"modifier_name":modifier.name,"group_name":group.name,"nodes":[node.name for node in n]}
    except Exception:
        if modifier: main.modifiers.remove(modifier)
        bpy.data.node_groups.remove(group); raise
