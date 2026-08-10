"""Sketchfab provider candidate for Harness-Blender evaluation.

This file intentionally stops before Blender import. It focuses on search,
metadata, license/attribution preservation and authorized download staging.

Official references:
- https://github.com/sketchfab/blender-plugin
- https://sketchfab.com/developers/data-api
- https://sketchfab.com/developers/download-api
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


API_BASE = "https://api.sketchfab.com/v3"
USER_AGENT = "Harness-Blender-Research/0.1"


@dataclass(slots=True, frozen=True)
class SketchfabAssetCandidate:
    uid: str
    name: str
    viewer_url: str | None
    downloadable: bool
    license: str | None
    creator_username: str | None
    creator_profile_url: str | None
    face_count: int | None = None
    vertex_count: int | None = None
    source: str = "Sketchfab"

    @property
    def attribution(self) -> str:
        creator = self.creator_username or "unknown creator"
        return f"{self.name} by {creator} — Sketchfab"


@dataclass(slots=True, frozen=True)
class SketchfabDownloadCandidate:
    format: str
    url: str
    size: int | None
    expires_seconds: int | None


class SketchfabAdapterCandidate:
    def __init__(
        self,
        *,
        access_token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    def _json_get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        require_auth: bool = False,
    ) -> Any:
        if require_auth and not self.access_token:
            raise PermissionError("Sketchfab download requires an authenticated user token")

        query = f"?{urlencode(params, doseq=True)}" if params else ""
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        request = Request(f"{API_BASE}{path}{query}", headers=headers, method="GET")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.load(response)

    def search_models(
        self,
        query: str,
        *,
        downloadable_only: bool = True,
        limit: int = 20,
    ) -> list[SketchfabAssetCandidate]:
        """Search models using the official `/v3/search?type=models` endpoint."""
        payload = self._json_get(
            "/search",
            params={
                "type": "models",
                "q": query,
                "downloadable": str(downloadable_only).lower(),
            },
        )
        results = payload.get("results", []) if isinstance(payload, dict) else []
        return [self._normalize_model(item) for item in results[: max(0, limit)]]

    def get_model(self, uid: str) -> SketchfabAssetCandidate:
        payload = self._json_get(f"/models/{quote(uid, safe='')}")
        if not isinstance(payload, dict):
            raise TypeError("Unexpected Sketchfab model response")
        return self._normalize_model(payload)

    def list_licenses(self) -> list[dict[str, Any]]:
        payload = self._json_get("/licenses")
        if not isinstance(payload, dict):
            raise TypeError("Unexpected Sketchfab licenses response")
        results = payload.get("results", [])
        return [item for item in results if isinstance(item, dict)]

    def request_download(self, uid: str) -> list[SketchfabDownloadCandidate]:
        """Request temporary download links. Requires authenticated user token."""
        payload = self._json_get(
            f"/models/{quote(uid, safe='')}/download",
            require_auth=True,
        )
        if not isinstance(payload, dict):
            raise TypeError("Unexpected Sketchfab download response")

        candidates: list[SketchfabDownloadCandidate] = []
        for fmt, info in payload.items():
            if not isinstance(info, dict) or not isinstance(info.get("url"), str):
                continue
            candidates.append(
                SketchfabDownloadCandidate(
                    format=str(fmt),
                    url=info["url"],
                    size=info.get("size") if isinstance(info.get("size"), int) else None,
                    expires_seconds=(
                        info.get("expires") if isinstance(info.get("expires"), int) else None
                    ),
                )
            )
        return candidates

    def download_archive(
        self,
        candidate: SketchfabDownloadCandidate,
        destination: str | Path,
        *,
        max_bytes: int | None = None,
    ) -> Path:
        """Download one temporary archive URL into explicit staging path.

        The temporary URL itself already authorizes the download, so this request
        deliberately does not forward the user's OAuth token to the storage host.
        """
        if max_bytes is not None and candidate.size is not None and candidate.size > max_bytes:
            raise ValueError(
                f"Sketchfab archive is larger than allowed: {candidate.size} > {max_bytes}"
            )

        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")

        request = Request(candidate.url, headers={"User-Agent": USER_AGENT}, method="GET")
        downloaded = 0
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response, temporary.open("wb") as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if max_bytes is not None and downloaded > max_bytes:
                        raise ValueError("Sketchfab archive exceeded max_bytes while downloading")
                    out.write(chunk)
            temporary.replace(target)
            return target
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _normalize_model(payload: dict[str, Any]) -> SketchfabAssetCandidate:
        user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
        license_value = payload.get("license")
        if isinstance(license_value, dict):
            license_value = (
                license_value.get("label")
                or license_value.get("slug")
                or license_value.get("fullName")
            )
        if license_value is not None:
            license_value = str(license_value)

        return SketchfabAssetCandidate(
            uid=str(payload.get("uid") or ""),
            name=str(payload.get("name") or payload.get("uid") or "unnamed"),
            viewer_url=(
                str(payload["viewerUrl"]) if payload.get("viewerUrl") else None
            ),
            downloadable=bool(payload.get("isDownloadable")),
            license=license_value,
            creator_username=(
                str(user["username"]) if user.get("username") else None
            ),
            creator_profile_url=(
                str(user["profileUrl"]) if user.get("profileUrl") else None
            ),
            face_count=(
                payload.get("faceCount") if isinstance(payload.get("faceCount"), int) else None
            ),
            vertex_count=(
                payload.get("vertexCount")
                if isinstance(payload.get("vertexCount"), int)
                else None
            ),
        )


# Deliberately absent:
# - OAuth login UI / token persistence
# - archive extraction (must be path-traversal-safe if added)
# - bpy import
# - automatic acceptance into a production scene
# - license filtering policy (Codex must define it explicitly)
