"""Command: batalkan versi - Undo commit easily."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_batalkan_versi(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Undo the last commit.

    Usage:
      batalkan versi           - Undo last commit, keep changes staged
      batalkan versi --hapus   - Undo last commit, discard changes
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        raise VesiError("Belum ada commit yang bisa dibatalkan.")

    # Get current commit info
    try:
        current_data = snapshot_mgr.load_snapshot(current_hash)
    except (FileNotFoundError, ValueError):
        raise VesiError("Gagal membaca commit saat ini.")

    parent_hash = current_data.get("parent")
    message = current_data.get("message", "")
    author = current_data.get("author", "")

    # Check if this is the first commit
    if not parent_hash:
        raise VesiError(
            "Ini adalah commit pertama. Tidak bisa dibatalkan.",
            hint="Gunakan 'mulai proyek' untuk membuat repository baru.",
        )

    # Check for --hapus flag
    discard_changes = "--hapus" in parsed.flags

    if discard_changes:
        # Reset to parent commit (discard changes)
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, parent_hash)

        # Add reflog entry
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(parent_hash, "reset", f"Undo commit: {message}", active_branch or "")

        print_color("✓ Commit dibatalkan dan perubahan dihapus!", "yellow")
        print(f"  Commit: {short_hash(current_hash)}")
        print(f"  Pesan: {message}")
        print(f"  Kembali ke: {short_hash(parent_hash)}")

    else:
        # Soft reset: move HEAD back but keep changes
        # Get the files from current commit
        current_tree = snapshot_mgr.get_tree(current_hash)

        # Stage all files from current commit
        index = {}
        for entry in current_tree.get_blob_entries():
            index[entry.path] = entry.hash_id
        repo.index.save(index)

        # Update branch reference
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, parent_hash)

        # Add reflog entry
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(parent_hash, "reset-soft", f"Undo commit: {message}", active_branch or "")

        print_color("✓ Commit dibatalkan! Perubahan tetap di-staging.", "green")
        print(f"  Commit: {short_hash(current_hash)}")
        print(f"  Pesan: {message}")
        print(f"  File: {len(index)} file dikembalikan ke staging")
        print(f"\n  Perubahan masih bisa disimpan lagi:")
        print(f'    vesi simpan "pesan baru"')

    if verbose:
        print(f"\n  Author: {author}")
        print(f"  Parent: {short_hash(parent_hash) if parent_hash else '(root)'}")

    return 0
