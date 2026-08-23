"""Command: jejak - Reflog - history of HEAD movements."""

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


class ReflogManager:
    """Manages reflog entries."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.reflog_file = repo.vesi_dir / "reflog.json"

    def add_entry(
        self,
        commit_hash: str,
        action: str,
        message: str = "",
        branch: str = "",
    ) -> None:
        """Add a reflog entry."""
        entries = self._load()

        entry = {
            "hash": commit_hash,
            "action": action,
            "message": message,
            "branch": branch or self.repo.refs.get_active_branch() or "detached",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        entries.append(entry)

        # Keep only last 100 entries
        if len(entries) > 100:
            entries = entries[-100:]

        self._save(entries)

    def get_entries(self, count: int = 0) -> list[dict]:
        """Get reflog entries.

        Args:
            count: Number of entries to return (0 = all).
        """
        entries = self._load()
        if count > 0:
            entries = entries[-count:]
        return list(reversed(entries))

    def _load(self) -> list[dict]:
        """Load reflog entries."""
        if not self.reflog_file.is_file():
            return []
        try:
            return json.loads(self.reflog_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, entries: list[dict]) -> None:
        """Save reflog entries."""
        self.reflog_file.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def cmd_jejak(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Reflog: show history of HEAD movements.

    Usage:
      jejak              - Show recent reflog
      jejak 20           - Show last 20 entries
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    reflog = ReflogManager(repo)

    # Parse count
    count = 0
    if parsed.args:
        try:
            count = int(parsed.args[0])
        except ValueError:
            raise VesiError(
                "Jumlah harus berupa angka.",
                hint="Contoh:\n  jejak 20",
            )

    entries = reflog.get_entries(count)

    if not entries:
        print("Jejak (reflog) kosong.")
        print("\nReflog akan terisi setelah operasi seperti:")
        print("  - simpan versi (commit)")
        print("  - pindah cabang (switch branch)")
        print("  - pulihkan (restore)")
        return 0

    print(f"Jejak ({len(entries)} entri):\n")

    for i, entry in enumerate(entries, 1):
        commit_hash = entry.get("hash", "")
        action = entry.get("action", "")
        message = entry.get("message", "")
        branch = entry.get("branch", "")
        timestamp = entry.get("timestamp", "")[:19]

        # Format: hash action (branch) message
        action_str = f"{short_hash(commit_hash)} {action}"
        if branch:
            action_str += f" ({branch})"
        if message:
            action_str += f": {message}"

        print(f"  {i:>3}. {action_str}")
        if verbose:
            print(f"        {timestamp}")

    return 0
