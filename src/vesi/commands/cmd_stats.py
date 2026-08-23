"""Command: statistik - Project statistics and metrics."""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_statistik(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show project statistics.

    Usage:
      statistik                  - Show basic stats
      statistik --detail         - Show detailed stats
      statistik --author         - Show author stats
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    show_detail = "--detail" in parsed.flags
    show_author = "--author" in parsed.flags

    # Collect all commits
    commits = []
    authors = Counter()
    files_touched = Counter()
    dates = Counter()
    current_hash = repo.get_head_commit()

    while current_hash:
        try:
            data = snapshot_mgr.load_snapshot(current_hash)
            commits.append((current_hash, data))

            author = data.get("author", "unknown")
            authors[author] += 1

            timestamp = data.get("timestamp", "")[:10]
            dates[timestamp] += 1

            # Get files in this commit
            tree = snapshot_mgr.get_tree(current_hash)
            for entry in tree.get_blob_entries():
                files_touched[entry.path] += 1

            current_hash = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    if not commits:
        print_color("Belum ada commit.", "yellow")
        return 0

    # Basic stats
    print_color("📊 Statistik Proyek\n", "cyan")
    print("━" * 50)

    print(f"\n  📁 Repository:")
    print(f"    Total commit:     {len(commits)}")
    print(f"    Total file:       {len(files_touched)}")
    print(f"    Total author:     {len(authors)}")

    # Working directory stats
    total_files = 0
    total_size = 0
    for root, dirs, files in os.walk(repo.root):
        dirs[:] = [d for d in dirs if d != ".vesi" and d != ".git"]
        for f in files:
            filepath = os.path.join(root, f)
            try:
                total_files += 1
                total_size += os.path.getsize(filepath)
            except OSError:
                pass

    if total_size < 1024:
        size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    else:
        size_str = f"{total_size / (1024 * 1024):.1f} MB"

    print(f"    Working files:    {total_files}")
    print(f"    Total ukuran:     {size_str}")

    # Author stats
    if show_author or len(authors) > 0:
        print(f"\n  👥 Kontributor:")
        for author, count in authors.most_common():
            pct = (count / len(commits)) * 100
            bar = "█" * int(pct / 5)
            print(f"    {author:<20} {count:>3}x ({pct:.0f}%) {bar}")

    # Activity by date
    if show_detail:
        print(f"\n  📅 Aktivitas Harian (10 terakhir):")
        for date, count in sorted(dates.items(), reverse=True)[:10]:
            bar = "█" * count
            print(f"    {date}  {count:>3}x {bar}")

    # Most changed files
    if show_detail:
        print(f"\n  📝 File Paling Sering Berubah:")
        for filepath, count in files_touched.most_common(10):
            print(f"    {count:>3}x  {filepath}")

    # Recent activity
    print(f"\n  🕐 Aktivitas Terakhir:")
    for commit_hash, data in commits[:5]:
        print(f"    {short_hash(commit_hash)}  {data.get('timestamp', '')[:10]}  {data.get('message', '')[:40]}")

    print(f"\n{'━' * 50}")
    print_color("💡 Tips: Gunakan --detail untuk info lebih lengkap", "dim")

    return 0
