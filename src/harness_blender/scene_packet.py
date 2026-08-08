"""Scene-aware gates for bounded Task Packets; contains no Blender calls."""
from __future__ import annotations

from typing import Any


def enrich_task_packet(packet: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    objects = snapshot.get("objects", [])
    curves = [item for item in objects if item.get("type") == "CURVE"]
    meshes = [item for item in objects if item.get("type") == "MESH"]
    requirements: list[tuple[str, bool, str]] = []
    skills = packet["skills"]
    if "curve-fundamentals" in skills:
        requirements.append(("at least one editable CURVE target", bool(curves), "Select or create a CURVE, then inspect it."))
    if "tubular-connections" in skills:
        requirements.append(("two MESH targets", len(meshes) >= 2, "Identify two compatible mesh boundary loops."))
    if "procedural-tubes" in skills:
        requirements.append(("one CURVE input", bool(curves), "Select or create a CURVE input."))
    checks = [
        {"requirement": name, "status": "passed" if passed else "blocked", "remedy": remedy}
        for name, passed, remedy in requirements
    ]
    blockers = [check["remedy"] for check in checks if check["status"] == "blocked"]
    allowed = list(packet["tools"]) if not blockers else ["inspect_scene_detailed", "inspect_object"]
    return {
        **packet,
        "scene": {"name": snapshot.get("scene"), "object_count": len(objects), "objects": objects},
        "precondition_checks": checks,
        "allowed_tools": allowed,
        "blocked_tools": [] if not blockers else list(packet["tools"]),
        "blockers": blockers,
    }
