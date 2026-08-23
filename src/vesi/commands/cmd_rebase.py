"""Command: susun ulang - Rebase/squash commits."""

from __future__ import annotations

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


def cmd_susun_ulang(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Rebase/squash commits.

    Usage:
      susun ulang [jumlah]
      susun ulang 3          # Squash last 3 commits
      susun ulang            # Squash last 2 commits
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Parse count (default: 2)
    count = 2
    if parsed.args:
        try:
            count = int(parsed.args[0])
            if count < 2:
                raise VesiError(
                    "Jumlah commit minimal 2 untuk disatukan.",
                    hint="Contoh:\n  susun ulang 3",
                )
        except ValueError:
            raise VesiError(
                "Jumlah harus berupa angka.",
                hint="Contoh:\n  susun ulang 3",
            )

    # Get HEAD
    current_hash = repo.get_head_commit()
    if not current_hash:
        raise VesiError("Belum ada versi yang bisa disatukan.")

    snapshot_mgr = SnapshotManager(repo)

    # Walk back through commits
    commits = []
    current = current_hash
    for _ in range(count):
        if not current:
            break
        try:
            data = snapshot_mgr.load_snapshot(current)
            commits.append((current, data))
            current = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    if len(commits) < 2:
        raise VesiError(
            f"Hanya ada {len(commits)} commit yang bisa disatukan.",
            hint="Butuh minimal 2 commit.",
        )

    # Get the oldest commit's parent
    oldest_commit = commits[-1]
    parent_of_oldest = oldest_commit[1].get("parent")

    # Build combined tree from most recent commit
    most_recent_hash, most_recent_data = commits[0]
    combined_tree = snapshot_mgr.get_tree(most_recent_hash)

    # Combine messages
    messages = []
    for _, data in reversed(commits):
        msg = data.get("message", "")
        if msg:
            messages.append(msg)

    combined_message = " + ".join(messages) if messages else "Gabungan commit"

    # Get total file count
    file_count = len(combined_tree.get_blob_entries())

    # Create new squashed commit
    author = repo.get_author()
    new_hash = snapshot_mgr.create_snapshot(
        tree=combined_tree,
        message=combined_message,
        author=author,
        parent=parent_of_oldest,
    )

    # Update branch reference
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, new_hash)

    # Display result
    print_color("✓ Commit berhasil disatukan!", "green")
    print(f"  Commit sebelumnya: {len(commits)}")
    for h, data in reversed(commits):
        print(f"    {short_hash(h)}  {data.get('message', '')}")
    print(f"\n  Commit baru: {short_hash(new_hash)}")
    print(f"  Pesan: {combined_message}")
    print(f"  File: {file_count} file")

    if verbose:
        print(f"\n  Parent: {short_hash(parent_of_oldest) if parent_of_oldest else '(root)'}")

    return 0


def cmd_susun_ulang_ke(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Rebase onto a specific base commit.

    Usage:
      susun ulang ke <base>
      susun ulang ke f4e5d6a
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan base commit.",
            hint="Contoh:\n  susun ulang ke f4e5d6a",
        )

    base_str = parsed.args[0]

    # Resolve base commit
    from vesi.commands.cmd_cherrypick import _resolve_version
    try:
        base_hash = _resolve_version(repo, base_str)
    except VersionNotFoundError:
        raise

    # Get HEAD
    current_hash = repo.get_head_commit()
    if not current_hash:
        raise VesiError("Belum ada commit.")

    # Check if already at base
    if current_hash == base_hash:
        print_color("✓ Sudah berada di base commit.", "yellow")
        return 0

    # Count commits to rebase
    snapshot_mgr = SnapshotManager(repo)
    commits_to_rebase = []
    current = current_hash
    while current and current != base_hash:
        try:
            data = snapshot_mgr.load_snapshot(current)
            commits_to_rebase.append((current, data))
            current = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    if not commits_to_rebase:
        raise VesiError(
            f"Commit '{base_str}' bukan ancestor dari HEAD.",
            hint="Gunakan 'lihat riwayat' untuk melihat riwayat.",
        )

    print_color(f"✓ Menyusun ulang {len(commits_to_rebase)} commit di atas {short_hash(base_hash)}", "cyan")

    # Re-apply commits on top of base
    new_parent = base_hash
    for commit_hash, data in reversed(commits_to_rebase):
        tree = snapshot_mgr.get_tree(commit_hash)
        new_hash = snapshot_mgr.create_snapshot(
            tree=tree,
            message=data.get("message", ""),
            author=data.get("author", ""),
            parent=new_parent,
        )
        new_parent = new_hash

    # Update branch reference
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, new_parent)

    print_color("✓ Rebase selesai!", "green")
    print(f"  Commit baru: {short_hash(new_parent)}")

    return 0
