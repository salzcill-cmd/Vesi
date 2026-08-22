"""Staging area (index) management.

The index tracks which files are staged for the next commit.
Format: JSON dict of {filepath: hash_id}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Index:
    """Manages the staging area (index)."""

    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path

    def load(self) -> dict[str, str]:
        """Load the current index."""
        if not self.index_path.is_file():
            return {}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            return {}
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, entries: dict[str, str]) -> None:
        """Save the index."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        # Sort for deterministic output
        sorted_entries = dict(sorted(entries.items()))
        self.index_path.write_text(
            json.dumps(sorted_entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def stage_file(self, filepath: str, hash_id: str) -> None:
        """Stage a single file."""
        entries = self.load()
        entries[filepath] = hash_id
        self.save(entries)

    def unstage_file(self, filepath: str) -> None:
        """Remove a file from staging."""
        entries = self.load()
        entries.pop(filepath, None)
        self.save(entries)

    def clear(self) -> None:
        """Clear the staging area."""
        self.save({})

    def is_empty(self) -> bool:
        """Check if staging area is empty."""
        return not self.load()

    def get_staged_files(self) -> dict[str, str]:
        """Get all staged files with their hashes."""
        return self.load()
