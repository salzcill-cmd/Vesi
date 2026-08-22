"""Tree object - represents directory structure as a snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vesi.storage.objects import ObjectStore


@dataclass
class TreeEntry:
    """A single entry in a tree object."""

    name: str
    type: str  # "blob" or "tree"
    hash_id: str
    path: str  # relative path from repo root

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "type": self.type, "hash": self.hash_id, "path": self.path}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> TreeEntry:
        return cls(
            name=data["name"],
            type=data["type"],
            hash_id=data["hash"],
            path=data["path"],
        )


class Tree:
    """Represents a directory structure as a collection of entries."""

    def __init__(self, entries: list[TreeEntry] | None = None) -> None:
        self.entries: list[TreeEntry] = entries or []

    def add_blob(self, name: str, hash_id: str, path: str) -> None:
        """Add a file entry."""
        self.entries.append(TreeEntry(name=name, type="blob", hash_id=hash_id, path=path))

    def add_tree(self, name: str, hash_id: str, path: str) -> None:
        """Add a subdirectory entry."""
        self.entries.append(TreeEntry(name=name, type="tree", hash_id=hash_id, path=path))

    def get_entry(self, path: str) -> TreeEntry | None:
        """Find an entry by relative path."""
        for entry in self.entries:
            if entry.path == path:
                return entry
        return None

    def get_blob_entries(self) -> list[TreeEntry]:
        """Get only blob (file) entries."""
        return [e for e in self.entries if e.type == "blob"]

    def to_dict(self) -> dict[str, Any]:
        """Serialize tree to dictionary."""
        return {"entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tree:
        """Deserialize tree from dictionary."""
        entries = [TreeEntry.from_dict(e) for e in data.get("entries", [])]
        return cls(entries)

    def save(self, objects: ObjectStore) -> str:
        """Save tree to object store. Returns hash."""
        return objects.save_json(self.to_dict())

    @classmethod
    def load(cls, objects: ObjectStore, hash_id: str) -> Tree:
        """Load tree from object store by hash."""
        data = objects.load_json(hash_id)
        return cls.from_dict(data)
