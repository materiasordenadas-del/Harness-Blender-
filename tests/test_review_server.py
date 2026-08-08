import json

from harness_blender import server


def test_snapshot_and_packet_use_actual_scene_object_types(monkeypatch):
    calls = []

    def fake_call(operation, params=None):
        calls.append((operation, params))
        if operation == "inspect_scene_detailed":
            return {"scene": "Main", "objects": [{"name": "Path", "type": "CURVE"}]}
        if operation == "evaluate_tubular":
            return {"point_count": 4, "radius": 0.2}
        raise AssertionError(operation)

    monkeypatch.setattr(server._connection, "call", fake_call)
    packet = json.loads(server.build_scene_task_packet("ajusta los handles bezier"))
    assert packet["scene"]["objects"][0]["name"] == "Path"
    assert packet["allowed_tools"] == packet["tools"]
    assert calls == [
        ("inspect_scene_detailed", None),
        ("evaluate_tubular", {"object_name": "Path", "spline_index": 0}),
    ]


def test_snapshot_keeps_scene_evidence_when_curve_metrics_are_unavailable(monkeypatch):
    def fake_call(operation, params=None):
        if operation == "inspect_scene_detailed":
            return {"scene": "Main", "objects": [{"name": "EmptyPath", "type": "CURVE"}]}
        raise RuntimeError("curve must contain at least two points")

    monkeypatch.setattr(server._connection, "call", fake_call)
    snapshot = json.loads(server.capture_scene_snapshot())
    assert "metrics_error" in snapshot["objects"][0]


def test_visual_review_capture_plan_requires_three_fixed_views():
    plan = json.loads(server.build_visual_review_capture_plan("Tube"))
    assert plan["focus_object"] == "Tube"
    assert plan["views"] == ["front", "right", "perspective"]
