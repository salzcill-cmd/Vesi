"""Commands: buat/lihat/pindah/hapus cabang - Branch management."""

from __future__ import annotations

from vesi.core.branch import (
    create_branch,
    list_branches,
    switch_branch,
    delete_branch,
    format_branches,
)
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import confirm, print_color


def cmd_buat_cabang(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Create a new branch."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan nama cabang baru.",
            hint="Contoh:\n    buat cabang <nama>",
        )

    name = parsed.args[0]
    commit_hash = create_branch(repo, name)

    from vesi.hashing import short_hash
    hash_display = short_hash(commit_hash) if commit_hash else "(root)"
    print_color(f"✓ Cabang '{name}' dibuat dari versi {hash_display}", "green")

    return 0


def cmd_lihat_cabang(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """List all branches."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    branches = list_branches(repo)
    print(format_branches(branches))

    return 0


def cmd_pindah_cabang(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Switch to another branch."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan nama cabang yang ingin dituju.",
            hint="Contoh:\n    pindah cabang <nama>",
        )

    name = parsed.args[0]

    # Check for uncommitted changes
    from vesi.core.change import detect_changes
    from vesi.core.snapshot import SnapshotManager
    index = repo.index.load()
    snapshot_mgr = SnapshotManager(repo)

    tree = None
    head_hash = repo.get_head_commit()
    if head_hash:
        try:
            tree = snapshot_mgr.get_tree(head_hash)
        except Exception:
            pass

    changes = detect_changes(repo.root, tree, index)
    if changes or index:
        print("⚠ Ada perubahan yang belum disimpan.")
        print("  Stel dan simpan perubahan terlebih dahulu, atau batalkan perubahan.")
        if not confirm("Tetap pindah cabang?", default=False):
            print("Dibatalkan.")
            return 0

    commit_hash = switch_branch(repo, name)

    from vesi.hashing import short_hash
    hash_display = short_hash(commit_hash) if commit_hash else "(root)"
    print_color(f"✓ Berpindah ke cabang '{name}'", "green")

    return 0


def cmd_hapus_cabang(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Delete a branch."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan nama cabang yang akan dihapus.",
            hint="Contoh:\n    hapus cabang <nama>",
        )

    name = parsed.args[0]

    # Check if branch is merged
    from vesi.core.snapshot import SnapshotManager
    snapshot_mgr = SnapshotManager(repo)
    branch_hash = repo.refs.get_branch_hash(name)
    active_branch = repo.refs.get_active_branch()

    if active_branch and branch_hash:
        active_hash = repo.refs.get_branch_hash(active_branch) or ""
        # Check if branch is an ancestor of active branch
        from vesi.merge.engine import _is_ancestor
        if not _is_ancestor(snapshot_mgr, branch_hash, active_hash):
            print(f"⚠ Cabang '{name}' belum digabungkan ke cabang aktif.")
            if not confirm("Hapus tetap?", default=False):
                print("Dibatalkan.")
                return 0

    # Check for --force flag
    force = "--force" in (parsed.flags or [])
    if not force:
        from vesi.merge.engine import _is_ancestor
        if branch_hash and active_hash:
            if not _is_ancestor(snapshot_mgr, branch_hash, active_hash):
                if not confirm(f"Cabang '{name}' belum digabungkan. Hapus tetap?", default=False):
                    print("Dibatalkan.")
                    return 0

    delete_branch(repo, name)
    print_color(f"✓ Cabang '{name}' dihapus.", "green")

    return 0
