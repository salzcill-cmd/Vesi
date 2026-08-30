"""Command: bersihkan - Remove untracked files."""

from __future__ import annotations

import os
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.ignore import load_ignore_patterns, is_ignored
from vesi.repository.repository import Repository
from vesi.utils.platform import confirm, print_color


def cmd_bersihkan(
    parsed: ParsedCommand,
    *,  
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Remove untracked files.

    Usage:
      bersihkan                    - Show untracked files
      bersihkan --force            - Remove untracked files
      bersihkan --dry-run          - Show what would be removed
      bersihkan --include <pattern> - Include specific patterns
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    force = "--force" in parsed.flags or "-f" in parsed.flags
    dry_run = "--dry-run" in parsed.flags

    # Find untracked files
    ignore_patterns = load_ignore_patterns(repo.root)
    untracked = []

    for root, dirs, files in os.walk(repo.root):
        # Skip .vesi directory
        dirs[:] = [d for d in dirs if d != ".vesi"]

        for filename in files:
            file_path = Path(root) / filename
            rel_path = str(file_path.relative_to(repo.root))

            # Skip ignored files
            if is_ignored(rel_path, ignore_patterns):
                continue

            # Check if file is tracked
            try:
                blob_hash = repo.blobs.file_hash(file_path)
                # Check if hash is in any tree
                is_tracked = False
                head_hash = repo.get_head_commit()
                if head_hash:
                    from vesi.core.snapshot import SnapshotManager
                    snapshot_mgr = SnapshotManager(repo)
                    tree = snapshot_mgr.get_tree(head_hash)
                    entry = tree.get_entry(rel_path)
                    if entry:
                        is_tracked = True

                # Check if staged
                index = repo.index.load()
                if rel_path in index:
                    is_tracked = True

                if not is_tracked:
                    untracked.append(rel_path)

            except Exception:
                continue

    if not untracked:
        print_color("✓ Tidak ada file untracked.", "green")
        return 0

    # Display untracked files
    print(f"File untracked ({len(untracked)}):\n")
    for f in sorted(untracked):
        print(f"  ? {f}")

    if dry_run or not force:
        print(f"\n  Gunakan 'bersihkan --force' untuk menghapus.")
        return 0

    # Confirm deletion
    print(f"\n⚠ {len(untracked)} file akan dihapus permanen!")
    if not confirm("Lanjutkan?", default=False):
        print("Dibatalkan.")
        return 0

    # Remove files
    removed = 0
    for filepath in untracked:
        file_path = repo.root / filepath
        try:
            file_path.unlink()
            removed += 1
            if verbose:
                print(f"  ✓ {filepath}")
        except Exception as e:
            print_color(f"  ✗ Gagal menghapus {filepath}: {e}", "red")

    print_color(f"\n✓ {removed} file untracked dihapus.", "green")
    return 0
