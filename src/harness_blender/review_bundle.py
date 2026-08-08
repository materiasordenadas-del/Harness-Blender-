"""AgentCAD-inspired evidence bundles without script execution or auto-editing."""
from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .evaluator import diff_reports
from .visual_review import validate_visual_review

_OPERATION = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_EVIDENCE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")


def _reports(snapshot: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("objects"), list):
        raise ValueError("snapshot must contain an objects list")
    result: dict[str, dict[str, Any]] = {}
    for item in snapshot["objects"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("snapshot objects require a name")
        report = item.get("metrics", {})
        if not isinstance(report, dict):
            raise ValueError("snapshot metrics must be an object")
        result[item["name"]] = report
    return result


def build_review_bundle(
    before: Any, after: Any, operations: Any, visual_review: Any | None = None, *, visual_required: bool = False
) -> dict[str, Any]:
    if not isinstance(operations, list) or len(operations) > 64 or not all(isinstance(item, str) and _OPERATION.fullmatch(item) for item in operations):
        raise ValueError("operations must contain at most 64 semantic operation names")
    before_reports, after_reports = _reports(before), _reports(after)
    object_diffs = {name: diff_reports(before_reports.get(name, {}), report) for name, report in after_reports.items()}
    regressions: list[dict[str, Any]] = []
    for name, report in after_reports.items():
        previous = before_reports.get(name, {})
        for field in ("self_intersections", "boundary_edges", "non_manifold_edges", "loose_edges", "degenerate_faces"):
            if field in report and int(report[field]) > int(previous.get(field, 0)):
                regressions.append({"object": name, "field": field, "before": previous.get(field, 0), "after": report[field]})
    normalized_visual = validate_visual_review(visual_review) if visual_review is not None else None
    if regressions:
        status, next_step = "FAIL", "undo or correct the deterministic regression"
    elif normalized_visual and normalized_visual["status"] == "needs_correction":
        status, next_step = "NEEDS_IMPROVEMENT", "apply one bounded correction and capture a new snapshot"
    elif normalized_visual and normalized_visual["status"] == "needs_review":
        status, next_step = "NEEDS_REVIEW", "capture more controlled views or request human review"
    elif visual_required and normalized_visual is None:
        status, next_step = "NEEDS_REVIEW", "visual evidence is required before completion"
    else:
        status, next_step = "PASS", "preserve the evidence bundle"
    return {
        "created_at": datetime.now(UTC).isoformat(), "operations": operations,
        "before": before, "after": after, "object_diffs": object_diffs,
        "regressions": regressions, "visual_review": normalized_visual,
        "status": status, "next_step": next_step,
    }


def save_review_bundle(bundle: dict[str, Any], evidence_id: str, directory: Path | None = None) -> Path:
    if not _EVIDENCE_ID.fullmatch(evidence_id):
        raise ValueError("evidence_id must contain 1-80 letters, numbers, _ or -")
    root = directory or Path(os.getenv("HARNESS_EVIDENCE_DIR", ""))
    if not root.is_absolute() or not root.is_dir():
        raise RuntimeError("HARNESS_EVIDENCE_DIR must be an existing absolute directory")
    target = root / f"{evidence_id}.json"
    if target.exists():
        raise FileExistsError("evidence_id already exists; bundles are immutable")
    target.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
