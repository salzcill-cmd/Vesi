"""Command: kembali ke waktu - Time travel to view past states."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_kembali_ke_waktu(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Time travel - view and restore past states.

    Usage:
      kembali ke waktu                - Show timeline
      kembali ke waktu lihat <hash>   - View files at that commit
      kembali ke waktu <hash>         - Restore to that commit
      kembali ke waktu --jam 2        - Go back 2 hours
      kembali ke waktu --hari 1       - Go back 1 day
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        raise VesiError("Belum ada commit.")

    args = parsed.args or []
    flags = parsed.flags

    # Parse subcommand
    sub = args[0] if args else ""

    if sub == "lihat" and len(args) > 1:
        # View files at a specific commit
        target_hash = _resolve_hash(repo, args[1])
        tree = snapshot_mgr.get_tree(target_hash)
        entries = tree.get_blob_entries()

        print_color(f"File di commit {short_hash(target_hash)}:\n", "cyan")
        for entry in entries:
            print(f"  {entry.path}")

        return 0

    elif "--jam" in flags:
        # Go back by hours
        idx = flags.index("--jam")
        hours = int(args[idx]) if idx < len(args) else 1

        # Find commit from N hours ago
        target = _find_commit_by_time(repo, hours * 3600)
        if target:
            return _restore_to(repo, snapshot_mgr, current_hash, target)
        else:
            raise VesiError(f"Tidak ditemukan commit dari {hours} jam yang lalu.")

    elif "--hari" in flags:
        # Go back by days
        idx = flags.index("--hari")
        days = int(args[idx]) if idx < len(args) else 1

        target = _find_commit_by_time(repo, days * 86400)
        if target:
            return _restore_to(repo, snapshot_mgr, current_hash, target)
        else:
            raise VesiError(f"Tidak ditemukan commit dari {days} hari yang lalu.")

    elif args and args[0] != "lihat":
        # Restore to specific commit
        target_hash = _resolve_hash(repo, args[0])
        return _restore_to(repo, snapshot_mgr, current_hash, target_hash)

    else:
        # Show timeline
        print_color("Timeline:\n", "cyan")
        current = current_hash
        count = 0

        while current and count < 20:
            try:
                data = snapshot_mgr.load_snapshot(current)
                timestamp = data.get("timestamp", "")[:19]
                message = data.get("message", "")
                author = data.get("author", "")

                print(f"  {short_hash(current)}  {timestamp}  {author:<10} {message}")
                current = data.get("parent")
                count += 1
            except (FileNotFoundError, ValueError):
                break

        if current:
            print(f"  ... dan commit lainnya")

        print(f"\nGunakan:")
        print(f"  kembali ke waktu <hash>       Kembali ke commit")
        print(f"  kembali ke waktu lihat <hash> Lihat file di commit")
        print(f"  kembali ke waktu --jam 2      Kembali 2 jam lalu")
        print(f"  kembali ke waktu --hari 1     Kembali 1 hari lalu")

    return 0


def _restore_to(
    repo: Repository,
    snapshot_mgr: SnapshotManager,
    current_hash: str,
    target_hash: str,
) -> int:
    """Restore repository to a specific commit."""
    # Get target data
    try:
        target_data = snapshot_mgr.load_snapshot(target_hash)
    except (FileNotFoundError, ValueError):
        raise VesiError(f"Commit '{short_hash(target_hash)}' tidak ditemukan.")

    # Get target tree
    target_tree = snapshot_mgr.get_tree(target_hash)

    # Restore files
    restored = []
    for entry in target_tree.get_blob_entries():
        blob_content = repo.objects.load_blob(entry.hash_id)
        file_path = repo.root / entry.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(blob_content)
        restored.append(entry.path)

    # Stage all files
    index = {}
    for entry in target_tree.get_blob_entries():
        index[entry.path] = entry.hash_id
    repo.index.save(index)

    # Update branch
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, target_hash)

    # Add reflog
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(target_hash, "time-travel", "Kembali ke waktu", active_branch or "")

    message = target_data.get("message", "")
    print_color("Kembali ke waktu berhasil!", "green")
    print(f"  Ke: {short_hash(target_hash)}")
    print(f"  Pesan: {message}")
    print(f"  File: {len(restored)} file dikembalikan")

    return 0


def _find_commit_by_time(repo: Repository, seconds_ago: int) -> str | None:
    """Find a commit from approximately N seconds ago."""
    import time
    snapshot_mgr = SnapshotManager(repo)
    current = repo.get_head_commit()
    target_time = time.time() - seconds_ago

    while current:
        try:
            data = snapshot_mgr.load_snapshot(current)
            timestamp_str = data.get("timestamp", "")
            # Parse timestamp
            from datetime import datetime
            try:
                commit_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp()
                if commit_time <= target_time:
                    return current
            except (ValueError, AttributeError):
                pass
            current = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    return None


def _resolve_hash(repo: Repository, version_str: str) -> str:
    """Resolve a version string to a full commit hash."""
    from vesi.commands.cmd_cherrypick import _resolve_version
    try:
        return _resolve_version(repo, version_str)
    except Exception:
        raise VesiError(f"Commit '{version_str}' tidak ditemukan.")
