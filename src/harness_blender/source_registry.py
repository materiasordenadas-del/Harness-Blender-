"""Curated, versioned research-source registry with no network access."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def default_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "sources.json"

def load_sources(path: Path | None = None) -> dict[str, dict[str, Any]]:
    entries = json.loads((path or default_path()).read_text(encoding="utf-8")).get("sources")
    required = {"id","name","canonical_url","license","revision","allowed_uses","prohibited_uses"}
    if not isinstance(entries, list): raise ValueError("sources registry must contain a sources list")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != required: raise ValueError("each source must contain the complete curated-source schema")
        if not isinstance(entry["id"], str) or not entry["id"] or entry["id"] in result: raise ValueError("source id must be unique")
        if not isinstance(entry["canonical_url"], str) or not entry["canonical_url"].startswith("https://"): raise ValueError("source canonical_url must be HTTPS")
        result[entry["id"]] = entry
    return result
