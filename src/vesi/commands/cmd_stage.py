"""Command: stel - Stage files for the next commit."""

from __future__ import annotations

import os
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.ignore import load_ignore_patterns, is_ignored
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_stel(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Stage files for the next commit."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan file yang akan disiapkan.",
            hint="Contoh:\n    stel <file>\n    stel . (semua file)",
        )

    target = parsed.args[0]
    ignore_patterns = load_ignore_patterns(repo.root)

    if target == ".":
        # Stage all changed files
        return _stage_all(repo, ignore_patterns, verbose)
    else:
        # Stage specific file/directory
        return _stage_path(repo, target, ignore_patterns, verbose)


def _stage_all(
    repo: Repository,
    ignore_patterns: list[str],
    verbose: bool,
) -> int:
    """Stage all changed files."""
    from vesi.core.change import detect_changes
    from vesi.core.snapshot import SnapshotManager

    snapshot_mgr = SnapshotManager(repo)
    index = repo.index.load()

    tree = None
    head_hash = repo.get_head_commit()
    if head_hash:
        try:
            tree = snapshot_mgr.get_tree(head_hash)
        except Exception:
            pass

    changes = detect_changes(repo.root, tree, index)
    staged_count = 0

    for change in changes:
        if change.change_type in ("new", "modified") and change.new_hash:
            # Save blob content to object store
            file_path = repo.root / change.path
            if file_path.is_file():
                blob_hash = repo.blobs.save_file(file_path)
                repo.index.stage_file(change.path, blob_hash)
            else:
                repo.index.stage_file(change.path, change.new_hash)
            staged_count += 1
            if verbose:
                print(f"  Disiapkan: {change.path}")

    if staged_count == 0:
        print("✓ Tidak ada perubahan yang perlu disiapkan.")
    else:
        print(f"✓ {staged_count} file disiapkan untuk disimpan.")

    return 0


def _stage_path(
    repo: Repository,
    target: str,
    ignore_patterns: list[str],
    verbose: bool,
) -> int:
    """Stage a specific file or directory."""
    target_path = repo.root / target

    if not target_path.exists():
        raise VesiError(
            f"File '{target}' tidak ditemukan.",
            hint="Periksa nama file dengan 'lihat perubahan'.",
        )

    if target_path.is_dir():
        # Stage all files in directory
        staged_count = 0
        for root, dirs, files in os.walk(target_path):
            # Skip .vesi and ignored dirs
            dirs[:] = [
                d for d in dirs
                if d != ".vesi" and not is_ignored(
                    str(Path(root).relative_to(repo.root) / d),
                    ignore_patterns,
                )
            ]

            for filename in files:
                file_path = Path(root) / filename
                rel_path = str(file_path.relative_to(repo.root))

                if is_ignored(rel_path, ignore_patterns):
                    continue

                try:
                    blob_hash = repo.blobs.save_file(file_path)
                    repo.index.stage_file(rel_path, blob_hash)
                    staged_count += 1
                    if verbose:
                        print(f"  Disiapkan: {rel_path}")
                except (OSError, PermissionError):
                    continue

        if staged_count == 0:
            print("✓ Tidak ada file yang perlu disiapkan di folder ini.")
        else:
            print(f"✓ {staged_count} file disiapkan untuk disimpan.")
    else:
        # Stage single file
        rel_path = str(target_path.relative_to(repo.root))

        if is_ignored(rel_path, ignore_patterns):
            raise VesiError(
                f"File '{target}' diabaikan oleh .abaikan.",
                hint="Hapus file dari .abaikan jika ingin melacak file ini.",
            )

        blob_hash = repo.blobs.save_file(target_path)
        repo.index.stage_file(rel_path, blob_hash)
        print(f"✓ '{rel_path}' disiapkan untuk disimpan.")

    return 0
