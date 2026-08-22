"""Ignore pattern matching (.abaikan file)."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path


def load_ignore_patterns(repo_root: Path) -> list[str]:
    """Load patterns from .abaikan file."""
    ignore_path = repo_root / ".abaikan"
    if not ignore_path.is_file():
        return []

    patterns: list[str] = []
    for line in ignore_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def is_ignored(filepath: str, patterns: list[str]) -> bool:
    """Check if a filepath matches any ignore pattern.

    Supports:
    - Wildcards: *.pyc
    - Directories: __pycache__/
    - Negation: !important.log
    - Exact names: .env
    """
    if not patterns:
        return False

    # Normalize path separators
    filepath = filepath.replace("\\", "/")

    result = False
    for pattern in patterns:
        # Handle negation
        negated = pattern.startswith("!")
        if negated:
            pattern = pattern[1:]

        # Normalize pattern
        pattern = pattern.replace("\\", "/")

        # Check if pattern matches
        matched = False

        # Directory pattern (ends with /)
        if pattern.endswith("/"):
            dir_pattern = pattern.rstrip("/")
            # Match if any part of the path matches
            parts = filepath.split("/")
            for part in parts:
                if fnmatch.fnmatch(part, dir_pattern):
                    matched = True
                    break
            # Also match the full path
            if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(
                filepath, "**/" + pattern
            ):
                matched = True
        else:
            # File pattern
            if fnmatch.fnmatch(filepath, pattern):
                matched = True
            elif fnmatch.fnmatch(Path(filepath).name, pattern):
                matched = True
            # Match with ** (recursive)
            if "**" in pattern:
                if re.match(pattern.replace("**", ".*").replace("*", "[^/]*"), filepath):
                    matched = True

        if negated:
            if matched:
                result = False
        else:
            if matched:
                result = True

    return result


def filter_ignored(
    files: list[str], patterns: list[str], base_dir: str = ""
) -> list[str]:
    """Filter out ignored files from a list."""
    result = []
    for f in files:
        check_path = f
        if base_dir:
            check_path = f"{base_dir}/{f}" if not f.startswith(base_dir) else f
        if not is_ignored(check_path, patterns):
            result.append(f)
    return result
