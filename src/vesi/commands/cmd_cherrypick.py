"""Command: ambil versi - Cherry-pick a specific commit with conflict support."""

from __future__ import annotations

import json
import time

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
    """Cherry-pick: apply a specific commit from another branch or history.

    Usage:
      ambil versi <hash>           - Cherry-pick one commit
      ambil versi <h1> <h2>        - Cherry-pick multiple commits
      ambil versi <hash> --no-commit - Apply changes without committing
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan versi yang akan diambil.",
            hint="Contoh:\n  ambil versi a1b2c3d\n  ambil versi f4e5d6a",
        )

    no_commit = "--no-commit" in parsed.flags

    # Resolve all versions
    commit_hashes = []
    for arg in parsed.args:
        if arg.startswith("--"):
            continue
        try:
            commit_hash = _resolve_version(repo, arg)
            commit_hashes.append(commit_hash)
        except VersionNotFoundError:
            raise

    if not commit_hashes:
        raise VesiError("Tidak ada versi valid untuk diambil.")

    # Cherry-pick each commit
    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    # Get current tree
    current_tree = None
    if current_hash:
        try:
            current_tree = snapshot_mgr.get_tree(current_hash)
        except Exception:
            pass

    current_files = {}
    if current_tree:
        current_files = {e.path: e.hash_id for e in current_tree.get_blob_entries()}

    # Track conflicts
    all_conflicts = []

    for commit_hash in commit_hashes:
        # Load the commit
        try:
            snapshot = snapshot_mgr.load_snapshot(commit_hash)
        except (FileNotFoundError, ValueError):
            raise VersionNotFoundError(short_hash(commit_hash))

        # Get the tree from the commit
        target_tree = snapshot_mgr.get_tree(commit_hash)
        target_files = {e.path: e.hash_id for e in target_tree.get_blob_entries()}

        # Find files that changed
        changed_files = []
        for filepath, hash_id in target_files.items():
            if filepath not in current_files or current_files[filepath] != hash_id:
                changed_files.append(filepath)

        # Check for conflicts (files modified in both current and target)
        conflicts = []
        for filepath in changed_files:
            if filepath in current_files:
                # Check if file also changed between parent and current
                try:
                    parent_hash = snapshot.get("parent")
                    if parent_hash:
                        parent_tree = snapshot_mgr.get_tree(parent_hash)
                        parent_files = {e.path: e.hash_id for e in parent_tree.get_blob_entries()}

                        parent_hash_for_file = parent_files.get(filepath)
                        current_hash_for_file = current_files.get(filepath)
                        target_hash_for_file = target_files.get(filepath)

                        # Conflict: both sides changed the file differently
                        if (parent_hash_for_file != current_hash_for_file and
                            parent_hash_for_file != target_hash_for_file and
                            current_hash_for_file != target_hash_for_file):
                            conflicts.append(filepath)
                except Exception:
                    pass

        if conflicts:
            all_conflicts.extend(conflicts)
            print_color(f"\n⚠ Konflik saat cherry-pick {short_hash(commit_hash)}:", "yellow")
            for f in conflicts:
                print(f"    {f}")

            # Write merge state for continue/abort
            merge_head_path = repo.vesi_dir / "MERGE_HEAD"
            merge_head_path.write_text(commit_hash, encoding="utf-8")

            merge_msg_path = repo.vesi_dir / "MERGE_MSG"
            merge_msg_path.write_text(
                f"Cherry-pick {short_hash(commit_hash)}: {snapshot.get('message', '')}",
                encoding="utf-8",
            )

            conflicts_path = repo.vesi_dir / "MERGE_CONFLICTS"
            conflicts_path.write_text(json.dumps(conflicts), encoding="utf-8")

            print(f"\n  Perbaiki file tersebut, lalu jalankan:")
            print(f"    lanjutkan gabungan")
            print(f"\n  Atau batalkan:")
            print(f"    batalkan gabungan")

            return 4

        # Apply changes (no conflicts)
        for filepath in changed_files:
            hash_id = target_files[filepath]
            blob_content = repo.objects.load_blob(hash_id)
            dst_path = repo.root / filepath
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            dst_path.write_bytes(blob_content)
            current_files[filepath] = hash_id

    if no_commit:
        # Stage changes without committing
        for filepath, hash_id in current_files.items():
            repo.index.stage_file(filepath, hash_id)
        print_color(f"✓ {len(commit_hashes)} commit diterapkan (belum di-commit).", "green")
        return 0

    # Create new commit(s)
    if len(commit_hashes) == 1:
        # Single cherry-pick: one commit
        commit_hash = commit_hashes[0]
        snapshot = snapshot_mgr.load_snapshot(commit_hash)
        target_tree = snapshot_mgr.get_tree(commit_hash)
        target_files = {e.path: e.hash_id for e in target_tree.get_blob_entries()}

        # Build new tree
        new_tree = Tree()
        for filepath, hash_id in current_files.items():
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

        # Reflog
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(new_hash, "cherry-pick", message, active_branch or "")

        # Display result
        print_color("✓ Cherry-pick berhasil!", "green")
        print(f"  Sumber: {short_hash(commit_hash)}")
        print(f"  Pesan asli: {snapshot.get('message', '')}")
        print(f"  Baru: {short_hash(new_hash)}")
        print(f"  File: {len(changed_files)} file diperbarui")

        if verbose:
            print("\n  File yang berubah:")
            for f in changed_files:
                print(f"    {f}")
    else:
        # Multiple cherry-picks: one combined commit
        new_tree = Tree()
        for filepath, hash_id in current_files.items():
            name = filepath.split("/")[-1]
            new_tree.add_blob(name, hash_id, filepath)

        author = repo.get_author()
        message = f"Cherry-pick {len(commit_hashes)} commits: {', '.join(short_hash(h) for h in commit_hashes)}"

        new_hash = snapshot_mgr.create_snapshot(
            tree=new_tree,
            message=message,
            author=author,
            parent=current_hash,
        )

        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, new_hash)

        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(new_hash, "cherry-pick-multi", message, active_branch or "")

        print_color("✓ Cherry-pick berhasil!", "green")
        print(f"  Commits: {len(commit_hashes)}")
        for h in commit_hashes:
            print(f"    {short_hash(h)}")
        print(f"  Baru: {short_hash(new_hash)}")

    return 0
