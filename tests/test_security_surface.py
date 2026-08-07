from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "blender_addon" / "harness_blender_bridge" / "__init__.py"
CONNECTION = ROOT / "src" / "harness_blender" / "connection.py"


def test_bridge_contains_no_exec_call_or_code_request_field():
    source = BRIDGE.read_text(encoding="utf-8")
    assert "exec(" not in source
    assert 'request.get("code")' not in source
    assert "strict_json" not in source


def test_external_connection_sends_operation_not_code():
    source = CONNECTION.read_text(encoding="utf-8")
    assert '"type": "operation"' in source
    assert '"operation": operation' in source
    assert '"code"' not in source


def test_no_public_fixed_token_remains_in_runtime_files():
    for path in (BRIDGE, CONNECTION):
        assert "harness-v0-local" not in path.read_text(encoding="utf-8")
