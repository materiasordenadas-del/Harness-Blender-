# SPDX-License-Identifier: GPL-3.0-or-later
"""Typed V2 mesh inspection using Blender's BMesh API."""

from __future__ import annotations

from typing import Any

import bmesh
import bpy
from mathutils import Vector
from bpy_extras import view3d_utils

from .operations import _record_undo


def _mesh_object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        raise TypeError("Operation requires an existing MESH object")
    return obj


def _topology_snapshot(mesh: bpy.types.Mesh) -> dict[str, Any]:
    return {
        "vertices": [tuple(vertex.co) for vertex in mesh.vertices],
        "edges": [tuple(edge.vertices) for edge in mesh.edges],
        "faces": [tuple(polygon.vertices) for polygon in mesh.polygons],
        "materials": [polygon.material_index for polygon in mesh.polygons],
        "smooth": [polygon.use_smooth for polygon in mesh.polygons],
    }


def _restore_topology(mesh: bpy.types.Mesh, snapshot: dict[str, Any]) -> None:
    mesh.clear_geometry()
    mesh.from_pydata(snapshot["vertices"], snapshot["edges"], snapshot["faces"])
    for polygon, material, smooth in zip(mesh.polygons, snapshot["materials"], snapshot["smooth"]):
        polygon.material_index, polygon.use_smooth = material, smooth
    mesh.update()


def inspect_mesh_detailed(params: dict[str, Any]) -> dict[str, Any]:
    obj = bpy.data.objects.get(params["object_name"])
    if obj is None:
        raise ValueError(f"Object not found: {params['object_name']}")
    if obj.type != "MESH":
        raise TypeError(f"Object {obj.name} is {obj.type}, not MESH")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        boundary = sum(edge.is_boundary for edge in bm.edges)
        loose = sum(not edge.link_faces for edge in bm.edges)
        non_manifold = sum(not edge.is_manifold and not edge.is_boundary for edge in bm.edges)
        return {"name": obj.name, "vertices": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
                "triangles": sum(len(face.verts) == 3 for face in bm.faces),
                "quads": sum(len(face.verts) == 4 for face in bm.faces),
                "ngons": sum(len(face.verts) > 4 for face in bm.faces),
                "boundary_edges": boundary, "loose_edges": loose, "non_manifold_edges": non_manifold,
                "is_closed_manifold": boundary == 0 and loose == 0 and non_manifold == 0,
                "materials": [slot.material.name if slot.material else None for slot in obj.material_slots]}
    finally:
        bm.free()


def inspect_uv(params: dict[str, Any]) -> dict[str, Any]:
    """Report UV-layer metadata and coordinate bounds without editing the mesh."""
    obj = _mesh_object(params["object_name"])
    layers: list[dict[str, Any]] = []
    for layer in obj.data.uv_layers:
        coordinates = [loop.uv for loop in layer.data]
        if coordinates:
            minimum = [min(float(uv[axis]) for uv in coordinates) for axis in range(2)]
            maximum = [max(float(uv[axis]) for uv in coordinates) for axis in range(2)]
        else:
            minimum = maximum = [0.0, 0.0]
        layers.append({
            "name": layer.name,
            "active": layer is obj.data.uv_layers.active,
            "render": layer.active_render,
            "loop_count": len(layer.data),
            "bounds": {"min": minimum, "max": maximum},
        })
    return {
        "object_name": obj.name,
        "has_uv": bool(layers),
        "active_layer": obj.data.uv_layers.active.name if obj.data.uv_layers.active else None,
        "layer_count": len(layers),
        "layers": layers,
    }


def _uv_cross(first: Vector, second: Vector, third: Vector) -> float:
    return float((second.x - first.x) * (third.y - first.y) - (second.y - first.y) * (third.x - first.x))


def _point_in_uv_triangle(point: Vector, triangle: tuple[Vector, Vector, Vector]) -> bool:
    values = [_uv_cross(triangle[index], triangle[(index + 1) % 3], point) for index in range(3)]
    return all(value > 1e-9 for value in values) or all(value < -1e-9 for value in values)


