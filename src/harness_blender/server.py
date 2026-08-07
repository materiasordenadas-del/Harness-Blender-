"""MCP server exposing the Harness Blender V1 semantic toolset."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP, Image

from .connection import BlenderConnection
from .docs_index import initialize as initialize_docs, search as search_docs
from .evaluator import diff_reports
from .router import route
from .skill_registry import content as skill_content, discover as discover_skills

mcp = FastMCP("Harness Blender V1")
_connection = BlenderConnection()


def _docs_path() -> Path:
    return Path(os.getenv("HARNESS_DOCS_INDEX", Path.cwd() / "config" / "v3_docs.sqlite"))


def _ensure_docs() -> Path:
    path = _docs_path()
    if not path.exists():
        initialize_docs(path)
    return path


def _run(operation: str, params: dict[str, Any] | None = None) -> str:
    return json.dumps(_connection.call(operation, params), ensure_ascii=False, indent=2)


@mcp.tool()
def route_blender_task(task: str) -> str:
    """Return only the V3 skills, official docs and tools relevant to a task."""
    result = route(task)
    return json.dumps({"task": result.task, "skills": result.skills, "tools": result.tools, "docs": result.docs}, ensure_ascii=False, indent=2)


@mcp.tool()
def diff_evaluation_reports(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Compare two V4 read-only evaluation reports without contacting Blender."""
    return json.dumps(diff_reports(before, after), ensure_ascii=False, indent=2)


@mcp.tool()
def list_blender_skills(domain: str | None = None) -> str:
    """List local skill metadata; optional domain filters without loading skill bodies."""
    skills = discover_skills()
    if domain:
        skills = [skill for skill in skills if skill.domain == domain]
    return json.dumps([{"name": skill.name, "domain": skill.domain, "applies_to": skill.applies_to, "tools": skill.tools} for skill in skills], ensure_ascii=False, indent=2)


@mcp.tool()
def get_blender_skill(name: str) -> str:
    """Load the Markdown body of one named local skill on demand."""
    return skill_content(name)


@mcp.tool()
def search_blender_docs(query: str, limit: int = 5) -> str:
    """Search the local index of official docs.blender.org entries."""
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    return json.dumps(search_docs(_ensure_docs(), query, limit), ensure_ascii=False, indent=2)


@mcp.tool()
def blender_ping() -> str:
    """Check that Blender and the local bridge are ready."""
    return _run("ping")


@mcp.tool()
def inspect_scene() -> str:
    """Return a compact, structured description of the current Blender scene."""
    return _run("inspect_scene")


@mcp.tool()
def inspect_scene_detailed() -> str:
    """Read hierarchy, collections, modifiers and mesh/curve metrics without editing Blender."""
    return _run("inspect_scene_detailed")


@mcp.tool()
def inspect_object(object_name: str) -> str:
    """Inspect one object, including transform, mesh counts, modifiers and materials."""
    return _run("inspect_object", {"object_name": object_name})


@mcp.tool()
def create_curve(name: str, spline_type: str, points: list[list[float]]) -> str:
    """Create an editable 3D Bézier, NURBS or Poly curve from 2-256 points."""
    return _run("create_curve", {"name": name, "spline_type": spline_type, "points": points})


@mcp.tool()
def inspect_curve(object_name: str) -> str:
    """Inspect an editable curve, including splines, points, handles, radius and bevel."""
    return _run("inspect_curve", {"object_name": object_name})


@mcp.tool()
def inspect_mesh_detailed(object_name: str) -> str:
    """Inspect mesh topology, manifold state, polygon types and materials."""
    return _run("inspect_mesh_detailed", {"object_name": object_name})


@mcp.tool()
def evaluate_mesh(object_name: str) -> str:
    """Measure mesh topology, area, volume and world bounding box without editing it."""
    return _run("evaluate_mesh", {"object_name": object_name})


@mcp.tool()
def evaluate_spatial(object_name: str, target_object_name: str) -> str:
    """Measure world bounding-box overlap and nearest-box distance without editing Blender."""
    return _run("evaluate_spatial", {"object_name": object_name, "target_object_name": target_object_name})


