"""Access bundled doxa resources from editable and wheel installs."""

from __future__ import annotations

from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
import shutil
import tempfile

from .schema import DoxaError


ASSET_PACKAGE = "doxa"
ASSET_ROOT = "_assets"


def resource_ref(*parts: str) -> Traversable:
    ref = resources.files(ASSET_PACKAGE).joinpath(ASSET_ROOT, *parts)
    if not (ref.is_file() or ref.is_dir()):
        joined = "/".join(parts)
        raise DoxaError(f"Bundled resource not found: {joined}")
    return ref


def read_text(*parts: str) -> str:
    return resource_ref(*parts).read_text(encoding="utf-8")


def _copy_resource(src: Traversable, dest: Path) -> None:
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for child in src.iterdir():
            _copy_resource(child, dest / child.name)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as in_handle, dest.open("wb") as out_handle:
        shutil.copyfileobj(in_handle, out_handle)


def resource_path(*parts: str) -> Path:
    """Return a filesystem path for a bundled resource.

    Wheels are normally unpacked, but this also handles zip-backed importers by
    copying the resource into a stable temp directory.
    """

    ref = resource_ref(*parts)
    if isinstance(ref, Path):
        return ref
    dest = Path(tempfile.gettempdir()) / "doxa-resources" / Path(*parts)
    if not dest.exists():
        _copy_resource(ref, dest)
    return dest


def demo_config_path() -> Path:
    return resource_path("demo") / "doxa.yaml"


def demo_data_dir() -> Path:
    return resource_path("demo") / "data"


def skill_text() -> str:
    return read_text("skill", "SKILL.md")


def banner_text() -> str:
    return read_text("banner.txt")