def _uv_triangles_overlap(first: tuple[Vector, Vector, Vector], second: tuple[Vector, Vector, Vector]) -> bool:
    if all(any((left - right).length_squared <= 1e-18 for right in second) for left in first):
        return True
    if any(_point_in_uv_triangle(point, second) for point in first) or any(_point_in_uv_triangle(point, first) for point in second):
        return True
    for left in range(3):
        a, b = first[left], first[(left + 1) % 3]
        for right in range(3):
            c, d = second[right], second[(right + 1) % 3]
            if _uv_cross(a, b, c) * _uv_cross(a, b, d) < -1e-18 and _uv_cross(c, d, a) * _uv_cross(c, d, b) < -1e-18:
                return True
    return False


def evaluate_uv_layout(params: dict[str, Any]) -> dict[str, Any]:
    """Read-only UV quality checks, including positive-area triangle overlaps."""
    obj = _mesh_object(params["object_name"])
    layer = obj.data.uv_layers.active
    if layer is None:
        return {"object_name": obj.name, "status": "needs_review", "issues": ["missing_uv_layer"], "zero_area_faces": 0, "outside_unit_square_loops": 0, "overlapping_triangle_pairs": 0}
    zero_area = 0
    outside = 0
    triangles: list[tuple[int, tuple[Vector, Vector, Vector]]] = []
    for loop in layer.data:
        if loop.uv.x < 0 or loop.uv.x > 1 or loop.uv.y < 0 or loop.uv.y > 1:
            outside += 1
    for polygon in obj.data.polygons:
        points = [layer.data[index].uv for index in polygon.loop_indices]
        area = sum(points[index].x * points[(index + 1) % len(points)].y - points[(index + 1) % len(points)].x * points[index].y for index in range(len(points))) / 2 if points else 0
        if abs(area) <= 1e-12:
            zero_area += 1
        for index in range(1, len(points) - 1):
            triangles.append((polygon.index, (points[0].copy(), points[index].copy(), points[index + 1].copy())))
    overlaps = sum(
        _uv_triangles_overlap(first, second)
        for index, (first_polygon, first) in enumerate(triangles)
        for second_polygon, second in triangles[index + 1:]
        if first_polygon != second_polygon
    )
    issues = []
    if zero_area:
        issues.append("zero_area_uv_faces")
    if outside:
        issues.append("outside_unit_square")
    if overlaps:
        issues.append("overlapping_uv_triangles")
    return {"object_name": obj.name, "status": "needs_review" if issues else "ready", "issues": issues, "zero_area_faces": zero_area, "outside_unit_square_loops": outside, "overlapping_triangle_pairs": overlaps}


def _uv_snapshot(mesh: bpy.types.Mesh) -> dict[str, Any]:
    return {
        "active_index": mesh.uv_layers.active_index,
        "layers": [
            {
                "name": layer.name,
                "active_render": layer.active_render,
                "coordinates": [tuple(loop.uv) for loop in layer.data],
            }
            for layer in mesh.uv_layers
        ],
    }


def _restore_uv(mesh: bpy.types.Mesh, snapshot: dict[str, Any]) -> None:
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    for saved in snapshot["layers"]:
        layer = mesh.uv_layers.new(name=saved["name"])
        for loop, coordinate in zip(layer.data, saved["coordinates"]):
            loop.uv = coordinate
        layer.active_render = saved["active_render"]
    if snapshot["layers"]:
        mesh.uv_layers.active_index = snapshot["active_index"]
    mesh.update()


