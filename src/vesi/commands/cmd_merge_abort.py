"""Commands: lanjutkan gabungan and batalkan gabungan."""

from __future__ import annotations

import shutil
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import confirm, print_color


def cmd_lanjutkan_gabungan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Continue a merge after resolving conflicts."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Check if there's a merge state file
    merge_head_path = repo.vesi_dir / "MERGE_HEAD"
    merge_msg_path = repo.vesi_dir / "MERGE_MSG"

    if not merge_head_path.is_file():
        print("✗ Tidak ada penggabungan yang sedang berlangsung.")
        return 0

    # Read merge state
    source_hash = merge_head_path.read_text(encoding="utf-8").strip()
    message = ""
    if merge_msg_path.is_file():
        message = merge_msg_path.read_text(encoding="utf-8").strip()

    # Create merge commit
    from vesi.core.snapshot import SnapshotManager
    from vesi.storage.tree import Tree

    snapshot_mgr = SnapshotManager(repo)

    # Get current HEAD
    head_hash = repo.get_head_commit()
    if not head_hash:
        print("✗ Tidak bisa melanjutkan. HEAD tidak ditemukan.")
        return 1

    # Get current tree
    try:
        current_tree = snapshot_mgr.get_tree(head_hash)
    except Exception:
        print("✗ Gagal memuat tree saat ini.")
        return 1

    # Build tree from staged files (resolved conflicts)
    index = repo.index.load()
    if index:
        # Use staged files as the merged result
        new_tree = Tree()
        for filepath, file_hash in index.items():
            name = filepath.split("/")[-1]
            new_tree.add_blob(name, file_hash, filepath)
    else:
        # Use current tree as-is
        new_tree = current_tree

    # Create merge commit
    merge_data = {
        "tree": new_tree.save(repo.objects),
        "message": message or f"Gabungan dari {source_hash[:7]}",
        "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "author": repo.get_author(),
        "parent": head_hash,
        "second_parent": source_hash,
    }

    merge_hash = repo.objects.save_json(merge_data)

    # Update branch
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, merge_hash)

    # Clean up merge state
    merge_head_path.unlink(missing_ok=True)
    merge_msg_path.unlink(missing_ok=True)
    repo.index.clear()

    from vesi.hashing import short_hash
    print_color(f"✓ Penggabungan selesai! Versi baru: {short_hash(merge_hash)}", "green")

    return 0


def cmd_batalkan_gabungan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Abort a merge in progress."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Check if there's a merge state file
    merge_head_path = repo.vesi_dir / "MERGE_HEAD"

    if not merge_head_path.is_file():
        print("✗ Tidak ada penggabungan yang sedang berlangsung.")
        return 0

    # Confirm
    print("⚠ Penggabungan akan dibatalkan.")
    if not confirm("Lanjutkan?", default=False):
        print("Dibatalkan.")
        return 0

    # Clean up merge state
    merge_head_path.unlink(missing_ok=True)
    (repo.vesi_dir / "MERGE_MSG").unlink(missing_ok=True)

    # Restore working directory from HEAD
    head_hash = repo.get_head_commit()
    if head_hash:
        from vesi.core.snapshot import SnapshotManager
        snapshot_mgr = SnapshotManager(repo)
        try:
            tree = snapshot_mgr.get_tree(head_hash)
            # Restore all tracked files
            for entry in tree.get_blob_entries():
                content = repo.blobs.load_content(entry.hash_id)
                target_path = repo.root / entry.path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(content)
        except Exception:
            pass

    # Clear staging
    repo.index.clear()

    print_color("✓ Penggabungan dibatalkan.", "green")
    return 0
