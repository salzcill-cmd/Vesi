"""Command: hapus file - Remove files from tracking."""

from __future__ import annotations

import os
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import confirm, print_color


def cmd_hapus_file(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Remove files from tracking.

    Usage:
      hapus file <file>          - Remove from tracking + delete file
      hapus file --cached <file> - Remove from tracking only (keep file)
      hapus file --force <file>  - Force remove
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    cached = "--cached" in parsed.flags
    force = "--force" in parsed.flags

    if not args:
        raise VesiError(
            "Tentukan file yang akan dihapus.",
            hint="Contoh:\n  hapus file old.txt\n  hapus file --cached temp.log",
        )

    for filepath in args:
        if filepath.startswith("--"):
            continue

        file_path = repo.root / filepath

        # Check if file is tracked
        head_hash = repo.get_head_commit()
        if head_hash:
            from vesi.core.snapshot import SnapshotManager
            snapshot_mgr = SnapshotManager(repo)
            try:
                tree = snapshot_mgr.get_tree(head_hash)
                entry = tree.get_entry(filepath)
                if entry is None and not file_path.exists():
                    raise VesiError(
                        f"File '{filepath}' tidak dilacak dan tidak ada di disk.",
                    )
            except Exception:
                pass

        # Check if file exists
        if not file_path.exists() and not cached:
            raise VesiError(
                f"File '{filepath}' tidak ditemukan.",
                hint="Gunakan --cached untuk menghapus dari tracking saja.",
            )

        # Confirm if not forced
        if not force and not cached:
            print(f"⚠ File '{filepath}' akan dihapus dari disk.")
            if not confirm("Lanjutkan?", default=False):
                print("Dibatalkan.")
                continue

        # Remove from staging
        repo.index.unstage_file(filepath)

        # Delete file if not cached mode
        if not cached and file_path.exists():
            try:
                if file_path.is_dir():
                    import shutil
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
                print_color(f"✓ '{filepath}' dihapus dari disk dan tracking.", "green")
            except Exception as e:
                raise VesiError(f"Gagal menghapus file: {e}")
        else:
            print_color(f"✓ '{filepath}' dihapus dari tracking (file tetap ada).", "green")

        if verbose:
            print(f"  File: {filepath}")
            print(f"  Mode: {'cached only' if cached else 'disk + tracking'}")

    return 0
