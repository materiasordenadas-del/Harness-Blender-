"""Local, read-only registry for Harness Blender Markdown skills."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Skill:
    name: str
    domain: str
    applies_to: tuple[str, ...]
    tools: tuple[str, ...]
    path: Path
    sources: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    validation: tuple[str, ...] = ()
    visual_evidence: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    common_failures: tuple[str, ...] = ()
    safety_limits: tuple[str, ...] = ()


def default_skills_root() -> Path:
    return Path(__file__).resolve().parents[2] / "skills"


def default_contract_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "skill_contracts.json"


def _contracts(path: Path | None = None) -> dict[str, dict[str, Any]]:
    data = json.loads((path or default_contract_path()).read_text(encoding="utf-8"))
    contracts = data.get("skills")
    if not isinstance(contracts, dict):
        raise ValueError("skill contracts must contain a skills object")
    required = {"domain", "applies_to", "tools", "sources", "aliases", "preconditions", "validation", "visual_evidence", "stop_conditions", "common_failures", "safety_limits"}
    for name, contract in contracts.items():
        if not isinstance(name, str) or not isinstance(contract, dict) or set(contract) != required:
            raise ValueError("each skill contract must contain the complete structured schema")
        list_fields = required - {"domain"}
        if not isinstance(contract["domain"], str) or not contract["domain"] or not all(isinstance(contract[key], list) and all(isinstance(value, str) and value for value in contract[key]) for key in list_fields):
            raise ValueError("skill contract values must be non-empty string lists")
    return contracts


def _list(value: str) -> tuple[str, ...]:
    value = value.strip().strip("[]")
    return tuple(item.strip().strip("'\"") for item in value.split(",") if item.strip())


def _metadata(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def discover(root: Path | None = None) -> list[Skill]:
    root = root or default_skills_root()
    contracts = _contracts()
    skills: list[Skill] = []
    for path in sorted(root.rglob("*.md")):
        meta = _metadata(path)
        name = meta.get("name", path.stem.replace("_", "-"))
        contract = contracts.get(name)
        if contract is None:
            raise ValueError(f"Missing structured contract for skill: {name}")
        skills.append(Skill(
            name, contract["domain"], tuple(contract["applies_to"]), tuple(contract["tools"]), path,
            tuple(contract["sources"]), tuple(contract["aliases"]), tuple(contract["preconditions"]),
            tuple(contract["validation"]), tuple(contract["visual_evidence"]), tuple(contract["stop_conditions"]),
            tuple(contract["common_failures"]), tuple(contract["safety_limits"]),
        ))
    return skills


def find(name: str, root: Path | None = None) -> Skill:
    for skill in discover(root):
        if skill.name == name:
            return skill
    raise KeyError(f"Unknown skill: {name}")


def content(name: str, root: Path | None = None) -> str:
    return find(name, root).path.read_text(encoding="utf-8")
