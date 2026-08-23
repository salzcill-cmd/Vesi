"""Command: cari riwayat - Search commit history."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.storage.tree import Tree
from vesi.utils.platform import print_color


def cmd_cari_riwayat(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Search commit history.

    Usage:
      cari riwayat <kata>              - Search by message
      cari riwayat --file <file>       - Search by file
      cari riwayat --author <name>     - Search by author
      cari riwayat --pesan <pesan>     - Search by message (explicit)
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)

    # Parse search options
    search_message = ""
    search_file = ""
    search_author = ""

    args = parsed.args or []
    flags = parsed.flags

    # Check for --file flag
    if "--file" in flags:
        idx = flags.index("--file")
        if idx + 1 < len(args):
            search_file = args[idx]
        else:
            # Check in regular args
            for i, arg in enumerate(args):
                if arg == "--file" and i + 1 < len(args):
                    search_file = args[i + 1]
                    break
    elif "--author" in flags:
        idx = flags.index("--author")
        if idx + 1 < len(args):
            search_author = args[idx]
        else:
            for i, arg in enumerate(args):
                if arg == "--author" and i + 1 < len(args):
                    search_author = args[i + 1]
                    break
    elif "--pesan" in flags:
        # Search by message explicitly
        search_message = " ".join(args)
    elif args:
        # Default: search by message
        search_message = " ".join(args)

    if not search_message and not search_file and not search_author:
        raise VesiError(
            "Tentukan apa yang ingin dicari.",
            hint="Contoh:\n  cari riwayat login\n  cari riwayat --file main.py\n  cari riwayat --author budi",
        )

    # Search commits
    results = []
    current_hash = repo.get_head_commit()
    visited = set()

    while current_hash and current_hash not in visited:
        visited.add(current_hash)
        try:
            data = snapshot_mgr.load_snapshot(current_hash)

            # Check message match
            if search_message:
                msg = data.get("message", "").lower()
                if search_message.lower() not in msg:
                    current_hash = data.get("parent")
                    continue

            # Check author match
            if search_author:
                author = data.get("author", "").lower()
                if search_author.lower() not in author:
                    current_hash = data.get("parent")
                    continue

            # Check file match
            if search_file:
                tree = snapshot_mgr.get_tree(current_hash)
                file_paths = [e.path for e in tree.get_blob_entries()]
                if not any(search_file.lower() in fp.lower() for fp in file_paths):
                    current_hash = data.get("parent")
                    continue

            results.append((current_hash, data))

            current_hash = data.get("parent")
        except (FileNotFoundError, ValueError):
            break

    # Display results
    if not results:
        print_color(f"Tidak ditemukan commit yang cocok.", "yellow")
        return 0

    print_color(f"Ditemukan {len(results)} commit:\n", "cyan")

    for commit_hash, data in results[:20]:  # Limit to 20 results
        commit_short = short_hash(commit_hash)
        message = data.get("message", "")
        timestamp = data.get("timestamp", "")[:10]
        author = data.get("author", "")

        print(f"  {commit_short}  {timestamp}  {author:<15} {message}")

    if len(results) > 20:
        print(f"\n  ... dan {len(results) - 20} commit lainnya")

    return 0
