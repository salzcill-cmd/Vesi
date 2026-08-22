"""Command: lihat perubahan - Show working directory status."""

from __future__ import annotations

from vesi.core.change import detect_changes, format_changes
from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import RepositoryNotFoundError
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_lihat_perubahan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show status of working directory."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    index = repo.index.load()

    # Get tree from last commit
    tree = None
    head_hash = repo.get_head_commit()
    if head_hash:
        try:
            tree = snapshot_mgr.get_tree(head_hash)
        except Exception:
            pass

    # Detect changes
    changes = detect_changes(repo.root, tree, index)

    # Get staged files
    staged_files = list(index.keys())

    print("Perubahan di direktori saat ini:\n")

    if not changes and not staged_files:
        print("✓ Tidak ada perubahan. Semua file sudah disimpan.")
        return 0

    # Show unstaged changes
    if changes:
        print(format_changes(changes))

    # Show staged files
    if staged_files:
        if changes:
            print()
        print("File yang disiapkan (staged):")
        for f in sorted(staged_files):
            print(f"  S {f}")

    if verbose:
        head = repo.refs.get_head()
        active_branch = repo.refs.get_active_branch()
        print(f"\nHEAD: {head}")
        print(f"Cabang aktif: {active_branch or '(detached)'}")
        print(f"File staged: {len(staged_files)}")

    return 0
