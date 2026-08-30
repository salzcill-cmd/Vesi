"""Command: lihat riwayat - Show version history with advanced formatting."""

from __future__ import annotations

from collections import defaultdict

from vesi.core.history import get_history, format_history
from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import RepositoryNotFoundError, VesiError
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


# ANSI colors for graph
COLORS = [
    "\033[31m", "\033[32m", "\033[33m", "\033[34m",
    "\033[35m", "\033[36m", "\033[91m", "\033[92m",
]
RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"


def cmd_lihat_riwayat(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show version history with advanced formatting.

    Options:
      --oneline     One line per commit
      --graph       Show ASCII graph
      --all         Show all branches
      --stat        Show file stats
      --author=X    Filter by author
      --since=X     Filter by date (YYYY-MM-DD)
      --until=X     Filter by date (YYYY-MM-DD)
      --grep=X      Filter by message
      --no-merges   Skip merge commits
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Parse limit from args
    limit = 10
    args = parsed.args or []
    if args:
        try:
            limit = int(args[0])
        except ValueError:
            pass

    # Parse options
    oneline = "--oneline" in parsed.flags
    show_graph = "--graph" in parsed.flags
    show_all = "--all" in parsed.flags
    show_stat = "--stat" in parsed.flags
    no_merges = "--no-merges" in parsed.flags

    # Parse filter options
    filter_author = _get_flag_value(parsed.flags, "--author")
    filter_since = _get_flag_value(parsed.flags, "--since")
    filter_until = _get_flag_value(parsed.flags, "--until")
    filter_grep = _get_flag_value(parsed.flags, "--grep")

    # Get branch name from options if specified
    branch_name = parsed.options.get("branch")

    if show_all or show_graph:
        return _show_graph_log(
            repo, limit, show_all, oneline, show_stat,
            filter_author, filter_since, filter_until, filter_grep,
            no_merges, verbose,
        )
    elif oneline:
        return _show_oneline_log(
            repo, limit, branch_name, filter_author, filter_grep, no_merges
        )
    elif show_stat:
        return _show_stat_log(
            repo, limit, branch_name, filter_author, filter_grep, no_merges
        )
    else:
        # Standard log with optional filters
        entries = get_history(repo, limit=limit * 3, branch_name=branch_name)  # Get more for filtering
        snapshot_mgr = SnapshotManager(repo)

        # Apply filters
        filtered = []
        for entry in entries:
            if len(filtered) >= limit:
                break

            info = entry.info
            data = snapshot_mgr.load_snapshot(info.full_id)

            # Apply filters
            if filter_author and filter_author.lower() not in info.author.lower():
                continue
            if filter_grep and filter_grep.lower() not in info.message.lower():
                continue
            if filter_since and info.timestamp[:10] < filter_since:
                continue
            if filter_until and info.timestamp[:10] > filter_until:
                continue
            if no_merges and data.get("second_parent"):
                continue

            filtered.append(entry)

        print(format_history(filtered))

    return 0


def _show_oneline_log(
    repo: Repository,
    limit: int,
    branch_name: str | None,
    filter_author: str | None,
    filter_grep: str | None,
    no_merges: bool,
) -> int:
    """Show compact one-line-per-commit log."""
    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        print("Belum ada commit.")
        return 0

    count = 0
    visited = set()

    while current_hash and count < limit and current_hash not in visited:
        visited.add(current_hash)

        try:
            data = snapshot_mgr.load_snapshot(current_hash)
        except Exception:
            break

        author = data.get("author", "unknown")
        message = data.get("message", "")
        timestamp = data.get("timestamp", "")[:10]
        is_merge = data.get("second_parent") is not None

        # Apply filters
        if filter_author and filter_author.lower() not in author.lower():
            current_hash = data.get("parent")
            continue
        if filter_grep and filter_grep.lower() not in message.lower():
            current_hash = data.get("parent")
            continue
        if no_merges and is_merge:
            current_hash = data.get("parent")
            continue

        # Format
        hash_str = short_hash(current_hash)
        merge_marker = " *" if is_merge else ""

        print(f"{BOLD}{hash_str}{RESET}{merge_marker} {message}")
        count += 1
        current_hash = data.get("parent")

    return 0


def _show_stat_log(
    repo: Repository,
    limit: int,
    branch_name: str | None,
    filter_author: str | None,
    filter_grep: str | None,
    no_merges: bool,
) -> int:
    """Show log with file stats."""
    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        print("Belum ada commit.")
        return 0

    count = 0
    visited = set()

    while current_hash and count < limit and current_hash not in visited:
        visited.add(current_hash)

        try:
            data = snapshot_mgr.load_snapshot(current_hash)
        except Exception:
            break

        author = data.get("author", "unknown")
        message = data.get("message", "")
        timestamp = data.get("timestamp", "")[:10]
        is_merge = data.get("second_parent") is not None

        # Apply filters
        if filter_author and filter_author.lower() not in author.lower():
            current_hash = data.get("parent")
            continue
        if filter_grep and filter_grep.lower() not in message.lower():
            current_hash = data.get("parent")
            continue
        if no_merges and is_merge:
            current_hash = data.get("parent")
            continue

        # Get file stats
        try:
            tree = snapshot_mgr.get_tree(current_hash)
            entries = tree.get_blob_entries()

            # Get parent tree for diff
            parent_hash = data.get("parent")
            parent_files = {}
            if parent_hash:
                try:
                    parent_tree = snapshot_mgr.get_tree(parent_hash)
                    parent_files = {e.path: e.hash_id for e in parent_tree.get_blob_entries()}
                except Exception:
                    pass

            current_files = {e.path: e.hash_id for e in entries}

            added = sum(1 for p in current_files if p not in parent_files)
            modified = sum(1 for p in current_files if p in parent_files and current_files[p] != parent_files[p])
            deleted = sum(1 for p in parent_files if p not in current_files)
            total = added + modified + deleted

        except Exception:
            total = 0
            added = modified = deleted = 0

        # Format
        hash_str = short_hash(current_hash)
        merge_marker = " (merge)" if is_merge else ""

        print(f"{BOLD}{hash_str}{RESET} {timestamp} {author}: {message}{merge_marker}")
        if total > 0:
            parts = []
            if added:
                parts.append(f"{added} file(+)")
            if modified:
                parts.append(f"{modified} file(~)")
            if deleted:
                parts.append(f"{deleted} file(-)")
            print(f"  {'  '.join(parts)}")
        print()

        count += 1
        current_hash = data.get("parent")

    return 0


def _show_graph_log(
    repo: Repository,
    limit: int,
    show_all: bool,
    oneline: bool,
    show_stat: bool,
    filter_author: str | None,
    filter_since: str | None,
    filter_until: str | None,
    filter_grep: str | None,
    no_merges: bool,
    verbose: bool,
) -> int:
    """Show commit graph."""
    snapshot_mgr = SnapshotManager(repo)

    # Collect commits with branch info
    branches = repo.refs.list_branches()
    branch_hashes = {}
    for branch in branches:
        h = repo.refs.get_branch_hash(branch)
        if h:
            branch_hashes[branch] = h

    active_branch = repo.refs.get_active_branch() or "HEAD"

    # Walk history
    commits = []
    current_hash = repo.get_head_commit()
    visited = set()

    while current_hash and len(commits) < limit * 2 and current_hash not in visited:
        visited.add(current_hash)
        try:
            data = snapshot_mgr.load_snapshot(current_hash)
            parent = data.get("parent")
            second_parent = data.get("second_parent")

            # Determine branches
            containing_branches = []
            for branch, bh in branch_hashes.items():
                if bh == current_hash:
                    containing_branches.append(branch)

            commits.append({
                "hash": current_hash,
                "parent": parent,
                "second_parent": second_parent,
                "message": data.get("message", ""),
                "timestamp": data.get("timestamp", "")[:10],
                "author": data.get("author", ""),
                "branches": containing_branches,
                "data": data,
            })

            current_hash = parent
        except (FileNotFoundError, ValueError):
            break

    # Apply filters
    filtered = []
    for c in commits:
        if filter_author and filter_author.lower() not in c["author"].lower():
            continue
        if filter_grep and filter_grep.lower() not in c["message"].lower():
            continue
        if filter_since and c["timestamp"] < filter_since:
            continue
        if filter_until and c["timestamp"] > filter_until:
            continue
        if no_merges and c["second_parent"]:
            continue
        filtered.append(c)
        if len(filtered) >= limit:
            break

    if not filtered:
        print("Belum ada commit.")
        return 0

    # Assign colors
    color_map = {}
    for i, branch in enumerate(branches):
        color_map[branch] = COLORS[i % len(COLORS)]

    # Display graph
    print_color("Grafik riwayat:\n", "cyan")

    for i, commit in enumerate(filtered):
        is_first = (i == 0)
        hash_str = short_hash(commit["hash"])

        # Format branch labels
        branches_str = ""
        if commit["branches"]:
            labels = []
            for b in commit["branches"]:
                color = color_map.get(b, "")
                labels.append(f"{color}*{b}{RESET}" if color else f"*{b}")
            branches_str = " " + " ".join(labels)

        # Graph line
        if is_first:
            marker = f"{COLORS[0]}*{RESET}"
            graph = f"  {marker} "
        else:
            color = color_map.get(active_branch, COLORS[0])
            if commit.get("second_parent"):
                graph = f"  {color}├─{RESET} "
            else:
                graph = f"  {color}│{RESET} "

        # Format commit info
        if oneline:
            print(f"{graph}{BOLD}{hash_str}{RESET} {commit['message'][:60]}{branches_str}")
        else:
            print(f"{graph}{BOLD}{hash_str}{RESET} ({commit['timestamp']}) {commit['author']}: {commit['message'][:50]}{branches_str}")

            if show_stat:
                try:
                    tree = snapshot_mgr.get_tree(commit["hash"])
                    entries = tree.get_blob_entries()
                    print(f"  {'│':1} {len(entries)} file{'s' if len(entries) != 1 else ''}")
                except Exception:
                    pass

    # Legend
    if branches:
        print(f"\n  {DIM}── Cabang ──{RESET}")
        for branch in branches:
            color = color_map.get(branch, "")
            is_active = " (aktif)" if branch == active_branch else ""
            h = branch_hashes.get(branch, "")
            print(f"  {color}●{RESET} {branch}{is_active} → {short_hash(h) if h else '(empty)'}")

    return 0


def _get_flag_value(flags: list[str], flag_name: str) -> str | None:
    """Extract value from --flag=value or --flag value."""
    for i, flag in enumerate(flags):
        if flag.startswith(f"{flag_name}="):
            return flag[len(flag_name) + 1:]
        if flag == flag_name and i + 1 < len(flags):
            return flags[i + 1]
    return None
