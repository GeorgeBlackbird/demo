from __future__ import annotations

import shutil
from pathlib import Path


def get_payload_dir() -> Path:
    """Return directory with exam solution files bundled in this package."""
    return Path(__file__).resolve().parent / "payload"


def copy_to(destination: str | Path, overwrite: bool = False) -> Path:
    """
    Copy bundled exam solution files into destination directory.

    Args:
        destination: Existing destination directory.
        overwrite: Replace existing files if True.
    """
    destination_path = Path(destination).resolve()
    if not destination_path.exists() or not destination_path.is_dir():
        raise ValueError(f"Destination directory does not exist: {destination_path}")

    payload_dir = get_payload_dir()
    for source in payload_dir.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(payload_dir)
        target = destination_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists() and not overwrite:
            continue
        shutil.copy2(source, target)

    return destination_path


__all__ = ["get_payload_dir", "copy_to"]
