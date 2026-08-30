"""Command: jejak - Reflog with expiry, purge, and advanced filtering."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
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
        self.default_retention_days = 90

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

        # Keep only last 500 entries
        if len(entries) > 500:
            entries = entries[-500:]

        self._save(entries)

    def get_entries(
        self,
        count: int = 0,
        branch: str | None = None,
        since: str | None = None,
        until: str | None = None,
        action: str | None = None,
    ) -> list[dict]:
        """Get reflog entries with optional filters.

        Args:
            count: Number of entries to return (0 = all)
            branch: Filter by branch name
            since: Filter by date (YYYY-MM-DD)
            until: Filter by date (YYYY-MM-DD)
            action: Filter by action type
        """
        entries = self._load()

        # Apply filters
        if branch:
            entries = [e for e in entries if e.get("branch") == branch]
        if since:
            entries = [e for e in entries if e.get("timestamp", "")[:10] >= since]
        if until:
            entries = [e for e in entries if e.get("timestamp", "")[:10] <= until]
        if action:
            entries = [e for e in entries if e.get("action") == action]

        if count > 0:
            entries = entries[-count:]

        return list(reversed(entries))

    def expire_entries(self, retention_days: int = 0) -> int:
        """Expire old reflog entries.

        Args:
            retention_days: Days to keep (0 = use default)

        Returns number of entries expired.
        """
        if retention_days <= 0:
            retention_days = self.default_retention_days

        entries = self._load()
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        original_count = len(entries)
        entries = [e for e in entries if e.get("timestamp", "") > cutoff_str]
        expired = original_count - len(entries)

        if expired > 0:
            self._save(entries)

        return expired

    def purge_branch(self, branch: str) -> int:
        """Remove all reflog entries for a specific branch.

        Returns number of entries removed.
        """
        entries = self._load()
        original_count = len(entries)
        entries = [e for e in entries if e.get("branch") != branch]
        removed = original_count - len(entries)

        if removed > 0:
            self._save(entries)

        return removed

    def get_branch_stats(self) -> dict[str, int]:
        """Get reflog statistics per branch."""
        entries = self._load()
        stats: dict[str, int] = {}

        for entry in entries:
            branch = entry.get("branch", "unknown")
            stats[branch] = stats.get(branch, 0) + 1

        return stats

    def get_action_stats(self) -> dict[str, int]:
        """Get reflog statistics per action type."""
        entries = self._load()
        stats: dict[str, int] = {}

        for entry in entries:
            action = entry.get("action", "unknown")
            stats[action] = stats.get(action, 0) + 1

        return stats

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

    Options:
      --branch <name>   Filter by branch
      --since <date>    Filter by date (YYYY-MM-DD)
      --until <date>    Filter by date
      --action <type>   Filter by action
      --expire          Expire old entries
      --purge <branch>  Remove entries for branch
      --stat            Show statistics
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    reflog = ReflogManager(repo)

    # Parse count from args
    count = 0
    args = parsed.args or []
    if args and args[0].isdigit():
        count = int(args[0])

    # Parse filter options
    filter_branch = _get_flag_value(parsed.flags, "--branch")
    filter_since = _get_flag_value(parsed.flags, "--since")
    filter_until = _get_flag_value(parsed.flags, "--until")
    filter_action = _get_flag_value(parsed.flags, "--action")

    # Handle special commands
    if "--expire" in parsed.flags:
        days = 90
        if args and args[0].isdigit():
            days = int(args[0])
        expired = reflog.expire_entries(days)
        print_color(f"✓ {expired} entri reflog dihapus (>{days} hari).", "green")
        return 0

    if "--purge" in parsed.flags:
        branch = _get_flag_value(parsed.flags, "--purge")
        if not branch:
            print("Tentukan branch: jejak --purge <branch>")
            return 1
        removed = reflog.purge_branch(branch)
        print_color(f"✓ {removed} entri reflog untuk '{branch}' dihapus.", "green")
        return 0

    if "--stat" in parsed.flags:
        return _show_stats(reflog)

    # Get entries
    entries = reflog.get_entries(
        count=count,
        branch=filter_branch,
        since=filter_since,
        until=filter_until,
        action=filter_action,
    )

    if not entries:
        print("Jejak (reflog) kosong.")
        print("\nReflog akan terisi setelah operasi seperti:")
        print("  - simpan versi (commit)")
        print("  - pindah cabang (switch branch)")
        print("  - pulihkan (restore)")
        return 0

    # Build filter description
    filters = []
    if filter_branch:
        filters.append(f"branch={filter_branch}")
    if filter_since:
        filters.append(f"since={filter_since}")
    if filter_until:
        filters.append(f"until={filter_until}")
    if filter_action:
        filters.append(f"action={filter_action}")

    header = f"Jejak ({len(entries)} entri)"
    if filters:
        header += f" [{', '.join(filters)}]"

    print(f"{header}:\n")

    for i, entry in enumerate(entries, 1):
        commit_hash = entry.get("hash", "")
        action = entry.get("action", "")
        message = entry.get("message", "")
        branch = entry.get("branch", "")
        timestamp = entry.get("timestamp", "")[:19]

        # Format action string
        action_str = f"{short_hash(commit_hash)} {action}"
        if branch:
            action_str += f" ({branch})"
        if message:
            action_str += f": {message}"

        print(f"  {i:>3}. {action_str}")
        if verbose:
            print(f"        {timestamp}")

    return 0


def _show_stats(reflog: ReflogManager) -> int:
    """Show reflog statistics."""
    branch_stats = reflog.get_branch_stats()
    action_stats = reflog.get_action_stats()
    all_entries = reflog.get_entries()

    print_color("📊 Statistik Reflog:\n", "cyan")
    print(f"  Total entri: {len(all_entries)}")

    if branch_stats:
        print(f"\n  Per cabang:")
        for branch, count in sorted(branch_stats.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            print(f"    {branch:<20} {count:>4}  {bar}")

    if action_stats:
        print(f"\n  Per aksi:")
        for action, count in sorted(action_stats.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            print(f"    {action:<20} {count:>4}  {bar}")

    return 0


def _get_flag_value(flags: list[str], flag_name: str) -> str | None:
    """Extract value from --flag=value or --flag value."""
    for i, flag in enumerate(flags):
        if flag.startswith(f"{flag_name}="):
            return flag[len(flag_name) + 1:]
        if flag == flag_name and i + 1 < len(flags):
            return flags[i + 1]
    return None
