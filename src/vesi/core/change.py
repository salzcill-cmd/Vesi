"""Change detection - detect new, modified, deleted files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from vesi.hashing import hash_file
from vesi.repository.ignore import load_ignore_patterns, is_ignored
from vesi.storage.tree import Tree


@dataclass
class FileChange:
    """Represents a change to a single file."""

    path: str
    change_type: str  # "new", "modified", "deleted", "unchanged"
    old_hash: str | None = None
    new_hash: str | None = None


def detect_changes(
    repo_root: Path,
    tree: Tree | None,
    index: dict[str, str],
) -> list[FileChange]:
    """Detect changes between working directory and last snapshot.

    Compares working directory files against the tree from the last commit.
    Also checks staged files in the index.

    Returns list of FileChange objects.
    """
    changes: list[FileChange] = []
    ignore_patterns = load_ignore_patterns(repo_root)

    # Build set of tracked files from tree
    tracked: dict[str, str] = {}  # path -> hash
    if tree:
        for entry in tree.get_blob_entries():
            tracked[entry.path] = entry.hash_id

    # Scan working directory
    working_files: dict[str, str] = {}  # path -> hash
    for root, dirs, files in os.walk(repo_root):
        # Skip .vesi directory and ignored directories
        dirs[:] = [
            d
            for d in dirs
            if d != ".vesi" and not is_ignored(
                str(Path(root).relative_to(repo_root) / d), ignore_patterns
            )
        ]

        for filename in files:
            file_path = Path(root) / filename
            rel_path = str(file_path.relative_to(repo_root))

            # Skip .abaikan (it's tracked but special)
            if rel_path == ".abaikan":
                working_files[rel_path] = hash_file(file_path)
                continue

            # Skip ignored files
            if is_ignored(rel_path, ignore_patterns):
                continue

            try:
                file_hash = hash_file(file_path)
                working_files[rel_path] = file_hash
            except (OSError, PermissionError):
                continue

    # Detect new and modified files
    for rel_path, new_hash in working_files.items():
        if rel_path not in tracked:
            changes.append(
                FileChange(path=rel_path, change_type="new", new_hash=new_hash)
            )
        elif tracked[rel_path] != new_hash:
            changes.append(
                FileChange(
                    path=rel_path,
                    change_type="modified",
                    old_hash=tracked[rel_path],
                    new_hash=new_hash,
                )
            )

    # Detect deleted files
    for rel_path in tracked:
        if rel_path not in working_files:
            changes.append(
                FileChange(path=rel_path, change_type="deleted", old_hash=tracked[rel_path])
            )

    return changes


def get_staged_changes(
    repo_root: Path,
    tree: Tree | None,
    index: dict[str, str],
) -> list[FileChange]:
    """Get changes that are staged (in the index)."""
    changes: list[FileChange] = []

    # Build set of tracked files from tree
    tracked: dict[str, str] = {}
    if tree:
        for entry in tree.get_blob_entries():
            tracked[entry.path] = entry.hash_id

    # Compare staged files against tree
    for filepath, staged_hash in index.items():
        if filepath not in tracked:
            changes.append(
                FileChange(path=filepath, change_type="new", new_hash=staged_hash)
            )
        elif tracked[filepath] != staged_hash:
            changes.append(
                FileChange(
                    path=filepath,
                    change_type="modified",
                    old_hash=tracked[filepath],
                    new_hash=staged_hash,
                )
            )

    # Check for files in tree but not staged (not deleted from index)
    # This is just informational for status display

    return changes


def format_changes(changes: list[FileChange]) -> str:
    """Format changes for display."""
    if not changes:
        return "✓ Tidak ada perubahan."

    new_files = [c for c in changes if c.change_type == "new"]
    modified_files = [c for c in changes if c.change_type == "modified"]
    deleted_files = [c for c in changes if c.change_type == "deleted"]

    lines: list[str] = []

    if new_files:
        lines.append("File baru (belum dilacak):")
        for c in new_files:
            lines.append(f"  ? {c.path}")

    if modified_files:
        if lines:
            lines.append("")
        lines.append("File yang diubah:")
        for c in modified_files:
            lines.append(f"  M {c.path}")

    if deleted_files:
        if lines:
            lines.append("")
        lines.append("File yang dihapus:")
        for c in deleted_files:
            lines.append(f"  D {c.path}")

    return "\n".join(lines)
