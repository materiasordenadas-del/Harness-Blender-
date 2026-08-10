"""Candidate Tripo provider adapter for Codex evaluation.

This file is NOT wired into Harness-Blender. It intentionally avoids Blender,
MCP registration and persistent credentials. Codex should decide whether this
shape fits the future Source Router / AssetDescriptor contract.

Upstream references:
- https://github.com/VAST-AI-Research/tripo-python-sdk
- https://github.com/VAST-AI-Research/tripo-3d-for-blender
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GeneratedAssetCandidate:
    provider: str
    task_id: str
    local_files: dict[str, str]
    generated: bool = True
    source_type: str = "external_3d_generator"
    license: str | None = None
    attribution: str | None = None


class TripoProviderCandidate:
    """Thin candidate wrapper around the official `tripo3d` Python SDK."""

    provider = "tripo"

    def __init__(self, api_key: str | None = None) -> None:
        # Import lazily so merely importing Harness-Blender never makes Tripo
        # a hard dependency.
        from tripo3d import TripoClient

        self._client = TripoClient(api_key=api_key)

    async def close(self) -> None:
        await self._client.close()

    async def generate_from_text(
        self,
        prompt: str,
        *,
        negative_prompt: str | None = None,
    ) -> str:
        """Create a Tripo task and return only its task id."""
        return await self._client.text_to_model(
            prompt=prompt,
            negative_prompt=negative_prompt,
        )

    async def generate_from_image(self, image_path: str | Path) -> str:
        """Create image-to-model task from one explicitly supplied file."""
        return await self._client.image_to_model(image=str(image_path))

    async def get_status(self, task_id: str) -> dict[str, Any]:
        """Return a small provider-neutral status payload."""
        task = await self._client.get_task(task_id)
        return {
            "provider": self.provider,
            "task_id": task_id,
            "status": str(task.status),
            "progress": getattr(task, "progress", None),
        }

    async def wait(self, task_id: str, *, timeout: float | None = None) -> Any:
        """Wait for completion using the official SDK polling implementation."""
        return await self._client.wait_for_task(task_id, timeout=timeout)

    async def download(
        self,
        task_id: str,
        output_dir: str | Path,
        *,
        timeout: float | None = None,
    ) -> GeneratedAssetCandidate:
        """Download results without importing anything into Blender."""
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)

        task = await self._client.wait_for_task(task_id, timeout=timeout)
        files = await self._client.download_task_models(task, str(destination))

        normalized = {
            str(model_type): str(path)
            for model_type, path in files.items()
            if path
        }
        return GeneratedAssetCandidate(
            provider=self.provider,
            task_id=task_id,
            local_files=normalized,
        )


# Deliberately absent:
# - MCP decorators
# - Blender bpy calls
# - automatic import into active scene
# - hard-coded API keys
# - automatic paid task creation on module import
