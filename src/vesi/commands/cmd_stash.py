"""Command: simpan sementara / ambil stash - Stash system for temporary storage."""

from __future__ import annotations

import json
import time
from pathlib import Path

from vesi.errors.exceptions import (
    NoChangesError,
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import hash_content, short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


class StashManager:
    """Manages stash entries in the repository."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.stash_dir = repo.vesi_dir / "stash"
        self.stash_dir.mkdir(parents=True, exist_ok=True)
        self.stash_file = self.stash_dir / "stash.json"

    def _load_stash(self) -> list[dict]:
        """Load stash list from file."""
        if not self.stash_file.is_file():
            return []
        try:
            return json.loads(self.stash_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_stash(self, stash_list: list[dict]) -> None:
        """Save stash list to file."""
        self.stash_file.write_text(
            json.dumps(stash_list, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create_stash(self, message: str = "") -> dict:
        """Create a new stash entry from staged and working changes.

        Returns the stash entry dict.
        """
        import shutil

        from vesi.core.change import detect_changes
        from vesi.core.snapshot import SnapshotManager
        from vesi.storage.tree import Tree

        # Get changes (both staged and working directory)
        index = self.repo.index.load()
        snapshot_mgr = SnapshotManager(self.repo)
        parent_hash = self.repo.get_head_commit()

        tree = None
        if parent_hash:
            try:
                tree = snapshot_mgr.get_tree(parent_hash)
            except Exception:
                pass

        changes = detect_changes(self.repo.root, tree, index or {})
        if not changes:
            raise NoChangesError()

        # Create stash entry
        stash_id = f"stash@{{{len(self._load_stash())}}}"
        stash_dir = self.stash_dir / f"stash_{int(time.time())}"
        stash_dir.mkdir(exist_ok=True)

        # Save changed files to stash directory
        saved_files = []
        for change in changes:
            filepath = change.path
            src_path = self.repo.root / filepath
            if src_path.is_file():
                dst_path = stash_dir / filepath.replace("/", "_")
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                saved_files.append(filepath)

        # Save stash metadata
        stash_entry = {
            "id": stash_id,
            "message": message or f"Stash dari {len(saved_files)} file",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": saved_files,
            "branch": self.repo.refs.get_active_branch() or "detached",
            "stash_dir": str(stash_dir),
        }

        # Save metadata
        (stash_dir / "stash.json").write_text(
            json.dumps(stash_entry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Add to stash list
        stash_list = self._load_stash()
        stash_list.append(stash_entry)
        self._save_stash(stash_list)

        # Clear staging area
        self.repo.index.clear()

        return stash_entry

    def list_stashes(self) -> list[dict]:
        """List all stash entries."""
        return self._load_stashes()

    def _load_stashes(self) -> list[dict]:
        """Load all stash entries."""
        stash_list = self._load_stash()
        result = []
        for entry in stash_list:
            stash_dir = Path(entry.get("stash_dir", ""))
            if stash_dir.is_dir():
                result.append(entry)
        return result

    def pop_stash(self, index: int = 0) -> dict:
        """Apply and remove a stash entry.

        Args:
            index: Stash index to pop (0 = most recent).

        Returns the popped stash entry.
        """
        import shutil

        stash_list = self._load_stash()
        if not stash_list or index >= len(stash_list):
            raise VesiError("Tidak ada stash untuk diambil.")

        entry = stash_list[index]
        stash_dir = Path(entry.get("stash_dir", ""))

        if not stash_dir.is_dir():
            raise VesiError(f"Stash '{entry['id']}' rusak atau tidak ditemukan.")

        # Restore files from stash
        for filepath in entry.get("files", []):
            src_path = stash_dir / filepath.replace("/", "_")
            dst_path = self.repo.root / filepath
            if src_path.is_file():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)

        # Remove stash
        stash_list.pop(index)
        self._save_stash(stash_list)

        # Cleanup stash directory
        shutil.rmtree(stash_dir, ignore_errors=True)

        return entry

    def drop_stash(self, index: int = 0) -> dict:
        """Remove a stash entry without applying.

        Args:
            index: Stash index to drop (0 = most recent).

        Returns the dropped stash entry.
        """
        import shutil

        stash_list = self._load_stash()
        if not stash_list or index >= len(stash_list):
            raise VesiError("Tidak ada stash untuk dihapus.")

        entry = stash_list.pop(index)
        self._save_stash(stash_list)

        # Cleanup stash directory
        stash_dir = Path(entry.get("stash_dir", ""))
        if stash_dir.is_dir():
            shutil.rmtree(stash_dir, ignore_errors=True)

        return entry


def cmd_simpan_sementara(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Stash changes temporarily."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    stash_mgr = StashManager(repo)

    try:
        message = parsed.first_arg or ""
        entry = stash_mgr.create_stash(message)

        print_color("✓ Perubahan disimpan sementara!", "green")
        print(f"  ID: {entry['id']}")
        print(f"  Pesan: {entry['message']}")
        print(f"  File: {len(entry['files'])} file")

        if verbose:
            print(f"  Branch: {entry['branch']}")
            print(f"  Waktu: {entry['timestamp']}")

        return 0

    except NoChangesError:
        print_color("✓ Tidak ada perubahan yang perlu disimpan.", "yellow")
        print("  Semua file sudah dalam keadaan bersih.")
        return 0


def cmd_ambil_stash(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Pop stash and apply changes."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    stash_mgr = StashManager(repo)

    # Parse index from args (default: 0)
    index = 0
    if parsed.args:
        try:
            index = int(parsed.args[0])
        except ValueError:
            raise VesiError(
                "Index stash harus berupa angka.",
                hint="Contoh:\n  ambil stash 0\n  ambil stash 1",
            )

    entry = stash_mgr.pop_stash(index)

    print_color(f"✓ Stash '{entry['id']}' diterapkan!", "green")
    print(f"  Pesan: {entry['message']}")
    print(f"  File: {len(entry['files'])} file dipulihkan")

    return 0


def cmd_hapus_stash(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Drop stash without applying."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    stash_mgr = StashManager(repo)

    # Parse index from args (default: 0)
    index = 0
    if parsed.args:
        try:
            index = int(parsed.args[0])
        except ValueError:
            raise VesiError(
                "Index stash harus berupa angka.",
                hint="Contoh:\n  hapus stash 0\n  hapus stash 1",
            )

    entry = stash_mgr.drop_stash(index)

    print_color(f"✓ Stash '{entry['id']}' dihapus.", "green")
    print(f"  Pesan: {entry['message']}")

    return 0


def cmd_lihat_stash(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """List all stash entries."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    stash_mgr = StashManager(repo)
    stashes = stash_mgr.list_stashes()

    if not stashes:
        print("Tidak ada stash tersimpan.")
        print("\nSimpan perubahan sementara:")
        print("  simpan sementara")
        print('  simpan sementara "pesan"')
        return 0

    print(f"Stash ({len(stashes)}):\n")
    for i, entry in enumerate(stashes):
        commit_short = entry.get("id", "")
        message = entry.get("message", "")
        timestamp = entry.get("timestamp", "")[:10]
        files = entry.get("files", [])

        print(f"  {commit_short:<15} {timestamp}  ({len(files)} file)")
        if message:
            print(f"  {'':15} {message}")

    return 0
