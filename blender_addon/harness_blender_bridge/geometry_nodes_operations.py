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
