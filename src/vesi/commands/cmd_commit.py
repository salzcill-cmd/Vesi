"""Command: simpan versi - Create a new snapshot/commit."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    MissingArgumentError,
    NoStagedChangesError,
    NoChangesError,
    RepositoryNotFoundError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.storage.blob import BlobStore
from vesi.storage.tree import Tree
from vesi.utils.platform import print_color


def cmd_simpan_versi(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Create a new snapshot/commit."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Get message
    message = parsed.first_arg
    if not message:
        raise MissingArgumentError(
            "simpan versi",
            "pesan deskriptif",
            'simpan versi "deskripsi perubahan"',
        )

    # Get staged files
    index = repo.index.load()
    if not index:
        raise NoStagedChangesError()

    # Get current tree
    snapshot_mgr = SnapshotManager(repo)
    parent_hash = repo.get_head_commit()

    old_tree = None
    if parent_hash:
        try:
            old_tree = snapshot_mgr.get_tree(parent_hash)
        except Exception:
            pass

    # Build new tree from staged files
    new_tree = Tree()
    for filepath, file_hash in index.items():
        name = filepath.split("/")[-1]
        new_tree.add_blob(name, file_hash, filepath)

    # Check if there are actual changes
    if old_tree:
        old_entries = {e.path: e.hash_id for e in old_tree.get_blob_entries()}
        new_entries = {e.path: e.hash_id for e in new_tree.get_blob_entries()}
        if old_entries == new_entries:
            raise NoChangesError()

    # Create snapshot
    author = repo.get_author()
    snapshot_hash = snapshot_mgr.create_snapshot(
        tree=new_tree,
        message=message,
        author=author,
        parent=parent_hash,
    )

    # Update branch reference
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, snapshot_hash)

    # Add reflog entry
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(snapshot_hash, "commit", message, active_branch or "")

    # Clear staging area
    repo.index.clear()

    # Display result
    file_count = len(new_tree.get_blob_entries())
    print_color("✓ Versi tersimpan!", "green")
    print(f"  ID: {short_hash(snapshot_hash)}")
    print(f"  Pesan: {message}")
    print(f"  File: {file_count} file disimpan")

    if verbose:
        print(f"  Author: {author}")
        print(f"  Branch: {active_branch or '(detached)'}")
        print(f"  Parent: {short_hash(parent_hash) if parent_hash else '(root)'}")

    return 0
