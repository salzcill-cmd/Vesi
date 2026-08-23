"""Command: cadangan - Backup system for destructive operations."""

from __future__ import annotations

import json
import shutil
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


class BackupManager:
    """Manages automatic backups."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.backup_dir = repo.vesi_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_index = self.backup_dir / "index.json"

    def _load_index(self) -> list[dict]:
        """Load backup index."""
        if not self.backup_index.is_file():
            return []
        try:
            return json.loads(self.backup_index.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_index(self, entries: list[dict]) -> None:
        """Save backup index."""
        self.backup_index.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create_backup(self, reason: str = "") -> dict:
        """Create a backup of current state.

        Returns backup entry.
        """
        # Create backup directory with timestamp
        timestamp = int(time.time())
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)

        # Copy current index
        index = self.repo.index.load()
        if index:
            for filepath, file_hash in index.items():
                src_path = self.repo.root / filepath
                if src_path.is_file():
                    dst_path = backup_path / filepath.replace("/", "_")
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)

        # Create backup metadata
        backup_entry = {
            "id": f"backup_{timestamp}",
            "reason": reason,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "head": self.repo.get_head_commit() or "",
            "branch": self.repo.refs.get_active_branch() or "detached",
            "path": str(backup_path),
            "files": list(index.keys()) if index else [],
        }

        # Save metadata
        (backup_path / "backup.json").write_text(
            json.dumps(backup_entry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Update index
        entries = self._load_index()
        entries.append(backup_entry)
        # Keep only last 20 backups
        if len(entries) > 20:
            entries = entries[-20:]
        self._save_index(entries)

        return backup_entry

    def list_backups(self) -> list[dict]:
        """List all backups."""
        return self._load_index()

    def restore_backup(self, backup_id: str) -> dict:
        """Restore files from a backup."""
        entries = self._load_index()

        backup_entry = None
        for entry in entries:
            if entry.get("id") == backup_id:
                backup_entry = entry
                break

        if not backup_entry:
            raise VesiError(f"Backup '{backup_id}' tidak ditemukan.")

        backup_path = Path(backup_entry.get("path", ""))
        if not backup_path.is_dir():
            raise VesiError(f"Backup '{backup_id}' rusak atau tidak ditemukan.")

        # Restore files
        restored_files = []
        for filename in backup_path.iterdir():
            if filename.is_file() and filename.name != "backup.json":
                # Convert back to original path
                filepath = filename.name.replace("_", "/")
                dst_path = self.repo.root / filepath
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(filename, dst_path)
                restored_files.append(filepath)

        return {
            "backup": backup_entry,
            "files": restored_files,
        }


def cmd_cadangan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Backup system.

    Usage:
      cadangan buat [alasan]    - Create backup
      cadangan                  - List backups
      cadangan pulihkan <id>    - Restore from backup
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    backup_mgr = BackupManager(repo)

    sub = parsed.subcommand or ""
    args = parsed.args or []

    if sub in ("buat", "create", "add"):
        # Create backup
        reason = " ".join(args) if args else ""
        entry = backup_mgr.create_backup(reason)

        print_color("✓ Backup berhasil dibuat!", "green")
        print(f"  ID: {entry['id']}")
        print(f"  File: {len(entry['files'])} file")
        if reason:
            print(f"  Alasan: {reason}")

    elif sub in ("pulihkan", "restore"):
        # Restore from backup
        if not args:
            raise VesiError(
                "Tentukan ID backup yang akan dipulihkan.",
                hint="Contoh:\n  cadangan pulihkan backup_1234567890",
            )

        result = backup_mgr.restore_backup(args[0])

        print_color("✓ Backup berhasil dipulihkan!", "green")
        print(f"  Backup: {result['backup']['id']}")
        print(f"  File: {len(result['files'])} file dipulihkan")

    else:
        # List backups
        backups = backup_mgr.list_backups()

        if not backups:
            print("Belum ada backup.")
            print("\nBuat backup baru:")
            print("  cadangan buat")
            print('  cadangan buat "sebelum refactor"')
        else:
            print(f"Backup ({len(backups)}):\n")
            for b in backups:
                backup_id = b.get("id", "")
                reason = b.get("reason", "")
                timestamp = b.get("timestamp", "")[:10]
                files = len(b.get("files", []))

                line = f"  {backup_id:<25} {timestamp}  ({files} file)"
                if reason:
                    line += f"  {reason}"
                print(line)

    return 0
