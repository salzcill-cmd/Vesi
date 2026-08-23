"""Command: kunci file - File locking system."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


class LockManager:
    """Manages file locks."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.locks_file = repo.vesi_dir / "locks.json"

    def _load_locks(self) -> dict[str, dict]:
        """Load locks from file."""
        if not self.locks_file.is_file():
            return {}
        try:
            return json.loads(self.locks_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_locks(self, locks: dict[str, dict]) -> None:
        """Save locks to file."""
        self.locks_file.write_text(
            json.dumps(locks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def lock_file(self, filepath: str, user: str = "") -> dict:
        """Lock a file."""
        locks = self._load_locks()

        if filepath in locks:
            lock_info = locks[filepath]
            lock_user = lock_info.get("user", "unknown")
            lock_time = lock_info.get("time", "")
            raise VesiError(
                f"File '{filepath}' sudah dikunci oleh {lock_user}.",
                hint=f"Dikunci pada: {lock_time}\nGunakan 'kunci buka {filepath}' untuk membuka.",
            )

        lock_info = {
            "user": user or os.environ.get("USER", "unknown"),
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pid": os.getpid(),
        }
        locks[filepath] = lock_info
        self._save_locks(locks)

        return lock_info

    def unlock_file(self, filepath: str) -> bool:
        """Unlock a file."""
        locks = self._load_locks()
        if filepath in locks:
            del locks[filepath]
            self._save_locks(locks)
            return True
        return False

    def is_locked(self, filepath: str) -> dict | None:
        """Check if a file is locked."""
        locks = self._load_locks()
        return locks.get(filepath)

    def list_locks(self) -> dict[str, dict]:
        """List all locked files."""
        return self._load_locks()


def cmd_kunci_file(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """File locking system.

    Usage:
      kunci file <filename>        - Lock a file
      kunci buka <filename>        - Unlock a file
      kunci                        - List all locked files
      kunci status <filename>      - Check if file is locked
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    lock_mgr = LockManager(repo)

    sub = parsed.subcommand or ""
    args = parsed.args or []

    if sub in ("buka", "unlock"):
        # Unlock file
        if not args:
            raise VesiError(
                "Tentukan file yang akan dibuka.",
                hint="Contoh:\n  kunci buka main.py",
            )

        filepath = args[0]
        if lock_mgr.unlock_file(filepath):
            print_color("✓ File berhasil dibuka.", "green")
            print(f"  File: {filepath}")
        else:
            print_color(f"File '{filepath}' tidak dikunci.", "yellow")

    elif sub in ("status", "cek"):
        # Check lock status
        if not args:
            raise VesiError("Tentukan file yang akan dicek.")

        filepath = args[0]
        lock_info = lock_mgr.is_locked(filepath)

        if lock_info:
            print_color(f"🔒 File '{filepath}' DIKUNCI", "red")
            print(f"  User: {lock_info.get('user', 'unknown')}")
            print(f"  Waktu: {lock_info.get('time', '')}")
        else:
            print_color(f"✓ File '{filepath}' TERBUKA", "green")

    else:
        # Lock file or list locks
        if args:
            # Lock file
            filepath = args[0]

            # Check if file exists
            file_path = repo.root / filepath
            if not file_path.is_file():
                raise VesiError(f"File '{filepath}' tidak ditemukan.")

            try:
                lock_info = lock_mgr.lock_file(filepath)
                print_color("✓ File berhasil dikunci!", "green")
                print(f"  File: {filepath}")
                print(f"  User: {lock_info.get('user', 'unknown')}")
                print(f"\n  File ini tidak bisa diedit oleh orang lain.")
                print(f"  Buka dengan: kunci buka {filepath}")
            except VesiError as e:
                print_color(f"✗ {e}", "red")
        else:
            # List all locks
            locks = lock_mgr.list_locks()

            if not locks:
                print("Tidak ada file yang dikunci.")
                print("\nKunci file:")
                print("  kunci file <filename>")
            else:
                print(f"File dikunci ({len(locks)}):\n")
                for filepath, info in locks.items():
                    user = info.get("user", "unknown")
                    lock_time = info.get("time", "")[:19]
                    print(f"  🔒 {filepath:<30} {user:<15} {lock_time}")

    return 0
