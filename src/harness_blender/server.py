"""MCP server exposing the V0 Blender semantic toolset."""

from __future__ import annotations

import base64
import json
from typing import Any

from mcp.server.fastmcp import FastMCP, Image

from .connection import BlenderConnection

mcp = FastMCP("Harness Blender V0")
_connection = BlenderConnection()


def _run(operation: str, params: dict[str, Any] | None = None) -> str:
    return json.dumps(_connection.call(operation, params), ensure_ascii=False, indent=2)


@mcp.tool()
def blender_ping() -> str:
    """Check that Blender and the local bridge are ready."""
    return _run("ping")


@mcp.tool()
def inspect_scene() -> str:
    """Return a compact, structured description of the current Blender scene."""
    return _run("inspect_scene")


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
    """Revert the most recent reversible Harness Blender V0 operation."""
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


@mcp.resource("harness://v0/capabilities")
def capabilities() -> str:
    """Describe the exact limits of V0 so the agent does not invent tools."""
    payload: dict[str, Any] = {
        "version": "0.1.0",
        "transport": "typed operation + validated params; no Python source over socket",
        "tools": [
            "blender_ping",
            "inspect_scene",
            "inspect_object",
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


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
