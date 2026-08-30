"""Command: impor git - Import a .git repository to .vesi format."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from vesi.core.git_parser import GitParser
from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryAlreadyExistsError,
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.storage.blob import BlobStore
from vesi.storage.objects import ObjectStore
from vesi.storage.tree import Tree, TreeEntry
from vesi.utils.platform import print_color


def cmd_impor_git(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Import a .git repository to .vesi format.

    Usage:
      impor git [path]          - Import from .git at path
      impor git .               - Import from current directory
      impor git --dari <path>   - Import from specific path
      impor git --bare          - Import bare repository
      impor git --branches      - Import all branches (default: HEAD only)
    """
    # Find source .git directory
    source_path = _find_git_repo(parsed)

    if not source_path:
        raise VesiError(
            "Repository .git tidak ditemukan.",
            hint="Pastikan direktori .git ada di lokasi yang ditentukan.",
        )

    git_parser = GitParser(source_path)

    if not git_parser.has_git_repo():
        raise VesiError(
            f"Bukan repository .git yang valid: {source_path}",
            hint="Pastikan direktori berisi .git/ yang valid.",
        )

    # Check if we're already in a vesi repo
    try:
        repo = Repository.find()
        raise VesiError(
            "Sudah ada repository vesi di sini.",
            hint="Gunakan direktori lain atau hapus .vesi/ terlebih dahulu.",
        )
    except RepositoryNotFoundError:
        pass

    # Determine target directory
    target_path = Path.cwd()
    if "--ke" in parsed.flags:
        idx = parsed.flags.index("--ke")
        args = parsed.args or []
        if idx < len(args):
            target_path = Path(args[idx])

    print_color("📦 Mengimpor repository Git...\n", "cyan")
    print(f"  Sumber: {source_path}")

    # Initialize vesi repository
    try:
        repo = Repository.init(target_path)
    except RepositoryAlreadyExistsError:
        raise VesiError("Sudah ada repository vesi di sini.")

    print(f"  Target: {target_path}")
    print()

    # Track import stats
    stats = {
        "commits": 0,
        "files": 0,
        "branches": 0,
        "tags": 0,
    }

    import_all_branches = "--branches" in parsed.flags
    import_bare = "--bare" in parsed.flags

    # Import HEAD and history
    head_hash = git_parser.resolve_head()
    if not head_hash:
        print_color("⚠ Tidak ada commit di repository Git.", "yellow")
        return 0

    print_color("1️⃣  Mengimpor riwayat commit...\n", "yellow")

    # Walk all commits and import them
    commit_map: dict[str, str] = {}  # git_hash -> vesi_hash
    tree_map: dict[str, str] = {}  # git_tree_hash -> vesi_tree_hash
    blob_map: dict[str, str] = {}  # git_blob_hash -> vesi_blob_hash

    # First pass: collect all commits
    all_commits = list(git_parser.walk_commits(max_count=10000))
    total_commits = len(all_commits)

    print(f"  Ditemukan {total_commits} commit")

    # Import in reverse order (oldest first)
    for i, git_commit in enumerate(reversed(all_commits)):
        git_hash = git_commit.hash_id

        if verbose:
            print(f"  [{i+1}/{total_commits}] {short_hash(git_hash)} {git_commit.message[:50]}")

        # Import tree
        vesi_tree_hash = _import_tree(
            git_parser, repo, git_commit.tree_hash, tree_map, blob_map, verbose
        )

        # Convert parents
        vesi_parents = []
        for parent_hash in git_commit.parent_hashes:
            if parent_hash in commit_map:
                vesi_parents.append(commit_map[parent_hash])

        # Parse timestamp
        try:
            timestamp = int(git_commit.author_timestamp)
        except (ValueError, TypeError):
            timestamp = int(time.time())

        # Create vesi snapshot
        tree = Tree()
        # We need to create a proper tree from the vesi tree hash
        # For now, create a simple tree with the imported files
        snapshot_mgr = SnapshotManager(repo)

        # Get all files from the git tree
        git_files = git_parser.get_tree_files(git_commit.tree_hash)

        # Create tree entries
        for filepath, git_blob_hash in git_files.items():
            # Get or create vesi blob
            if git_blob_hash not in blob_map:
                git_obj = git_parser.read_object(git_blob_hash)
                if git_obj:
                    vesi_hash = repo.blobs.save_blob(git_obj.data)
                    blob_map[git_blob_hash] = vesi_hash

            vesi_blob_hash = blob_map.get(git_blob_hash, "")
            name = filepath.split("/")[-1]
            tree.add_blob(name, vesi_blob_hash, filepath)

        # Save tree
        vesi_tree_hash_actual = tree.save(repo.objects)

        # Create snapshot
        author = git_commit.author or git_commit.committer or "unknown"
        message = git_commit.message or "Imported commit"

        parent_hash = vesi_parents[0] if vesi_parents else None

        vesi_hash = snapshot_mgr.create_snapshot(
            tree=tree,
            message=message,
            author=author,
            parent=parent_hash,
        )

        commit_map[git_hash] = vesi_hash
        stats["commits"] += 1

    print(f"  ✓ {stats['commits']} commit diimpor")

    # Import branches
    print_color("\n2️⃣  Mengimpor branch...\n", "yellow")

    refs = git_parser.read_refs()
    head_ref = None

    for ref in refs:
        if ref.name == "HEAD" and ref.ref_type == "symbolic":
            head_ref = ref.target.replace("refs/heads/", "")
            continue

        if ref.ref_type == "branch":
            branch_name = ref.name
            git_commit_hash = ref.target

            if git_commit_hash in commit_map:
                vesi_hash = commit_map[git_commit_hash]
                repo.refs.set_branch_hash(branch_name, vesi_hash)
                stats["branches"] += 1

                if verbose:
                    print(f"  ✓ {branch_name} -> {short_hash(vesi_hash)}")

    # Set HEAD to main branch
    if head_ref and head_ref in [r.name for r in refs if r.ref_type == "branch"]:
        repo.refs.set_head(head_ref)
        print(f"  ✓ HEAD -> {head_ref}")
    elif stats["branches"] > 0:
        # Use first branch as default
        first_branch = next(
            (r.name for r in refs if r.ref_type == "branch"),
            "main",
        )
        repo.refs.set_head(first_branch)
        print(f"  ✓ HEAD -> {first_branch}")

    print(f"  ✓ {stats['branches']} branch diimpor")

    # Import tags
    print_color("\n3️⃣  Mengimpor tag...\n", "yellow")

    tags_dir = source_path / "refs" / "tags"
    if tags_dir.is_dir():
        for tag_file in tags_dir.rglob("*"):
            if tag_file.is_file():
                tag_name = str(tag_file.relative_to(tags_dir))
                target_hash = tag_file.read_text(encoding="utf-8").strip()

                if target_hash in commit_map:
                    vesi_hash = commit_map[target_hash]
                    repo.refs.set_branch_hash(f"tag-{tag_name}", vesi_hash)
                    stats["tags"] += 1

                    if verbose:
                        print(f"  ✓ {tag_name} -> {short_hash(vesi_hash)}")

    print(f"  ✓ {stats['tags']} tag diimpor")

    # Summary
    print_color(f"\n{'━' * 50}", "dim")
    print_color("✓ Import selesai!", "green")
    print(f"  📁 Repository: {target_path}")
    print(f"  📝 Commits:    {stats['commits']}")
    print(f"  🌿 Branches:   {stats['branches']}")
    print(f"  🏷️  Tags:       {stats['tags']}")

    print(f"\n  Gunakan vesi seperti biasa:")
    print(f"    vesi lihat riwayat")
    print(f"    vesi lihat perubahan")
    print(f"    vesi lihat cabang")

    return 0


