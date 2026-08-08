"""Deterministic intent router built from structured skill contracts."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from .skill_registry import find


@dataclass(frozen=True)
class Route:
    task: str
    skills: tuple[str, ...]
    tools: tuple[str, ...]
    docs: tuple[str, ...]


@dataclass(frozen=True)
class Intent:
    name: str
    skills: tuple[str, ...]
    priority: int
    docs: tuple[str, ...]


_INTENTS = (
    Intent("bezier_handles", ("curve-fundamentals", "smooth-curves"), 50, ("https://docs.blender.org/api/current/bpy.types.BezierSplinePoint.html",)),
    Intent("procedural_tubes", ("procedural-tubes",), 45, ("https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/geometry/index.html",)),
    Intent("surface_scatter", ("surface-scatter",), 45, ("https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/geometry/operations/distribute_points_on_faces.html",)),
    Intent("visual_review", ("visual-review",), 40, ("https://docs.blender.org/manual/en/latest/editors/3dview/navigate/views.html",)),
    Intent("tubular_connection", ("tubular-connections", "smooth-transitions", "bridge-loops"), 35, ("https://docs.blender.org/api/current/bmesh.ops.html",)),
    Intent("boolean", ("booleans",), 30, ("https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/boolean.html",)),
    Intent("normals", ("normals",), 25, ("https://docs.blender.org/manual/en/latest/modeling/meshes/editing/mesh/normals.html",)),
)


def _words(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return set(re.findall(r"[a-z0-9]+", normalized))


def _score(intent: Intent, words: set[str]) -> int:
    score = 0
    for name in intent.skills:
        for alias in find(name).aliases:
            alias_words = _words(alias)
            if alias_words and alias_words <= words:
                score += len(alias_words)
    return score


def _tools(names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(tool for name in names for tool in find(name).tools))


def route(task: str) -> Route:
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be a non-empty string")
    words = _words(task)
    scored = [(intent, _score(intent, words)) for intent in _INTENTS]
    selected, score = max(scored, key=lambda item: (item[1], item[0].priority))
    if score == 0:
        return Route(task, (), ("inspect_scene",), ())
    return Route(task, selected.skills, _tools(selected.skills), selected.docs)
