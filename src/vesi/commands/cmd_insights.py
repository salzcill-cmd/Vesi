"""Command: lihat file - File insights and statistics."""

from __future__ import annotations

from collections import Counter
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


def cmd_lihat_file(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show file insights and statistics.

    Usage:
      lihat file <file>              - Show file stats
      lihat file <file> --riwayat    - Show file history
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan file yang akan dianalisis.",
            hint="Contoh:\n  lihat file main.py\n  lihat file main.py --riwayat",
        )

    filepath = parsed.args[0]
    show_history = "--riwayat" in parsed.flags

    snapshot_mgr = SnapshotManager(repo)

    # Check if file exists in working directory
    file_path = repo.root / filepath
    file_exists = file_path.is_file()

    # Get file history
    commits = []
    authors = Counter()
    current_hash = repo.get_head_commit()

    while current_hash:
        try:
            data = snapshot_mgr.load_snapshot(current_hash)
            tree = snapshot_mgr.get_tree(current_hash)
            file_entries = [e for e in tree.get_blob_entries() if e.path == filepath]

            if file_entries:
                commits.append((current_hash, data))
                author = data.get("author", "unknown")
                authors[author] += 1

            current_hash = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    if not commits:
        print_color(f"File '{filepath}' tidak ditemukan dalam riwayat.", "yellow")
        return 0

    # Display insights
    print_color(f"📊 Insights: {filepath}\n", "cyan")

    # Basic stats
    print(f"  📁 Status: {'Ada' if file_exists else 'Hapus'}")
    print(f"  📝 Total commit: {len(commits)}")

    # Author breakdown
    print(f"\n  👥 Author:")
    for author, count in authors.most_common():
        pct = (count / len(commits)) * 100
        bar = "█" * int(pct / 5)
        print(f"    {author:<15} {count:>3}x ({pct:.0f}%) {bar}")

    # Last modified
    if commits:
        last_commit, last_data = commits[0]
        print(f"\n  🕐 Terakhir diubah:")
        print(f"    Commit: {short_hash(last_commit)}")
        print(f"    Author: {last_data.get('author', 'unknown')}")
        print(f"    Waktu: {last_data.get('timestamp', '')[:19]}")
        print(f"    Pesan: {last_data.get('message', '')}")

    # File size
    if file_exists:
        size = file_path.stat().st_size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        print(f"\n  📏 Ukuran: {size_str}")

    # Show detailed history if requested
    if show_history and commits:
        print(f"\n  📜 Riwayat ({len(commits)} commit):")
        for commit_hash, data in commits[:10]:
            print(f"    {short_hash(commit_hash)}  {data.get('timestamp', '')[:10]}  {data.get('message', '')[:50]}")

    return 0