@mcp.tool()
def evaluate_tubular(object_name: str, spline_index: int = 0) -> str:
    """Measure curve radii, thickness progression, centerline and approximate curvature."""
    return _run("evaluate_tubular", {"object_name": object_name, "spline_index": spline_index})


@mcp.tool()
def evaluate_penetration(object_name: str, target_object_name: str) -> str:
    """Measure intersecting face pairs between two meshes without editing Blender."""
    return _run("evaluate_penetration", {"object_name": object_name, "target_object_name": target_object_name})


@mcp.tool()
def recalculate_normals(object_name: str, outward: bool = True) -> str:
    """Recalculate all mesh face normals outward or inward."""
    return _run("recalculate_normals", {"object_name": object_name, "outward": outward})


@mcp.tool()
def flip_normals(object_name: str) -> str:
    """Invert all mesh face normals reversibly."""
    return _run("flip_normals", {"object_name": object_name})


@mcp.tool()
def subdivide_mesh(object_name: str, cuts: int) -> str:
    """Subdivide all mesh edges with 1-4 cuts, reversibly."""
    return _run("subdivide_mesh", {"object_name": object_name, "cuts": cuts})


@mcp.tool()
def smooth_mesh(object_name: str, factor: float) -> str:
    """Smooth mesh vertices with a bounded factor from 0 to 1."""
    return _run("smooth_mesh", {"object_name": object_name, "factor": factor})


@mcp.tool()
def create_material(name: str) -> str:
    """Create a basic Principled material."""
    return _run("create_material", {"name": name})


@mcp.tool()
def assign_material(object_name: str, material_name: str) -> str:
    """Append a material to a mesh object."""
    return _run("assign_material", {"object_name": object_name, "material_name": material_name})


@mcp.tool()
def set_base_color(material_name: str, base_color: list[float]) -> str:
    """Set a material RGBA base color, values 0-1."""
    return _run("set_base_color", {"material_name": material_name, "base_color": base_color})


@mcp.tool()
def set_roughness(material_name: str, roughness: float) -> str:
    """Set Principled roughness from 0 to 1."""
    return _run("set_roughness", {"material_name": material_name, "roughness": roughness})


@mcp.tool()
def set_metallic(material_name: str, metallic: float) -> str:
    """Set Principled metallic from 0 to 1."""
    return _run("set_metallic", {"material_name": material_name, "metallic": metallic})


@mcp.tool()
def set_alpha(material_name: str, alpha: float) -> str:
    """Set Principled alpha from 0 to 1."""
    return _run("set_alpha", {"material_name": material_name, "alpha": alpha})


@mcp.tool()
def add_modifier(object_name: str, name: str, modifier_type: str) -> str:
    """Add one modifier from the V2 allowlist, reversibly."""
    return _run("add_modifier", {"object_name": object_name, "name": name, "modifier_type": modifier_type})


@mcp.tool()
def set_modifier_parameter(object_name: str, modifier_name: str, parameter: str, value: float) -> str:
    """Set a limited V2 modifier parameter: levels, thickness or ratio."""
    return _run("set_modifier_parameter", {"object_name": object_name, "modifier_name": modifier_name, "parameter": parameter, "value": value})


@mcp.tool()
def remove_modifier(object_name: str, modifier_name: str) -> str:
    """Remove a V2 modifier and restore its supported settings with undo."""
    return _run("remove_modifier", {"object_name": object_name, "modifier_name": modifier_name})


@mcp.tool()
def apply_modifier(object_name: str, modifier_name: str) -> str:
    """Apply one existing modifier and preserve a reversible Harness snapshot."""
    return _run("apply_modifier", {"object_name": object_name, "modifier_name": modifier_name})


@mcp.tool()
def merge_vertices(object_name: str, vertex_indices: list[int]) -> str:
    """Merge 2-256 vertices at their shared center, reversibly."""
    return _run("merge_vertices", {"object_name": object_name, "vertex_indices": vertex_indices})


