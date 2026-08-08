"""Bounded, deterministic task context assembled from V3 routing rules."""
from __future__ import annotations
from typing import Any
from .router import route

_PROFILES = {
"curve-fundamentals":{"preconditions":["Object is an editable CURVE","inspect_curve completed"],"validation":["inspect_curve after each handle change"],"visual_evidence":["capture_controlled_view only if smoothness is disputed"],"stop_conditions":["Curve remains editable","requested handle transition is confirmed"]},
"tubular-connections":{"preconditions":["Both target meshes are identified","boundary loops are compatible","inspect_mesh_detailed completed"],"validation":["validate_mesh","evaluate_mesh","recalculate_normals when needed"],"visual_evidence":["capture_controlled_view for organic continuity"],"stop_conditions":["No new boundary or non-manifold errors","visual transition passes or needs_review"]},
"procedural-tubes":{"preconditions":["Input object is CURVE","inspect_curve completed"],"validation":["inspect_geometry_node_tree","evaluate_tubular","evaluate_mesh on evaluated output"],"visual_evidence":["capture_controlled_view only if appearance is disputed"],"stop_conditions":["Named node group is attached","curve remains editable","evaluated mesh exists"]}}

def build_task_packet(task: str) -> dict[str, Any]:
    selected = route(task); skills = selected.skills[:3]
    profiles = [_PROFILES[name] for name in skills if name in _PROFILES]
    def fields(name: str) -> list[str]: return list(dict.fromkeys(value for profile in profiles for value in profile[name]))
    if not profiles:
        profiles = [{"preconditions":["inspect_scene completed"],"validation":["inspect_scene"],"visual_evidence":[],"stop_conditions":["Task requires a classified skill before editing"]}]
    return {"task":selected.task,"skills":list(skills),"tools":list(selected.tools),"docs":list(selected.docs),"preconditions":fields("preconditions"),"validation":fields("validation"),"visual_evidence":fields("visual_evidence"),"stop_conditions":fields("stop_conditions")}
