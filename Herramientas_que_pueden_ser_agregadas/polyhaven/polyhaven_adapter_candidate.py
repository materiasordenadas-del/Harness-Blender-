"""Small Poly Haven API adapter candidate for Harness-Blender evaluation.

Not wired into MCP or Blender. Uses only Python stdlib.
Official API: https://api.polyhaven.com
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote
from urllib.request import Request, urlopen


API_BASE = "https://api.polyhaven.com"
DEFAULT_USER_AGENT = "Harness-Blender-Research/0.1"


@dataclass(slots=True, frozen=True)
class PolyHavenAssetCandidate:
    asset_id: str
    name: str
    asset_type: int | None
    category: str | None
    tags: tuple[str, ...]
    polycount: int | None
    dimensions: tuple[float, ...] | None
    thumbnail_url: str | None
    source: str = "Poly Haven"
    asset_license: str = "CC0"


@dataclass(slots=True, frozen=True)
class PolyHavenFileCandidate:
    url: str
    size: int | None = None
    md5: str | None = None
    key_path: tuple[str, ...] = ()


class PolyHavenAdapterCandidate:
    """Read/search/download boundary for Poly Haven's public API."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not user_agent.strip():
            raise ValueError("Poly Haven requires an identifiable User-Agent")
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def _json_get(self, path: str) -> Any:
        request = Request(
            f"{API_BASE}{path}",
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.load(response)

    def list_assets(self) -> dict[str, dict[str, Any]]:
        """Return the official `/assets` catalog as provider-native metadata."""
        payload = self._json_get("/assets")
        if not isinstance(payload, dict):
            raise TypeError("Unexpected Poly Haven /assets response")
        return payload

    def search(
        self,
        query: str,
        *,
        asset_types: set[int] | None = None,
        limit: int = 20,
    ) -> list[PolyHavenAssetCandidate]:
        """Simple deterministic local search over the fetched metadata catalog.

        Asset type values currently used by Poly Haven metadata include:
        0 = HDRI, 1 = texture, 2 = model.
        Codex should verify/centralize this mapping before production use.
        """
        if limit <= 0:
            return []

        terms = tuple(term.casefold() for term in query.split() if term.strip())
        catalog = self.list_assets()
        ranked: list[tuple[int, str, dict[str, Any]]] = []

        for asset_id, meta in catalog.items():
            if not isinstance(meta, dict):
                continue
            asset_type = meta.get("type")
            if asset_types is not None and asset_type not in asset_types:
                continue

            name = str(meta.get("name") or "")
            category = str(meta.get("category") or "")
            tags = [str(tag) for tag in (meta.get("tags") or [])]
            description = str(meta.get("description") or "")

            name_cf = name.casefold()
            tags_cf = " ".join(tags).casefold()
            haystack = " ".join((asset_id, name, category, description, *tags)).casefold()

            if terms and not all(term in haystack for term in terms):
                continue

            score = 0
            for term in terms:
                if term in name_cf:
                    score += 4
                if term in tags_cf:
                    score += 2
                if term in asset_id.casefold():
                    score += 1

            ranked.append((score, asset_id, meta))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [self._normalize_asset(asset_id, meta) for _, asset_id, meta in ranked[:limit]]

    def _normalize_asset(
        self,
        asset_id: str,
        meta: dict[str, Any],
    ) -> PolyHavenAssetCandidate:
        raw_dimensions = meta.get("dimensions")
        dimensions = None
        if isinstance(raw_dimensions, list):
            try:
                dimensions = tuple(float(value) for value in raw_dimensions)
            except (TypeError, ValueError):
                dimensions = None

        polycount = meta.get("polycount")
        if not isinstance(polycount, int):
            polycount = None

        return PolyHavenAssetCandidate(
            asset_id=asset_id,
            name=str(meta.get("name") or asset_id),
            asset_type=meta.get("type") if isinstance(meta.get("type"), int) else None,
            category=str(meta["category"]) if meta.get("category") else None,
            tags=tuple(str(tag) for tag in (meta.get("tags") or [])),
            polycount=polycount,
            dimensions=dimensions,
            thumbnail_url=str(meta["thumbnail_url"]) if meta.get("thumbnail_url") else None,
        )

    def get_files(self, asset_id: str) -> dict[str, Any]:
        """Get `/files/{id}` including URLs, sizes, hashes and dependencies."""
        payload = self._json_get(f"/files/{quote(asset_id, safe='')}")
        if not isinstance(payload, dict):
            raise TypeError("Unexpected Poly Haven /files response")
        return payload

    def iter_files(self, asset_id: str) -> Iterable[PolyHavenFileCandidate]:
        """Flatten every file record with a URL from Poly Haven's nested tree."""
        tree = self.get_files(asset_id)

        def walk(node: Any, path: tuple[str, ...]) -> Iterable[PolyHavenFileCandidate]:
            if isinstance(node, dict):
                url = node.get("url")
                if isinstance(url, str):
                    yield PolyHavenFileCandidate(
                        url=url,
                        size=node.get("size") if isinstance(node.get("size"), int) else None,
                        md5=node.get("md5") if isinstance(node.get("md5"), str) else None,
                        key_path=path,
                    )
                for key, value in node.items():
                    if key not in {"url", "size", "md5"}:
                        yield from walk(value, path + (str(key),))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    yield from walk(value, path + (str(index),))

        yield from walk(tree, ())

    def choose_file(
        self,
        asset_id: str,
        *,
        required_tokens: tuple[str, ...],
        max_bytes: int | None = None,
    ) -> PolyHavenFileCandidate:
        """Choose the smallest file whose nested key path contains all tokens."""
        wanted = tuple(token.casefold() for token in required_tokens)
        matches = []
        for candidate in self.iter_files(asset_id):
            key_text = "/".join(candidate.key_path).casefold()
            if not all(token in key_text for token in wanted):
                continue
            if max_bytes is not None and candidate.size is not None and candidate.size > max_bytes:
                continue
            matches.append(candidate)

        if not matches:
            raise LookupError(
                f"No Poly Haven file matched asset={asset_id!r}, tokens={required_tokens!r}"
            )

        return min(
            matches,
            key=lambda item: (item.size is None, item.size or 0, item.key_path),
        )

    def download(
        self,
        file: PolyHavenFileCandidate,
        destination: str | Path,
        *,
        verify_md5: bool = True,
    ) -> Path:
        """Stream one selected file to an explicit destination and verify MD5."""
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")

        request = Request(file.url, headers={"User-Agent": self.user_agent}, method="GET")
        digest = hashlib.md5()

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response, temporary.open("wb") as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    digest.update(chunk)

            if verify_md5 and file.md5:
                actual = digest.hexdigest().casefold()
                expected = file.md5.casefold()
                if actual != expected:
                    raise ValueError(
                        f"Poly Haven MD5 mismatch: expected {expected}, got {actual}"
                    )

            temporary.replace(target)
            return target
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


# Deliberately absent:
# - bpy imports
# - automatic scene changes
# - arbitrary URLs supplied by the agent
# - arbitrary shell execution
# - provider credentials (Poly Haven default endpoints require no API key)
