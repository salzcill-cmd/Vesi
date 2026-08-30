"""Command: balikkan - Create new commit that undoes changes."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.storage.tree import Tree
from vesi.utils.platform import print_color


def _resolve_version(repo: Repository, version_str: str) -> str:
    """Resolve a version string to a full commit hash."""
    version_str = version_str.strip()

    if version_str.upper().startswith("HEAD"):
        base_hash = repo.get_head_commit()
        if not base_hash:
            raise VersionNotFoundError(version_str)
        if version_str.upper() == "HEAD":
            return base_hash
        if "~" in version_str:
            try:
                n = int(version_str.split("~")[1])
            except (ValueError, IndexError):
                raise VersionNotFoundError(version_str)
            snapshot_mgr = SnapshotManager(repo)
            current = base_hash
            for _ in range(n):
                try:
                    parent = snapshot_mgr.get_parent(current)
                    if not parent:
                        raise VersionNotFoundError(version_str)
                    current = parent
                except Exception:
                    raise VersionNotFoundError(version_str)
            return current

    # Try as branch name
    branches = repo.refs.list_branches()
    if version_str in branches:
        branch_hash = repo.refs.get_branch_hash(version_str)
        if branch_hash:
            return branch_hash

    # Try as short/full hash
    if len(version_str) >= 7:
        objects_dir = repo.vesi_dir / "objects"
        if objects_dir.is_dir():
            for prefix_dir in objects_dir.iterdir():
                if not prefix_dir.is_dir() or len(prefix_dir.name) != 2:
                    continue
                for obj_file in prefix_dir.iterdir():
                    if obj_file.is_file():
                        full_hash = prefix_dir.name + obj_file.name
                        if full_hash.startswith(version_str):
                            return full_hash

    raise VersionNotFoundError(version_str)


def cmd_balikkan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Revert: create new commit that undoes changes from a specific commit.

    Usage:
      balikkan <commit>           - Revert a specific commit
      balikkan <commit> --no-commit - Apply changes without committing
      balikkan HEAD               - Revert last commit
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan commit yang akan dibalikkan.",
            hint="Contoh:\n  balikkan abc1234\n  balikkan HEAD",
        )

    commit_str = parsed.args[0]
    no_commit = "--no-commit" in parsed.flags

    # Resolve commit
    try:
        commit_hash = _resolve_version(repo, commit_str)
    except VersionNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)

    # Load the commit to revert
    try:
        commit_data = snapshot_mgr.load_snapshot(commit_hash)
    except (FileNotFoundError, ValueError):
        raise VersionNotFoundError(commit_str)

    commit_message = commit_data.get("message", "")
    commit_parent = commit_data.get("parent")

    if not commit_parent:
        raise VesiError(
            "Tidak bisa membalikkan commit pertama.",
            hint="Gunakan 'mulai proyek' untuk membuat repository baru.",
        )

    # Get the tree from the commit to revert
    try:
        revert_tree = snapshot_mgr.get_tree(commit_hash)
    except Exception:
        raise VesiError("Gagal memuat tree dari commit yang akan dibalikkan.")

    # Get the parent tree (the state before the commit)
    try:
        parent_tree = snapshot_mgr.get_tree(commit_parent)
    except Exception:
        raise VesiError("Gagal memuat tree parent.")

    # Build new tree from parent (undo the changes)
    new_tree = Tree()
    for entry in parent_tree.get_blob_entries():
        new_tree.add_blob(entry.name, entry.hash_id, entry.path)

    if no_commit:
        # Apply changes to working directory without committing
        for entry in parent_tree.get_blob_entries():
            content = repo.blobs.load_content(entry.hash_id)
            file_path = repo.root / entry.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)

        # Stage the changes
        index = {}
        for entry in parent_tree.get_blob_entries():
            index[entry.path] = entry.hash_id
        repo.index.save(index)

        print_color("✓ Perubahan dibalikkan (belum di-commit).", "green")
        print(f"  Commit: {short_hash(commit_hash)}")
        print(f"  Pesan: {commit_message}")
        print(f"\n  Untuk menyimpan:")
        print(f'    vesi simpan "Balikkan: {commit_message}"')
        return 0

    # Create revert commit
    current_hash = repo.get_head_commit()
    author = repo.get_author()

    revert_message = f"Balikkan: {commit_message}"

    new_hash = snapshot_mgr.create_snapshot(
        tree=new_tree,
        message=revert_message,
        author=author,
        parent=current_hash,
    )

    # Update branch
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, new_hash)

    # Reflog
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(new_hash, "revert", revert_message, active_branch or "")

    print_color("✓ Commit dibalikkan!", "green")
    print(f"  Commit asli: {short_hash(commit_hash)} ({commit_message})")
    print(f"  Commit baru: {short_hash(new_hash)} ({revert_message})")

    if verbose:
        # Show what files changed
        revert_files = {e.path for e in revert_tree.get_blob_entries()}
        parent_files = {e.path for e in parent_tree.get_blob_entries()}

        added = parent_files - revert_files
        removed = revert_files - parent_files

        if added:
            print(f"\n  File yang dipulihkan:")
            for f in added:
                print(f"    + {f}")
        if removed:
            print(f"\n  File yang dihapus:")
            for f in removed:
                print(f"    - {f}")

    return 0
