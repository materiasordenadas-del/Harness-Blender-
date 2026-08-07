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
