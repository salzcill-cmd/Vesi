"""Command: gabungkan - Merge branches."""

from __future__ import annotations

import time
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.merge.engine import merge_branch, MergeResult
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.storage.tree import Tree
from vesi.utils.platform import print_color


def cmd_gabungkan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Merge a branch into the current active branch.

    Options:
      --no-ff    Force merge commit even for fast-forward
      --squash   Squash all commits into one
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan cabang yang akan digabungkan.",
            hint="Contoh:\n    gabungkan <nama-cabang>",
        )

    source_branch = parsed.args[0]
    no_ff = "--no-ff" in parsed.flags
    squash = "--squash" in parsed.flags

    # Check for uncommitted changes
    index = repo.index.load()
    head_hash = repo.get_head_commit()
    if index and head_hash:
        raise VesiError(
            "Ada perubahan yang belum disimpan.",
            hint="Simpan atau stashing terlebih dahulu:\n    simpan \"pesan\"\n    simpan sementara",
        )

    # Check if source branch exists
    source_hash = repo.refs.get_branch_hash(source_branch)
    if source_hash is None:
        raise VesiError(
            f"Cabang '{source_branch}' tidak ditemukan.",
            hint="Lihat cabang yang tersedia:\n    lihat cabang",
        )

    active_branch = repo.refs.get_active_branch()
    if not active_branch:
        raise VesiError("Tidak ada cabang aktif.")

    if squash:
        return _squash_merge(repo, source_branch, source_hash, active_branch, verbose)
    elif no_ff:
        return _no_ff_merge(repo, source_branch, source_hash, active_branch, verbose)
    else:
        result = merge_branch(repo, source_branch, dry_run=False)

        if result.success:
            print_color(f"✓ {result.message}", "green")
            return 0
        elif result.merge_type == "conflict":
            _write_merge_state(repo, source_branch, source_hash, result.conflicts)
            _print_conflict_details(repo, result.conflicts)
            print(f"\n  Perbaiki file tersebut, lalu jalankan:")
            print(f"    lanjutkan gabungan")
            print(f"\n  Atau batalkan:")
            print(f"    batalkan gabungan")
            return 4
        else:
            print_color(f"✗ {result.message}", "red")
            return 1


def _squash_merge(
    repo: Repository,
    source_branch: str,
    source_hash: str,
    active_branch: str,
    verbose: bool,
) -> int:
    """Squash merge: combine all source changes into one commit."""
    from vesi.core.snapshot import SnapshotManager
    from vesi.hashing import short_hash

    snapshot_mgr = SnapshotManager(repo)
    target_hash = repo.get_head_commit()

    if not target_hash or source_hash == target_hash:
        print_color("✓ Sudah up to date.", "yellow")
        return 0

    # Get trees
    try:
        source_tree = snapshot_mgr.get_tree(source_hash)
        target_tree = snapshot_mgr.get_tree(target_hash) if target_hash else Tree()
    except Exception as e:
        raise VesiError(f"Gagal memuat tree: {e}")

    # Build merged tree: source changes on top of target
    source_files = {e.path: e.hash_id for e in source_tree.get_blob_entries()}
    target_files = {e.path: e.hash_id for e in target_tree.get_blob_entries()}

    # Start with target files, overlay source files
    merged_files = dict(target_files)
    changed_files = []
    for filepath, hash_id in source_files.items():
        old_hash = merged_files.get(filepath)
        if old_hash != hash_id:
            changed_files.append(filepath)
        merged_files[filepath] = hash_id

    # Detect deleted files
    for filepath in target_files:
        if filepath not in source_files:
            del merged_files[filepath]
            changed_files.append(filepath)

    if not changed_files:
        print_color("✓ Tidak ada perubahan untuk di-squash.", "yellow")
        return 0

    # Create merged tree
    merged_tree = Tree()
    for filepath, hash_id in merged_files.items():
        name = filepath.split("/")[-1]
        merged_tree.add_blob(name, hash_id, filepath)

    # Create squash commit
    author = repo.get_author()
    message = f"Squash gabungan '{source_branch}' ke '{active_branch}'"

    new_hash = snapshot_mgr.create_snapshot(
        tree=merged_tree,
        message=message,
        author=author,
        parent=target_hash,
    )

    repo.refs.set_branch_hash(active_branch, new_hash)

    # Add reflog entry
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(new_hash, "squash-merge", message, active_branch)

    print_color("✓ Squash merge berhasil!", "green")
    print(f"  ID: {short_hash(new_hash)}")
    print(f"  Cabang: {source_branch} → {active_branch}")
    print(f"  File: {len(changed_files)} file berubah")
    if verbose:
        for f in changed_files:
            print(f"    {f}")

    return 0