def unwrap_uv(params: dict[str, Any]) -> dict[str, Any]:
    """Unwrap all mesh faces and register a full UV-layer restoration action."""
    obj = _mesh_object(params["object_name"])
    if bpy.context.mode != "OBJECT":
        raise RuntimeError("unwrap_uv requires Blender Object Mode")
    snapshot = _uv_snapshot(obj.data)
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    try:
        for item in selected:
            item.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        result = bpy.ops.uv.unwrap(method=params["method"], margin=params["margin"])
        bpy.ops.object.mode_set(mode="OBJECT")
        if "FINISHED" not in result:
            raise RuntimeError("Blender did not finish UV unwrap")
    except Exception:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        _restore_uv(obj.data, snapshot)
        raise
    finally:
        for item in list(bpy.context.selected_objects):
            item.select_set(False)
        for item in selected:
            item.select_set(True)
        bpy.context.view_layer.objects.active = active
    _record_undo("unwrap UV", lambda: _restore_uv(obj.data, snapshot))
    report = inspect_uv({"object_name": obj.name})
    return {"object_name": obj.name, "method": params["method"], "margin": params["margin"], "uv": report}


def sculpt_smooth_region(params: dict[str, Any]) -> dict[str, Any]:
    """Smooth named vertices only; this is a bounded, undoable sculpt-like edit."""
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        if any(index >= len(bm.verts) for index in params["vertex_indices"]):
            raise ValueError("vertex_indices contains an index outside the mesh")
        vertices = [bm.verts[index] for index in params["vertex_indices"]]
        for _ in range(params["iterations"]):
            positions = {}
            for vertex in vertices:
                neighbours = [edge.other_vert(vertex) for edge in vertex.link_edges]
                if neighbours:
                    average = sum((item.co for item in neighbours), Vector()) / len(neighbours)
                    positions[vertex] = vertex.co.lerp(average, params["factor"])
            for vertex, coordinate in positions.items():
                vertex.co = coordinate
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("sculpt smooth region", lambda: _restore_topology(obj.data, snapshot))
    return {"object_name": obj.name, "vertex_indices": params["vertex_indices"], "factor": params["factor"], "iterations": params["iterations"]}


