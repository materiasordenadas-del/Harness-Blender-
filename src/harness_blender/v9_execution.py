"""Small, bounded V9 plan validation; it never calls Blender directly."""

from __future__ import annotations

from typing import Any

MAX_STEPS = 16
_BATCH_OPERATION = "execute_batch"


def validate_plan_steps(steps: Any, allowed_tools: list[str]) -> list[dict[str, Any]]:
    """Normalize a reviewed plan without granting tools outside its Task Packet."""
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError(f"steps must contain between 1 and {MAX_STEPS} items")
    allowed = set(allowed_tools)
    normalized: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or set(step) != {"operation", "params"}:
            raise ValueError(f"step {index + 1} must contain only operation and params")
        operation, params = step["operation"], step["params"]
        if not isinstance(operation, str) or operation not in allowed:
            raise ValueError(f"step {index + 1}: TOOL_NOT_ALLOWED_FOR_CURRENT_TASK")
        if operation == _BATCH_OPERATION or not isinstance(params, dict):
            raise ValueError(f"step {index + 1} is invalid")
        normalized.append({"operation": operation, "params": params})
    return normalized
