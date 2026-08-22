"""Cross-platform path utilities."""

from __future__ import annotations

import os
from pathlib import Path, PurePath


REPO_DIR = ".vesi"


def get_repo_root(start: Path | None = None) -> Path | None:
    """Find the repository root by walking up from start.

    Returns the directory containing .vesi/, or None if not found.
    """
    if start is None:
        start = Path.cwd()
    current = start.resolve()
    while True:
        if (current / REPO_DIR).is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def get_repo_path(start: Path | None = None) -> Path | None:
    """Get the .vesi directory path if it exists."""
    root = get_repo_root(start)
    if root is None:
        return None
    return root / REPO_DIR


def is_repo_root(path: Path) -> bool:
    """Check if a path is a repository root (contains .vesi)."""
    return (path / REPO_DIR).is_dir()


def relpath(path: Path, start: Path) -> str:
    """Get relative path as string, handling cross-platform differences."""
    try:
        return str(path.relative_to(start))
    except ValueError:
        return str(path)


def normalize_path(path_str: str) -> Path:
    """Normalize a path string for consistent handling."""
    return Path(path_str).as_posix()


def is_binary_file(path: Path, check_bytes: int = 8192) -> bool:
    """Detect if a file is binary by checking for null bytes."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(check_bytes)
            return b"\x00" in chunk
    except (OSError, UnicodeDecodeError):
        return True


def safe_exists(path: Path) -> bool:
    """Safely check if path exists."""
    try:
        return path.exists()
    except OSError:
        return False


def get_file_size(path: Path) -> int:
    """Get file size safely."""
    try:
        return path.stat().st_size
    except OSError:
        return 0
