"""File watcher - auto-save on file changes.

Monitors working directory for changes and auto-saves periodically.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Callable


@dataclass
class WatchConfig:
    """Configuration for file watcher."""

    enabled: bool = False
    interval: int = 300  # seconds
    max_files: int = 1000
    ignore_patterns: list[str] | None = None
    auto_commit: bool = False
    commit_prefix: str = "auto: "

    def __post_init__(self):
        if self.ignore_patterns is None:
            self.ignore_patterns = [
                "__pycache__",
                "*.pyc",
                ".git",
                ".vesi",
                "node_modules",
                ".env",
                "*.log",
            ]


@dataclass
class FileState:
    """State of a file for change detection."""

    path: str
    mtime: float
    size: int
    hash_id: str = ""


class FileWatcher:
    """Watches files for changes."""

    def __init__(self, repo_root: Path, config: WatchConfig | None = None) -> None:
        self.repo_root = repo_root
        self.config = config or WatchConfig()
        self.config_file = repo_root / ".vesi" / "watch.json"
        self._last_check = 0
        self._file_states: dict[str, FileState] = {}
        self._running = False
        self._callbacks: list[Callable] = []

    def start(self) -> None:
        """Start watching for changes."""
        self._running = True
        self._scan_files()

    def stop(self) -> None:
        """Stop watching."""
        self._running = False

    def check_for_changes(self) -> list[str]:
        """Check for changed files.

        Returns list of changed file paths.
        """
        if not self._running:
            return []

        changed = []
        current_time = time.time()

        # Check interval
        if current_time - self._last_check < self.config.interval:
            return []

        self._last_check = current_time

        # Scan for changes
        current_files = self._scan_files()

        for filepath, state in current_files.items():
            old_state = self._file_states.get(filepath)

            if old_state is None:
                # New file
                changed.append(filepath)
            elif old_state.mtime != state.mtime or old_state.size != state.size:
                # Modified file
                changed.append(filepath)

        # Check for deleted files
        for filepath in self._file_states:
            if filepath not in current_files:
                changed.append(filepath)

        return changed

    def _scan_files(self) -> dict[str, FileState]:
        """Scan directory and return file states."""
        files = {}

        for root, dirs, filenames in os.walk(self.repo_root):
            # Skip ignored directories
            dirs[:] = [
                d for d in dirs
                if not self._should_ignore(d)
            ]

            for filename in filenames:
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(self.repo_root))

                # Skip ignored files
                if self._should_ignore(rel_path):
                    continue

                try:
                    stat = filepath.stat()
                    files[rel_path] = FileState(
                        path=rel_path,
                        mtime=stat.st_mtime,
                        size=stat.st_size,
                    )
                except OSError:
                    continue

        return files

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        if not self.config.ignore_patterns:
            return False

        path_lower = path.lower()
        for pattern in self.config.ignore_patterns:
            if pattern.startswith("*"):
                if path_lower.endswith(pattern[1:].lower()):
                    return True
            elif pattern in path_lower:
                return True

        return False

    def on_change(self, callback: Callable) -> None:
        """Register a callback for file changes."""
        self._callbacks.append(callback)

    def get_state(self) -> dict:
        """Get watcher state."""
        return {
            "enabled": self.config.enabled,
            "interval": self.config.interval,
            "last_check": self._last_check,
            "tracked_files": len(self._file_states),
            "running": self._running,
        }


class AutoSaveManager:
    """Manages auto-save functionality."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.vesi_dir = repo_root / ".vesi"
        self.config_file = self.vesi_dir / "autosave.json"
        self.watcher = FileWatcher(repo_root)

    def _load_config(self) -> WatchConfig:
        """Load auto-save config."""
        if not self.config_file.is_file():
            return WatchConfig()

        try:
            data = json.loads(self.config_file.read_text(encoding="utf-8"))
            return WatchConfig(
                enabled=data.get("enabled", False),
                interval=data.get("interval", 300),
                max_files=data.get("max_files", 1000),
                ignore_patterns=data.get("ignore_patterns"),
                auto_commit=data.get("auto_commit", False),
                commit_prefix=data.get("commit_prefix", "auto: "),
            )
        except (json.JSONDecodeError, OSError):
            return WatchConfig()

    def _save_config(self, config: WatchConfig) -> None:
        """Save auto-save config."""
        self.config_file.write_text(
            json.dumps({
                "enabled": config.enabled,
                "interval": config.interval,
                "max_files": config.max_files,
                "ignore_patterns": config.ignore_patterns,
                "auto_commit": config.auto_commit,
                "commit_prefix": config.commit_prefix,
            }, indent=2),
            encoding="utf-8",
        )

    def enable(self, interval: int = 300) -> None:
        """Enable auto-save."""
        config = self._load_config()
        config.enabled = True
        config.interval = interval
        self._save_config(config)

        self.watcher.config = config
        self.watcher.start()

    def disable(self) -> None:
        """Disable auto-save."""
        config = self._load_config()
        config.enabled = False
        self._save_config(config)

        self.watcher.stop()

    def is_enabled(self) -> bool:
        """Check if auto-save is enabled."""
        config = self._load_config()
        return config.enabled

    def get_status(self) -> dict:
        """Get auto-save status."""
        config = self._load_config()
        return {
            "enabled": config.enabled,
            "interval": config.interval,
            "interval_human": f"{config.interval // 60} menit",
            "auto_commit": config.auto_commit,
            "watcher": self.watcher.get_state(),
        }

    def check_and_save(self) -> bool:
        """Check for changes and auto-save if needed."""
        if not self.is_enabled():
            return False

        changed = self.watcher.check_for_changes()

        if not changed:
            return False

        # Stage changed files
        try:
            from vesi.repository.repository import Repository
            repo = Repository.find()

            for filepath in changed:
                file_path = repo.root / filepath
                if file_path.is_file():
                    blob_hash = repo.blobs.save_file(file_path)
                    repo.index.stage_file(filepath, blob_hash)

            # Auto-commit if enabled
            config = self._load_config()
            if config.auto_commit:
                from vesi.core.snapshot import SnapshotManager
                from vesi.storage.tree import Tree

                snapshot_mgr = SnapshotManager(repo)
                index = repo.index.load()

                if index:
                    tree = Tree()
                    for filepath, file_hash in index.items():
                        name = filepath.split("/")[-1]
                        tree.add_blob(name, file_hash, filepath)

                    parent_hash = repo.get_head_commit()
                    timestamp = time.strftime("%H:%M", time.localtime())
                    message = f"{config.commit_prefix}{timestamp}"

                    snapshot_hash = snapshot_mgr.create_snapshot(
                        tree=tree,
                        message=message,
                        author=repo.get_author(),
                        parent=parent_hash,
                    )

                    # Update branch
                    active_branch = repo.refs.get_active_branch()
                    if active_branch:
                        repo.refs.set_branch_hash(active_branch, snapshot_hash)

                    repo.index.clear()

                    print(f"Auto-commit: {message} ({len(changed)} files)")
            else:
                print(f"Auto-staged: {len(changed)} files")

            return True

        except Exception as e:
            print(f"Auto-save error: {e}")
            return False
