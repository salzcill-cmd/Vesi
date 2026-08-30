"""Command: pindah file - Move/rename files in repository."""

from __future__ import annotations

import shutil
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.ignore import load_ignore_patterns, is_ignored
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_pindah_file(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Move or rename files in the repository.

    Usage:
      pindah file <source> <dest>    - Move/rename file
      pindah file src/ dest/         - Move directory
      pindah file --force <src> <dst> - Force move (overwrite)
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    force = "--force" in parsed.flags

    if len(args) < 2:
        raise VesiError(
            "Tentukan sumber dan tujuan.",
            hint="Contoh:\n  pindah file old.txt new.txt\n  pindah file src/ backup/",
        )

    source = args[0]
    dest = args[1]

    source_path = repo.root / source
    dest_path = repo.root / dest

    # Check source exists
    if not source_path.exists():
        raise VesiError(
            f"File '{source}' tidak ditemukan.",
            hint="Periksa nama file dengan 'lihat perubahan'.",
        )

    # Check if dest already exists
    if dest_path.exists() and not force:
        raise VesiError(
            f"File '{dest}' sudah ada.",
            hint="Gunakan --force untuk menimpa, atau pilih nama lain.",
        )

    # Check if ignored
    ignore_patterns = load_ignore_patterns(repo.root)
    if is_ignored(source, ignore_patterns):
        raise VesiError(
            f"File '{source}' diabaikan oleh .abaikan.",
            hint="Hapus dari .abaikan jika ingin memindah file ini.",
        )

    # Get relative path for staging
    rel_source = str(source_path.relative_to(repo.root))

    # If dest is a directory, move into it
    if dest_path.is_dir():
        dest_path = dest_path / source_path.name

    # Create parent directory if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Move the file
    try:
        shutil.move(str(source_path), str(dest_path))
    except Exception as e:
        raise VesiError(f"Gagal memindah file: {e}")

    # Stage the changes
    # Stage deletion of old file
    repo.index.unstage_file(rel_source)

    # Stage addition of new file
    rel_dest = str(dest_path.relative_to(repo.root))
    if dest_path.is_file():
        blob_hash = repo.blobs.save_file(dest_path)
        repo.index.stage_file(rel_dest, blob_hash)

    print_color(f"✓ File dipindah!", "green")
    print(f"  {source} → {dest}")

    if verbose:
        print(f"\n  Perubahan:")
        print(f"    Dihapus: {rel_source}")
        print(f"    Ditambah: {rel_dest}")

    return 0
