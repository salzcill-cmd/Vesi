"""Command: grafik - Visual commit graph display."""

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


# Branch colors for graph display
BRANCH_COLORS = [
    "\033[31m",  # red
    "\033[32m",  # green
    "\033[33m",  # yellow
    "\033[34m",  # blue
    "\033[35m",  # magenta
    "\033[36m",  # cyan
    "\033[91m",  # bright red
    "\033[92m",  # bright green
    "\033[93m",  # bright yellow
    "\033[94m",  # bright blue
]
RESET = "\033[0m"
DIM = "\033[2m"


def cmd_grafik(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Visual commit graph.

    Usage:
      grafik                     - Show commit graph
      grafik <count>             - Show last N commits
      grafik --all               - Show all branches
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    limit = 20

    args = parsed.args or []
    if args:
        try:
            limit = int(args[0])
        except ValueError:
            pass

    # Get all branch tips
    branches = repo.refs.list_branches()
    branch_hashes: dict[str, str] = {}
    for branch in branches:
        h = repo.refs.get_branch_hash(branch)
        if h:
            branch_hashes[branch] = h

    # Walk history and build graph
    active_branch = repo.refs.get_active_branch() or "HEAD"

    # Collect commits with their branch info
    commits = []
    current_hash = repo.get_head_commit()
    visited = set()

    while current_hash and len(commits) < limit and current_hash not in visited:
        visited.add(current_hash)
        try:
            data = snapshot_mgr.load_snapshot(current_hash)
            parent = data.get("parent")
            second_parent = data.get("second_parent")

            # Determine which branches contain this commit
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
            })

            current_hash = parent
        except (FileNotFoundError, ValueError):
            break

    if not commits:
        print("Belum ada commit.")
        return 0

    # Assign colors to branches
    branch_color_map = {}
    color_idx = 0
    for branch in branches:
        branch_color_map[branch] = BRANCH_COLORS[color_idx % len(BRANCH_COLORS)]
        color_idx += 1

    # Build and display graph
    print_color("Grafik commit:\n", "cyan")

    # Simple graph rendering
    for i, commit in enumerate(commits):
        commit_hash = commit["hash"]
        is_first = (i == 0)
        branches_str = ""

        # Format branch labels
        if commit["branches"]:
            labels = []
            for b in commit["branches"]:
                color = branch_color_map.get(b, "")
                labels.append(f"{color}*{b}{RESET}" if color else f"*{b}")
            branches_str = " " + " ".join(labels)

        # Draw graph line
        if is_first:
            # HEAD commit
            marker = f"{BRANCH_COLORS[0]}*{RESET}"
            graph_line = f"  {marker} "
        else:
            parent_commit = commits[i - 1] if i > 0 else None
            # Check if this is a merge commit
            if commit.get("second_parent"):
                # Merge commit: show two lines converging
                color = branch_color_map.get(active_branch, BRANCH_COLORS[0])
                graph_line = f"  {color}│{RESET} "
            else:
                # Normal commit
                color = branch_color_map.get(active_branch, BRANCH_COLORS[0])
                graph_line = f"  {color}│{RESET} "

        # Format the line
        hash_str = short_hash(commit_hash)
        message = commit["message"][:50]
        author = commit["author"][:15]
        timestamp = commit["timestamp"]

        if is_first:
            print(f"  {BRANCH_COLORS[0]}*{RESET} {hash_str} ({timestamp}) {author}: {message}{branches_str}")
        else:
            color = branch_color_map.get(active_branch, BRANCH_COLORS[0])
            print(f"  {color}│{RESET} {hash_str} ({timestamp}) {author}: {message}{branches_str}")

    # Show branch connections
    if len(commits) > 1:
        print(f"  {DIM}│{RESET}")

    # Legend
    print(f"\n  {DIM}── Legend ──{RESET}")
    for branch in branches:
        color = branch_color_map.get(branch, "")
        is_active = " (aktif)" if branch == active_branch else ""
        h = branch_hashes.get(branch, "")
        print(f"  {color}●{RESET} {branch}{is_active} → {short_hash(h) if h else '(empty)'}")

    return 0
