"""Local, read-only registry for Harness Blender Markdown skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    domain: str
    applies_to: tuple[str, ...]
    tools: tuple[str, ...]
    path: Path


def default_skills_root() -> Path:
    return Path(__file__).resolve().parents[2] / "skills"


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
    skills: list[Skill] = []
    for path in sorted(root.rglob("*.md")):
        meta = _metadata(path)
        if not {"name", "domain", "applies_to", "tools"} <= set(meta):
            continue
        skills.append(Skill(meta["name"], meta["domain"], _list(meta["applies_to"]), _list(meta["tools"]), path))
    return skills


def find(name: str, root: Path | None = None) -> Skill:
    for skill in discover(root):
        if skill.name == name:
            return skill
    raise KeyError(f"Unknown skill: {name}")


def content(name: str, root: Path | None = None) -> str:
    return find(name, root).path.read_text(encoding="utf-8")
