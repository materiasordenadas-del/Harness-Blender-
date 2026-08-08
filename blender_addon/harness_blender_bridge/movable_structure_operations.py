# SPDX-License-Identifier: GPL-3.0-or-later
"""V8.0 reversible metadata for structures Harness can later move."""
from __future__ import annotations

import json
from typing import Any
import bpy

_KEY = "harness_movable_structure_v8"

def _object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type not in {"MESH", "CURVE"}:
        raise TypeError("movable structure requires an existing MESH or CURVE object")
    return obj

def _default(obj: bpy.types.Object, mode: str | None = None) -> dict[str, Any]:
    mode = mode or ("curve_guided" if obj.type == "CURVE" else "mesh_guided")
    if (obj.type == "CURVE") != (mode == "curve_guided"):
        raise ValueError(f"{obj.type} objects require {'curve_guided' if obj.type == 'CURVE' else 'mesh_guided'} mode")
    parts = [{"name": "Core", "movable": False, "state": "fixed"}]
    if obj.type == "CURVE":
        parts += [{"name": f"Process_{i:02d}", "movable": True, "state": "neutral", "spline_index": i - 1} for i in range(1, len(obj.data.splines) + 1)]
    return {"version": "v8.0", "object": obj.name, "mode": mode, "parts": parts,
            "status": "prepared" if obj.type == "CURVE" else "needs_review",
            "notes": [] if obj.type == "CURVE" else ["mesh_segmentation_is_planned_for_v8_2"]}

def _stored(obj: bpy.types.Object) -> dict[str, Any] | None:
    raw = obj.get(_KEY)
    try: return json.loads(raw) if isinstance(raw, str) else None
    except json.JSONDecodeError: return None

def inspect(params: dict[str, Any]) -> dict[str, Any]:
    obj = _object(params["object_name"]); stored = _stored(obj)
    return {"prepared": stored is not None, **(stored or _default(obj))}

def prepare(params: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    obj = _object(params["object_name"]); previous = obj.get(_KEY); structure = _default(obj, params.get("mode"))
    obj[_KEY] = json.dumps(structure, separators=(",", ":"))
    return {"prepared": True, **structure}, previous if isinstance(previous, str) else None

def list_parts(params: dict[str, Any]) -> dict[str, Any]:
    report = inspect(params)
    return {key: report[key] for key in ("object", "mode", "prepared", "parts")}

def get_part_state(params: dict[str, Any]) -> dict[str, Any]:
    report = inspect({"object_name": params["object_name"]})
    for part in report["parts"]:
        if part["name"] == params["part_name"]:
            return {"object": report["object"], "mode": report["mode"], "prepared": report["prepared"], "part": part}
    raise ValueError(f"part not found: {params['part_name']}")

def reset(params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    obj = _object(params["object_name"]); previous = obj.get(_KEY); structure = _stored(obj)
    if not isinstance(previous, str) or structure is None: raise ValueError("structure is not prepared")
    for part in structure["parts"]:
        if part["movable"]: part["state"] = "neutral"
    obj[_KEY] = json.dumps(structure, separators=(",", ":"))
    return {"object": obj.name, "reset": True, "parts": structure["parts"]}, previous

def restore_metadata(object_name: str, previous: str | None) -> None:
    obj = bpy.data.objects.get(object_name)
    if obj is None: return
    if previous is None: obj.pop(_KEY, None)
    else: obj[_KEY] = previous