@mcp.tool()
def bridge_edge_loops(object_name: str, edge_indices: list[int]) -> str:
    """Bridge two compatible boundary loops selected by their edge indices."""
    return _run("bridge_edge_loops", {"object_name": object_name, "edge_indices": edge_indices})


@mcp.tool()
def fill_hole(object_name: str, boundary_edge_indices: list[int]) -> str:
    """Fill one closed boundary loop chosen by edge indices, reversibly."""
    return _run("fill_hole", {"object_name": object_name, "boundary_edge_indices": boundary_edge_indices})


@mcp.tool()
def boolean_union(object_name: str, target_object_name: str) -> str:
    """Apply an exact Boolean union to one mesh, reversibly."""
    return _run("boolean_union", {"object_name": object_name, "target_object_name": target_object_name})


@mcp.tool()
def boolean_difference(object_name: str, target_object_name: str) -> str:
    """Apply an exact Boolean difference to one mesh, reversibly."""
    return _run("boolean_difference", {"object_name": object_name, "target_object_name": target_object_name})


@mcp.tool()
def boolean_intersection(object_name: str, target_object_name: str) -> str:
    """Apply an exact Boolean intersection to one mesh, reversibly."""
    return _run("boolean_intersection", {"object_name": object_name, "target_object_name": target_object_name})


@mcp.tool()
def decimate_mesh(object_name: str, ratio: float) -> str:
    """Apply Decimate with a ratio from 0.01 to 1, reversibly."""
    return _run("decimate_mesh", {"object_name": object_name, "ratio": ratio})


@mcp.tool()
def voxel_remesh(object_name: str, voxel_size: float) -> str:
    """Apply voxel remesh with an explicit, bounded voxel size."""
    return _run("voxel_remesh", {"object_name": object_name, "voxel_size": voxel_size})


@mcp.tool()
def add_curve_point(object_name: str, spline_index: int, co: list[float]) -> str:
    """Append one editable point to a single-spline curve."""
    return _run("add_curve_point", {"object_name": object_name, "spline_index": spline_index, "co": co})


@mcp.tool()
def move_curve_point(object_name: str, spline_index: int, point_index: int, co: list[float]) -> str:
    """Move one editable curve point without converting the curve."""
    return _run("move_curve_point", {
        "object_name": object_name, "spline_index": spline_index, "point_index": point_index, "co": co,
    })


@mcp.tool()
def remove_curve_point(object_name: str, spline_index: int, point_index: int) -> str:
    """Remove one point while retaining at least two points in the spline."""
    return _run("remove_curve_point", {
        "object_name": object_name, "spline_index": spline_index, "point_index": point_index,
    })


@mcp.tool()
def set_curve_handle_type(
    object_name: str, spline_index: int, point_index: int, side: str, handle_type: str
) -> str:
    """Set one Bézier handle type: AUTO, ALIGNED, FREE or VECTOR."""
    return _run("set_curve_handle_type", {
        "object_name": object_name, "spline_index": spline_index, "point_index": point_index,
        "side": side, "handle_type": handle_type,
    })


@mcp.tool()
def set_curve_handle_position(
    object_name: str, spline_index: int, point_index: int, side: str, co: list[float]
) -> str:
    """Set the position of one Bézier handle in object-local coordinates."""
    return _run("set_curve_handle_position", {
        "object_name": object_name, "spline_index": spline_index, "point_index": point_index,
        "side": side, "co": co,
    })


@mcp.tool()
def subdivide_curve(object_name: str, spline_index: int, cuts: int) -> str:
    """Insert 1-16 evenly spaced editable control points per spline segment."""
    return _run("subdivide_curve", {"object_name": object_name, "spline_index": spline_index, "cuts": cuts})


@mcp.tool()
def resample_curve(object_name: str, spline_index: int, point_count: int) -> str:
    """Replace a spline with exactly 2-256 editable, evenly sampled control points."""
    return _run("resample_curve", {
        "object_name": object_name, "spline_index": spline_index, "point_count": point_count,
    })


