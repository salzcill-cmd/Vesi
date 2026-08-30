"""Command: simpan sementara / ambil stash - Advanced stash system."""

from __future__ import annotations

import json
import shutil
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

    def create_stash(self, message: str = "", include_untracked: bool = False) -> dict:
        """Create a new stash entry from staged and working changes.

        Args:
            message: Optional stash message
            include_untracked: Include untracked files

        Returns the stash entry dict.
        """
        from vesi.core.change import detect_changes
        from vesi.core.snapshot import SnapshotManager
        from vesi.storage.tree import Tree

        # Get changes
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

        # Save index state
        index_state = {}
        if index:
            for filepath, file_hash in index.items():
                if filepath in saved_files:
                    index_state[filepath] = file_hash

        # Create stash metadata
        stash_entry = {
            "id": stash_id,
            "message": message or f"Stash dari {len(saved_files)} file",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": saved_files,
            "index_state": index_state,
            "branch": self.repo.refs.get_active_branch() or "detached",
            "head": parent_hash or "",
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

        # Clear staging area and working directory
        self.repo.index.clear()

        # Restore working directory to HEAD state
        if parent_hash:
            self._restore_working_dir(parent_hash)

        return stash_entry

    def create_stash_only(self, message: str = "") -> dict:
        """Create stash without modifying working directory (git stash create)."""
        from vesi.core.change import detect_changes
        from vesi.core.snapshot import SnapshotManager

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

        # Create stash commit (but don't apply to working dir)
        from vesi.storage.tree import Tree
        new_tree = Tree()
        for change in changes:
            if change.new_hash:
                new_tree.add_blob(change.path.split("/")[-1], change.new_hash, change.path)

        stash_hash = snapshot_mgr.create_snapshot(
            tree=new_tree,
            message=message or "Stash",
            author=self.repo.get_author(),
            parent=parent_hash,
        )

        return {
            "hash": stash_hash,
            "message": message or "Stash",
            "files": [c.path for c in changes],
        }

    def list_stashes(self) -> list[dict]:
        """List all stash entries."""
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

        # Restore index state
        index_state = entry.get("index_state", {})
        if index_state:
            current_index = self.repo.index.load()
            current_index.update(index_state)
            self.repo.index.save(current_index)

        # Remove stash
        stash_list.pop(index)
        self._save_stash(stash_list)

        # Cleanup stash directory
        shutil.rmtree(stash_dir, ignore_errors=True)

        return entry

    def apply_stash(self, index: int = 0) -> dict:
        """Apply a stash entry without removing it.

        Args:
            index: Stash index to apply (0 = most recent).

        Returns the applied stash entry.
        """
        stash_list = self._load_stash()
        if not stash_list or index >= len(stash_list):
            raise VesiError("Tidak ada stash untuk diapply.")

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

        # Restore index state
        index_state = entry.get("index_state", {})
        if index_state:
            current_index = self.repo.index.load()
            current_index.update(index_state)
            self.repo.index.save(current_index)

        return entry

    def drop_stash(self, index: int = 0) -> dict:
        """Remove a stash entry without applying.

        Args:
            index: Stash index to drop (0 = most recent).

        Returns the dropped stash entry.
        """
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

    def show_stash(self, index: int = 0) -> dict | None:
        """Show details of a stash entry."""
        stash_list = self._load_stash()
        if not stash_list or index >= len(stash_list):
            return None
        return stash_list[index]

    def branch_from_stash(self, branch_name: str, index: int = 0) -> dict:
        """Create a new branch from a stash entry.

        Like 'git stash branch'.
        """
        from vesi.commands.cmd_branch import create_branch, switch_branch

        stash_list = self._load_stash()
        if not stash_list or index >= len(stash_list):
            raise VesiError("Tidak ada stash.")

        entry = stash_list[index]

        # Create branch at stash's HEAD
        stash_head = entry.get("head", "")
        if stash_head:
            create_branch(self.repo, branch_name)
            switch_branch(self.repo, branch_name)

        # Apply stash
        self.pop_stash(index)

        return entry

    def _restore_working_dir(self, commit_hash: str) -> None:
        """Restore working directory to a commit's state."""
        from vesi.core.snapshot import SnapshotManager

        snapshot_mgr = SnapshotManager(self.repo)
        try:
            tree = snapshot_mgr.get_tree(commit_hash)
            for entry in tree.get_blob_entries():
                content = self.repo.blobs.load_content(entry.hash_id)
                file_path = self.repo.root / entry.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)
        except Exception:
            pass


