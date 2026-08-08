"""Read-only catalog of curated tool candidates; candidates are never executable."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .source_registry import load_sources

def default_path() -> Path:
    return Path(__file__).resolve().parents[2] / "catalog" / "tool_candidates.json"

def list_candidates(path: Path | None = None) -> list[dict[str, Any]]:
    candidates = json.loads((path or default_path()).read_text(encoding="utf-8")).get("candidates")
    required = {"name","phase","object_types","risk","recovery","validation","source","status"}
    if not isinstance(candidates, list): raise ValueError("tool catalog must contain a candidates list")
    sources, seen = load_sources(), set()
    for item in candidates:
        if not isinstance(item, dict) or set(item) != required: raise ValueError("each candidate must contain the complete safety schema")
        if item["name"] in seen or item["source"] not in sources: raise ValueError("candidate names and source references must be valid")
        if item["status"] not in {"candidate","approved","implemented","rejected"}: raise ValueError("candidate status is invalid")
        if not all(isinstance(item[key], str) and item[key] for key in ("risk","recovery","validation")): raise ValueError("candidate risk, recovery and validation are required")
        seen.add(item["name"])
    return candidates
