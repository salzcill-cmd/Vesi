"""Command: tampilkan versi - Show detailed commit information."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.diff.engine import diff_files
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

    branches = repo.refs.list_branches()
    if version_str in branches:
        branch_hash = repo.refs.get_branch_hash(version_str)
        if branch_hash:
            return branch_hash

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


def cmd_tampilkan_versi(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show detailed information about a commit.

    Usage:
      tampilkan versi                 - Show latest commit
      tampilkan versi <hash>         - Show specific commit
      tampilkan versi <hash> --stat  - Show only stats
      tampilkan versi <hash> --patch - Show full patch
      tampilkan versi <hash> --file  - Show only file list
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)

    # Determine which commit to show
    args = parsed.args or []
    if args:
        commit_hash = _resolve_version(repo, args[0])
    else:
        commit_hash = repo.get_head_commit()
        if not commit_hash:
            raise VesiError("Belum ada commit.")

    # Load commit data
    try:
        data = snapshot_mgr.load_snapshot(commit_hash)
    except (FileNotFoundError, ValueError):
        raise VersionNotFoundError(args[0] if args else "HEAD")

    # Get commit info
    message = data.get("message", "")
    author = data.get("author", "unknown")
    timestamp = data.get("timestamp", "")
    parent_hash = data.get("parent")
    second_parent = data.get("second_parent")
    tree_hash = data.get("tree", "")

    # Determine display modes
    show_stat = "--stat" in parsed.flags
    show_patch = "--patch" in parsed.flags
    show_file = "--file" in parsed.flags
    show_stat_only = "--stat-only" in parsed.flags

    # Default: show stat + brief patch
    if not show_stat and not show_patch and not show_file and not show_stat_only:
        show_stat = True

    # Print header
    print_color(f"commit {short_hash(commit_hash)}", "cyan")
    print(f"Author: {author}")
    print(f"Date:   {timestamp[:19] if timestamp else 'unknown'}")

    if second_parent:
        print(f"Merge:  {short_hash(commit_hash)}^ ({short_hash(parent_hash or '')}) + {short_hash(second_parent)}")

    # Get tree
    try:
        tree = snapshot_mgr.get_tree(commit_hash)
    except Exception:
        print_color("\n  Gagal memuat tree.", "red")
        return 1

    # Get parent tree for diff
    parent_tree = None
    if parent_hash:
        try:
            parent_tree = snapshot_mgr.get_tree(parent_hash)
        except Exception:
            pass

    # Build file maps
    current_files = {e.path: e.hash_id for e in tree.get_blob_entries()}
    parent_files = {}
    if parent_tree:
        parent_files = {e.path: e.hash_id for e in parent_tree.get_blob_entries()}

    # Calculate stats
    added_files = []
    modified_files = []
    deleted_files = []
    total_additions = 0
    total_deletions = 0

    all_files = set(list(current_files.keys()) + list(parent_files.keys()))
    for filepath in sorted(all_files):
        old_hash = parent_files.get(filepath)
        new_hash = current_files.get(filepath)

        if old_hash is None:
            added_files.append(filepath)
            # Count additions
            content = repo.blobs.load_content(new_hash)
            try:
                lines = content.decode("utf-8").splitlines()
                total_additions += len(lines)
            except (UnicodeDecodeError, AttributeError):
                pass
        elif new_hash is None:
            deleted_files.append(filepath)
            # Count deletions
            content = repo.blobs.load_content(old_hash)
            try:
                lines = content.decode("utf-8").splitlines()
                total_deletions += len(lines)
            except (UnicodeDecodeError, AttributeError):
                pass
        elif old_hash != new_hash:
            modified_files.append(filepath)
            # Count changes
            old_content = repo.blobs.load_content(old_hash)
            new_content = repo.blobs.load_content(new_hash)
            try:
                old_lines = old_content.decode("utf-8").splitlines()
                new_lines = new_content.decode("utf-8").splitlines()
                total_additions += max(0, len(new_lines) - len(old_lines))
                total_deletions += max(0, len(old_lines) - len(new_lines))
            except (UnicodeDecodeError, AttributeError):
                pass

    # Print message
    print(f"\n    {message}")

    # Print stat
    if show_stat or show_stat_only:
        total_files = len(added_files) + len(modified_files) + len(deleted_files)
        print(f"\n{total_files} file{'s' if total_files != 1 else ''} changed", end="")
        if total_additions > 0:
            print(f", {total_additions} insertion{'s' if total_additions != 1 else ''}(+)", end="")
        if total_deletions > 0:
            print(f", {total_deletions} deletion{'s' if total_deletions != 1 else ''}(-)", end="")
        print()

        # Print per-file stats
        max_path_len = max(
            (len(f) for f in all_files if f in current_files or f in parent_files),
            default=20,
        )
        max_path_len = min(max_path_len, 40)

        for filepath in added_files:
            content = repo.blobs.load_content(current_files[filepath])
            try:
                count = len(content.decode("utf-8").splitlines())
            except (UnicodeDecodeError, AttributeError):
                count = 0
            bar = "+" * min(count, 10)
            print(f"  {filepath:<{max_path_len}} | {count:>4} {'+' * min(count, 20)}")

        for filepath in modified_files:
            old_content = repo.blobs.load_content(parent_files[filepath])
            new_content = repo.blobs.load_content(current_files[filepath])
            try:
                old_count = len(old_content.decode("utf-8").splitlines())
                new_count = len(new_content.decode("utf-8").splitlines())
                diff_count = abs(new_count - old_count)
            except (UnicodeDecodeError, AttributeError):
                diff_count = 0
            plus = "+" * min(new_count, 10)
            minus = "-" * min(old_count, 10)
            print(f"  {filepath:<{max_path_len}} | {diff_count:>4} {plus}{minus}")

        for filepath in deleted_files:
            content = repo.blobs.load_content(parent_files[filepath])
            try:
                count = len(content.decode("utf-8").splitlines())
            except (UnicodeDecodeError, AttributeError):
                count = 0
            print(f"  {filepath:<{max_path_len}} | {count:>4} {'-' * min(count, 20)}")

    # Print file list
    if show_file:
        print(f"\nFile dalam commit:")
        for filepath in sorted(added_files):
            print(f"  + {filepath}")
        for filepath in sorted(modified_files):
            print(f"  ~ {filepath}")
        for filepath in sorted(deleted_files):
            print(f"  - {filepath}")

    # Print patch
    if show_patch or (not show_stat_only and not show_file):
        if show_patch:
            print(f"\n{'─' * 60}")

        for filepath in sorted(added_files):
            content = repo.blobs.load_content(current_files[filepath])
            print(f"\n{filepath} [file baru]")
            try:
                lines = content.decode("utf-8").splitlines()
                for line in lines:
                    print(f"+{line}")
            except (UnicodeDecodeError, AttributeError):
                print("[binary file]")

        for filepath in sorted(modified_files):
            old_content = repo.blobs.load_content(parent_files[filepath])
            new_content = repo.blobs.load_content(current_files[filepath])
            diff = diff_files(old_content, new_content, f"a/{filepath}", f"b/{filepath}")
            if diff:
                print(f"\n{diff}")

        for filepath in sorted(deleted_files):
            content = repo.blobs.load_content(parent_files[filepath])
            print(f"\n{filepath} [file dihapus]")
            try:
                lines = content.decode("utf-8").splitlines()
                for line in lines:
                    print(f"-{line}")
            except (UnicodeDecodeError, AttributeError):
                print("[binary file]")

    return 0