def _no_ff_merge(
    repo: Repository,
    source_branch: str,
    source_hash: str,
    active_branch: str,
    verbose: bool,
) -> int:
    """No-fast-forward merge: always create a merge commit."""
    from vesi.core.snapshot import SnapshotManager
    from vesi.hashing import short_hash
    from vesi.merge.engine import _find_merge_base, _three_way_merge

    snapshot_mgr = SnapshotManager(repo)
    target_hash = repo.get_head_commit()

    if not target_hash or source_hash == target_hash:
        print_color("✓ Sudah up to date.", "yellow")
        return 0

    # Check if fast-forward is possible
    from vesi.merge.engine import _is_ancestor
    if target_hash == "" or _is_ancestor(snapshot_mgr, target_hash, source_hash):
        # Force merge commit even for fast-forward
        try:
            source_tree = snapshot_mgr.get_tree(source_hash)
        except Exception:
            raise VesiError("Gagal memuat tree.")

        # Create merge commit with both parents
        import time as _time
        merge_data = {
            "tree": source_tree.save(repo.objects),
            "message": f"Gabungan '{source_branch}' ke '{active_branch}'",
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
            "author": repo.get_author(),
            "parent": target_hash,
            "second_parent": source_hash,
        }

        merge_hash = repo.objects.save_json(merge_data)
        repo.refs.set_branch_hash(active_branch, merge_hash)

        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(merge_hash, "merge-no-ff", f"Merge '{source_branch}'", active_branch)

        print_color("✓ Gabungan (--no-ff) berhasil!", "green")
        print(f"  ID: {short_hash(merge_hash)}")
        print(f"  Gabungan: merge commit (no-ff)")
        return 0
    else:
        # Diverged: do three-way merge
        result = merge_branch(repo, source_branch, dry_run=False)
        if result.success:
            print_color(f"✓ {result.message}", "green")
            return 0
        elif result.merge_type == "conflict":
            _write_merge_state(repo, source_branch, source_hash, result.conflicts)
            _print_conflict_details(repo, result.conflicts)
            return 4
        else:
            print_color(f"✗ {result.message}", "red")
            return 1


def _write_merge_state(
    repo: Repository,
    source_branch: str,
    source_hash: str,
    conflicts: list[str],
) -> None:
    """Write merge state files for continue/abort."""
    # Write MERGE_HEAD
    merge_head_path = repo.vesi_dir / "MERGE_HEAD"
    merge_head_path.write_text(source_hash, encoding="utf-8")

    # Write MERGE_MSG
    merge_msg_path = repo.vesi_dir / "MERGE_MSG"
    merge_msg_path.write_text(
        f"Gabungan '{source_branch}' ke '{repo.refs.get_active_branch()}'",
        encoding="utf-8",
    )

    # Write MERGE_MODE
    merge_mode_path = repo.vesi_dir / "MERGE_MODE"
    merge_mode_path.write_text("normal", encoding="utf-8")

    # Write MERGE_CONFLICTS
    import json
    conflicts_path = repo.vesi_dir / "MERGE_CONFLICTS"
    conflicts_path.write_text(
        json.dumps(conflicts), encoding="utf-8"
    )


def _print_conflict_details(repo: Repository, conflicts: list[str]) -> None:
    """Print detailed conflict information with actual conflict markers."""
    print_color(f"\n⚠ Konflik ditemukan di {len(conflicts)} file:\n", "yellow")

    for filepath in conflicts:
        file_path = repo.root / filepath
        if not file_path.is_file():
            print(f"  {filepath} [file tidak ditemukan di working dir]")
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            # Count conflict markers
            conflicts_count = content.count("<<<<<<< HEAD")

            print(f"  {filepath} ({conflicts_count} konflik)")

            # Show conflict sections
            in_conflict = False
            section = 0
            our_lines = []
            their_lines = []

            for i, line in enumerate(lines, 1):
                if line.startswith("<<<<<<< HEAD"):
                    in_conflict = True
                    section += 1
                    our_lines = []
                    their_lines = []
                elif line.startswith("======="):
                    pass  # separator
                elif line.startswith(">>>>>>>"):
                    in_conflict = False
                    print(f"    Konflik #{section}: baris {i - len(their_lines) - len(our_lines) - 2}-{i}")
                    print(f"      Versi kami: {len(our_lines)} baris")
                    print(f"      Versi mereka: {len(their_lines)} baris")
                    if our_lines == their_lines:
                        print(f"      💡 Kedua versi identik")
                    our_lines = []
                    their_lines = []
                elif in_conflict:
                    if not their_lines:
                        our_lines.append(line)
                    else:
                        their_lines.append(line)
                # Simple heuristic: if we see content after ======= marker
                elif line.startswith("======="):
                    in_conflict = True  # We're now in "theirs" section

        except (OSError, UnicodeDecodeError):
            print(f"  {filepath} [tidak bisa dibaca]")

    print()
