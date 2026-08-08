import pytest

from harness_blender.visual_evidence import validate_visual_comparison


def _comparison(status="pass"):
    return {
        "reference_id": "reference-vessel-01", "target_object": "Vessel_Result",
        "views": ["front", "right", "perspective"],
        "regions": [{"reference_region": "branch junction", "result_region": "branch junction", "assessment": "continuity matches at this scale"}],
        "review": {"status": status, "confidence": 0.9, "issues": []},
    }


def test_visual_comparison_requires_reference_three_views_and_mapped_regions():
    result = validate_visual_comparison(_comparison())
    assert result["views"] == ["front", "right", "perspective"]
    assert result["regions"][0]["result_region"] == "branch junction"


def test_visual_comparison_rejects_inconsistent_view_set():
    packet = _comparison()
    packet["views"] = ["front", "left", "perspective"]
    with pytest.raises(ValueError, match="exactly front"):
        validate_visual_comparison(packet)
