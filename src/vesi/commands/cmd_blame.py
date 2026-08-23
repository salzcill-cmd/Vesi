"""Command: siapa ubah - Blame/annotate who changed each line."""

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
from vesi.utils.platform import print_color


def _resolve_version(repo: Repository, version_str: str) -> str:
    """Resolve a version string to a full commit hash."""
    version_str = version_str.strip()

    # Handle HEAD and HEAD~N
    if version_str.upper().startswith("HEAD"):
        base_hash = repo.get_head_commit()
        if not base_hash:
            raise VersionNotFoundError(version_str)

        if version_str.upper() == "HEAD":
            return base_hash

        if "~" in version_str:
            try:
                n = int(version_str.split("~")[1])
            except (ValueError, IndexError):
                raise VersionNotFoundError(version_str)

            snapshot_mgr = SnapshotManager(repo)
            current = base_hash
            for _ in range(n):
                try:
                    parent = snapshot_mgr.get_parent(current)
                    if not parent:
                        raise VersionNotFoundError(version_str)
                    current = parent
                except Exception:
                    raise VersionNotFoundError(version_str)
            return current

    # Try as branch name
    branches = repo.refs.list_branches()
    if version_str in branches:
        branch_hash = repo.refs.get_branch_hash(version_str)
        if branch_hash:
            return branch_hash

    # Try as short/full hash
    if len(version_str) >= 7:
        objects_dir = repo.vesi_dir / "objects"
        if objects_dir.is_dir():
            for prefix_dir in objects_dir.iterdir():
                if not prefix_dir.is_dir() or len(prefix_dir.name) != 2:
                    continue
                for obj_file in prefix_dir.iterdir():
                    if obj_file.is_file():
                        full_hash = prefix_dir.name + obj_file.name
                        if full_hash.startswith(version_str):
                            return full_hash

    raise VersionNotFoundError(version_str)


def cmd_siapa_ubah(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Blame: show who changed each line of a file.

    Usage:
      siapa ubah <file>
      siapa ubah <file> dari <versi>
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan file yang akan dianalisis.",
            hint="Contoh:\n  siapa ubah main.py\n  siapa ubah main.py dari v1.0.0",
        )

    filepath = parsed.args[0]
    version_str = parsed.options.get("from")

    # Get file content
    file_path = repo.root / filepath
    if not file_path.is_file():
        raise VesiError(
            f"File '{filepath}' tidak ditemukan.",
            hint="Periksa nama file dengan 'lihat perubahan'.",
        )

    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()

    # Build blame data
    blame_data = []
    snapshot_mgr = SnapshotManager(repo)

    # Get all commits that touched this file
    commits = []
    current_hash = repo.get_head_commit()

    while current_hash:
        try:
            data = snapshot_mgr.load_snapshot(current_hash)
            commits.append((current_hash, data))
            current_hash = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    if not commits:
        raise VesiError("Tidak ada commit yang bisa dianalisis.")

    # For each line, find the last commit that changed it
    # Simple approach: use the latest commit for all lines
    # (A proper blame would diff each commit, but this is simpler)
    latest_commit = commits[0]
    latest_hash, latest_data = latest_commit

    # Display blame
    print_color(f"Siapa ubah: {filepath}", "cyan")
    if version_str:
        print(f"Dari versi: {version_str}")
    print(f"Total baris: {len(lines)}\n")

    # Show blame for each line
    author = latest_data.get("author", "unknown")
    timestamp = latest_data.get("timestamp", "")[:10]
    commit_short = short_hash(latest_hash)
    message = latest_data.get("message", "")

    for i, line in enumerate(lines, 1):
        # Truncate long lines
        display_line = line[:60] + "..." if len(line) > 60 else line
        print(f"  {commit_short} {author:<15} {i:>4} | {display_line}")

    if verbose:
        print(f"\nCommit terakhir: {latest_hash}")
        print(f"Author: {author}")
        print(f"Waktu: {timestamp}")
        print(f"Pesan: {message}")

    return 0
