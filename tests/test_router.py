from harness_blender.router import route


def test_routes_tubular_connection_without_unrelated_tools():
    result = route("conectar estos dos vasos con una transición suave")
    assert result.skills == ("tubular-connections", "smooth-transitions", "bridge-loops")
    assert "bridge_edge_loops" in result.tools
    assert "voxel_remesh" in result.tools
    assert "create_material" not in result.tools
    assert result.docs[0].startswith("https://docs.blender.org/")


def test_routes_boolean_task():
    result = route("hacer una intersección boolean entre dos mallas")
    assert result.skills == ("booleans",)
    assert "boolean_intersection" in result.tools


def test_unknown_task_returns_safe_inspection_only():
    assert route("algo no clasificado").tools == ("inspect_scene",)
