"""Commands: pulihkan (restore) and batalkan perubahan (discard changes)."""

from __future__ import annotations

import shutil
from pathlib import Path

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    FileNotTrackedError,
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import confirm, print_color


def cmd_pulihkan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Restore a file from a specific version."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan file yang akan dipulihkan.",
            hint="Contoh:\n    pulihkan <file>\n    pulihkan <file> dari <versi>",
        )

    filepath = parsed.args[0]
    version_id = parsed.options.get("from")

    snapshot_mgr = SnapshotManager(repo)

    # Determine source version
    if version_id:
        commit_hash = _resolve_version(repo, version_id)
    else:
        commit_hash = repo.get_head_commit()
        if not commit_hash:
            raise VesiError("Belum ada versi yang tersimpan.")

    # Get tree from version
    try:
        tree = snapshot_mgr.get_tree(commit_hash)
    except Exception:
        raise VersionNotFoundError(version_id or "latest")

    # Find file in tree
    entry = tree.get_entry(filepath)
    if entry is None:
        # Try to find by name only
        for e in tree.get_blob_entries():
            if e.path == filepath or e.name == filepath:
                entry = e
                filepath = e.path
                break

    if entry is None:
        raise VesiError(
            f"File '{filepath}' tidak ada di versi {version_id or 'terakhir'}.",
        )

    # Load content
    content = repo.blobs.load_content(entry.hash_id)

    # Create backup
    target_path = repo.root / filepath
    backup_dir = repo.vesi_dir / "backups"
    backup_dir.mkdir(exist_ok=True)

    if target_path.is_file():
        backup_path = backup_dir / f"{filepath.replace('/', '_')}.bak"
        shutil.copy2(target_path, backup_path)
        if verbose:
            print(f"  Backup: {backup_path}")

    # Restore file
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(content)

    version_label = version_id or "terakhir"
    print_color(f"✓ File '{filepath}' dipulihkan dari versi {version_label}.", "green")

    return 0


def cmd_batalkan_perubahan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Discard changes to a file (revert to last committed version)."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan file yang perubahannya akan dibatalkan.",
            hint="Contoh:\n    batalkan perubahan <file>",
        )

    filepath = parsed.args[0]
    target_path = repo.root / filepath

    # Check if file is tracked
    head_hash = repo.get_head_commit()
    if not head_hash:
        raise VesiError("Belum ada versi yang tersimpan.")

    snapshot_mgr = SnapshotManager(repo)
    try:
        tree = snapshot_mgr.get_tree(head_hash)
    except Exception:
        raise VesiError("Gagal memuat versi terakhir.")

    entry = tree.get_entry(filepath)
    if entry is None:
        # Check if file exists at all
        if not target_path.is_file():
            raise VesiError(
                f"File '{filepath}' belum pernah disimpan. Tidak ada yang bisa dibatalkan."
            )
        # File is new (untracked)
        raise VesiError(
            f"File '{filepath}' belum pernah disimpan. Tidak ada yang bisa dibatalkan."
        )

    # Check if there are actual changes
    if target_path.is_file():
        current_hash = repo.blobs.file_hash(target_path)
        if current_hash == entry.hash_id:
            print(f"✓ File '{filepath}' tidak memiliki perubahan.")
            return 0

    # Show what will be lost and confirm
    print(f"⚠ Perubahan pada '{filepath}' akan dibatalkan.")
    if not confirm("Lanjutkan?", default=False):
        print("Dibatalkan.")
        return 0

    # Restore from last commit
    content = repo.blobs.load_content(entry.hash_id)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(content)

    # Remove from staging if staged
    repo.index.unstage_file(filepath)

    print_color(f"✓ Perubahan pada '{filepath}' dibatalkan.", "green")
    return 0


def _resolve_version(repo: Repository, version_id: str) -> str:
    """Resolve a version ID to full hash."""
    # Try as full hash first
    if repo.objects.exists(version_id):
        return version_id

    # Walk history to find matching short hash
    snapshot_mgr = SnapshotManager(repo)
    head_hash = repo.get_head_commit()
    if head_hash:
        current = head_hash
        while current:
            if current.startswith(version_id):
                return current
            try:
                data = snapshot_mgr.load_snapshot(current)
                current = data.get("parent")
            except Exception:
                break

    raise VersionNotFoundError(version_id)
