"""Command: bandingkan pintar - Smart diff with highlighting and summary."""

from __future__ import annotations

from collections import Counter
from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_bandingkan_pintar(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Smart diff with summary and stats.

    Usage:
      bandingkan pintar              - Diff working directory vs last commit
      bandingkan pintar <v1> <v2>    - Diff between two versions
      bandingkan pintar --stat       - Show only stats
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        raise VesiError("Belum ada commit untuk dibandingkan.")

    # Parse arguments
    args = parsed.args or []
    show_stat_only = "--stat" in parsed.flags

    # Get current tree
    try:
        current_tree = snapshot_mgr.get_tree(current_hash)
        current_entries = {e.path: e.hash_id for e in current_tree.get_blob_entries()}
    except (FileNotFoundError, ValueError):
        current_entries = {}

    # Get parent tree
    try:
        current_data = snapshot_mgr.load_snapshot(current_hash)
        parent_hash = current_data.get("parent")
        if parent_hash:
            parent_tree = snapshot_mgr.get_tree(parent_hash)
            parent_entries = {e.path: e.hash_id for e in parent_tree.get_blob_entries()}
        else:
            parent_entries = {}
    except (FileNotFoundError, ValueError):
        parent_entries = {}

    # Compare with working directory
    from vesi.core.change import detect_changes
    from vesi.repository.staging import Index

    index = repo.index.load()
    changes = detect_changes(repo.root, None, index or {})

    # Categorize changes
    added = []
    modified = []
    deleted = []

    for change in changes:
        if change.change_type == "new":
            added.append(change.path)
        elif change.change_type == "modified":
            modified.append(change.path)
        elif change.change_type == "deleted":
            deleted.append(change.path)

    # Summary
    total_changes = len(added) + len(modified) + len(deleted)

    if total_changes == 0:
        print_color("✓ Tidak ada perubahan.", "green")
        return 0

    print_color(f"📊 Ringkasan Perubahan\n", "cyan")
    print(f"  📁 File berubah: {total_changes}")
    if added:
        print(f"  ✅ Baru: {len(added)}")
    if modified:
        print(f"  ✏️  Diubah: {len(modified)}")
    if deleted:
        print(f"  🗑️  Dihapus: {len(deleted)}")

    if show_stat_only:
        return 0

    # Show detailed diff
    print(f"\n{'─' * 50}")

    if added:
        print_color(f"\n📁 File Baru ({len(added)}):", "green")
        for f in added:
            print(f"  + {f}")

    if modified:
        print_color(f"\n✏️  File Diubah ({len(modified)}):", "yellow")
        for f in modified:
            # Try to show line diff
            file_path = repo.root / f
            if file_path.is_file():
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                added_lines = len([l for l in lines if l.strip()])
                print(f"  ~ {f} ({added_lines} baris)")
            else:
                print(f"  ~ {f}")

    if deleted:
        print_color(f"\n🗑️  File Dihapus ({len(deleted)}):", "red")
        for f in deleted:
            print(f"  - {f}")

    # Stats
    print(f"\n{'─' * 50}")
    print(f"  📊 Statistik:")
    print(f"    + Baru: {len(added)}")
    print(f"    ~ Diubah: {len(modified)}")
    print(f"    - Dihapus: {len(deleted)}")
    print(f"    Total: {total_changes} file")

    return 0
