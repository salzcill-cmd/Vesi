"""Command: simpan --amend - Amend the last commit."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.storage.tree import Tree
from vesi.utils.platform import print_color


def cmd_simpan_amend(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Amend the last commit with staged changes."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Get current HEAD
    head_hash = repo.get_head_commit()
    if not head_hash:
        raise VesiError("Belum ada versi yang bisa diubah.")

    # Get staged files
    index = repo.index.load()
    if not index:
        raise VesiError(
            "Tidak ada file yang di-stage untuk di-amend.",
            hint="Stel file terlebih dahulu:\n    stel <file>",
        )

    # Load current commit
    snapshot_mgr = SnapshotManager(repo)
    try:
        current_data = snapshot_mgr.load_snapshot(head_hash)
        old_tree = Tree.load(repo.objects, current_data["tree"])
    except Exception:
        raise VesiError("Gagal memuat versi terakhir.")

    # Get parent
    parent_hash = current_data.get("parent")

    # Build new tree merging old tree with staged changes
    new_tree = Tree()

    # Start with old tree entries
    old_entries = {e.path: e for e in old_tree.get_blob_entries()}
    for path, entry in old_entries.items():
        if path not in index:
            # Keep old entry if not in staged changes
            new_tree.add_blob(entry.name, entry.hash_id, path)

    # Add/update staged entries
    for filepath, file_hash in index.items():
        name = filepath.split("/")[-1]
        new_tree.add_blob(name, file_hash, filepath)

    # Check if there are actual changes
    new_entries = {e.path: e.hash_id for e in new_tree.get_blob_entries()}
    old_entries_hashes = {e.path: e.hash_id for e in old_tree.get_blob_entries()}
    if new_entries == old_entries_hashes:
        raise VesiError("Tidak ada perubahan untuk di-amend.")

    # Get message (use new if provided, otherwise keep old)
    message = parsed.first_arg
    if not message:
        message = current_data.get("message", "")

    # Create amended commit
    author = repo.get_author()
    new_hash = snapshot_mgr.create_snapshot(
        tree=new_tree,
        message=message,
        author=author,
        parent=parent_hash,
    )

    # Update branch reference
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, new_hash)

    # Clear staging area
    repo.index.clear()

    file_count = len(new_tree.get_blob_entries())
    print_color("✓ Versi terakhir diubah!", "green")
    print(f"  ID: {short_hash(new_hash)}")
    print(f"  Pesan: {message}")
    print(f"  File: {file_count} file")

    if verbose:
        print(f"  Author: {author}")
        print(f"  Branch: {active_branch or '(detached)'}")

    return 0
