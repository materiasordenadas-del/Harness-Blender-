import json

from harness_blender import server


def test_v9_curve_execution_uses_tubular_snapshot(monkeypatch):
    calls = []

    def fake_call(operation, params=None):
        calls.append((operation, params))
        if operation == "inspect_scene_detailed":
            return {"scene": "Main", "objects": [{"name": "Path", "type": "CURVE"}]}
        if operation == "evaluate_tubular":
            return {"name": "Path", "point_count": 4}
        if operation == "execute_batch":
            return {"status": "completed", "results": [
                {"operation": "set_curve_handle_position", "result": {"updated": True}},
                {"operation": "inspect_scene_detailed", "result": {"scene": "Main", "objects": [{"name": "Path", "type": "CURVE"}]}},
                {"operation": "evaluate_tubular", "result": {"name": "Path", "point_count": 4}},
            ]}
        raise AssertionError(operation)

    monkeypatch.setattr(server._connection, "call", fake_call)
    prepared = json.loads(server.prepare_v9_task("ajusta los handles bezier", ["Path"]))
    result = json.loads(server.execute_v9_task(prepared["task_id"], [{"operation": "set_curve_handle_position", "params": {"object_name": "Path"}}]))
    assert result["status"] == "PASS"
    assert calls[-1][0] == "execute_batch"
    assert calls[-1][1]["steps"][-1]["operation"] == "evaluate_tubular"
