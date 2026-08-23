"""Command: simpan interaktif - Interactive commit wizard."""

from __future__ import annotations

import sys
from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    NoStagedChangesError,
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_simpan_interaktif(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Interactive commit wizard - guides you step by step.

    Usage:
      simpan interaktif           - Start interactive commit
      simpan wizard               - Same as above
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)

    # Step 1: Show current status
    print_color("🔄 Simpan Interaktif - Langkah demi Langkah\n", "cyan")
    print("━" * 50)

    # Check staged files
    index = repo.index.load()
    if not index:
        print_color("\n⚠️  Tidak ada file yang disiapkan.\n", "yellow")
        print("Langkah 1: Siapkan file terlebih dahulu")
        print("  vesi stel <file>   # Siapkan file tertentu")
        print("  vesi stel .        # Siapkan semua file")
        print("\nLalu jalankan lagi: vesi simpan interaktif")
        return 0

    print_color(f"\n📁 Langkah 1: File yang akan disimpan ({len(index)} file)", "green")
    for filepath in sorted(index.keys()):
        print(f"  ✓ {filepath}")

    # Step 2: Choose commit type
    print(f"\n{'━' * 50}")
    print_color("🏷️  Langkah 2: Pilih tipe commit\n", "green")
    print("  1. feat      Fitur baru")
    print("  2. fix       Perbaikan bug")
    print("  3. docs      Dokumentasi")
    print("  4. style     Style/format")
    print("  5. refactor  Refactor kode")
    print("  6. test      Test")
    print("  7. chore     Maintenance")
    print("  8. other     Lainnya")

    # For non-interactive mode (testing), use default
    if not sys.stdin.isatty():
        commit_type = "feat"
        print(f"\n  → {commit_type} (otomatis)")
    else:
        try:
            choice = input("\n  Pilih (1-8) [1]: ").strip() or "1"
            type_map = {
                "1": "feat", "2": "fix", "3": "docs", "4": "style",
                "5": "refactor", "6": "test", "7": "chore", "8": "other"
            }
            commit_type = type_map.get(choice, "feat")
            print(f"  → {commit_type}")
        except (EOFError, KeyboardInterrupt):
            commit_type = "feat"
            print(f"\n  → {commit_type} (otomatis)")

    # Step 3: Enter description
    print(f"\n{'━' * 50}")
    print_color("✍️  Langkah 3: Deskripsi perubahan\n", "green")

    if not sys.stdin.isatty():
        description = "update dari simpan interaktif"
        print(f"  → {description} (otomatis)")
    else:
        try:
            description = input("  Deskripsi: ").strip()
            if not description:
                description = "update dari simpan interaktif"
            print(f"  → {description}")
        except (EOFError, KeyboardInterrupt):
            description = "update dari simpan interaktif"
            print(f"\n  → {description} (otomatis)")

    # Step 4: Preview and confirm
    commit_msg = f"{commit_type}: {description}" if commit_type != "other" else description

    print(f"\n{'━' * 50}")
    print_color("👀 Langkah 4: Preview\n", "green")
    print(f"  Pesan: \"{commit_msg}\"")
    print(f"  File:  {len(index)} file")

    # Step 5: Confirm
    print(f"\n{'━' * 50}")
    print_color("✅ Langkah 5: Konfirmasi\n", "green")

    if not sys.stdin.isatty():
        confirm = "y"
        print(f"  → y (otomatis)")
    else:
        try:
            confirm = input("  Simpan? [Y/n]: ").strip().lower() or "y"
        except (EOFError, KeyboardInterrupt):
            confirm = "n"

    if confirm != "y":
        print_color("\n❌ Dibatalkan.", "yellow")
        return 0

    # Create commit
    parent_hash = repo.get_head_commit()

    # Build tree
    from vesi.storage.tree import Tree
    new_tree = Tree()
    for filepath, file_hash in index.items():
        name = filepath.split("/")[-1]
        new_tree.add_blob(name, file_hash, filepath)

    # Create snapshot
    author = repo.get_author()
    snapshot_hash = snapshot_mgr.create_snapshot(
        tree=new_tree,
        message=commit_msg,
        author=author,
        parent=parent_hash,
    )

    # Update branch
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        repo.refs.set_branch_hash(active_branch, snapshot_hash)

    # Add reflog entry
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    reflog.add_entry(snapshot_hash, "commit", commit_msg, active_branch or "")

    # Clear staging
    repo.index.clear()

    # Success
    print(f"\n{'━' * 50}")
    print_color("🎉 Berhasil!\n", "green")
    print(f"  ID:    {short_hash(snapshot_hash)}")
    print(f"  Pesan: {commit_msg}")
    print(f"  File:  {len(index)} file disimpan")

    return 0
