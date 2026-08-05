"""MCP server exposing the V0 Blender semantic toolset."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP, Image

from . import code_templates
from .connection import BlenderConnection

mcp = FastMCP("Harness Blender V0")
_connection = BlenderConnection()


def _run(code: str) -> str:
    return json.dumps(_connection.execute(code), ensure_ascii=False, indent=2)


@mcp.tool()
def blender_ping() -> str:
    """Check that Blender and the local bridge are ready."""
    return _run(code_templates.ping())


@mcp.tool()
def inspect_scene() -> str:
    """Return a compact, structured description of the current Blender scene."""
    return _run(code_templates.inspect_scene())


@mcp.tool()
def inspect_object(object_name: str) -> str:
    """Inspect one object, including transform, mesh counts, modifiers and materials."""
    return _run(code_templates.inspect_object(object_name))


@mcp.tool()
def create_primitive(
    primitive: str,
    name: str,
    location: list[float] | None = None,
    scale: list[float] | None = None,
) -> str:
    """Create a safe primitive: cube, uv_sphere, cylinder, cone or torus."""
    return _run(
        code_templates.create_primitive(
            primitive,
            name,
            location or [0.0, 0.0, 0.0],
            scale or [1.0, 1.0, 1.0],
        )
    )


@mcp.tool()
def transform_object(
    object_name: str,
    location: list[float] | None = None,
    rotation_degrees: list[float] | None = None,
    scale: list[float] | None = None,
) -> str:
    """Set an object's location, Euler rotation in degrees and/or scale."""
    if location is None and rotation_degrees is None and scale is None:
        raise ValueError("Provide at least one transform field")
    return _run(
        code_templates.transform_object(
            object_name,
            location,
            rotation_degrees,
            scale,
        )
    )


@mcp.tool()
def delete_object(object_name: str) -> str:
    """Delete one named object and unlink it from the blend file."""
    return _run(code_templates.delete_object(object_name))


@mcp.tool()
def validate_mesh(object_name: str) -> str:
    """Measure basic mesh integrity: boundary, non-manifold, loose and degenerate geometry."""
    return _run(code_templates.validate_mesh(object_name))


@mcp.tool()
def save_blend(filepath: str | None = None) -> str:
    """Save the current blend file; provide an absolute filepath for Save As."""
    return _run(code_templates.save_blend(filepath))


@mcp.tool()
def undo_last_action() -> str:
    """Ask Blender to undo the most recent undoable operation."""
    return _run(code_templates.undo())


@mcp.tool()
def capture_blender_screen() -> Image:
    """Capture Blender's current UI as PNG for visual inspection."""
    target = Path(tempfile.gettempdir()) / "harness_blender_screen.png"
    _connection.execute(code_templates.capture_screen(str(target)))
    if not target.exists():
        raise RuntimeError("Blender reported success but did not create the screenshot")
    data = target.read_bytes()
    try:
        target.unlink()
    except OSError:
        pass
    return Image(data=data, format="png")


@mcp.resource("harness://v0/capabilities")
def capabilities() -> str:
    """Describe the exact limits of V0 so the agent does not invent tools."""
    payload: dict[str, Any] = {
        "version": "0.1.0",
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
