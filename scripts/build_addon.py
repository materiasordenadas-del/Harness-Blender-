"""Build an installable Blender extension ZIP."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "blender_addon" / "harness_blender_bridge"
DIST = ROOT / "dist"
OUTPUT = DIST / "harness_blender_bridge-0.1.0.zip"


def main() -> None:
    if not (SOURCE / "blender_manifest.toml").exists():
        raise SystemExit(f"Missing Blender manifest: {SOURCE}")
    DIST.mkdir(exist_ok=True)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        for path in sorted(SOURCE.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(SOURCE).as_posix())
    print(OUTPUT)


if __name__ == "__main__":
    main()
