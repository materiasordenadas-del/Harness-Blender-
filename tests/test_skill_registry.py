from harness_blender.skill_registry import discover, find


def test_discovers_existing_skills_without_loading_content():
    skills = discover()
    names = {skill.name for skill in skills}
    assert "tubular-connections" in names
    assert "topology" in names


def test_skill_metadata_includes_relevant_tools():
    skill = find("tubular-connections")
    assert skill.domain == "organic"
    assert "inspect_mesh_detailed" in skill.tools


def test_discovers_v7_asset_validation_as_read_only_skill():
    skill = find("asset-validation")
    assert skill.domain == "production"
    assert skill.tools == (
        "inspect_scene_detailed",
        "inspect_mesh_detailed",
        "inspect_uv",
        "evaluate_mesh",
        "evaluate_asset_readiness",
    )
    assert skill.safety_limits == ("read-only; never edit geometry, UVs or modifiers",)


def test_discovers_v7_uv_inspection_as_read_only_skill():
    skill = find("uv-inspection")
    assert skill.domain == "production"
    assert skill.tools == ("inspect_mesh_detailed", "inspect_uv", "unwrap_uv")
