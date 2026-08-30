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


def _get_file_content_at_commit(
    repo: Repository,
    snapshot_mgr: SnapshotManager,
    commit_hash: str,
    filepath: str,
) -> str | None:
    """Get file content at a specific commit."""
    try:
        tree = snapshot_mgr.get_tree(commit_hash)
        entry = tree.get_entry(filepath)
        if entry is None:
            return None
        content = repo.blobs.load_content(entry.hash_id)
        return content.decode("utf-8", errors="replace")
    except (FileNotFoundError, ValueError):
        return None


def _build_blame_history(
    repo: Repository,
    snapshot_mgr: SnapshotManager,
    filepath: str,
) -> list[dict]:
    """Build per-line blame by walking commit history and diffing.

    Returns a list of blame entries, one per line, with commit info.
    """
    # Collect all commits that touched this file
    commits = []
    current_hash = repo.get_head_commit()
    visited = set()

    while current_hash and current_hash not in visited:
        visited.add(current_hash)
        try:
            data = snapshot_mgr.load_snapshot(current_hash)
            # Check if this commit has the file
            tree = snapshot_mgr.get_tree(current_hash)
            entry = tree.get_entry(filepath)
            if entry is not None:
                commits.append((current_hash, data))
            current_hash = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    if not commits:
        return []

    # Get current file content
    current_content = _get_file_content_at_commit(
        repo, snapshot_mgr, commits[0][0], filepath
    )
    if current_content is None:
        return []

    current_lines = current_content.splitlines()

    # For each line, walk back through commits to find who last changed it
    # Start with all lines attributed to the latest commit
    blame = []
    for line in current_lines:
        blame.append({
            "line": line,
            "commit_hash": commits[0][0],
            "author": commits[0][1].get("author", "unknown"),
            "timestamp": commits[0][1].get("timestamp", "")[:10],
            "message": commits[0][1].get("message", ""),
        })

    # Walk back through commits, updating blame for changed lines
    for i in range(len(commits) - 1):
        newer_hash, newer_data = commits[i]
        older_hash, older_data = commits[i + 1]

        newer_content = _get_file_content_at_commit(
            repo, snapshot_mgr, newer_hash, filepath
        )
        older_content = _get_file_content_at_commit(
            repo, snapshot_mgr, older_hash, filepath
        )

        if newer_content is None or older_content is None:
            continue

        newer_lines = newer_content.splitlines()
        older_lines = older_content.splitlines()

        # Simple line-by-line diff to find which lines changed
        changed_indices = _find_changed_line_indices(newer_lines, older_lines)

        for idx in changed_indices:
            if idx < len(blame):
                blame[idx] = {
                    "line": newer_lines[idx] if idx < len(newer_lines) else "",
                    "commit_hash": older_hash,
                    "author": older_data.get("author", "unknown"),
                    "timestamp": older_data.get("timestamp", "")[:10],
                    "message": older_data.get("message", ""),
                }

    return blame


def _find_changed_line_indices(newer_lines: list[str], older_lines: list[str]) -> list[int]:
    """Find line indices that differ between two versions.

    Uses a simple LCS-based approach to identify changed lines.
    """
    changed = set()

    # Quick check: if same content, nothing changed
    if newer_lines == older_lines:
        return []

    # Build a map of line content to positions in older version
    older_map: dict[str, list[int]] = {}
    for i, line in enumerate(older_lines):
        if line not in older_map:
            older_map[line] = []
        older_map[line].append(i)

    # For each line in newer, try to find it in older
    # Lines that don't match are "changed"
    used_old = set()
    matched_new = set()

    for new_idx, new_line in enumerate(newer_lines):
        if new_line in older_map:
            for old_idx in older_map[new_line]:
                if old_idx not in used_old:
                    used_old.add(old_idx)
                    matched_new.add(new_idx)
                    break

    # Lines in newer that weren't matched are new/changed
    for new_idx in range(len(newer_lines)):
        if new_idx not in matched_new:
            changed.add(new_idx)

    # Lines in older that weren't matched indicate changes nearby
    for old_idx in range(len(older_lines)):
        if old_idx not in used_old:
            # Mark surrounding lines as potentially changed
            for offset in range(-1, 2):
                idx = old_idx + offset
                if 0 <= idx < len(newer_lines):
                    changed.add(idx)

    return sorted(changed)


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
      siapa ubah <file> --baris <start>-<end>
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

    snapshot_mgr = SnapshotManager(repo)

    # Build blame data
    blame_data = _build_blame_history(repo, snapshot_mgr, filepath)

    if not blame_data:
        print_color(f"Siapa ubah: {filepath}", "cyan")
        print("Tidak ada riwayat yang bisa dianalisis.")
        return 0

    # Parse line range if provided
    line_range = parsed.options.get("baris")
    start_line = 1
    end_line = len(blame_data)

    if line_range and "-" in line_range:
        try:
            parts = line_range.split("-")
            start_line = int(parts[0])
            end_line = int(parts[1])
        except (ValueError, IndexError):
            pass

    # Display blame
    print_color(f"Siapa ubah: {filepath}", "cyan")
    if version_str:
        print(f"Dari versi: {version_str}")
    print(f"Total baris: {len(blame_data)}")
    print()

    # Find max widths for formatting
    max_commit_len = 7
    max_author_len = max(len(b["author"]) for b in blame_data) if blame_data else 10
    max_author_len = min(max_author_len, 20)

    # Display blame for each line
    for i in range(start_line - 1, min(end_line, len(blame_data))):
        entry = blame_data[i]
        commit_short = short_hash(entry["commit_hash"])
        author = entry["author"][:max_author_len]
        line_num = i + 1
        line_content = entry["line"]

        # Truncate long lines
        display_line = line_content[:72] + "..." if len(line_content) > 75 else line_content

        # Color code: different commits get different formatting
        if i > 0 and blame_data[i]["commit_hash"] != blame_data[i - 1]["commit_hash"]:
            print()  # Blank line between different commit sections

        print(f"  {commit_short} {author:<{max_author_len}} {line_num:>4} │ {display_line}")

    # Show summary
    unique_commits = set(b["commit_hash"] for b in blame_data)
    print(f"\n  ── Ringkasan ──")
    print(f"  {len(unique_commits)} commit menyentuh file ini")
    print(f"  {len(blame_data)} baris total")

    if verbose:
        # Show commit summary
        print(f"\n  Commit yang terlibat:")
        seen = set()
        for entry in blame_data:
            if entry["commit_hash"] not in seen:
                seen.add(entry["commit_hash"])
                print(f"    {short_hash(entry['commit_hash'])}  {entry['author']:<15}  {entry['message'][:50]}")

    return 0
