from harness_blender.evaluator import diff_reports
from harness_blender.visual_review import next_visual_review_step, validate_visual_review


def test_diff_reports_calculates_count_and_volume_changes():
    result = diff_reports(
        {"vertices": 100, "faces": 90, "volume": 10.0, "surface_area": 20.0},
        {"vertices": 124, "faces": 112, "volume": 10.18, "surface_area": 22.0},
    )
    assert result["vertices_delta"] == 24
    assert result["faces_delta"] == 22
    assert result["volume_delta_percent"] == 1.8
    assert result["surface_area_delta_percent"] == 10.0


def test_diff_returns_none_percent_for_zero_baseline():
    assert diff_reports({"volume": 0}, {"volume": 1})["volume_delta_percent"] is None


def test_visual_review_is_normalized_and_allows_bounded_correction():
    review = validate_visual_review({
        "status": "needs_correction", "confidence": 0.88,
        "issues": [{"region": "distal_branch", "problem": "transition too abrupt", "severity": 0.7}],
    })
    assert next_visual_review_step(review, iteration=0)["action"] == "correction_allowed"
    assert next_visual_review_step(review, iteration=2)["reason"] == "iteration_limit_reached"


def test_visual_review_stops_for_pass_or_insufficient_evidence():
    assert next_visual_review_step({"status": "pass", "confidence": 1.0, "issues": []})["reason"] == "visual_pass"
    assert next_visual_review_step({"status": "needs_review", "confidence": 0.3, "issues": []})["reason"] == "insufficient_visual_evidence"


def test_visual_review_rejects_unfounded_or_unbounded_reports():
    import pytest

    with pytest.raises(ValueError, match="requires at least one issue"):
        validate_visual_review({"status": "needs_correction", "confidence": 0.8, "issues": []})
    with pytest.raises(ValueError, match="between 1 and 5"):
        next_visual_review_step({"status": "pass", "confidence": 1.0, "issues": []}, max_iterations=6)
