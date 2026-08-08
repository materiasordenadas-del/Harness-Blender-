"""Bounded, deterministic task context assembled from V3 routing rules."""
from __future__ import annotations
from typing import Any
from .router import route
from .skill_registry import find

def build_task_packet(task: str) -> dict[str, Any]:
    selected = route(task); skills = selected.skills[:3]
    profiles = [find(name) for name in skills]
    def fields(name: str) -> list[str]: return list(dict.fromkeys(value for profile in profiles for value in getattr(profile, name)))
    if not profiles:
        return {"task": selected.task, "skills": [], "tools": list(selected.tools), "docs": list(selected.docs), "preconditions": ["inspect_scene completed"], "validation": ["inspect_scene"], "visual_evidence": [], "stop_conditions": ["Task requires a classified skill before editing"], "common_failures": ["task intent is unknown"], "safety_limits": ["inspection only"]}
    return {"task":selected.task,"skills":list(skills),"tools":list(selected.tools),"docs":list(selected.docs),"preconditions":fields("preconditions"),"validation":fields("validation"),"visual_evidence":fields("visual_evidence"),"stop_conditions":fields("stop_conditions"),"common_failures":fields("common_failures"),"safety_limits":fields("safety_limits")}
