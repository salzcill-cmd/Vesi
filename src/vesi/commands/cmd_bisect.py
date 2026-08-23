"""Command: bagi cari - Binary search to find bug-introducing commit."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


class BisectSession:
    """Manages a bisect session."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.state_file = repo.vesi_dir / "bisect.json"

    def start(self, good_hash: str, bad_hash: str) -> None:
        """Start a bisect session."""
        import json
        import time

        state = {
            "good": good_hash,
            "bad": bad_hash,
            "current": bad_hash,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_state(self) -> dict | None:
        """Get current bisect state."""
        import json

        if not self.state_file.is_file():
            return None
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def mark_good(self) -> dict:
        """Mark current commit as good."""
        state = self.get_state()
        if not state:
            raise VesiError("Tidak ada sesi bisect yang aktif.")

        state["good"] = state["current"]

        # Get next commit to test
        next_hash = self._get_next()
        if not next_hash:
            # Bisect complete
            self.clear()
            return {"complete": True, "result": state["bad"]}

        state["current"] = next_hash
        self._save(state)
        return {"complete": False, "current": next_hash}

    def mark_bad(self) -> dict:
        """Mark current commit as bad."""
        state = self.get_state()
        if not state:
            raise VesiError("Tidak ada sesi bisect yang aktif.")

        state["bad"] = state["current"]

        # Get next commit to test
        next_hash = self._get_next()
        if not next_hash:
            # Bisect complete
            self.clear()
            return {"complete": True, "result": state["current"]}

        state["current"] = next_hash
        self._save(state)
        return {"complete": False, "current": next_hash}

    def _get_next(self) -> str | None:
        """Get next commit to test (midpoint between good and bad)."""
        state = self.get_state()
        if not state:
            return None

        # Get commit list between good and bad
        commits = self._get_commits_between(state["good"], state["bad"])
        if len(commits) <= 1:
            return None

        # Return midpoint
        mid = len(commits) // 2
        return commits[mid]

    def _get_commits_between(self, start: str, end: str) -> list[str]:
        """Get list of commits between start and end."""
        snapshot_mgr = SnapshotManager(self.repo)
        commits = []

        # Walk from end back to start
        current = end
        while current:
            commits.append(current)
            if current == start:
                break
            try:
                data = snapshot_mgr.load_snapshot(current)
                current = data.get("parent")
            except (FileNotFoundError, ValueError):
                break

        return list(reversed(commits))

    def _save(self, state: dict) -> None:
        """Save bisect state."""
        import json

        self.state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def clear(self) -> None:
        """Clear bisect session."""
        if self.state_file.is_file():
            self.state_file.unlink()


def cmd_bagi_cari(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Bisect: binary search to find bug-introducing commit.

    Usage:
      bagi cari mulai <baik> <buruk>  - Start bisect
      bagi cari baik                  - Mark current as good
      bagi cari buruk                 - Mark current as bad
      bagi cari selesai               - End bisect
      bagi cari                       - Show current state
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    bisect = BisectSession(repo)

    # Parse subcommand
    sub = parsed.subcommand or ""
    args = parsed.args or []

    if sub in ("mulai", "start"):
        # Start bisect
        if len(args) < 2:
            raise VesiError(
                "Butuh 2 versi untuk memulai bisect.",
                hint="Contoh:\n  bagi cari mulai a1b2c3d f4e5d6a",
            )

        from vesi.commands.cmd_cherrypick import _resolve_version

        try:
            good_hash = _resolve_version(repo, args[0])
            bad_hash = _resolve_version(repo, args[1])
        except VersionNotFoundError:
            raise

        bisect.start(good_hash, bad_hash)
        print_color("✓ Bisect dimulai!", "green")
        print(f"  Good (tidak ada bug): {short_hash(good_hash)}")
        print(f"  Bad (ada bug): {short_hash(bad_hash)}")
        print(f"\n  Test commit ini:")
        print(f"    bagi cari baik  - jika tidak ada bug")
        print(f"    bagi cari buruk - jika ada bug")

    elif sub in ("baik", "good"):
        # Mark as good
        result = bisect.mark_good()
        if result.get("complete"):
            print_color("✓ Bisect selesai!", "green")
            print(f"\n  Commit yang menyebabkan bug:")
            print_color(f"    {short_hash(result['result'])}", "red")
        else:
            state = bisect.get_state()
            print_color(f"✓ Commit {short_hash(result['current'])} ditest", "cyan")
            print(f"  Good: {short_hash(state['good'])}")
            print(f"  Bad: {short_hash(state['bad'])}")

    elif sub in ("buruk", "bad"):
        # Mark as bad
        result = bisect.mark_bad()
        if result.get("complete"):
            print_color("✓ Bisect selesai!", "green")
            print(f"\n  Commit yang menyebabkan bug:")
            print_color(f"    {short_hash(result['result'])}", "red")
        else:
            state = bisect.get_state()
            print_color(f"✓ Commit {short_hash(result['current'])} ditest", "cyan")
            print(f"  Good: {short_hash(state['good'])}")
            print(f"  Bad: {short_hash(state['bad'])}")

    elif sub in ("selesai", "reset", "clear"):
        # Clear bisect
        bisect.clear()
        print_color("✓ Bisect dihentikan.", "yellow")

    else:
        # Show current state
        state = bisect.get_state()
        if not state:
            print("Tidak ada sesi bisect yang aktif.")
            print("\nMulai bisect:")
            print("  bagi cari mulai <baik> <buruk>")
        else:
            print_color("Sesi bisect aktif:", "cyan")
            print(f"  Good: {short_hash(state['good'])}")
            print(f"  Bad: {short_hash(state['bad'])}")
            print(f"  Current: {short_hash(state['current'])}")
            print(f"\n  Test commit ini:")
            print(f"    bagi cari baik  - jika tidak ada bug")
            print(f"    bagi cari buruk - jika ada bug")

    return 0
