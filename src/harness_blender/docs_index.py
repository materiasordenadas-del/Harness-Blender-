"""Small SQLite FTS index containing only official Blender documentation."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class DocEntry:
    title: str
    url: str
    api_object: str
    version: str
    text: str
    keywords: str


SEED_DOCS = (
    DocEntry("BMesh Module", "https://docs.blender.org/api/current/bmesh.html", "bmesh", "current", "BMesh provides mesh connectivity and editing operations through a mesh converted to BMesh.", "bmesh topology bridge loops fill merge"),
    DocEntry("Boolean Modifier", "https://docs.blender.org/manual/en/dev/modeling/modifiers/generate/booleans.html", "BooleanModifier", "current", "The Boolean modifier combines meshes through union, difference and intersection operations.", "boolean union difference intersection manifold"),
    DocEntry("Curve", "https://docs.blender.org/api/current/bpy.types.Curve.html", "bpy.types.Curve", "current", "Curve datablocks store splines and bevel settings for editable curve geometry.", "curve spline bevel radius tilt"),
    DocEntry("BezierSplinePoint", "https://docs.blender.org/api/current/bpy.types.BezierSplinePoint.html", "bpy.types.BezierSplinePoint", "current", "Bezier spline points expose coordinates, handle types and handle positions for editable curve continuity.", "bezier handle left right aligned auto vector curve"),
    DocEntry("GeometryNodeTree", "https://docs.blender.org/api/current/bpy.types.GeometryNodeTree.html", "bpy.types.GeometryNodeTree", "current", "Geometry node trees expose node interfaces, sockets and links for procedural geometry modifiers.", "geometry nodes tree interface socket curve to mesh resample"),
)


def _official(url: str) -> bool:
    return urlparse(url).scheme == "https" and urlparse(url).netloc == "docs.blender.org"


def initialize(path: Path, entries: tuple[DocEntry, ...] = SEED_DOCS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS blender_docs USING fts5(title, url UNINDEXED, api_object, version UNINDEXED, text, keywords)")
        connection.execute("DELETE FROM blender_docs")
        for entry in entries:
            if not _official(entry.url):
                raise ValueError("Documentation URL must be an official docs.blender.org HTTPS URL")
            connection.execute("INSERT INTO blender_docs VALUES (?, ?, ?, ?, ?, ?)", (entry.title, entry.url, entry.api_object, entry.version, entry.text, entry.keywords))


def search(path: Path, query: str, limit: int = 5) -> list[dict[str, str]]:
    if not query.strip():
        return []
    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT title, url, api_object, version, text, keywords FROM blender_docs WHERE blender_docs MATCH ? LIMIT ?", (query, limit)).fetchall()
    keys = ("title", "url", "api_object", "version", "text", "keywords")
    return [dict(zip(keys, row)) for row in rows]
