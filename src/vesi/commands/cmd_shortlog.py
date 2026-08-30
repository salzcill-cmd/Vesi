"""Command: ringkasan - Commit summary grouped by author."""

from __future__ import annotations

from collections import Counter

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_ringkasan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Commit summary grouped by author.

    Usage:
      ringkasan                - Show summary grouped by author
      ringkasan --numbered     - Sort by number of commits
      ringkasan --email        - Group by email instead of name
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    show_numbered = "--numbered" in parsed.flags
    show_email = "--email" in parsed.flags

    # Collect all commits
    author_commits: dict[str, list[tuple[str, str]]] = {}
    current_hash = repo.get_head_commit()
    total = 0

    while current_hash:
        try:
            data = snapshot_mgr.load_snapshot(current_hash)
            author = data.get("author", "unknown") if not show_email else data.get("author", "unknown")
            message = data.get("message", "")
            timestamp = data.get("timestamp", "")[:10]

            if author not in author_commits:
                author_commits[author] = []
            author_commits[author].append((current_hash, message))

            total += 1
            current_hash = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    if not author_commits:
        print("Belum ada commit.")
        return 0

    # Sort authors
    if show_numbered:
        sorted_authors = sorted(author_commits.items(), key=lambda x: len(x[1]), reverse=True)
    else:
        sorted_authors = sorted(author_commits.items())

    # Display
    print_color("Ringkasan commit:\n", "cyan")

    max_author_len = max(len(a) for a in author_commits.keys())
    max_author_len = min(max_author_len, 30)

    for author, commits in sorted_authors:
        count = len(commits)
        bar_len = min(count, 30)
        bar = "█" * bar_len

        # Show latest commit message
        latest_msg = commits[0][1] if commits else ""

        print(f"  {author:<{max_author_len}} {count:>4}  {bar}")

        if verbose:
            # Show all commit messages for this author
            for commit_hash, msg in commits[:5]:
                print(f"    {short_hash(commit_hash)}  {msg[:60]}")
            if len(commits) > 5:
                print(f"    ... dan {len(commits) - 5} commit lainnya")
            print()

    print(f"\n  Total: {total} commit dari {len(author_commits)} kontributor")

    return 0
