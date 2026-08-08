"""Deterministic V3 router from a short task to relevant skills and tools."""

from __future__ import annotations

from dataclasses import dataclass

from .skill_registry import find


@dataclass(frozen=True)
class Route:
    task: str
    skills: tuple[str, ...]
    tools: tuple[str, ...]
    docs: tuple[str, ...]


_RULES = (
    (
        ("geometry nodes", "geometry node", "nodos", "procedural", "procedimental", "tubo procedural"),
        ("procedural-tubes",),
        ("create_procedural_tube_setup", "inspect_geometry_node_tree", "evaluate_tubular", "evaluate_mesh"),
        ("https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/geometry/index.html",),
    ),
    (
        ("visual", "vista", "imagen", "captura", "referencia", "parece", "apariencia", "deformaci"),
        ("visual-review",),
        ("inspect_scene_detailed", "evaluate_mesh", "evaluate_tubular", "capture_controlled_view"),
        ("https://docs.blender.org/manual/en/latest/editors/3dview/navigate/views.html",),
    ),
    (
        ("conectar", "unir", "union", "vaso", "vasos", "tubo", "tubos", "bifurc"),
        ("tubular-connections", "smooth-transitions", "bridge-loops"),
        ("inspect_mesh_detailed", "bridge_edge_loops", "voxel_remesh", "smooth_mesh", "recalculate_normals", "validate_mesh"),
        ("https://docs.blender.org/api/current/bmesh.ops.html",),
    ),
    (
        ("boolean", "restar", "interseccion", "intersección"),
        ("booleans",),
        ("inspect_mesh_detailed", "boolean_union", "boolean_difference", "boolean_intersection", "validate_mesh"),
        ("https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/boolean.html",),
    ),
    (
        ("normal", "normales"),
        ("normals",),
        ("inspect_mesh_detailed", "recalculate_normals", "flip_normals"),
        ("https://docs.blender.org/manual/en/latest/modeling/meshes/editing/mesh/normals.html",),
    ),
)


def route(task: str) -> Route:
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be a non-empty string")
    lowered = task.casefold()
    selected = next((rule for rule in _RULES if any(word in lowered for word in rule[0])), None)
    if selected is None:
        return Route(task, (), ("inspect_scene",), ())
    _, names, tools, docs = selected
    # Validate only the selected skills; the router never returns guessed names.
    for name in names:
        find(name)
    return Route(task, names, tools, docs)
