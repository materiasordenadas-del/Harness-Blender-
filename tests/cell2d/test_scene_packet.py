import pytest

from harness_blender.cell2d.scene_packet import build_scene_packet


def _ready_plan():
    return {
        "reference": {"reference_id": "ref_123"},
        "target_style_id": "harness-cell-diagram",
        "instances": [{
            "instance_id": "ion_channel_001",
            "source_observation_id": "observation_1",
            "asset_id": "aqp2",
            "visual_category": "ion_channel",
            "domain": "apical",
            "bounds": [1.0, 2.0, 3.0, 4.0],
            "style": {"layer": "membrane_proteins", "material": "membrane_protein", "shape_family": "membrane_capsule", "z": 0.3, "color": "#F4C542"},
        }],
        "review_items": [],
        "status": "ready_for_blender",
    }


def test_scene_packet_preserves_canonical_identity_and_provenance():
    packet = build_scene_packet(_ready_plan())
    operation = packet["operations"][0]

    assert operation["operation"] == "create_cell2d_symbol"
    assert operation["params"]["object_name"] == "Cell2D_ion_channel_001"
    assert operation["params"]["asset_id"] == "aqp2"
    assert operation["params"]["reference_id"] == "ref_123"
    assert operation["params"]["z"] == 0.3


def test_scene_packet_rejects_unreviewed_plan():
    plan = _ready_plan()
    plan["status"] = "needs_review"
    plan["review_items"] = [{"reason": "low_confidence"}]

    with pytest.raises(ValueError, match="must be reviewed"):
        build_scene_packet(plan)
