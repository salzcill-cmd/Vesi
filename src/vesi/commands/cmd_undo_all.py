"""Command: batalkan semua - Undo all recent changes."""

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


def cmd_batalkan_semua(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Undo all recent changes and go back to a previous state.

    Usage:
      batalkan semua              - Undo last commit, keep changes
      batalkan semua --hapus      - Undo last commit, discard changes
      batalkan semua 3            - Undo last 3 commits
      batalkan semua --ke <hash>  - Go back to specific commit
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        raise VesiError("Belum ada commit yang bisa dibatalkan.")

    args = parsed.args or []
    flags = parsed.flags
    discard_changes = "--hapus" in flags

    # Parse target
    target_hash = None
    commits_to_undo = 1

    if "--ke" in flags:
        # Go to specific commit
        idx = flags.index("--ke")
        if idx < len(args):
            target_str = args[idx]
            # Resolve hash
            target_hash = _resolve_hash(repo, target_str)
        else:
            raise VesiError("Tentukan hash commit yang ingin dikembalikan.")
    elif args:
        # Number of commits to undo
        try:
            commits_to_undo = int(args[0])
        except ValueError:
            # Try as hash
            target_hash = _resolve_hash(repo, args[0])

    # Walk back to find target
    if not target_hash:
        current = current_hash
        for _ in range(commits_to_undo):
            try:
                data = snapshot_mgr.load_snapshot(current)
                parent = data.get("parent")
                if not parent:
                    raise VesiError(
                        f"Tidak bisa batalkan {commits_to_undo} commit. "
                        f"Hanya ada {_} commit yang bisa dibatalkan."
                    )
                current = parent
            except (FileNotFoundError, ValueError):
                break
        target_hash = current

    # Get target commit info
    try:
        target_data = snapshot_mgr.load_snapshot(target_hash)
    except (FileNotFoundError, ValueError):
        raise VesiError(f"Commit '{target_hash[:7]}' tidak ditemukan.")

    # Get current commit info
    try:
        current_data = snapshot_mgr.load_snapshot(current_hash)
        current_message = current_data.get("message", "")
    except (FileNotFoundError, ValueError):
        current_message = ""

    if discard_changes:
        # Hard reset: just move HEAD
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, target_hash)

        # Add reflog entry
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(target_hash, "reset-hard", "Batalkan semua perubahan", active_branch or "")

        print_color("Semua perubahan dibatalkan!", "yellow")
        print(f"  Dari: {short_hash(current_hash)} ({current_message})")
        print(f"  Ke:   {short_hash(target_hash)}")
    else:
        # Soft reset: restore files to staging
        target_tree = snapshot_mgr.get_tree(target_hash)

        # Stage all files from target
        index = {}
        for entry in target_tree.get_blob_entries():
            index[entry.path] = entry.hash_id
        repo.index.save(index)

        # Update branch
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, target_hash)

        # Add reflog entry
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(target_hash, "reset-soft", "Batalkan semua perubahan", active_branch or "")

        print_color("Semua perubahan dibatalkan! File dikembalikan ke staging.", "green")
        print(f"  Dari: {short_hash(current_hash)} ({current_message})")
        print(f"  Ke:   {short_hash(target_hash)}")
        print(f"  File: {len(index)} file di-staging")
        print(f"\n  Perubahan masih bisa disimpan lagi:")
        print(f'    vesi simpan "pesan baru"')

    return 0


def _resolve_hash(repo: Repository, version_str: str) -> str:
    """Resolve a version string to a full commit hash."""
    from vesi.commands.cmd_cherrypick import _resolve_version
    try:
        return _resolve_version(repo, version_str)
    except Exception:
        raise VesiError(f"Commit '{version_str}' tidak ditemukan.")
