import json

import pytest

from harness_blender.tool_catalog import list_candidates


def test_approval_requires_contract_and_all_test_gates(tmp_path):
    candidate = {
        "name": "candidate_tool", "phase": "V7", "object_types": ["MESH"], "risk": "risk",
        "recovery": "undo", "validation": "validate_mesh", "source": "blender_mcp_n8n", "status": "approved",
        "parameter_contract": "", "unit_test": "", "background_test": "", "gui_test": "", "mcp_e2e_test": "", "acceptance_scenario": "",
    }
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps({"candidates": [candidate]}), encoding="utf-8")
    with pytest.raises(ValueError, match="approved candidates"):
        list_candidates(path)


def test_candidate_can_remain_research_only_without_test_gates():
    assert all(item["status"] == "candidate" for item in list_candidates())
