"""Command: isi - Show file content from a version."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.paths import is_binary_file


def cmd_isi(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show file content from a version."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan file yang akan ditampilkan.",
            hint="Contoh:\n    isi <file>\n    isi <file> dari <versi>",
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

    # Load and display content
    content = repo.blobs.load_content(entry.hash_id)

    # Check if binary
    if b"\x00" in content:
        print(f"[Binary file: {filepath}]")
        print(f"Ukuran: {len(content)} bytes")
        return 0

    # Display text content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        print(f"[File dengan encoding non-UTF-8: {filepath}]")
        return 0

    # Add line numbers if verbose
    if verbose:
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            print(f"{i:4d} | {line}")
    else:
        print(text)

    return 0


def _resolve_version(repo: Repository, version_id: str) -> str:
    """Resolve a version ID to full hash."""
    snapshot_mgr = SnapshotManager(repo)

    if repo.objects.exists(version_id):
        return version_id

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