@mcp.tool()
def convert_curve_to_mesh(object_name: str, mesh_name: str) -> str:
    """Create an explicit mesh copy of a curve, preserving its editable source."""
    return _run("convert_curve_to_mesh", {"object_name": object_name, "mesh_name": mesh_name})


@mcp.tool()
def set_curve_point_radius(object_name: str, spline_index: int, point_index: int, radius: float) -> str:
    """Set the taper radius of one editable curve point."""
    return _run("set_curve_point_radius", {
        "object_name": object_name, "spline_index": spline_index, "point_index": point_index, "radius": radius,
    })


@mcp.tool()
def set_curve_point_tilt(object_name: str, spline_index: int, point_index: int, tilt: float) -> str:
    """Set the tilt in radians of one editable curve point."""
    return _run("set_curve_point_tilt", {
        "object_name": object_name, "spline_index": spline_index, "point_index": point_index, "tilt": tilt,
    })


@mcp.tool()
def set_curve_bevel_depth(object_name: str, bevel_depth: float) -> str:
    """Set the curve's tube radius without converting it to a mesh."""
    return _run("set_curve_bevel_depth", {"object_name": object_name, "bevel_depth": bevel_depth})


@mcp.tool()
def set_curve_bevel_resolution(object_name: str, bevel_resolution: int) -> str:
    """Set the number of sides used for the editable curve tube."""
    return _run("set_curve_bevel_resolution", {
        "object_name": object_name, "bevel_resolution": bevel_resolution,
    })


@mcp.tool()
def set_curve_resolution(object_name: str, spline_index: int, resolution_u: int) -> str:
    """Set the evaluated resolution of one editable spline."""
    return _run("set_curve_resolution", {
        "object_name": object_name, "spline_index": spline_index, "resolution_u": resolution_u,
    })


@mcp.tool()
def set_curve_cyclic(object_name: str, spline_index: int, cyclic: bool) -> str:
    """Open or close one editable spline."""
    return _run("set_curve_cyclic", {
        "object_name": object_name, "spline_index": spline_index, "cyclic": cyclic,
    })


@mcp.tool()
def create_primitive(
    primitive: str,
    name: str,
    location: list[float] | None = None,
    scale: list[float] | None = None,
) -> str:
    """Create a safe primitive: cube, uv_sphere, cylinder, cone or torus."""
    params: dict[str, Any] = {"primitive": primitive, "name": name}
    if location is not None:
        params["location"] = location
    if scale is not None:
        params["scale"] = scale
    return _run("create_primitive", params)


@mcp.tool()
def transform_object(
    object_name: str,
    location: list[float] | None = None,
    rotation_degrees: list[float] | None = None,
    scale: list[float] | None = None,
) -> str:
    """Set an object's location, Euler rotation in degrees and/or scale."""
    params: dict[str, Any] = {"object_name": object_name}
    if location is not None:
        params["location"] = location
    if rotation_degrees is not None:
        params["rotation_degrees"] = rotation_degrees
    if scale is not None:
        params["scale"] = scale
    return _run("transform_object", params)


@mcp.tool()
def delete_object(object_name: str) -> str:
    """Delete one named object using Blender's undo-aware object operator."""
    return _run("delete_object", {"object_name": object_name})


@mcp.tool()
def validate_mesh(object_name: str) -> str:
    """Measure boundary, multi-face non-manifold, loose and degenerate geometry separately."""
    return _run("validate_mesh", {"object_name": object_name})


@mcp.tool()
def save_blend(filepath: str | None = None) -> str:
    """Save the current blend file; provide an absolute .blend filepath for Save As."""
    return _run("save_blend", {"filepath": filepath})


@mcp.tool()
def undo_last_action() -> str:
    """Revert the most recent reversible Harness Blender operation."""
    return _run("undo")


