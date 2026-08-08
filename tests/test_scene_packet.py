from harness_blender.scene_packet import enrich_task_packet
from harness_blender.task_packet import build_task_packet


def test_curve_packet_uses_live_curve_state_and_keeps_task_tools_available():
    packet = enrich_task_packet(
        build_task_packet("ajusta los handles bezier"),
        {"scene": "Main", "objects": [{"name": "Path", "type": "CURVE", "metrics": {"point_count": 4}}]},
    )
    assert packet["precondition_checks"][0]["status"] == "passed"
    assert packet["allowed_tools"] == packet["tools"]
    assert packet["blockers"] == []


def test_curve_packet_blocks_editing_until_a_curve_exists():
    packet = enrich_task_packet(
        build_task_packet("ajusta los handles bezier"),
        {"scene": "Main", "objects": [{"name": "Cube", "type": "MESH", "metrics": {}}]},
    )
    assert packet["precondition_checks"][0]["status"] == "blocked"
    assert packet["allowed_tools"] == ["inspect_scene_detailed", "inspect_object"]
    assert packet["blocked_tools"] == packet["tools"]


def test_tubular_packet_requires_two_mesh_targets():
    packet = enrich_task_packet(
        build_task_packet("conecta dos tubos organicos"),
        {"scene": "Main", "objects": [{"name": "One", "type": "MESH", "metrics": {}}]},
    )
    assert packet["precondition_checks"][0]["requirement"] == "two MESH targets"
    assert packet["precondition_checks"][0]["status"] == "blocked"


def test_surface_scatter_packet_requires_surface_and_instance_meshes():
    packet = enrich_task_packet(
        build_task_packet("distribuye instancias sobre esta superficie"),
        {"scene": "Main", "objects": [{"name": "Surface", "type": "MESH", "metrics": {}}]},
    )
    assert packet["precondition_checks"][0]["status"] == "blocked"
