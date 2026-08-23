"""Command: auto simpan - Periodic auto-save of changes."""

from __future__ import annotations

import json
import time
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


class AutoSaveManager:
    """Manages auto-save settings and snapshots."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.config_file = repo.vesi_dir / "autosave.json"

    def _load_config(self) -> dict:
        """Load auto-save config."""
        if not self.config_file.is_file():
            return {"enabled": False, "interval": 300, "last_save": 0}
        try:
            return json.loads(self.config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"enabled": False, "interval": 300, "last_save": 0}

    def _save_config(self, config: dict) -> None:
        """Save auto-save config."""
        self.config_file.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def enable(self, interval: int = 300) -> None:
        """Enable auto-save with interval in seconds."""
        config = self._load_config()
        config["enabled"] = True
        config["interval"] = interval
        self._save_config(config)

    def disable(self) -> None:
        """Disable auto-save."""
        config = self._load_config()
        config["enabled"] = False
        self._save_config(config)

    def is_enabled(self) -> bool:
        """Check if auto-save is enabled."""
        config = self._load_config()
        return config.get("enabled", False)

    def get_interval(self) -> int:
        """Get auto-save interval in seconds."""
        config = self._load_config()
        return config.get("interval", 300)

    def check_and_save(self) -> bool:
        """Check if it's time to auto-save and do it."""
        config = self._load_config()
        if not config.get("enabled", False):
            return False

        last_save = config.get("last_save", 0)
        interval = config.get("interval", 300)
        current_time = time.time()

        if current_time - last_save >= interval:
            # Check for changes
            from vesi.core.change import detect_changes
            from vesi.core.snapshot import SnapshotManager

            snapshot_mgr = SnapshotManager(self.repo)
            parent_hash = self.repo.get_head_commit()
            tree = None
            if parent_hash:
                try:
                    tree = snapshot_mgr.get_tree(parent_hash)
                except Exception:
                    pass

            index = self.repo.index.load()
            changes = detect_changes(self.repo.root, tree, index or {})

            if changes:
                # Auto-save with timestamp message
                timestamp = time.strftime("%Y-%m-%d %H:%M", time.localtime())
                message = f"auto-save: {timestamp}"

                # Stage all changes
                for change in changes:
                    if change.new_hash:
                        self.repo.index.stage_file(change.path, change.new_hash)

                # Create commit
                from vesi.storage.tree import Tree
                new_tree = Tree()
                staged = self.repo.index.load()
                for filepath, file_hash in (staged or {}).items():
                    name = filepath.split("/")[-1]
                    new_tree.add_blob(name, file_hash, filepath)

                author = self.repo.get_author()
                snapshot_hash = snapshot_mgr.create_snapshot(
                    tree=new_tree,
                    message=message,
                    author=author,
                    parent=parent_hash,
                )

                # Update branch
                active_branch = self.repo.refs.get_active_branch()
                if active_branch:
                    self.repo.refs.set_branch_hash(active_branch, snapshot_hash)

                # Clear staging
                self.repo.index.clear()

                # Update last save time
                config["last_save"] = current_time
                self._save_config(config)

                return True

        return False


def cmd_auto_simpan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Auto-save management.

    Usage:
      auto simpan aktifkan [detik]   - Enable auto-save (default: 300 detik)
      auto simpan nonaktifkan        - Disable auto-save
      auto simpan status             - Show auto-save status
      auto simpan                    - Check and auto-save if needed
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    auto_mgr = AutoSaveManager(repo)

    sub = parsed.subcommand or ""
    args = parsed.args or []

    if sub in ("aktifkan", "enable", "on"):
        # Enable auto-save
        interval = 300  # Default 5 minutes
        if args:
            try:
                interval = int(args[0])
            except ValueError:
                raise VesiError("Interval harus berupa angka (detik).")

        auto_mgr.enable(interval)
        print_color("✓ Auto-save diaktifkan!", "green")
        print(f"  Interval: {interval} detik ({interval // 60} menit)")
        print(f"\n  Auto-save akan otomatis menyimpan perubahan setiap {interval // 60} menit.")

    elif sub in ("nonaktifkan", "disable", "off"):
        # Disable auto-save
        auto_mgr.disable()
        print_color("✓ Auto-save dinonaktifkan.", "yellow")

    elif sub in ("status",):
        # Show status
        enabled = auto_mgr.is_enabled()
        interval = auto_mgr.get_interval()

        print_color("📊 Status Auto-Save:\n", "cyan")
        print(f"  Status:    {'🟢 Aktif' if enabled else '🔴 Nonaktif'}")
        if enabled:
            print(f"  Interval:  {interval} detik ({interval // 60} menit)")

    else:
        # Try to auto-save
        if auto_mgr.check_and_save():
            print_color("✓ Auto-save berhasil!", "green")
        else:
            if auto_mgr.is_enabled():
                print_color("✓ Belum waktunya auto-save.", "dim")
            else:
                print_color("⚠️  Auto-save nonaktif.", "yellow")
                print("\n  Aktifkan dengan:")
                print("    vesi auto simpan aktifkan")

    return 0
