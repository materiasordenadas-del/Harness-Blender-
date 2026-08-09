import pytest

from harness_blender.rig_profile import validate


def profile():
    return {"version": "v8", "object_name": "Branch", "rig_name": "Rig", "root": "root", "articulations": [
        {"name": "root", "role": "ROOT", "head": [0, 0, 0], "tail": [0, 0, 1], "deform": False},
        {"name": "tip", "role": "END_EFFECTOR", "parent": "root", "head": [0, 0, 1], "tail": [0, 0, 2], "deform": True},
    ]}


def test_accepts_a_manual_v8_rig_profile():
    assert validate(profile())["root"] == "root"


def test_rejects_unknown_parent_and_zero_length_bone():
    invalid = profile(); invalid["articulations"][1]["parent"] = "missing"
    with pytest.raises(ValueError, match="parent"):
        validate(invalid)
    invalid = profile(); invalid["articulations"][1]["tail"] = [0, 0, 1]
    with pytest.raises(ValueError, match="head and tail"):
        validate(invalid)
