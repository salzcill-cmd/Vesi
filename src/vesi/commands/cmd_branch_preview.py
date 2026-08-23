"""Command: lihat cabang - Preview branch contents before switching."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    BranchNotFoundError,
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_lihat_cabang_detail(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Preview branch contents.

    Usage:
      lihat cabang detail <branch>   - Show files in branch
      lihat cabang detail            - Show current branch info
      lihat cabang bandingkan <b1> <b2> - Compare two branches
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    snapshot_mgr = SnapshotManager(repo)

    if not args:
        # Show current branch info
        current_hash = repo.get_head_commit()
        active_branch = repo.refs.get_active_branch() or "detached"

        if current_hash:
            try:
                data = snapshot_mgr.load_snapshot(current_hash)
                tree = snapshot_mgr.get_tree(current_hash)
                files = tree.get_blob_entries()

                print_color(f"Cabang: {active_branch}\n", "cyan")
                print(f"  HEAD: {short_hash(current_hash)}")
                print(f"  Pesan: {data.get('message', '')}")
                print(f"  Waktu: {data.get('timestamp', '')[:19]}")
                print(f"  File: {len(files)} file")

                if verbose:
                    print(f"\n  File di cabang ini:")
                    for entry in files:
                        print(f"    {entry.path}")
            except Exception as e:
                print_color(f"Gagal membaca cabang: {e}", "red")
        else:
            print(f"Cabang: {active_branch} (belum ada commit)")

        return 0

    elif args[0] == "bandingkan" and len(args) >= 3:
        # Compare two branches
        branch1 = args[1]
        branch2 = args[2]
        return _compare_branches(repo, snapshot_mgr, branch1, branch2)

    else:
        # Preview specific branch
        branch_name = args[0]
        branches = repo.refs.list_branches()

        if branch_name not in branches:
            raise BranchNotFoundError(branch_name)

        branch_hash = repo.refs.get_branch_hash(branch_name)
        if not branch_hash:
            print_color(f"Cabang '{branch_name}' belum memiliki commit.", "yellow")
            return 0

        try:
            data = snapshot_mgr.load_snapshot(branch_hash)
            tree = snapshot_mgr.get_tree(branch_hash)
            files = tree.get_blob_entries()

            print_color(f"Preview cabang: {branch_name}\n", "cyan")
            print(f"  HEAD: {short_hash(branch_hash)}")
            print(f"  Pesan: {data.get('message', '')}")
            print(f"  Waktu: {data.get('timestamp', '')[:19]}")
            print(f"  File: {len(files)} file")

            print(f"\n  File di cabang ini:")
            for entry in files:
                print(f"    {entry.path}")

            # Show difference with current branch
            current_hash = repo.get_head_commit()
            if current_hash and current_hash != branch_hash:
                print(f"\n  Perbedaan dengan cabang saat ini:")
                current_tree = snapshot_mgr.get_tree(current_hash)
                current_files = {e.path for e in current_tree.get_blob_entries()}
                branch_files = {e.path for e in files}

                new_in_branch = branch_files - current_files
                deleted_in_branch = current_files - branch_files

                if new_in_branch:
                    print(f"    File baru di '{branch_name}':")
                    for f in new_in_branch:
                        print(f"      + {f}")
                if deleted_in_branch:
                    print(f"    File hilang di '{branch_name}':")
                    for f in deleted_in_branch:
                        print(f"      - {f}")
                if not new_in_branch and not deleted_in_branch:
                    print(f"    Tidak ada perbedaan file")

        except Exception as e:
            print_color(f"Gagal membaca cabang: {e}", "red")

    return 0


def _compare_branches(
    repo: Repository,
    snapshot_mgr: SnapshotManager,
    branch1: str,
    branch2: str,
) -> int:
    """Compare two branches."""
    branches = repo.refs.list_branches()

    if branch1 not in branches:
        raise BranchNotFoundError(branch1)
    if branch2 not in branches:
        raise BranchNotFoundError(branch2)

    hash1 = repo.refs.get_branch_hash(branch1)
    hash2 = repo.refs.get_branch_hash(branch2)

    if not hash1:
        print_color(f"Cabang '{branch1}' belum memiliki commit.", "yellow")
        return 0
    if not hash2:
        print_color(f"Cabang '{branch2}' belum memiliki commit.", "yellow")
        return 0

    try:
        tree1 = snapshot_mgr.get_tree(hash1)
        tree2 = snapshot_mgr.get_tree(hash2)

        files1 = {e.path for e in tree1.get_blob_entries()}
        files2 = {e.path for e in tree2.get_blob_entries()}

        print_color(f"Perbandingan: {branch1} vs {branch2}\n", "cyan")

        only1 = files1 - files2
        only2 = files2 - files1
        common = files1 & files2

        if only1:
            print(f"  Hanya di '{branch1}':")
            for f in sorted(only1):
                print(f"    + {f}")

        if only2:
            print(f"  Hanya di '{branch2}':")
            for f in sorted(only2):
                print(f"    + {f}")

        if common:
            print(f"  File sama: {len(common)} file")

        if not only1 and not only2:
            print(f"  Kedua cabang memiliki file yang sama")

    except Exception as e:
        print_color(f"Gagal membandingkan: {e}", "red")

    return 0
