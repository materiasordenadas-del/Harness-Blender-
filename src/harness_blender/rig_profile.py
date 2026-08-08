"""Strict, dependency-free validation for V8 manual rig profiles."""

from __future__ import annotations

import math
from typing import Any

_ROLES = {"ROOT", "CORE", "BASE", "SEGMENT", "END_EFFECTOR"}


def validate(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict) or set(profile) != {"version", "object_name", "rig_name", "root", "articulations"}:
        raise ValueError("rig profile must contain the complete V8 schema")
    if profile["version"] != "v8":
        raise ValueError("rig profile version must be v8")
    if not all(isinstance(profile[field], str) and profile[field] for field in ("object_name", "rig_name", "root")):
        raise ValueError("object_name, rig_name and root must be non-empty strings")
    items = profile["articulations"]
    if not isinstance(items, list) or not items:
        raise ValueError("articulations must be a non-empty list")
    names: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) - {"name", "role", "parent", "head", "tail", "deform"} or not {"name", "role", "head", "tail"} <= set(item):
            raise ValueError("each articulation must use the V8 schema")
        if not isinstance(item["name"], str) or not item["name"] or item["name"] in names or item["role"] not in _ROLES:
            raise ValueError("articulation names must be unique and roles must be allowed")
        names.add(item["name"])
        for field in ("head", "tail"):
            value = item[field]
            if not isinstance(value, list) or len(value) != 3 or any(isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) for number in value):
                raise ValueError(f"{field} must contain three finite numbers")
        if item["head"] == item["tail"]:
            raise ValueError("articulation head and tail must differ")
        if "parent" in item and item["parent"] is not None and not isinstance(item["parent"], str):
            raise ValueError("parent must be a string or null")
        if "deform" in item and not isinstance(item["deform"], bool):
            raise ValueError("deform must be a boolean")
    if profile["root"] not in names:
        raise ValueError("root must name an articulation")
    if any(item.get("parent") not in names for item in items if item.get("parent") is not None):
        raise ValueError("each parent must name an articulation")
    return profile
