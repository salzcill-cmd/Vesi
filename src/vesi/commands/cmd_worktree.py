"""Command: folder kerja - Worktree - checkout branches in separate directories."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


class WorktreeManager:
    """Manages worktrees."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.worktrees_file = repo.vesi_dir / "worktrees.json"

    def _load(self) -> list[dict]:
        """Load worktree list."""
        if not self.worktrees_file.is_file():
            return []
        try:
            return json.loads(self.worktrees_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, worktrees: list[dict]) -> None:
        """Save worktree list."""
        self.worktrees_file.write_text(
            json.dumps(worktrees, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add(self, path: str, branch: str) -> dict:
        """Add a new worktree."""
        worktrees = self._load()

        # Check if path already exists
        abs_path = Path(path).resolve()
        if abs_path.exists():
            raise VesiError(
                f"Folder '{path}' sudah ada.",
                hint="Gunakan nama folder yang berbeda.",
            )

        # Check if branch already has a worktree
        for wt in worktrees:
            if wt.get("branch") == branch:
                raise VesiError(
                    f"Branch '{branch}' sudah memiliki worktree di '{wt['path']}'.",
                )

        # Get branch commit hash
        branch_hash = self.repo.refs.get_branch_hash(branch)
        if not branch_hash:
            raise VesiError(f"Branch '{branch}' tidak ditemukan.")

        # Create worktree by copying the repo
        abs_path.mkdir(parents=True, exist_ok=True)

        # Copy current files (simulated - in real VCS would checkout specific commit)
        for item in self.repo.root.iterdir():
            if item.name == ".vesi":
                continue
            dst = abs_path / item.name
            if item.is_dir():
                shutil.copytree(item, dst, ignore=shutil.ignore_patterns(".vesi"))
            else:
                shutil.copy2(item, dst)

        # Register worktree
        worktree_entry = {
            "path": str(abs_path),
            "branch": branch,
            "head": branch_hash,
            "added": str(Path.cwd()),
        }
        worktrees.append(worktree_entry)
        self._save(worktrees)

        return worktree_entry

    def list_worktrees(self) -> list[dict]:
        """List all worktrees."""
        return self._load()

    def remove(self, path: str) -> dict:
        """Remove a worktree."""
        worktrees = self._load()
        abs_path = Path(path).resolve()

        for i, wt in enumerate(worktrees):
            if Path(wt["path"]).resolve() == abs_path:
                removed = worktrees.pop(i)
                self._save(worktrees)

                # Optionally remove directory
                if abs_path.is_dir():
                    shutil.rmtree(abs_path, ignore_errors=True)

                return removed

        raise VesiError(f"Worktree '{path}' tidak ditemukan.")


def cmd_folder_kerja(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Worktree: manage worktrees.

    Usage:
      folder kerja buat <path> <branch>  - Create worktree
      folder kerja                        - List worktrees
      folder kerja hapus <path>           - Remove worktree
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    wt_mgr = WorktreeManager(repo)

    sub = parsed.subcommand or ""
    args = parsed.args or []

    if sub in ("buat", "create", "add"):
        # Create worktree
        if len(args) < 2:
            raise VesiError(
                "Butuh path dan branch untuk membuat worktree.",
                hint="Contoh:\n  folder kerja buat ../project-v2 fitur-baru",
            )

        path = args[0]
        branch = args[1]

        entry = wt_mgr.add(path, branch)

        print_color("✓ Worktree dibuat!", "green")
        print(f"  Path: {entry['path']}")
        print(f"  Branch: {entry['branch']}")
        print(f"  HEAD: {short_hash(entry['head'])}")

    elif sub in ("hapus", "remove", "rm"):
        # Remove worktree
        if not args:
            raise VesiError(
                "Tentukan path worktree yang akan dihapus.",
                hint="Contoh:\n  folder kerja hapus ../project-v2",
            )

        removed = wt_mgr.remove(args[0])

        print_color("✓ Worktree dihapus.", "green")
        print(f"  Path: {removed['path']}")
        print(f"  Branch: {removed['branch']}")

    else:
        # List worktrees
        worktrees = wt_mgr.list_worktrees()

        if not worktrees:
            print("Tidak ada worktree aktif.")
            print("\nBuat worktree baru:")
            print("  folder kerja buat <path> <branch>")
        else:
            print(f"Worktree ({len(worktrees)}):\n")
            for wt in worktrees:
                path = wt.get("path", "")
                branch = wt.get("branch", "")
                head = wt.get("head", "")

                print(f"  {branch:<20} {short_hash(head)}  {path}")

    return 0
