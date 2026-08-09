"""Pure validation and bounded control for V5 visual-review reports."""

from __future__ import annotations

import math
from typing import Any

_STATUSES = {"pass", "needs_correction", "needs_review"}


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and between 0 and 1")
    return result


def _text(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must contain 1-{maximum} characters")
    return value.strip()


def validate_visual_review(review: Any) -> dict[str, Any]:
    """Validate an observation supplied by a vision-capable MCP client."""
    if not isinstance(review, dict):
        raise ValueError("review must be a JSON object")
    unknown = set(review) - {"status", "confidence", "issues"}
    if unknown:
        raise ValueError(f"review has unknown field(s): {', '.join(sorted(unknown))}")
    status = review.get("status")
    if status not in _STATUSES:
        raise ValueError("status must be pass, needs_correction or needs_review")
    confidence = _number(review.get("confidence"), "confidence")
    issues = review.get("issues", [])
    if not isinstance(issues, list) or len(issues) > 20:
        raise ValueError("issues must be a list with at most 20 items")
    normalized: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict) or set(issue) != {"region", "problem", "severity"}:
            raise ValueError("each issue must contain only region, problem and severity")
        normalized.append({
            "region": _text(issue["region"], "issue.region", 255),
            "problem": _text(issue["problem"], "issue.problem", 500),
            "severity": _number(issue["severity"], "issue.severity"),
        })
    if status == "pass" and normalized:
        raise ValueError("pass review must not contain issues")
    if status == "needs_correction" and not normalized:
        raise ValueError("needs_correction review requires at least one issue")
    return {"status": status, "confidence": confidence, "issues": normalized}


def next_visual_review_step(review: Any, iteration: int = 0, max_iterations: int = 3) -> dict[str, Any]:
    """Return a bounded next step; this function never edits Blender."""
    if isinstance(iteration, bool) or not isinstance(iteration, int) or iteration < 0:
        raise ValueError("iteration must be a non-negative integer")
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= 5:
        raise ValueError("max_iterations must be an integer between 1 and 5")
    normalized = validate_visual_review(review)
    if normalized["status"] == "pass":
        return {"action": "stop", "reason": "visual_pass", "iteration": iteration, "max_iterations": max_iterations}
    if normalized["status"] == "needs_review":
        return {"action": "stop", "reason": "insufficient_visual_evidence", "iteration": iteration, "max_iterations": max_iterations}
    if iteration + 1 >= max_iterations:
        return {"action": "stop", "reason": "iteration_limit_reached", "iteration": iteration, "max_iterations": max_iterations}
    return {"action": "correction_allowed", "reason": "visual_issues_reported", "iteration": iteration, "next_iteration": iteration + 1, "max_iterations": max_iterations}
