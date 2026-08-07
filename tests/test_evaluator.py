from harness_blender.evaluator import diff_reports


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