def _import_tree(
    git_parser: GitParser,
    repo: Repository,
    git_tree_hash: str,
    tree_map: dict[str, str],
    blob_map: dict[str, str],
    verbose: bool,
) -> str:
    """Import a Git tree into vesi object store."""
    if git_tree_hash in tree_map:
        return tree_map[git_tree_hash]

    git_obj = git_parser.read_object(git_tree_hash)
    if git_obj is None:
        return ""

    git_tree = git_parser.parse_tree(git_obj)

    # Import all entries
    for entry in git_tree.entries:
        if entry.is_blob and entry.hash_id not in blob_map:
            blob_data = git_parser.get_file_content(entry.hash_id)
            if blob_data is not None:
                vesi_hash = repo.blobs.save_blob(blob_data)
                blob_map[entry.hash_id] = vesi_hash

        elif entry.is_tree:
            _import_tree(
                git_parser, repo, entry.hash_id,
                tree_map, blob_map, verbose
            )

    # Create vesi tree
    tree = Tree()
    for entry in git_tree.entries:
        if entry.is_blob:
            vesi_blob_hash = blob_map.get(entry.hash_id, "")
            tree.add_blob(entry.name, vesi_blob_hash, entry.name)
        elif entry.is_tree:
            vesi_tree_hash = tree_map.get(entry.hash_id, "")
            tree.add_tree(entry.name, vesi_tree_hash, entry.name)

    vesi_hash = tree.save(repo.objects)
    tree_map[git_tree_hash] = vesi_hash

    return vesi_hash


def _find_git_repo(parsed: ParsedCommand) -> Path | None:
    """Find the .git directory to import from."""
    args = parsed.args or []

    # Check --dari flag
    if "--dari" in parsed.flags:
        idx = parsed.flags.index("--dari")
        if idx < len(args):
            path = Path(args[idx])
            if (path / ".git").is_dir():
                return path / ".git"
            elif path.name == ".git" and path.is_dir():
                return path

    # Check regular args
    for arg in args:
        if arg.startswith("--"):
            continue
        path = Path(arg)
        if (path / ".git").is_dir():
            return path / ".git"
        elif path.name == ".git" and path.is_dir():
            return path

    # Default: current directory
    cwd = Path.cwd()
    if (cwd / ".git").is_dir():
        return cwd / ".git"

    return None
