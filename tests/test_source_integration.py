import json

from harness_blender import server
from harness_blender.skill_registry import find
from harness_blender.source_registry import load_sources
from harness_blender.task_packet import build_task_packet
from harness_blender.tool_catalog import list_candidates


def test_curated_sources_and_sourced_skills_are_consistent():
    sources = load_sources()
    assert "blender_api" in sources
    for name in ("curve-fundamentals", "smooth-curves", "tubular-connections", "procedural-tubes"):
        skill = find(name)
        assert skill.sources
        assert set(skill.sources) <= set(sources)


def test_tool_candidates_are_non_executable_and_safety_complete():
    candidates = list_candidates()
    assert all(item["status"] == "candidate" for item in candidates)
    assert all(item["risk"] and item["recovery"] and item["validation"] for item in candidates)


def test_task_packet_is_bounded_and_specific():
    first = build_task_packet("ajusta los handles Bezier de esta curva")
    second = build_task_packet("ajusta los handles Bezier de esta curva")
    assert first == second
    assert first["skills"] == ["curve-fundamentals", "smooth-curves"]
    assert len(first["skills"]) <= 3
    assert "create_material" not in first["tools"]
    assert first["validation"] == ["inspect_curve after each handle change"]


def test_task_packet_requires_v4_v5_evidence_for_tubular_and_procedural_work():
    tubular = build_task_packet("conectar dos vasos")
    assert "evaluate_mesh" in tubular["validation"]
    assert tubular["visual_evidence"]
    procedural = build_task_packet("crear tubo procedural con geometry nodes")
    assert "inspect_geometry_node_tree" in procedural["validation"]
    assert "evaluate_tubular" in procedural["validation"]


def test_source_and_candidate_mcp_tools_are_read_only():
    sources = json.loads(server.list_harness_sources())
    candidates = json.loads(server.list_tool_candidates("candidate"))
    packet = json.loads(server.build_blender_task_packet("tubo procedural"))
    assert any(item["id"] == "agentcad" for item in sources)
    assert len(candidates) == 3
    assert packet["skills"] == ["procedural-tubes"]
