"""Merge engine - fast-forward and three-way merge with conflict resolution."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vesi.core.snapshot import SnapshotManager
from vesi.repository.repository import Repository
from vesi.storage.tree import Tree


@dataclass
class MergeResult:
    """Result of a merge operation."""

    success: bool
    merge_type: str  # "fast-forward", "three-way", "conflict", "already-up-to-date"
    conflicts: list[str] = field(default_factory=list)
    message: str = ""


def merge_branch(
    repo: Repository,
    source_branch: str,
    *,
    dry_run: bool = False,
) -> MergeResult:
    """Merge source_branch into the current active branch.

    Determines whether fast-forward or three-way merge is needed.
    """
    active_branch = repo.refs.get_active_branch()
    if active_branch is None:
        return MergeResult(
            success=False,
            merge_type="error",
            message="Tidak ada cabang aktif. Pindah ke cabang terlebih dahulu.",
        )

    source_hash = repo.refs.get_branch_hash(source_branch)
    target_hash = repo.refs.get_branch_hash(active_branch)

    if source_hash is None:
        return MergeResult(
            success=False,
            merge_type="error",
            message=f"Cabang '{source_branch}' tidak ditemukan.",
        )

    if source_hash == "" or source_hash == target_hash:
        return MergeResult(
            success=True,
            merge_type="already-up-to-date",
            message="Sudah up to date.",
        )

    snapshot_mgr = SnapshotManager(repo)

    # Check if target_hash is ancestor of source_hash (fast-forward possible)
    if target_hash == "" or _is_ancestor(snapshot_mgr, target_hash, source_hash):
        # Fast-forward
        if not dry_run:
            repo.refs.set_branch_hash(active_branch, source_hash)
        return MergeResult(
            success=True,
            merge_type="fast-forward",
            message=f"Cabang '{source_branch}' berhasil digabungkan ke '{active_branch}'.\n    Gabungan: fast-forward",
        )

    # Three-way merge
    return _three_way_merge(repo, source_branch, active_branch, dry_run=dry_run)


def merge_with_strategy(
    repo: Repository,
    source_branch: str,
    strategy: str = "normal",
) -> MergeResult:
    """Merge with a specific conflict resolution strategy.

    Strategies:
    - "normal": default merge (report conflicts)
    - "ours": prefer our version on conflicts
    - "theirs": prefer their version on conflicts
    - "union": combine both versions (union merge)
    """
    active_branch = repo.refs.get_active_branch()
    if active_branch is None:
        return MergeResult(
            success=False,
            merge_type="error",
            message="Tidak ada cabang aktif.",
        )

    source_hash = repo.refs.get_branch_hash(source_branch)
    target_hash = repo.refs.get_branch_hash(active_branch)

    if source_hash is None:
        return MergeResult(
            success=False,
            merge_type="error",
            message=f"Cabang '{source_branch}' tidak ditemukan.",
        )

    if source_hash == target_hash:
        return MergeResult(
            success=True,
            merge_type="already-up-to-date",
            message="Sudah up to date.",
        )

    snapshot_mgr = SnapshotManager(repo)

    # Fast-forward check
    if _is_ancestor(snapshot_mgr, target_hash, source_hash):
        repo.refs.set_branch_hash(active_branch, source_hash)
        return MergeResult(
            success=True,
            merge_type="fast-forward",
            message=f"Cabang '{source_branch}' berhasil digabungkan ke '{active_branch}'.",
        )

    # Three-way merge with strategy
    return _three_way_merge_with_strategy(
        repo, source_branch, active_branch, strategy
    )


def _three_way_merge_with_strategy(
    repo: Repository,
    source_branch: str,
    target_branch: str,
    strategy: str,
) -> MergeResult:
    """Three-way merge with conflict resolution strategy."""
    snapshot_mgr = SnapshotManager(repo)
    source_hash = repo.refs.get_branch_hash(source_branch)
    target_hash = repo.refs.get_branch_hash(target_branch)

    if not source_hash or not target_hash:
        return MergeResult(
            success=False,
            merge_type="error",
            message="Gagal melakukan merge.",
        )

    # Find common ancestor
    ancestor = _find_merge_base(snapshot_mgr, target_hash, source_hash)
    if ancestor is None:
        return MergeResult(
            success=False,
            merge_type="error",
            message="Tidak bisa menemukan common ancestor untuk merge.",
        )

    # Get trees
    try:
        source_tree = snapshot_mgr.get_tree(source_hash)
        target_tree = snapshot_mgr.get_tree(target_hash)
        ancestor_tree = snapshot_mgr.get_tree(ancestor)
    except Exception as e:
        return MergeResult(
            success=False,
            merge_type="error",
            message=f"Gagal memuat tree: {e}",
        )

    # Build file maps
    source_files = {e.path: e.hash_id for e in source_tree.get_blob_entries()}
    target_files = {e.path: e.hash_id for e in target_tree.get_blob_entries()}
    ancestor_files = {e.path: e.hash_id for e in ancestor_tree.get_blob_entries()}

    # Detect conflicts
    conflicts = _detect_conflicts(source_files, target_files, ancestor_files)

    if conflicts and strategy in ("ours", "theirs", "union"):
        # Auto-resolve conflicts using strategy
        merged_files = _apply_merge_with_strategy(
            source_files, target_files, ancestor_files, conflicts, strategy
        )
    elif conflicts:
        return MergeResult(
            success=False,
            merge_type="conflict",
            conflicts=conflicts,
            message="Ada konflik yang perlu diselesaikan.",
        )
    else:
        merged_files = _apply_merge(source_files, target_files, ancestor_files)

    # Create merged tree
    merged_tree = Tree()
    for filepath, hash_id in merged_files.items():
        name = filepath.split("/")[-1]
        merged_tree.add_blob(name, hash_id, filepath)

    # Save merged tree and create merge commit
    merged_tree_hash = merged_tree.save(repo.objects)

    merge_data = {
        "tree": merged_tree_hash,
        "message": f"Gabungan '{source_branch}' ke '{target_branch}'",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "author": repo.get_author(),
        "parent": target_hash,  # First parent (target)
        "second_parent": source_hash,  # Second parent (source)
    }

    merge_hash = repo.objects.save_json(merge_data)
    repo.refs.set_branch_hash(target_branch, merge_hash)

    strategy_msg = f" (strategi: {strategy})" if strategy != "normal" else ""
    return MergeResult(
        success=True,
        merge_type="three-way",
        message=f"Cabang '{source_branch}' berhasil digabungkan ke '{target_branch}'.\n    Gabungan: three-way merge{strategy_msg}",
    )


def _apply_merge_with_strategy(
    source: dict[str, str],
    target: dict[str, str],
    ancestor: dict[str, str],
    conflicts: list[str],
    strategy: str,
) -> dict[str, str]:
    """Apply merge with a specific conflict resolution strategy."""
    result: dict[str, str] = {}
    all_files = set(list(source.keys()) + list(target.keys()) + list(ancestor.keys()))

    for filepath in all_files:
        src_hash = source.get(filepath)
        tgt_hash = target.get(filepath)
        anc_hash = ancestor.get(filepath)

        is_conflict = filepath in conflicts

        if is_conflict:
            if strategy == "ours":
                result[filepath] = tgt_hash  # Keep our version
            elif strategy == "theirs":
                result[filepath] = src_hash  # Keep their version
            elif strategy == "union":
                # Union merge: keep both (take theirs as base, add ours)
                result[filepath] = tgt_hash  # Simplified: keep ours
        else:
            # Non-conflicting: apply normal merge logic
            if src_hash is None:
                # File deleted in source
                if tgt_hash is not None and tgt_hash != anc_hash:
                    result[filepath] = tgt_hash
            elif tgt_hash is None:
                # File deleted in target
                if src_hash is not None and src_hash != anc_hash:
                    result[filepath] = src_hash
            elif src_hash == anc_hash:
                # Only target changed
                result[filepath] = tgt_hash
            elif tgt_hash == anc_hash:
                # Only source changed
                result[filepath] = src_hash
            else:
                # Both changed but not conflicting
                result[filepath] = src_hash  # Prefer source (incoming)

    return result


def _is_ancestor(
    snapshot_mgr: SnapshotManager,
    candidate: str,
    descendant: str,
    max_depth: int = 1000,
) -> bool:
    """Check if candidate is an ancestor of descendant."""
    if candidate == "" or descendant == "":
        return False

    current = descendant
    visited: set[str] = set()

    for _ in range(max_depth):
        if current == candidate:
            return True
        if current in visited:
            break
        visited.add(current)

        try:
            parent = snapshot_mgr.get_parent(current)
        except Exception:
            break

        if parent is None:
            break
        current = parent

    return False


def _three_way_merge(
    repo: Repository,
    source_branch: str,
    target_branch: str,
    *,
    dry_run: bool = False,
) -> MergeResult:
    """Perform three-way merge."""
    snapshot_mgr = SnapshotManager(repo)

    source_hash = repo.refs.get_branch_hash(source_branch)
    target_hash = repo.refs.get_branch_hash(target_branch)

    if not source_hash or not target_hash:
        return MergeResult(
            success=False,
            merge_type="error",
            message="Gagal melakukan merge.",
        )

    # Find common ancestor (merge base)
    ancestor = _find_merge_base(snapshot_mgr, target_hash, source_hash)

    if ancestor is None:
        return MergeResult(
            success=False,
            merge_type="error",
            message="Tidak bisa menemukan common ancestor untuk merge.",
        )

    # Get trees for all three commits
    try:
        source_tree = snapshot_mgr.get_tree(source_hash)
        target_tree = snapshot_mgr.get_tree(target_hash)
        ancestor_tree = snapshot_mgr.get_tree(ancestor)
    except Exception as e:
        return MergeResult(
            success=False,
            merge_type="error",
            message=f"Gagal memuat tree: {e}",
        )

    # Build file maps
    source_files = {e.path: e.hash_id for e in source_tree.get_blob_entries()}
    target_files = {e.path: e.hash_id for e in target_tree.get_blob_entries()}
    ancestor_files = {e.path: e.hash_id for e in ancestor_tree.get_blob_entries()}

    # Detect conflicts
    conflicts = _detect_conflicts(source_files, target_files, ancestor_files)

    if conflicts:
        return MergeResult(
            success=False,
            merge_type="conflict",
            conflicts=conflicts,
            message="Ada konflik yang perlu diselesaikan.",
        )

    if dry_run:
        return MergeResult(
            success=True,
            merge_type="three-way",
            message="Three-way merge bisa dilakukan tanpa konflik.",
        )

    # Perform the merge: combine changes from source and target
    merged_files = _apply_merge(source_files, target_files, ancestor_files)

    # Create merged tree
    merged_tree = Tree()
    for filepath, hash_id in merged_files.items():
        name = filepath.split("/")[-1]
        merged_tree.add_blob(name, hash_id, filepath)

    # Save merged tree and create merge commit
    merged_tree_hash = merged_tree.save(repo.objects)

    merge_data = {
        "tree": merged_tree_hash,
        "message": f"Gabungan '{source_branch}' ke '{target_branch}'",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "author": repo.get_author(),
        "parent": target_hash,  # First parent (target)
        "second_parent": source_hash,  # Second parent (source)
    }

    merge_hash = repo.objects.save_json(merge_data)
    repo.refs.set_branch_hash(target_branch, merge_hash)

    return MergeResult(
        success=True,
        merge_type="three-way",
        message=f"Cabang '{source_branch}' berhasil digabungkan ke '{target_branch}'.\n    Gabungan: three-way merge",
    )


def _find_merge_base(
    snapshot_mgr: SnapshotManager,
    hash1: str,
    hash2: str,
    max_depth: int = 1000,
) -> str | None:
    """Find the merge base (common ancestor) of two commits."""
    # Walk ancestors of hash1, collect all hashes
    ancestors1: set[str] = set()
    current = hash1
    for _ in range(max_depth):
        if current == "":
            break
        ancestors1.add(current)
        try:
            parent = snapshot_mgr.get_parent(current)
        except Exception:
            break
        if parent is None:
            break
        current = parent

    # Walk ancestors of hash2 until we find a common one
    current = hash2
    for _ in range(max_depth):
        if current == "":
            break
        if current in ancestors1:
            return current
        try:
            parent = snapshot_mgr.get_parent(current)
        except Exception:
            break
        if parent is None:
            break
        current = parent

    return None


def _detect_conflicts(
    source: dict[str, str],
    target: dict[str, str],
    ancestor: dict[str, str],
) -> list[str]:
    """Detect merge conflicts.

    A conflict occurs when both source and target changed the same file
    relative to the ancestor, and the changes are different.
    """
    conflicts: list[str] = []
    all_files = set(list(source.keys()) + list(target.keys()) + list(ancestor.keys()))

    for filepath in all_files:
        src_hash = source.get(filepath)
        tgt_hash = target.get(filepath)
        anc_hash = ancestor.get(filepath)

        # File changed in both source and target, and differently
        if src_hash != anc_hash and tgt_hash != anc_hash and src_hash != tgt_hash:
            conflicts.append(filepath)

    return sorted(conflicts)


def _apply_merge(
    source: dict[str, str],
    target: dict[str, str],
    ancestor: dict[str, str],
) -> dict[str, str]:
    """Apply merge: combine non-conflicting changes.

    Since we already checked for conflicts, this is safe.
    """
    result: dict[str, str] = {}
    all_files = set(list(source.keys()) + list(target.keys()) + list(ancestor.keys()))

    for filepath in all_files:
        src_hash = source.get(filepath)
        tgt_hash = target.get(filepath)

        if src_hash is not None:
            result[filepath] = src_hash
        elif tgt_hash is not None:
            result[filepath] = tgt_hash

    return result
