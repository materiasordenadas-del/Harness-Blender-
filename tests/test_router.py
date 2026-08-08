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


def test_routes_visual_review_without_editing_tools():
    result = route("revisa visualmente si esta bifurcación parece abrupta")
    assert result.skills == ("visual-review",)
    assert result.tools == ("inspect_scene_detailed", "evaluate_mesh", "evaluate_tubular", "capture_controlled_view")
    assert "smooth_mesh" not in result.tools


def test_unknown_task_returns_safe_inspection_only():
    assert route("algo no clasificado").tools == ("inspect_scene",)
