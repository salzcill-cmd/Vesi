"""Command: ambil versi - Cherry-pick a specific commit."""

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
    """Resolve a version string to a full commit hash.

    Supports:
    - Full hash (40 chars)
    - Short hash (7+ chars)
    - HEAD, HEAD~1, HEAD~2, etc.
    - Branch name
    """
    version_str = version_str.strip()

    # Handle HEAD and HEAD~N
    if version_str.upper().startswith("HEAD"):
        base_hash = repo.get_head_commit()
        if not base_hash:
            raise VersionNotFoundError(version_str)

        if version_str.upper() == "HEAD":
            return base_hash

        # Parse HEAD~N
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
        # Search in objects using the hash prefix structure
        objects_dir = repo.vesi_dir / "objects"
        if objects_dir.is_dir():
            # First try as full hash (40 chars)
            if len(version_str) == 40:
                try:
                    repo.objects.load_object(version_str)
                    return version_str
                except (FileNotFoundError, ValueError):
                    pass

            # Try as prefix match in object store
            # Objects are stored as: .vesi/objects/<hash[0:2]>/<hash[2:]>
            for prefix_dir in objects_dir.iterdir():
                if not prefix_dir.is_dir() or len(prefix_dir.name) != 2:
                    continue
                for obj_file in prefix_dir.iterdir():
                    if obj_file.is_file():
                        full_hash = prefix_dir.name + obj_file.name
                        if full_hash.startswith(version_str):
                            return full_hash

    raise VersionNotFoundError(version_str)


def cmd_ambil_versi(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Cherry-pick: apply a specific commit from another branch or history."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan versi yang akan diambil.",
            hint="Contoh:\n  ambil versi a1b2c3d\n  ambil versi f4e5d6a",
        )

    version_str = parsed.args[0]

    # Resolve version
    try:
        commit_hash = _resolve_version(repo, version_str)
    except VersionNotFoundError:
        raise

    # Load the commit
    snapshot_mgr = SnapshotManager(repo)
    try:
        snapshot = snapshot_mgr.load_snapshot(commit_hash)
    except (FileNotFoundError, ValueError):
        raise VersionNotFoundError(version_str)

    # Get the tree from the commit
    target_tree = snapshot_mgr.get_tree(commit_hash)

    # Get current HEAD tree for comparison
    current_hash = repo.get_head_commit()
    current_tree = None
    if current_hash:
        try:
            current_tree = snapshot_mgr.get_tree(current_hash)
        except Exception:
            pass

    # Compare trees and apply changes
    target_entries = {e.path: e.hash_id for e in target_tree.get_blob_entries()}
    current_entries = {}
    if current_tree:
        current_entries = {e.path: e.hash_id for e in current_tree.get_blob_entries()}

    # Find files that changed
    changed_files = []
    for filepath, hash_id in target_entries.items():
        if filepath not in current_entries or current_entries[filepath] != hash_id:
            changed_files.append(filepath)

    if not changed_files:
        print_color("✓ Tidak ada perubahan untuk diambil.", "yellow")
        print(f"  Versi '{short_hash(commit_hash)}' sudah sesuai.")
        return 0

    # Apply changes
    for filepath in changed_files:
        hash_id = target_entries[filepath]
        blob_content = repo.objects.load_blob(hash_id)
        dst_path = repo.root / filepath
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst_path.write_bytes(blob_content)

    # Create new commit
    new_tree = Tree()
    for filepath, hash_id in target_entries.items():
        name = filepath.split("/")[-1]
        new_tree.add_blob(name, hash_id, filepath)

    author = repo.get_author()
    message = f"Cherry-pick dari {short_hash(commit_hash)}: {snapshot.get('message', '')}"

    new_hash = snapshot_mgr.create_snapshot(
        tree=new_tree,
        message=message,
        author=author,
        parent=current_hash,
    )

    # Update branch reference
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, new_hash)

    # Display result
    print_color("✓ Versi berhasil diambil!", "green")
    print(f"  Sumber: {short_hash(commit_hash)}")
    print(f"  Pesan asli: {snapshot.get('message', '')}")
    print(f"  Baru: {short_hash(new_hash)}")
    print(f"  File: {len(changed_files)} file diperbarui")

    if verbose:
        print("\nFile yang berubah:")
        for f in changed_files:
            print(f"    {f}")

    return 0
