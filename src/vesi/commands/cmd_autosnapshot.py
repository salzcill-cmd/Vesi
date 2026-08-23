"""Command: foto otomatis - Auto snapshot before destructive operations."""

from __future__ import annotations

import json
import time
from pathlib import Path

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


class AutoSnapshotManager:
    """Manages automatic snapshots."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.config_file = repo.vesi_dir / "autosnapshot.json"

    def _load_config(self) -> dict:
        """Load config."""
        if not self.config_file.is_file():
            return {"enabled": True, "snapshots": []}
        try:
            return json.loads(self.config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"enabled": True, "snapshots": []}

    def _save_config(self, config: dict) -> None:
        """Save config."""
        self.config_file.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create_snapshot(self, reason: str = "") -> str | None:
        """Create an automatic snapshot if there are changes."""
        from vesi.core.change import detect_changes

        snapshot_mgr = SnapshotManager(self.repo)
        current_hash = self.repo.get_head_commit()

        tree = None
        if current_hash:
            try:
                tree = snapshot_mgr.get_tree(current_hash)
            except Exception:
                pass

        index = self.repo.index.load()
        changes = detect_changes(self.repo.root, tree, index or {})

        if not changes:
            return None

        # Stage all changes
        for change in changes:
            if change.new_hash:
                self.repo.index.stage_file(change.path, change.new_hash)

        # Create snapshot
        new_tree = Tree()
        staged = self.repo.index.load()
        for filepath, file_hash in (staged or {}).items():
            name = filepath.split("/")[-1]
            new_tree.add_blob(name, file_hash, filepath)

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        message = reason or f"auto-snapshot: {timestamp}"

        author = self.repo.get_author()
        snapshot_hash = snapshot_mgr.create_snapshot(
            tree=new_tree,
            message=message,
            author=author,
            parent=current_hash,
        )

        # Update branch
        active_branch = self.repo.refs.get_active_branch()
        if active_branch:
            self.repo.refs.set_branch_hash(active_branch, snapshot_hash)

        # Clear staging
        self.repo.index.clear()

        # Record snapshot
        config = self._load_config()
        config["snapshots"].append({
            "hash": snapshot_hash,
            "reason": reason,
            "timestamp": timestamp,
        })
        # Keep only last 50 snapshots
        if len(config["snapshots"]) > 50:
            config["snapshots"] = config["snapshots"][-50:]
        self._save_config(config)

        return snapshot_hash

    def list_snapshots(self) -> list[dict]:
        """List all auto-snapshots."""
        config = self._load_config()
        return config.get("snapshots", [])

    def restore_snapshot(self, index: int = 0) -> bool:
        """Restore from an auto-snapshot."""
        config = self._load_config()
        snapshots = config.get("snapshots", [])

        if not snapshots or index >= len(snapshots):
            return False

        snapshot = snapshots[index]
        snapshot_hash = snapshot.get("hash", "")

        snapshot_mgr = SnapshotManager(self.repo)
        try:
            tree = snapshot_mgr.get_tree(snapshot_hash)
        except Exception:
            return False

        # Restore files
        for entry in tree.get_blob_entries():
            blob_content = self.repo.objects.load_blob(entry.hash_id)
            file_path = self.repo.root / entry.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(blob_content)

        return True


def cmd_foto_otomatis(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Auto snapshot management.

    Usage:
      foto otomatis                - Create snapshot now
      foto otomatis lihat          - List all auto-snapshots
      foto otomatis pulihkan <n>   - Restore from snapshot n
      foto otomatis aktifkan       - Enable auto-snapshot
      foto otomatis nonaktifkan    - Disable auto-snapshot
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    auto_mgr = AutoSnapshotManager(repo)

    sub = parsed.subcommand or ""
    args = parsed.args or []

    if sub in ("lihat", "list"):
        # List snapshots
        snapshots = auto_mgr.list_snapshots()

        if not snapshots:
            print("Belum ada auto-snapshot.")
            print("\nBuat snapshot:")
            print("  foto otomatis")
        else:
            print(f"Auto-snapshot ({len(snapshots)}):\n")
            for i, s in enumerate(snapshots):
                print(f"  {i}. {s.get('hash', '')[:7]}  {s.get('timestamp', '')}  {s.get('reason', '')}")

    elif sub in ("pulihkan", "restore"):
        # Restore from snapshot
        if not args:
            raise VesiError("Tentukan nomor snapshot yang akan dipulihkan.")

        try:
            index = int(args[0])
        except ValueError:
            raise VesiError("Nomor harus berupa angka.")

        if auto_mgr.restore_snapshot(index):
            print_color("Snapshot berhasil dipulihkan!", "green")
        else:
            raise VesiError(f"Snapshot nomor {index} tidak ditemukan.")

    elif sub in ("aktifkan", "enable", "on"):
        config = auto_mgr._load_config()
        config["enabled"] = True
        auto_mgr._save_config(config)
        print_color("Auto-snapshot diaktifkan!", "green")

    elif sub in ("nonaktifkan", "disable", "off"):
        config = auto_mgr._load_config()
        config["enabled"] = False
        auto_mgr._save_config(config)
        print_color("Auto-snapshot dinonaktifkan.", "yellow")

    else:
        # Create snapshot now
        snapshot_hash = auto_mgr.create_snapshot()
        if snapshot_hash:
            print_color("Auto-snapshot berhasil dibuat!", "green")
            print(f"  Hash: {short_hash(snapshot_hash)}")
        else:
            print_color("Tidak ada perubahan untuk di-snapshot.", "dim")

    return 0
