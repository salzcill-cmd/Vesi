"""Snapshot/Version model - creates immutable snapshots of project state."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from vesi.hashing import hash_content, short_hash
from vesi.repository.repository import Repository
from vesi.storage.objects import ObjectStore
from vesi.storage.tree import Tree


@dataclass
class SnapshotInfo:
    """Lightweight snapshot info for display."""

    id: str
    full_id: str
    message: str
    timestamp: str
    author: str
    tree_hash: str
    parent: str | None
    file_count: int = 0
    total_size: int = 0


class SnapshotManager:
    """Manages snapshot creation and retrieval."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def create_snapshot(
        self,
        tree: Tree,
        message: str,
        author: str,
        parent: str | None = None,
    ) -> str:
        """Create a new snapshot.

        Args:
            tree: The tree object representing the project state.
            message: Version message/description.
            author: Author name.
            parent: Parent commit hash (None for first commit).

        Returns:
            The hash of the created snapshot.
        """
        # Save tree first
        tree_hash = tree.save(self.repo.objects)

        # Create snapshot object
        snapshot_data: dict[str, Any] = {
            "tree": tree_hash,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "author": author,
        }
        if parent:
            snapshot_data["parent"] = parent

        # Save snapshot to object store
        snapshot_hash = self.repo.objects.save_json(snapshot_data)

        return snapshot_hash

    def load_snapshot(self, hash_id: str) -> dict[str, Any]:
        """Load a snapshot by hash."""
        return self.repo.objects.load_json(hash_id)

    def get_info(self, hash_id: str) -> SnapshotInfo:
        """Get lightweight info about a snapshot."""
        data = self.load_snapshot(hash_id)

        # Count files in tree
        tree = Tree.load(self.repo.objects, data["tree"])
        file_count = len(tree.get_blob_entries())

        return SnapshotInfo(
            id=short_hash(hash_id),
            full_id=hash_id,
            message=data.get("message", ""),
            timestamp=data.get("timestamp", ""),
            author=data.get("author", ""),
            tree_hash=data["tree"],
            parent=data.get("parent"),
            file_count=file_count,
        )

    def get_tree(self, snapshot_hash: str) -> Tree:
        """Get the tree for a snapshot."""
        data = self.load_snapshot(snapshot_hash)
        return Tree.load(self.repo.objects, data["tree"])

    def get_parent(self, snapshot_hash: str) -> str | None:
        """Get the parent commit hash."""
        data = self.load_snapshot(snapshot_hash)
        return data.get("parent")
