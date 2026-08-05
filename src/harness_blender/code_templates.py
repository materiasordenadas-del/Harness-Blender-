"""Generate vetted Blender Python for the V0 semantic tools.

The LLM never supplies raw Python in V0. Inputs are validated by the MCP tool
and inserted only as Python literals.
"""

from __future__ import annotations

from typing import Iterable

ALLOWED_PRIMITIVES = {"cube", "uv_sphere", "cylinder", "cone", "torus"}


def _literal(value: object) -> str:
    return repr(value)


def _vec3(value: Iterable[float], name: str) -> tuple[float, float, float]:
    values = tuple(float(item) for item in value)
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three numbers")
    return values  # type: ignore[return-value]


def ping() -> str:
    return """
import bpy
result = {
    "status": "ready",
    "blender_version": bpy.app.version_string,
    "file": bpy.data.filepath or None,
    "mode": bpy.context.mode,
}
""".strip()


def inspect_scene() -> str:
    return """
import bpy
scene = bpy.context.scene
objects = []
for obj in scene.objects:
    item = {
        "name": obj.name,
        "type": obj.type,
        "location": [round(v, 6) for v in obj.location],
        "rotation_euler": [round(v, 6) for v in obj.rotation_euler],
        "scale": [round(v, 6) for v in obj.scale],
        "dimensions": [round(v, 6) for v in obj.dimensions],
        "visible": obj.visible_get(),
    }
    if obj.type == "MESH":
        item["mesh"] = {
            "vertices": len(obj.data.vertices),
            "edges": len(obj.data.edges),
            "polygons": len(obj.data.polygons),
        }
    objects.append(item)
result = {
    "scene": scene.name,
    "file": bpy.data.filepath or None,
    "active_object": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
    "selected_objects": [obj.name for obj in bpy.context.selected_objects],
    "object_count": len(objects),
    "objects": objects,
}
""".strip()


def inspect_object(name: str) -> str:
    return f"""
import bpy
name = {_literal(name)}
obj = bpy.data.objects.get(name)
if obj is None:
    raise ValueError(f"Object not found: {{name}}")
info = {{
    "name": obj.name,
    "type": obj.type,
    "location": [round(v, 6) for v in obj.location],
    "rotation_euler": [round(v, 6) for v in obj.rotation_euler],
    "rotation_mode": obj.rotation_mode,
    "scale": [round(v, 6) for v in obj.scale],
    "dimensions": [round(v, 6) for v in obj.dimensions],
    "parent": obj.parent.name if obj.parent else None,
    "modifiers": [{{"name": m.name, "type": m.type}} for m in obj.modifiers],
    "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
}}
if obj.type == "MESH":
    mesh = obj.data
    info["mesh"] = {{
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "uv_layers": [layer.name for layer in mesh.uv_layers],
        "shape_keys": list(mesh.shape_keys.key_blocks.keys()) if mesh.shape_keys else [],
    }}
result = info
""".strip()


def create_primitive(
    kind: str,
    name: str,
    location: Iterable[float],
    scale: Iterable[float],
) -> str:
    if kind not in ALLOWED_PRIMITIVES:
        raise ValueError(f"Unsupported primitive: {kind}")
    loc = _vec3(location, "location")
    scl = _vec3(scale, "scale")
    operator = {
        "cube": "bpy.ops.mesh.primitive_cube_add",
        "uv_sphere": "bpy.ops.mesh.primitive_uv_sphere_add",
        "cylinder": "bpy.ops.mesh.primitive_cylinder_add",
        "cone": "bpy.ops.mesh.primitive_cone_add",
        "torus": "bpy.ops.mesh.primitive_torus_add",
    }[kind]
    return f"""
import bpy
{operator}(location={_literal(loc)})
obj = bpy.context.active_object
if obj is None:
    raise RuntimeError("Blender did not create an active object")
obj.name = {_literal(name)}
obj.scale = {_literal(scl)}
bpy.context.view_layer.update()
result = {{
    "name": obj.name,
    "type": obj.type,
    "location": list(obj.location),
    "scale": list(obj.scale),
    "dimensions": list(obj.dimensions),
}}
""".strip()


def transform_object(
    name: str,
    location: Iterable[float] | None,
    rotation_degrees: Iterable[float] | None,
    scale: Iterable[float] | None,
) -> str:
    loc = _vec3(location, "location") if location is not None else None
    rot = _vec3(rotation_degrees, "rotation_degrees") if rotation_degrees is not None else None
    scl = _vec3(scale, "scale") if scale is not None else None
    return f"""
import bpy
import math
name = {_literal(name)}
obj = bpy.data.objects.get(name)
if obj is None:
    raise ValueError(f"Object not found: {{name}}")
location = {_literal(loc)}
rotation_degrees = {_literal(rot)}
scale = {_literal(scl)}
if location is not None:
    obj.location = location
if rotation_degrees is not None:
    obj.rotation_euler = tuple(math.radians(v) for v in rotation_degrees)
if scale is not None:
    obj.scale = scale
bpy.context.view_layer.update()
result = {{
    "name": obj.name,
    "location": list(obj.location),
    "rotation_euler": list(obj.rotation_euler),
    "scale": list(obj.scale),
    "dimensions": list(obj.dimensions),
}}
""".strip()


def delete_object(name: str) -> str:
    return f"""
import bpy
name = {_literal(name)}
obj = bpy.data.objects.get(name)
if obj is None:
    raise ValueError(f"Object not found: {{name}}")
bpy.data.objects.remove(obj, do_unlink=True)
result = {{"deleted": name}}
""".strip()


def validate_mesh(name: str) -> str:
    return f"""
import bpy
import bmesh
name = {_literal(name)}
obj = bpy.data.objects.get(name)
if obj is None:
    raise ValueError(f"Object not found: {{name}}")
if obj.type != "MESH":
    raise TypeError(f"Object {{name}} is {{obj.type}}, not MESH")
bm = bmesh.new()
try:
    bm.from_mesh(obj.data)
    boundary_edges = sum(1 for edge in bm.edges if edge.is_boundary)
    non_manifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
    loose_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 0)
    loose_vertices = sum(1 for vert in bm.verts if len(vert.link_edges) == 0)
    degenerate_faces = sum(1 for face in bm.faces if face.calc_area() <= 1e-12)
    result = {{
        "name": name,
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": boundary_edges,
        "non_manifold_edges": non_manifold_edges,
        "loose_edges": loose_edges,
        "loose_vertices": loose_vertices,
        "degenerate_faces": degenerate_faces,
        "is_closed_manifold": non_manifold_edges == 0 and boundary_edges == 0,
    }}
finally:
    bm.free()
""".strip()


def save_blend(filepath: str | None) -> str:
    return f"""
import bpy
filepath = {_literal(filepath)}
if filepath:
    bpy.ops.wm.save_as_mainfile(filepath=filepath)
else:
    if not bpy.data.filepath:
        raise ValueError("Current file has no path; provide filepath")
    bpy.ops.wm.save_mainfile()
result = {{"filepath": bpy.data.filepath}}
""".strip()


def undo() -> str:
    return """
import bpy
status = bpy.ops.ed.undo()
result = {"status": sorted(status)}
""".strip()


def capture_screen(filepath: str) -> str:
    return f"""
import bpy
from pathlib import Path
filepath = {_literal(filepath)}
if bpy.app.background:
    raise RuntimeError("Screen capture requires Blender GUI mode")
Path(filepath).parent.mkdir(parents=True, exist_ok=True)
status = bpy.ops.screen.screenshot(filepath=filepath)
result = {{"filepath": filepath, "status": sorted(status)}}
""".strip()
