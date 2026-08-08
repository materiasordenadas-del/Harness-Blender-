import json
from pathlib import Path

import pytest

from harness_blender.cell_style import load_style_contract, symbol_contract, validate_style_contract


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "config" / "cell_diagram_style.json"


def test_repository_style_contract_is_valid():
    style = load_style_contract(STYLE)
    assert style["style_id"] == "harness-cell-diagram"
    assert style["coordinate_system"]["camera"] == "ORTHOGRAPHIC"
    assert style["layers"]["labels"] > style["layers"]["membrane"]


def test_symbol_contract_resolves_semantic_style():
    style = load_style_contract(STYLE)
    channel = symbol_contract(style, "ion_channel")
    assert channel["layer"] == "membrane_proteins"
    assert channel["z"] == style["layers"]["membrane_proteins"]
    assert channel["color"] == style["palette"]["membrane_protein"]


def test_unknown_symbol_is_rejected():
    style = load_style_contract(STYLE)
    with pytest.raises(ValueError, match="unknown cell diagram symbol"):
        symbol_contract(style, "random_red_blob")


def test_symbol_cannot_reference_unregistered_palette_entry():
    style = json.loads(STYLE.read_text(encoding="utf-8"))
    style["symbols"]["ion_channel"]["material"] = "invented_color"
    with pytest.raises(ValueError, match="not in palette"):
        validate_style_contract(style)


def test_arbitrary_font_family_is_rejected():
    style = json.loads(STYLE.read_text(encoding="utf-8"))
    style["text"]["family"] = "random-font"
    with pytest.raises(ValueError, match="logical sans"):
        validate_style_contract(style)


def test_layer_z_values_must_be_unique():
    style = json.loads(STYLE.read_text(encoding="utf-8"))
    style["layers"]["labels"] = style["layers"]["arrows"]
    with pytest.raises(ValueError, match="unique Z"):
        validate_style_contract(style)
