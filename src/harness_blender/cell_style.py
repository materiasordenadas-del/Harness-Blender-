"""Deterministic validation for the Harness Cell Diagram style contract."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

_REQUIRED_LAYERS = {
    "background",
    "cell_body",
    "organelles",
    "membrane",
    "membrane_proteins",
    "pathways",
    "arrows",
    "labels",
}

_REQUIRED_SYMBOLS = {
    "membrane",
    "cytoplasm",
    "organelle",
    "ion_channel",
    "pump",
    "exchanger",
    "receptor",
    "signaling_protein",
    "second_messenger",
    "ion",
    "vesicle",
    "activation_arrow",
    "inhibition_line",
    "transport_arrow",
    "label",
}


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _hex_color(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        raise ValueError(f"{name} must be #RRGGBB")
    try:
        int(value[1:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be #RRGGBB") from exc
    return value.upper()


def validate_style_contract(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("style contract must be a JSON object")

    for key in ("style_id", "version", "coordinate_system", "layers", "palette", "line_weights", "text", "symbols", "constraints"):
        if key not in data:
            raise ValueError(f"missing required field: {key}")

    coordinate_system = data["coordinate_system"]
    if coordinate_system != {"plane": "XY", "camera": "ORTHOGRAPHIC", "camera_axis": "-Z"}:
        raise ValueError("C0 requires XY + orthographic -Z camera")

    layers = data["layers"]
    if not isinstance(layers, dict) or set(layers) != _REQUIRED_LAYERS:
        raise ValueError("layers must match the C0 layer contract exactly")
    normalized_layers = {name: _finite_number(value, f"layers.{name}") for name, value in layers.items()}
    if len(set(normalized_layers.values())) != len(normalized_layers):
        raise ValueError("each C0 layer requires a unique Z value")

    palette = data["palette"]
    if not isinstance(palette, dict) or not palette:
        raise ValueError("palette must be a non-empty object")
    normalized_palette = {name: _hex_color(value, f"palette.{name}") for name, value in palette.items()}

    line_weights = data["line_weights"]
    if not isinstance(line_weights, dict) or not line_weights:
        raise ValueError("line_weights must be a non-empty object")
    normalized_weights = {}
    for name, value in line_weights.items():
        weight = _finite_number(value, f"line_weights.{name}")
        if not 0.0 < weight <= 1.0:
            raise ValueError(f"line_weights.{name} must be > 0 and <= 1")
        normalized_weights[name] = weight

    text = data["text"]
    if not isinstance(text, dict):
        raise ValueError("text must be an object")
    minimum = _finite_number(text.get("minimum_size"), "text.minimum_size")
    default = _finite_number(text.get("default_size"), "text.default_size")
    maximum = _finite_number(text.get("maximum_size"), "text.maximum_size")
    if not 0 < minimum <= default <= maximum:
        raise ValueError("text sizes must satisfy 0 < minimum <= default <= maximum")
    if text.get("family") != "sans":
        raise ValueError("C0 uses the logical sans font family")

    symbols = data["symbols"]
    if not isinstance(symbols, dict) or set(symbols) != _REQUIRED_SYMBOLS:
        raise ValueError("symbols must match the C0 symbol contract exactly")
    normalized_symbols: dict[str, dict[str, str]] = {}
    for name, symbol in symbols.items():
        if not isinstance(symbol, dict) or set(symbol) != {"layer", "material", "shape_family"}:
            raise ValueError(f"symbols.{name} requires layer, material and shape_family")
        layer = symbol["layer"]
        material = symbol["material"]
        shape_family = symbol["shape_family"]
        if layer not in normalized_layers:
            raise ValueError(f"symbols.{name}.layer is unknown")
        if material not in normalized_palette:
            raise ValueError(f"symbols.{name}.material is not in palette")
        if not isinstance(shape_family, str) or not shape_family.strip():
            raise ValueError(f"symbols.{name}.shape_family must be non-empty")
        normalized_symbols[name] = {"layer": layer, "material": material, "shape_family": shape_family}

    constraints = data["constraints"]
    if not isinstance(constraints, dict) or not all(value is True for value in constraints.values()):
        raise ValueError("all C0 constraints must be enabled")

    return {
        **data,
        "layers": normalized_layers,
        "palette": normalized_palette,
        "line_weights": normalized_weights,
        "symbols": normalized_symbols,
    }


def load_style_contract(path: Path) -> dict[str, Any]:
    return validate_style_contract(json.loads(path.read_text(encoding="utf-8")))


def symbol_contract(style: dict[str, Any], symbol_name: str) -> dict[str, Any]:
    normalized = validate_style_contract(style)
    try:
        symbol = normalized["symbols"][symbol_name]
    except KeyError as exc:
        raise ValueError(f"unknown cell diagram symbol: {symbol_name}") from exc
    return {
        **symbol,
        "z": normalized["layers"][symbol["layer"]],
        "color": normalized["palette"][symbol["material"]],
    }
