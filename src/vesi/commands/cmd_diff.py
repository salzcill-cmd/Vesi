"""Command: bandingkan - Show differences between versions."""

from __future__ import annotations

import os
from pathlib import Path

from vesi.core.snapshot import SnapshotManager
from vesi.diff.engine import (
    diff_working_vs_snapshot,
    diff_between_trees,
    format_diff_header,
)
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.ignore import load_ignore_patterns, is_ignored
from vesi.repository.repository import Repository
from vesi.utils.paths import is_binary_file


def cmd_bandingkan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show differences between versions or working directory."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    args = parsed.args

    if len(args) == 0:
        # Diff working directory vs last commit
        return _diff_working_vs_last(repo, snapshot_mgr, verbose)
    elif len(args) == 1:
        # Diff specific version vs last commit, or working dir vs specific version
        version_id = args[0]
        commit_hash = _resolve_version(repo, version_id)
        return _diff_working_vs_version(repo, snapshot_mgr, commit_hash, version_id, verbose)
    elif len(args) == 2:
        # Diff between two versions
        v1_hash = _resolve_version(repo, args[0])
        v2_hash = _resolve_version(repo, args[1])
        return _diff_between_versions(repo, snapshot_mgr, v1_hash, v2_hash, args[0], args[1], verbose)
    else:
        raise VesiError("Terlalu banyak argumen. Gunakan: bandingkan [versi1] [versi2]")


def _resolve_version(repo: Repository, version_id: str) -> str:
    """Resolve a version ID (short hash) to full hash."""
    snapshot_mgr = SnapshotManager(repo)

    # Try as full hash first
    if repo.objects.exists(version_id):
        return version_id

    # Try to find by short hash prefix
    head_hash = repo.get_head_commit()
    if head_hash:
        # Walk history to find matching short hash
        current = head_hash
        while current:
            if current.startswith(version_id):
                return current
            try:
                data = snapshot_mgr.load_snapshot(current)
                current = data.get("parent")
            except Exception:
                break

    raise VersionNotFoundError(version_id)


def _diff_working_vs_last(
    repo: Repository,
    snapshot_mgr: SnapshotManager,
    verbose: bool,
) -> int:
    """Diff working directory vs last commit."""
    head_hash = repo.get_head_commit()
    if not head_hash:
        print("Belum ada versi yang tersimpan. Tidak bisa membandingkan.")
        return 0

    try:
        tree = snapshot_mgr.get_tree(head_hash)
    except Exception:
        print("Gagal memuat versi terakhir.")
        return 0

    # Build file contents from tree
    print(format_diff_header("diff", f"Perbandingan: working directory vs {head_hash[:7]}"))

    diffs_found = False
    for entry in tree.get_blob_entries():
        snapshot_content = repo.blobs.load_content(entry.hash_id)
        diff = diff_working_vs_snapshot(repo.root, entry.path, snapshot_content)
        if diff:
            print(diff)
            diffs_found = True

    # Check for new files in working directory
    ignore_patterns = load_ignore_patterns(repo.root)
    tracked_paths = {e.path for e in tree.get_blob_entries()}

    for root_dir, dirs, files in os.walk(repo.root):
        dirs[:] = [d for d in dirs if d != ".vesi"]

        for filename in files:
            file_path = Path(root_dir) / filename
            rel_path = str(file_path.relative_to(repo.root))

            if rel_path in tracked_paths or is_ignored(rel_path, ignore_patterns):
                continue

            if not is_binary_file(file_path):
                try:
                    diff = diff_working_vs_snapshot(repo.root, rel_path, None)
                    if diff:
                        print(diff)
                        diffs_found = True
                except (OSError, PermissionError):
                    continue

    if not diffs_found:
        print("Tidak ada perbedaan.")

    return 0


def _diff_working_vs_version(
    repo: Repository,
    snapshot_mgr: SnapshotManager,
    commit_hash: str,
    version_label: str,
    verbose: bool,
) -> int:
    """Diff working directory vs a specific version."""
    try:
        tree = snapshot_mgr.get_tree(commit_hash)
    except Exception:
        print(f"Gagal memuat versi {version_label}.")
        return 0

    print(format_diff_header("diff", f"Perbandingan: working directory vs {version_label}"))

    diffs_found = False
    for entry in tree.get_blob_entries():
        snapshot_content = repo.blobs.load_content(entry.hash_id)
        diff = diff_working_vs_snapshot(repo.root, entry.path, snapshot_content)
        if diff:
            print(diff)
            diffs_found = True

    if not diffs_found:
        print("Tidak ada perbedaan.")

    return 0


def _diff_between_versions(
    repo: Repository,
    snapshot_mgr: SnapshotManager,
    hash1: str,
    hash2: str,
    label1: str,
    label2: str,
    verbose: bool,
) -> int:
    """Diff between two specific versions."""
    try:
        tree1 = snapshot_mgr.get_tree(hash1)
        tree2 = snapshot_mgr.get_tree(hash2)
    except Exception as e:
        print(f"Gagal memuat versi: {e}")
        return 1

    # Build file content maps
    files1: dict[str, bytes] = {}
    for entry in tree1.get_blob_entries():
        files1[entry.path] = repo.blobs.load_content(entry.hash_id)

    files2: dict[str, bytes] = {}
    for entry in tree2.get_blob_entries():
        files2[entry.path] = repo.blobs.load_content(entry.hash_id)

    print(format_diff_header("diff", f"Perbandingan: {label1} vs {label2}"))
    result = diff_between_trees(repo.root, files1, files2)
    print(result)

    return 0
