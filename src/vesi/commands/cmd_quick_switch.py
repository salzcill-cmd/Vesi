"""Command: pindah cepat - Quick branch switch with auto-save."""

from __future__ import annotations

from vesi.errors.exceptions import (
    BranchNotFoundError,
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_pindah_cepat(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Quick branch switch with auto-save.

    Usage:
      pindah cepat <branch>         - Switch with auto-save
      pindah cepat <branch> --tanpa-simpan - Switch without saving
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    flags = parsed.flags

    if not args:
        # List branches with quick switch info
        from vesi.commands.cmd_branch import list_branches, format_branches
        branches = list_branches(repo)
        print(format_branches(branches))
        print(f"\nGunakan: pindah cepat <nama-cabang>")
        return 0

    branch_name = args[0]
    auto_save = "--tanpa-simpan" not in flags

    # Check if branch exists
    branches = repo.refs.list_branches()
    if branch_name not in branches:
        raise BranchNotFoundError(branch_name)

    # Check for uncommitted changes
    from vesi.core.change import detect_changes
    from vesi.core.snapshot import SnapshotManager

    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()
    tree = None
    if current_hash:
        try:
            tree = snapshot_mgr.get_tree(current_hash)
        except Exception:
            pass

    index = repo.index.load()
    changes = detect_changes(repo.root, tree, index or {})

    # Auto-save if there are changes
    if changes and auto_save:
        print_color("Menyimpan perubahan terlebih dahulu...", "cyan")

        # Stage all changes
        for change in changes:
            if change.new_hash:
                repo.index.stage_file(change.path, change.new_hash)

        # Create auto-save commit
        from vesi.storage.tree import Tree
        new_tree = Tree()
        staged = repo.index.load()
        for filepath, file_hash in (staged or {}).items():
            name = filepath.split("/")[-1]
            new_tree.add_blob(name, file_hash, filepath)

        import time
        timestamp = time.strftime("%H:%M", time.localtime())
        message = f"auto-save sebelum pindah ke {branch_name}"

        author = repo.get_author()
        snapshot_hash = snapshot_mgr.create_snapshot(
            tree=new_tree,
            message=message,
            author=author,
            parent=current_hash,
        )

        # Update branch
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, snapshot_hash)

        # Add reflog
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(snapshot_hash, "auto-save", message, active_branch or "")

        # Clear staging
        repo.index.clear()

        print_color(f"Perubahan tersimpan: {short_hash(snapshot_hash)}", "green")

    elif changes and not auto_save:
        print_color("Ada perubahan yang belum disimpan.", "yellow")
        print("  Gunakan 'vesi stel . && vesi simpan' untuk menyimpan")
        print("  Atau tambahkan --tanpa-simpan untuk paksa pindah")

        # Check if user wants to force
        if "--paksa" not in flags:
            return 1

    # Switch branch
    repo.refs.set_head(branch_name)
    new_hash = repo.refs.get_branch_hash(branch_name)

    # Add reflog
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(new_hash or "", "checkout", f"Pindah ke {branch_name}", branch_name)

    print_color(f"Berpindah ke cabang '{branch_name}'", "green")
    if new_hash:
        print(f"  HEAD: {short_hash(new_hash)}")

    return 0
