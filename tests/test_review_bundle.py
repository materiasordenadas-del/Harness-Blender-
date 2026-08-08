import json

import pytest

from harness_blender.review_bundle import build_review_bundle, save_review_bundle


def _snapshot(metrics):
    return {"scene": "Main", "objects": [{"name": "Tube", "type": "MESH", "metrics": metrics}]}


def test_review_bundle_passes_and_preserves_per_object_diff():
    bundle = build_review_bundle(
        _snapshot({"vertices": 10, "self_intersections": 0, "boundary_edges": 0}),
        _snapshot({"vertices": 12, "self_intersections": 0, "boundary_edges": 0}),
        ["bridge_loops"],
    )
    assert bundle["status"] == "PASS"
    assert bundle["object_diffs"]["Tube"]["vertices_delta"] == 2


def test_review_bundle_fails_on_deterministic_geometry_regression():
    bundle = build_review_bundle(
        _snapshot({"self_intersections": 0, "boundary_edges": 0}),
        _snapshot({"self_intersections": 1, "boundary_edges": 0}),
        ["bridge_loops"],
    )
    assert bundle["status"] == "FAIL"
    assert bundle["regressions"][0]["field"] == "self_intersections"


def test_review_bundle_uses_visual_gate_when_required():
    bundle = build_review_bundle(_snapshot({}), _snapshot({}), ["capture_controlled_view"], visual_required=True)
    assert bundle["status"] == "NEEDS_REVIEW"


def test_review_bundle_is_saved_once_as_immutable_evidence(tmp_path):
    bundle = build_review_bundle(_snapshot({}), _snapshot({}), ["inspect_scene_detailed"])
    saved = save_review_bundle(bundle, "review-01", tmp_path)
    assert json.loads(saved.read_text(encoding="utf-8"))["status"] == "PASS"
    with pytest.raises(FileExistsError):
        save_review_bundle(bundle, "review-01", tmp_path)
