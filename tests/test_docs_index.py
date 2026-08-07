from pathlib import Path

import pytest

from harness_blender.docs_index import DocEntry, initialize, search


def test_indexes_and_searches_official_docs(tmp_path: Path):
    index = tmp_path / "docs.sqlite"
    initialize(index)
    results = search(index, "bridge topology")
    assert results[0]["api_object"] == "bmesh"
    assert results[0]["url"].startswith("https://docs.blender.org/")


def test_rejects_non_official_documentation(tmp_path: Path):
    entry = DocEntry("Bad", "https://example.com/doc", "bad", "1", "bad", "bad")
    with pytest.raises(ValueError, match="official"):
        initialize(tmp_path / "docs.sqlite", (entry,))
