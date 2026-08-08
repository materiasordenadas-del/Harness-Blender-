"""Small deterministic benchmarks for checking task routing quality."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .task_packet import build_task_packet


def default_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "benchmarks.json"


def run_benchmarks(path: Path | None = None) -> list[dict[str, Any]]:
    cases = json.loads((path or default_path()).read_text(encoding="utf-8")).get("benchmarks")
    if not isinstance(cases, list):
        raise ValueError("benchmarks must contain a list")
    results = []
    for case in cases:
        if not isinstance(case, dict) or not {"id", "task", "skills", "forbidden_tools", "requires_visual"} <= set(case):
            raise ValueError("invalid benchmark case")
        packet = build_task_packet(case["task"])
        passed = packet["skills"] == case["skills"] and not set(packet["tools"]) & set(case["forbidden_tools"])
        if case["requires_visual"]:
            passed = passed and bool(packet["visual_evidence"])
        results.append({"id": case["id"], "passed": passed, "skills": packet["skills"], "tools": packet["tools"]})
    return results
