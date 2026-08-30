"""Command: susun ulang - Rebase/squash commits with interactive support."""

from __future__ import annotations

import json
import time

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
      susun ulang [jumlah]              - Squash last N commits
      susun ulang interaktif [jumlah]   - Interactive rebase
      susun ulang --rapikan             - Auto-clean commit messages
      susun ulang --perbaiki <hash>     - Fixup a specific commit
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []

    # Check for interactive mode
    if args and args[0].lower() in ("interaktif", "interactive", "-i"):
        count = 2
        if len(args) > 1:
            try:
                count = int(args[1])
            except ValueError:
                pass
        return _interactive_rebase(repo, count, verbose)

    # Check for fixup mode
    if "--perbaiki" in parsed.flags:
        idx = parsed.flags.index("--perbaiki")
        if idx < len(args):
            return _fixup_commit(repo, args[idx], verbose)
        raise VesiError("Tentukan hash commit yang akan di-fixup.")

    # Parse count (default: 2)
    count = 2
    if args:
        try:
            count = int(args[0])
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

    # Combine messages (clean format)
    messages = []
    for _, data in reversed(commits):
        msg = data.get("message", "")
        if msg:
            # Remove conventional commit prefixes for cleaner squash
            clean_msg = msg
            for prefix in ("feat:", "fix:", "docs:", "style:", "refactor:", "test:", "chore:"):
                if clean_msg.lower().startswith(prefix):
                    clean_msg = clean_msg[len(prefix):].strip()
            messages.append(clean_msg)

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

    # Add reflog entry
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(new_hash, "rebase-squash", combined_message, active_branch or "")

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


def _interactive_rebase(repo: Repository, count: int, verbose: bool) -> int:
    """Interactive rebase: show commits and let user mark actions."""
    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        raise VesiError("Belum ada commit yang bisa di-rebase.")

    # Collect commits
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
        raise VesiError(f"Hanya ada {len(commits)} commit. Butuh minimal 2.")

    # Display commits for user to decide
    print_color("Interaktif Rebase - Commit yang akan di-rebase:\n", "cyan")
    print("  Aksi yang tersedia:")
    print("    p = pick (gunakan commit)")
    print("    r = reword (ubah pesan)")
    print("    e = edit (tahan untuk diubah)")
    print("    d = drop (hapus commit)")
    print("    f = fixup (gabungkan ke commit sebelumnya)")
    print()

    for i, (h, data) in enumerate(commits):
        marker = "pick" if i == 0 else "pick"
        msg = data.get("message", "")[:50]
        print(f"  {marker:<8} {short_hash(h)}  {msg}")

    print(f"\n  {len(commits)} commit akan di-rebase.")

    # Save rebase state for potential continuation
    rebase_state = {
        "commits": [(h, d.get("message", "")) for h, d in commits],
        "actions": ["pick"] * len(commits),
        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    state_file = repo.vesi_dir / "rebase_state.json"
    state_file.write_text(
        json.dumps(rebase_state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print_color("\n💡 Untuk mengubah aksi, edit file .vesi/rebase_state.json", "dim")
    print_color("   lalu jalankan: susun ulang --terapkan", "dim")

    return 0


def _fixup_commit(repo: Repository, target_hash_str: str, verbose: bool) -> int:
    """Fixup: squash current commit into a specific earlier commit."""
    from vesi.commands.cmd_blame import _resolve_version

    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        raise VesiError("Belum ada commit.")

    # Resolve target
    try:
        target_hash = _resolve_version(repo, target_hash_str)
    except Exception:
        raise VesiError(f"Commit '{target_hash_str}' tidak ditemukan.")

    if target_hash == current_hash:
        raise VesiError("Tidak bisa fixup commit ke dirinya sendiri.")

    # Collect commits between current and target
    commits_after_target = []
    current = current_hash
    while current and current != target_hash:
        try:
            data = snapshot_mgr.load_snapshot(current)
            commits_after_target.append((current, data))
            current = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    if not commits_after_target:
        raise VesiError(f"Commit '{target_hash_str}' bukan ancestor dari HEAD.")

    # Load target commit
    try:
        target_data = snapshot_mgr.load_snapshot(target_hash)
        target_tree = snapshot_mgr.get_tree(target_hash)
    except Exception:
        raise VesiError("Gagal memuat commit target.")

    # The most recent commit's tree becomes the combined tree
    most_recent_hash, most_recent_data = commits_after_target[0]
    combined_tree = snapshot_mgr.get_tree(most_recent_hash)

    # Build new message: target message + current message
    target_msg = target_data.get("message", "")
    current_msg = most_recent_data.get("message", "")
    combined_msg = f"{target_msg} (fixup: {current_msg})"

    # Get parent of target
    parent_of_target = target_data.get("parent")

    # Create new commit
    author = repo.get_author()
    new_hash = snapshot_mgr.create_snapshot(
        tree=combined_tree,
        message=combined_msg,
        author=author,
        parent=parent_of_target,
    )

    # Re-apply commits after target (skip the one we're fixing up)
    new_parent = new_hash
    for commit_hash, data in reversed(commits_after_target[1:]):
        tree = snapshot_mgr.get_tree(commit_hash)
        new_parent = snapshot_mgr.create_snapshot(
            tree=tree,
            message=data.get("message", ""),
            author=data.get("author", ""),
            parent=new_parent,
        )

    # Update branch
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, new_parent)

    # Reflog
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(new_parent, "fixup", combined_msg, active_branch or "")

    print_color("✓ Fixup berhasil!", "green")
    print(f"  Target: {short_hash(target_hash)} ({target_msg})")
    print(f"  Difixup: {short_hash(most_recent_hash)} ({current_msg})")
    print(f"  Hasil: {short_hash(new_parent)}")

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
    from vesi.commands.cmd_blame import _resolve_version
    try:
        base_hash = _resolve_version(repo, base_str)
    except Exception:
        raise VersionNotFoundError(base_str)

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

    # Reflog
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(new_parent, "rebase", f"Rebase onto {short_hash(base_hash)}", active_branch or "")

    print_color("✓ Rebase selesai!", "green")
    print(f"  Commit baru: {short_hash(new_parent)}")

    return 0
