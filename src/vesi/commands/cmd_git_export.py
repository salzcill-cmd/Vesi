"""Command: ekspor git - Export a .vesi repository to .git format."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from vesi.core.git_writer import GitWriter
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


def cmd_ekspor_git(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Export a .vesi repository to .git format.

    Usage:
      ekspor git [path]          - Export to .git at path
      ekspor git .               - Export to current directory
      ekspor git --ke <path>     - Export to specific path
      ekspor git --bare          - Export as bare repository
      ekspor git --all           - Export all branches
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Determine target path
    target_path = None
    args = parsed.args or []

    if "--ke" in parsed.flags:
        idx = parsed.flags.index("--ke")
        if idx < len(args):
            target_path = Path(args[idx])

    if target_path is None:
        for arg in args:
            if not arg.startswith("--"):
                target_path = Path(arg)
                break

    if target_path is None:
        target_path = Path.cwd() / f"{repo.root.name}.git"

    # Create target directory
    if target_path.exists():
        if "--force" in parsed.flags:
            shutil.rmtree(target_path)
        else:
            raise VesiError(
                f"Directory '{target_path}' sudah ada.",
                hint="Gunakan --force untuk menimpa, atau pilih path lain.",
            )

    target_path.mkdir(parents=True, exist_ok=True)

    print_color("📦 Mengekspor repository ke Git...\n", "cyan")
    print(f"  Sumber: {repo.root}")
    print(f"  Target: {target_path}")

    # Initialize .git directory
    git_writer = GitWriter(target_path)
    git_writer.init()
    git_writer.write_description(f"Exported from vesi repository: {repo.root.name}")
    git_writer.write_config(bare="--bare" in parsed.flags)
    git_writer.write_exclude()

    # Track export stats
    stats = {
        "commits": 0,
        "files": 0,
        "branches": 0,
        "tags": 0,
    }

    export_all = "--all" in parsed.flags

    # Export all branches
    print_color("\n1️⃣  Mengekspor branch...\n", "yellow")

    branches = repo.refs.list_branches()
    snapshot_mgr = SnapshotManager(repo)

    vesi_to_git_commit: dict[str, str] = {}  # vesi_hash -> git_hash
    vesi_to_git_tree: dict[str, str] = {}  # vesi_tree_hash -> git_tree_hash
    vesi_to_git_blob: dict[str, str] = {}  # vesi_blob_hash -> git_blob_hash

    # Export each branch
    for branch_name in branches:
        branch_hash = repo.refs.get_branch_hash(branch_name)
        if not branch_hash:
            continue

        print(f"  🌿 Exporting branch: {branch_name}")

        # Walk and export commits for this branch
        current = branch_hash
        visited = set()

        while current and current not in visited:
            visited.add(current)

            try:
                vesi_data = snapshot_mgr.load_snapshot(current)
            except (FileNotFoundError, ValueError):
                break

            # Export tree
            git_tree_hash = _export_tree(
                repo, snapshot_mgr, vesi_data.get("tree", ""),
                vesi_to_git_tree, vesi_to_git_blob, verbose
            )

            # Convert parents
            git_parents = []
            parent = vesi_data.get("parent")
            if parent and parent in vesi_to_git_commit:
                git_parents.append(vesi_to_git_commit[parent])

            second_parent = vesi_data.get("second_parent")
            if second_parent and second_parent in vesi_to_git_commit:
                git_parents.append(vesi_to_git_commit[second_parent])

            # Parse timestamp
            timestamp_str = vesi_data.get("timestamp", "")
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamp = int(dt.timestamp())
            except (ValueError, TypeError):
                timestamp = int(time.time())

            # Create git commit
            author = vesi_data.get("author", "unknown")
            message = vesi_data.get("message", "Exported commit")

            git_hash = git_writer.write_commit(
                tree_hash=git_tree_hash,
                parent_hashes=git_parents,
                author=author,
                author_email=f"{author}@vesi.local",
                author_timestamp=timestamp,
                committer=author,
                committer_email=f"{author}@vesi.local",
                committer_timestamp=timestamp,
                message=message,
            )

            vesi_to_git_commit[current] = git_hash
            stats["commits"] += 1

            if verbose:
                print(f"    {short_hash(current)} -> {short_hash(git_hash)}")

            # Follow parent
            current = parent

        # Set branch reference
        if branch_hash in vesi_to_git_commit:
            git_writer.set_branch(branch_name, vesi_to_git_commit[branch_hash])
            stats["branches"] += 1

    # Set HEAD
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        git_writer.set_head(active_branch, symbolic=True)
        print(f"\n  ✓ HEAD -> {active_branch}")

    print(f"  ✓ {stats['branches']} branch diexport")

    # Export tags
    print_color("\n2️⃣  Mengekspor tag...\n", "yellow")

    tags_dir = repo.vesi_dir / "refs" / "tags"
    if tags_dir.is_dir():
        for tag_file in tags_dir.iterdir():
            if tag_file.is_file():
                tag_name = tag_file.name
                content = tag_file.read_text(encoding="utf-8").strip()

                # Check if it's a vesi hash
                if len(content) == 40 and content in vesi_to_git_commit:
                    git_writer.set_tag(tag_name, vesi_to_git_commit[content])
                    stats["tags"] += 1

                    if verbose:
                        print(f"  ✓ {tag_name}")

    print(f"  ✓ {stats['tags']} tag diexport")

    # Summary
    print_color(f"\n{'━' * 50}", "dim")
    print_color("✓ Export selesai!", "green")
    print(f"  📁 Repository: {target_path}")
    print(f"  📝 Commits:    {stats['commits']}")
    print(f"  🌿 Branches:   {stats['branches']}")
    print(f"  🏷️  Tags:       {stats['tags']}")

    print(f"\n  Repository Git sudah bisa digunakan:")
    print(f"    cd {target_path}")
    print(f"    git log")
    print(f"    git status")

    return 0


def _export_tree(
    repo: Repository,
    snapshot_mgr: SnapshotManager,
    vesi_tree_hash: str,
    tree_map: dict[str, str],
    blob_map: dict[str, str],
    verbose: bool,
) -> str:
    """Export a vesi tree to Git tree format."""
    if vesi_tree_hash in tree_map:
        return tree_map[vesi_tree_hash]

    if not vesi_tree_hash:
        return ""

    try:
        vesi_tree = Tree.load(repo.objects, vesi_tree_hash)
    except (FileNotFoundError, ValueError):
        return ""

    # Build git tree entries
    git_entries = []

    for entry in vesi_tree.entries:
        if entry.type == "blob":
            # Export blob
            if entry.hash_id not in blob_map:
                try:
                    blob_data = repo.objects.load_blob(entry.hash_id)
                    git_hash = _write_git_blob(repo, blob_data)
                    blob_map[entry.hash_id] = git_hash
                except (FileNotFoundError, ValueError):
                    continue

            git_blob_hash = blob_map.get(entry.hash_id, "")
            if git_blob_hash:
                # Git mode: 100644 for regular files
                git_entries.append((entry.name, 100644, git_blob_hash))

        elif entry.type == "tree":
            # Recursively export subtree
            git_subtree_hash = _export_tree(
                repo, snapshot_mgr, entry.hash_id,
                tree_map, blob_map, verbose
            )
            if git_subtree_hash:
                # Git mode: 040000 for directories
                git_entries.append((entry.name, 0o040000, git_subtree_hash))

    if not git_entries:
        # Empty tree
        import hashlib
        content = b""
        header = f"tree {len(content)}\x00".encode()
        store = header + content
        git_hash = hashlib.sha1(store).hexdigest()
        tree_map[vesi_tree_hash] = git_hash
        return git_hash

    # Write git tree
    git_hash = _write_git_tree(repo, git_entries)
    tree_map[vesi_tree_hash] = git_hash

    return git_hash


def _write_git_blob(repo: Repository, data: bytes) -> str:
    """Write a Git blob object."""
    import hashlib
    import zlib
    import tempfile
    import os

    header = f"blob {len(data)}\x00".encode()
    store = header + data
    hash_id = hashlib.sha1(store).hexdigest()

    # Write to objects
    objects_dir = repo.vesi_dir / "git_objects"
    objects_dir.mkdir(parents=True, exist_ok=True)

    obj_dir = objects_dir / hash_id[:2]
    obj_dir.mkdir(parents=True, exist_ok=True)

    obj_path = obj_dir / hash_id[2:]
    compressed = zlib.compress(store)

    fd, tmp_path = tempfile.mkstemp(dir=str(objects_dir), prefix=".tmp_")
    try:
        os.write(fd, compressed)
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp_path, str(obj_path))
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return hash_id


def _write_git_tree(repo: Repository, entries: list[tuple[str, int, str]]) -> str:
    """Write a Git tree object."""
    import hashlib
    import zlib
    import tempfile
    import os

    content = b""
    for name, mode, hash_id in sorted(entries, key=lambda x: x[0]):
        mode_str = f"{mode:o}".encode()
        name_bytes = name.encode("utf-8")
        hash_bytes = bytes.fromhex(hash_id)
        content += mode_str + b" " + name_bytes + b"\x00" + hash_bytes

    header = f"tree {len(content)}\x00".encode()
    store = header + content
    hash_id = hashlib.sha1(store).hexdigest()

    # Write to objects
    objects_dir = repo.vesi_dir / "git_objects"
    objects_dir.mkdir(parents=True, exist_ok=True)

    obj_dir = objects_dir / hash_id[:2]
    obj_dir.mkdir(parents=True, exist_ok=True)

    obj_path = obj_dir / hash_id[2:]
    compressed = zlib.compress(store)

    fd, tmp_path = tempfile.mkstemp(dir=str(objects_dir), prefix=".tmp_")
    try:
        os.write(fd, compressed)
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp_path, str(obj_path))
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return hash_id
