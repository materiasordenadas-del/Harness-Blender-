import json
from pathlib import Path

from harness_blender.cell2d.reference import build_reconstruction_plan, load_asset_catalog, register_reference
from harness_blender.cell2d.style import load_style_contract


ROOT = Path(__file__).resolve().parents[2]
STYLE = ROOT / "cell2d" / "config" / "style.json"


def test_reference_plan_reuses_known_asset_and_routes_unknown_asset_to_review(tmp_path):
    image = tmp_path / "sketch.png"
    image.write_bytes(b"user sketch")
    reference = register_reference(image)
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({"assets": [{"asset_id": "aqp2", "display_name": "AQP2"}]}), encoding="utf-8")
    observations = [
        {"observation_id": "o1", "visual_category": "ion_channel", "domain": "apical", "bounds": [0, 0, 2, 1], "confidence": 0.95, "asset_id": "aqp2"},
        {"observation_id": "o2", "visual_category": "receptor", "domain": "basal", "bounds": [3, 0, 2, 1], "confidence": 0.95, "asset_id": "unknown"},
    ]

    plan = build_reconstruction_plan(reference, observations, load_asset_catalog(catalog_path), load_style_contract(STYLE))

    assert plan["status"] == "needs_review"
    assert plan["instances"][0]["asset_id"] == "aqp2"
    assert plan["instances"][0]["style"]["layer"] == "membrane_proteins"
    assert plan["review_items"] == [{"observation_id": "o2", "reason": "unknown_asset_id", "proposed_value": "unknown"}]


def test_low_confidence_reference_element_is_not_assigned_a_canonical_identity(tmp_path):
    image = tmp_path / "drawing.svg"
    image.write_text("<svg/>", encoding="utf-8")
    reference = register_reference(image)
    plan = build_reconstruction_plan(
        reference,
        [{"observation_id": "o1", "visual_category": "ion", "domain": "cytoplasm", "bounds": [0, 0, 1, 1], "confidence": 0.5, "asset_id": None}],
        {},
        load_style_contract(STYLE),
    )

    assert plan["instances"] == []
    assert plan["review_items"][0]["reason"] == "low_confidence"