def cmd_simpan_sementara(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Stash changes temporarily.

    Options:
      --include-untracked   Include untracked files
      --keep                Keep changes in working directory
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    stash_mgr = StashManager(repo)

    try:
        message = parsed.first_arg or ""
        include_untracked = "--include-untracked" in parsed.flags
        keep = "--keep" in parsed.flags

        if keep:
            entry = stash_mgr.create_stash_only(message)
            print_color("✓ Perubahan di-stash (working directory tetap)!".encode().decode(), "green")
            print(f"  Hash: {short_hash(entry['hash'])}")
            print(f"  File: {len(entry['files'])} file")
        else:
            entry = stash_mgr.create_stash(message, include_untracked)
            print_color("✓ Perubahan disimpan sementara!", "green")
            print(f"  ID: {entry['id']}")
            print(f"  Pesan: {entry['message']}")
            print(f"  File: {len(entry['files'])} file")

        if verbose:
            print(f"  Branch: {entry.get('branch', 'unknown')}")

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
    """Pop stash and apply changes.

    Options:
      --apply    Apply without removing stash
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    stash_mgr = StashManager(repo)

    # Parse index from args
    index = 0
    args = parsed.args or []
    if args:
        try:
            index = int(args[0])
        except ValueError:
            raise VesiError(
                "Index stash harus berupa angka.",
                hint="Contoh:\n  ambil stash 0\n  ambil stash 1",
            )

    apply_only = "--apply" in parsed.flags

    if apply_only:
        entry = stash_mgr.apply_stash(index)
        print_color(f"✓ Stash '{entry['id']}' diterapkan!", "green")
        print(f"  Pesan: {entry['message']}")
        print(f"  File: {len(entry['files'])} file dipulihkan")
    else:
        entry = stash_mgr.pop_stash(index)
        print_color(f"✓ Stash '{entry['id']}' diterapkan dan dihapus!", "green")
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

    # Parse index
    index = 0
    args = parsed.args or []
    if args:
        try:
            index = int(args[0])
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
    """List all stash entries.

    Options:
      --stat    Show file stats
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    stash_mgr = StashManager(repo)
    stashes = stash_mgr.list_stashes()
    show_stat = "--stat" in parsed.flags

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
        branch = entry.get("branch", "")

        print(f"  stash@{{{i}}}: {timestamp} ({len(files)} file) {branch}")
        print(f"    {message}")

        if show_stat and files:
            for f in files[:5]:
                print(f"      W {f}")
            if len(files) > 5:
                print(f"      ... dan {len(files) - 5} file lainnya")

    return 0


def cmd_stash_branch(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Create branch from stash and apply.

    Usage:
      simpan sementara cabang <nama>         - Create branch from stash@{0}
      simpan sementara cabang <nama> <index> - Create branch from stash@{index}
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan nama cabang.",
            hint="Contoh:\n  simpan sementara cabang fix-branch",
        )

    branch_name = parsed.args[0]
    stash_index = int(parsed.args[1]) if len(parsed.args) > 1 else 0

    stash_mgr = StashManager(repo)
    entry = stash_mgr.branch_from_stash(branch_name, stash_index)

    print_color(f"✓ Cabang '{branch_name}' dibuat dari stash!", "green")
    print(f"  Stash: {entry.get('id', 'unknown')}")
    print(f"  File: {len(entry.get('files', []))} file")

    return 0


def cmd_stash_show(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show stash entry details.

    Usage:
      simpan sementara lihat          - Show stash@{0}
      simpan sementara lihat <index>  - Show stash@{index}
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    stash_mgr = StashManager(repo)

    index = 0
    args = parsed.args or []
    if args:
        try:
            index = int(args[0])
        except ValueError:
            pass

    entry = stash_mgr.show_stash(index)
    if not entry:
        print(f"Tidak ada stash di index {index}.")
        return 0

    print_color(f"stash@{{{index}}}:", "cyan")
    print(f"  Pesan:   {entry.get('message', '')}")
    print(f"  Branch:  {entry.get('branch', '')}")
    print(f"  HEAD:    {short_hash(entry.get('head', ''))}")
    print(f"  Waktu:   {entry.get('timestamp', '')[:19]}")
    print(f"\n  File yang di-stash:")
    for f in entry.get("files", []):
        print(f"    {f}")

    return 0
