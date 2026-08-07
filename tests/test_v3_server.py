import json

from harness_blender import server


def test_v3_router_tool_returns_narrow_result():
    result = json.loads(server.route_blender_task("conectar dos vasos"))
    assert "tubular-connections" in result["skills"]
    assert "bridge_edge_loops" in result["tools"]
    assert "create_material" not in result["tools"]


def test_v3_skill_and_docs_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_DOCS_INDEX", str(tmp_path / "docs.sqlite"))
    skills = json.loads(server.list_blender_skills("organic"))
    assert any(item["name"] == "tubular-connections" for item in skills)
    assert "Conexiones tubulares" in server.get_blender_skill("tubular-connections")
    docs = json.loads(server.search_blender_docs("boolean"))
    assert docs[0]["url"].startswith("https://docs.blender.org/")


def test_v3_acceptance_task_to_router_skills_docs_and_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_DOCS_INDEX", str(tmp_path / "docs.sqlite"))
    route = json.loads(server.route_blender_task("conectar estos dos vasos"))
    assert route["skills"] == ["tubular-connections", "smooth-transitions", "bridge-loops"]
    assert "bridge_edge_loops" in route["tools"]
    assert "Conexiones tubulares" in server.get_blender_skill(route["skills"][0])
    docs = json.loads(server.search_blender_docs("bmesh"))
    assert docs[0]["api_object"] == "bmesh"
    assert json.loads(server.v3_skills_resource())