def recalculate_normals(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if not params["outward"]:
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("recalculate mesh normals", lambda: _restore_topology(obj.data, snapshot))
    return {"name": obj.name, "orientation": "outside" if params["outward"] else "inside"}


def flip_normals(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("flip mesh normals", lambda: _restore_topology(obj.data, snapshot))
    return {"name": obj.name, "faces": len(obj.data.polygons), "orientation": "flipped"}


def subdivide_mesh(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=params["cuts"], use_grid_fill=True)
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("subdivide mesh", lambda: _restore_topology(obj.data, snapshot))
    return {"name": obj.name, "vertices": len(obj.data.vertices), "faces": len(obj.data.polygons), "cuts": params["cuts"]}


def smooth_mesh(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.smooth_vert(bm, verts=list(bm.verts), factor=params["factor"], use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("smooth mesh", lambda: _restore_topology(obj.data, snapshot))
    return {"name": obj.name, "vertices": len(obj.data.vertices), "factor": params["factor"]}


def _material(name: str) -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if material is None:
        raise ValueError(f"Material not found: {name}")
    material.use_nodes = True
    return material


def _principled(material: bpy.types.Material):
    node = material.node_tree.nodes.get("Principled BSDF") if material.node_tree else None
    if node is None:
        raise RuntimeError("Material has no Principled BSDF node")
    return node


def create_material(params: dict[str, Any]) -> dict[str, Any]:
    name = params["name"]
    if bpy.data.materials.get(name) is not None:
        raise ValueError(f"Material already exists: {name}")
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    _record_undo("create material", lambda: bpy.data.materials.remove(material) if material.users == 0 else None)
    return {"name": material.name}


def assign_material(params: dict[str, Any]) -> dict[str, Any]:
    obj, material = _mesh_object(params["object_name"]), _material(params["material_name"])
    obj.data.materials.append(material)
    index = len(obj.data.materials) - 1
    _record_undo("assign material", lambda: obj.data.materials.pop(index=index))
    return {"object_name": obj.name, "material_name": material.name, "slot": index}


def set_material_value(params: dict[str, Any], input_name: str, response_name: str) -> dict[str, Any]:
    socket = _principled(_material(params["material_name"])).inputs[input_name]
    previous = socket.default_value[:]
    socket.default_value = params[response_name]
    _record_undo("set material value", lambda: setattr(socket, "default_value", previous))
    return {"material_name": params["material_name"], response_name: list(socket.default_value)}


def set_material_scalar(params: dict[str, Any], input_name: str, response_name: str) -> dict[str, Any]:
    socket = _principled(_material(params["material_name"])).inputs[input_name]
    previous = socket.default_value
    socket.default_value = params[response_name]
    _record_undo("set material value", lambda: setattr(socket, "default_value", previous))
    return {"material_name": params["material_name"], response_name: float(socket.default_value)}


def add_modifier(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    name, modifier_type = params["name"], params["modifier_type"]
    if obj.modifiers.get(name) is not None:
        raise ValueError(f"Modifier already exists: {name}")
    modifier = obj.modifiers.new(name, modifier_type)
    _record_undo("add modifier", lambda: obj.modifiers.remove(modifier) if modifier.name in obj.modifiers else None)
    return {"object_name": obj.name, "name": modifier.name, "modifier_type": modifier.type}


def set_modifier_parameter(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    modifier = obj.modifiers.get(params["modifier_name"])
    if modifier is None:
        raise ValueError(f"Modifier not found: {params['modifier_name']}")
    field, value = params["parameter"], params["value"]
    previous = getattr(modifier, field)
    setattr(modifier, field, value)
    _record_undo("set modifier parameter", lambda: setattr(modifier, field, previous))
    return {"object_name": obj.name, "modifier_name": modifier.name, "parameter": field, "value": getattr(modifier, field)}


def remove_modifier(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    modifier = obj.modifiers.get(params["modifier_name"])
    if modifier is None:
        raise ValueError(f"Modifier not found: {params['modifier_name']}")
    fields = {"SUBSURF": ("levels",), "SOLIDIFY": ("thickness",), "DECIMATE": ("ratio",)}.get(modifier.type, ())
    state = {field: getattr(modifier, field) for field in fields}
    name, modifier_type = modifier.name, modifier.type
    obj.modifiers.remove(modifier)

    def restore() -> None:
        restored = obj.modifiers.new(name, modifier_type)
        for field, value in state.items():
            setattr(restored, field, value)

    _record_undo("remove modifier", restore)
    return {"object_name": obj.name, "removed": name, "modifier_type": modifier_type}


def _modifier_state(modifier: bpy.types.Modifier) -> dict[str, Any]:
    fields = {"SUBSURF": ("levels",), "SOLIDIFY": ("thickness",), "DECIMATE": ("ratio",)}.get(modifier.type, ())
    return {
        "name": modifier.name,
        "type": modifier.type,
        "settings": {field: getattr(modifier, field) for field in fields},
        "show_viewport": modifier.show_viewport,
        "show_render": modifier.show_render,
    }


def _restore_modifier(obj: bpy.types.Object, state: dict[str, Any]) -> None:
    modifier = obj.modifiers.get(state["name"]) or obj.modifiers.new(state["name"], state["type"])
    modifier.show_viewport = state["show_viewport"]
    modifier.show_render = state["show_render"]
    for field, value in state["settings"].items():
        setattr(modifier, field, value)


def apply_modifier(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    modifier = obj.modifiers.get(params["modifier_name"])
    if modifier is None:
        raise ValueError(f"Modifier not found: {params['modifier_name']}")
    topology = _topology_snapshot(obj.data)
    state = _modifier_state(modifier)
    previous_active = bpy.context.view_layer.objects.active
    previous_selection = tuple(bpy.context.selected_objects)
    try:
        for selected in previous_selection:
            selected.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        status = bpy.ops.object.modifier_apply(modifier=modifier.name)
        if "FINISHED" not in status:
            raise RuntimeError(f"Blender modifier_apply returned {sorted(status)}")
    finally:
        obj.select_set(False)
        for selected in previous_selection:
            selected.select_set(True)
        bpy.context.view_layer.objects.active = previous_active

    def restore() -> None:
        _restore_topology(obj.data, topology)
        _restore_modifier(obj, state)

    _record_undo("apply modifier", restore)
    return {"object_name": obj.name, "applied": state["name"], "modifier_type": state["type"], "vertices": len(obj.data.vertices), "faces": len(obj.data.polygons)}


def merge_vertices(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        indices = params["vertex_indices"]
        if any(index >= len(bm.verts) for index in indices):
            raise IndexError("vertex index out of range")
        vertices = [bm.verts[index] for index in indices]
        center = sum((vertex.co for vertex in vertices), Vector()) / len(vertices)
        bmesh.ops.pointmerge(bm, verts=vertices, merge_co=center)
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("merge vertices", lambda: _restore_topology(obj.data, snapshot))
    return {"object_name": obj.name, "merged_vertices": len(params["vertex_indices"]), "vertices": len(obj.data.vertices)}


def bridge_edge_loops(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        indices = params["edge_indices"]
        if any(index >= len(bm.edges) for index in indices):
            raise IndexError("edge index out of range")
        result = bmesh.ops.bridge_loops(bm, edges=[bm.edges[index] for index in indices])
        if not result.get("faces"):
            raise ValueError("Selected edges do not form two bridgeable loops")
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("bridge edge loops", lambda: _restore_topology(obj.data, snapshot))
    return {"object_name": obj.name, "faces_created": len(result["faces"]), "faces": len(obj.data.polygons)}


def split_mesh_by_plane(params: dict[str, Any]) -> dict[str, Any]:
    """Create two capped meshes and retain the source as a hidden reversible backup."""
    obj = _mesh_object(params["object_name"])
    if bpy.data.objects.get(params["positive_name"]) or bpy.data.objects.get(params["negative_name"]):
        raise ValueError("Split output object name already exists")
    inverse = obj.matrix_world.inverted()
    point = inverse @ Vector(params["plane_point"])
    normal = (inverse.transposed().to_3x3() @ Vector(params["plane_normal"])).normalized()
    created: list[bpy.types.Object] = []
    source_hidden, source_render = obj.hide_get(), obj.hide_render
    try:
        for name, clear_inner, clear_outer in ((params["positive_name"], True, False), (params["negative_name"], False, True)):
            bm = bmesh.new()
            try:
                bm.from_mesh(obj.data)
                cut = bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), plane_co=point, plane_no=normal, clear_inner=clear_inner, clear_outer=clear_outer)
                if params["cap"]:
                    cut_edges = [item for item in cut.get("geom_cut", []) if isinstance(item, bmesh.types.BMEdge) and item.is_valid and item.is_boundary]
                    if cut_edges:
                        bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
                if not bm.faces:
                    raise ValueError("Cut plane does not produce two non-empty mesh parts")
                mesh = bpy.data.meshes.new(name)
                bm.to_mesh(mesh)
                mesh.update()
            finally:
                bm.free()
            part = obj.copy(); part.name = name; part.data = mesh
            for collection in obj.users_collection or (bpy.context.collection,):
                collection.objects.link(part)
            created.append(part)
        obj.hide_set(True); obj.hide_render = True
    except Exception:
        for part in created:
            bpy.data.objects.remove(part, do_unlink=True)
        raise

    def restore() -> None:
        for part in created:
            current = bpy.data.objects.get(part.name)
            if current is not None:
                bpy.data.objects.remove(current, do_unlink=True)
        obj.hide_set(source_hidden); obj.hide_render = source_render
        bpy.context.view_layer.update()

    _record_undo("split mesh by plane", restore)
    return {"source_backup": obj.name, "positive_object": created[0].name, "negative_object": created[1].name, "source_hidden": True, "cap": params["cap"]}


def split_selected_mesh_by_view_line(params: dict[str, Any]) -> dict[str, Any]:
    active = bpy.context.view_layer.objects.active
    if active is None or active.type != "MESH" or not active.select_get():
        raise TypeError("Select one active MESH object before using a viewport cut line")
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D": continue
            region = next((item for item in area.regions if item.type == "WINDOW"), None)
            if region is None: continue
            space = area.spaces.active
            def ray(point: list[float]) -> Vector:
                coord = Vector((point[0] * region.width, point[1] * region.height))
                return view3d_utils.region_2d_to_vector_3d(region, space.region_3d, coord)
            first, second = ray(params["line_start"]), ray(params["line_end"])
            normal = first.cross(second)
            if normal.length == 0: raise ValueError("Viewport line cannot define a cut plane")
            origin = view3d_utils.region_2d_to_origin_3d(region, space.region_3d, Vector((region.width / 2, region.height / 2)))
            return split_mesh_by_plane({"object_name": active.name, "plane_point": list(origin), "plane_normal": list(normal.normalized()), "positive_name": params["positive_name"], "negative_name": params["negative_name"], "cap": params["cap"]})
    raise RuntimeError("A Blender VIEW_3D window is required for viewport cut lines")


def fill_hole(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        indices = params["boundary_edge_indices"]
        if any(index >= len(bm.edges) for index in indices):
            raise IndexError("boundary edge index out of range")
        result = bmesh.ops.holes_fill(bm, edges=[bm.edges[index] for index in indices], sides=0)
        if not result.get("faces"):
            raise ValueError("Selected edges do not form a fillable boundary")
        face_count = len(result["faces"])
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    _record_undo("fill mesh hole", lambda: _restore_topology(obj.data, snapshot))
    return {"object_name": obj.name, "faces_created": face_count, "faces": len(obj.data.polygons)}


def boolean_operation(params: dict[str, Any], operation: str) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    target = _mesh_object(params["target_object_name"])
    if obj == target:
        raise ValueError("Boolean target must be a different object")
    snapshot = _topology_snapshot(obj.data)
    modifier = obj.modifiers.new("Harness Boolean", "BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = target
    previous_active = bpy.context.view_layer.objects.active
    previous_selection = tuple(bpy.context.selected_objects)
    try:
        for selected in previous_selection:
            selected.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        status = bpy.ops.object.modifier_apply(modifier=modifier.name)
        if "FINISHED" not in status:
            raise RuntimeError(f"Blender modifier_apply returned {sorted(status)}")
    finally:
        obj.select_set(False)
        for selected in previous_selection:
            selected.select_set(True)
        bpy.context.view_layer.objects.active = previous_active
    _record_undo("boolean mesh operation", lambda: _restore_topology(obj.data, snapshot))
    return {"object_name": obj.name, "target_object_name": target.name, "operation": operation, "vertices": len(obj.data.vertices), "faces": len(obj.data.polygons)}


def decimate_mesh(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    modifier = obj.modifiers.new("Harness Decimate", "DECIMATE")
    modifier.ratio = params["ratio"]
    previous_active = bpy.context.view_layer.objects.active
    try:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        status = bpy.ops.object.modifier_apply(modifier=modifier.name)
        if "FINISHED" not in status:
            raise RuntimeError(f"Blender modifier_apply returned {sorted(status)}")
    finally:
        obj.select_set(False)
        bpy.context.view_layer.objects.active = previous_active
    _record_undo("decimate mesh", lambda: _restore_topology(obj.data, snapshot))
    return {"object_name": obj.name, "ratio": params["ratio"], "vertices": len(obj.data.vertices), "faces": len(obj.data.polygons)}


def voxel_remesh(params: dict[str, Any]) -> dict[str, Any]:
    obj = _mesh_object(params["object_name"])
    snapshot = _topology_snapshot(obj.data)
    previous_active = bpy.context.view_layer.objects.active
    try:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        obj.data.remesh_voxel_size = params["voxel_size"]
        status = bpy.ops.object.voxel_remesh()
        if "FINISHED" not in status:
            raise RuntimeError(f"Blender voxel_remesh returned {sorted(status)}")
    finally:
        obj.select_set(False)
        bpy.context.view_layer.objects.active = previous_active
    _record_undo("voxel remesh", lambda: _restore_topology(obj.data, snapshot))
    return {"object_name": obj.name, "voxel_size": params["voxel_size"], "vertices": len(obj.data.vertices), "faces": len(obj.data.polygons)}