@mcp.tool()
def capture_blender_screen() -> Image:
    """Capture Blender's current UI as PNG for visual inspection."""
    result = _connection.call("capture_screen")
    encoded = result.get("png_base64")
    if result.get("format") != "png" or not isinstance(encoded, str):
        raise RuntimeError("Blender returned an invalid screenshot response")
    try:
        data = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise RuntimeError("Blender returned invalid base64 screenshot data") from exc
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Blender screenshot response is not a PNG")
    return Image(data=data, format="png")


@mcp.resource("harness://v1/capabilities")
def capabilities() -> str:
    """Describe the exact limits of V1 so the agent does not invent tools."""
    payload: dict[str, Any] = {
        "version": "0.2.0-v1-curves",
        "transport": "typed operation + validated params; no Python source over socket",
        "tools": [
            "blender_ping",
            "inspect_scene",
            "inspect_object",
            "create_curve",
            "inspect_curve",
            "add_curve_point",
            "move_curve_point",
            "remove_curve_point",
            "set_curve_handle_type",
            "set_curve_handle_position",
            "set_curve_point_radius",
            "set_curve_point_tilt",
            "set_curve_bevel_depth",
            "set_curve_bevel_resolution",
            "set_curve_resolution",
            "set_curve_cyclic",
            "subdivide_curve",
            "resample_curve",
            "convert_curve_to_mesh",
            "create_primitive",
            "transform_object",
            "delete_object",
            "validate_mesh",
            "save_blend",
            "undo_last_action",
            "capture_blender_screen",
        ],
        "not_yet_available": [
            "arbitrary model-generated Python",
            "Geometry Nodes authoring",
            "sculpt operations",
            "skill retrieval",
            "automatic visual correction loop",
            "persistent memory",
        ],
    }
    return json.dumps(payload, indent=2)


@mcp.resource("harness://v3/skills")
def v3_skills_resource() -> str:
    """Read-only local skill metadata for V3 planning."""
    return list_blender_skills()


@mcp.resource("harness://v3/docs")
def v3_docs_resource() -> str:
    """Read-only catalog of the local official Blender documentation index."""
    return search_blender_docs("bmesh OR boolean OR curve", 10)


@mcp.resource("harness://v2/capabilities")
def v2_capabilities() -> str:
    """Describe the typed V2 mesh and material operations."""
    payload = {
        "version": "0.3.0-v2-mesh",
        "transport": "typed operation + validated params; no Python source over socket",
        "tools": [
            "inspect_mesh_detailed", "recalculate_normals", "flip_normals",
            "subdivide_mesh", "smooth_mesh", "merge_vertices", "bridge_edge_loops", "fill_hole",
            "boolean_union", "boolean_difference", "boolean_intersection", "voxel_remesh", "decimate_mesh",
            "create_material", "assign_material", "set_base_color", "set_roughness", "set_metallic", "set_alpha",
            "add_modifier", "set_modifier_parameter", "apply_modifier", "remove_modifier", "undo_last_action",
        ],
        "limits": {
            "vertex_or_edge_indices": "2-256 (bridge requires at least 6; fill requires at least 3)",
            "subdivide_cuts": "1-4", "smooth_factor": "0-1", "decimate_ratio": "0.01-1",
            "voxel_size": "0.001-1000", "material_values": "0-1",
        },
        "not_yet_available": ["arbitrary model-generated Python", "Geometry Nodes authoring", "sculpt operations"],
    }
    return json.dumps(payload, indent=2)


@mcp.resource("harness://v4/capabilities")
def v4_capabilities() -> str:
    """Describe the read-only V4 evaluation surface."""
    payload = {
        "version": "0.5.0-v4-evaluator",
        "read_only": True,
        "tools": [
            "inspect_scene_detailed", "evaluate_mesh", "evaluate_spatial",
            "evaluate_penetration", "evaluate_tubular", "diff_evaluation_reports",
        ],
        "limits": {
            "spatial_distance": "axis-aligned world bounding boxes",
            "penetration": "intersecting triangulated mesh surfaces",
            "tubular": "editable CURVE with bevel_depth",
        },
        "not_yet_available": ["automatic correction", "Geometry Nodes authoring", "sculpt operations"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
