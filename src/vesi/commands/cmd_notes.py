"""Command: catatan - Commit notes system for adding metadata."""

from __future__ import annotations

import json
import time
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


class NotesManager:
    """Manages commit notes."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.notes_dir = repo.vesi_dir / "notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.notes_file = self.notes_dir / "notes.json"

    def _load_notes(self) -> dict[str, list[dict]]:
        """Load all notes."""
        if not self.notes_file.is_file():
            return {}
        try:
            return json.loads(self.notes_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_notes(self, notes: dict[str, list[dict]]) -> None:
        """Save notes."""
        self.notes_file.write_text(
            json.dumps(notes, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_note(
        self,
        commit_hash: str,
        message: str,
        author: str = "",
        namespace: str = "default",
    ) -> dict:
        """Add a note to a commit.

        Args:
            commit_hash: Commit hash to annotate
            message: Note message
            author: Note author
            namespace: Note namespace (default, review, etc.)

        Returns the note entry.
        """
        notes = self._load_notes()

        if commit_hash not in notes:
            notes[commit_hash] = []

        note = {
            "message": message,
            "author": author or self.repo.get_author(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "namespace": namespace,
        }

        notes[commit_hash].append(note)
        self._save_notes(notes)

        return note

    def get_notes(
        self,
        commit_hash: str,
        namespace: str | None = None,
    ) -> list[dict]:
        """Get notes for a commit."""
        notes = self._load_notes()
        commit_notes = notes.get(commit_hash, [])

        if namespace:
            commit_notes = [n for n in commit_notes if n.get("namespace") == namespace]

        return commit_notes

    def list_notes(self, namespace: str | None = None) -> dict[str, list[dict]]:
        """List all commits with notes."""
        notes = self._load_notes()

        if namespace:
            return {
                commit: [n for n in notes_list if n.get("namespace") == namespace]
                for commit, notes_list in notes.items()
                if any(n.get("namespace") == namespace for n in notes_list)
            }

        return notes

    def remove_note(
        self,
        commit_hash: str,
        index: int = 0,
    ) -> bool:
        """Remove a note from a commit."""
        notes = self._load_notes()

        if commit_hash not in notes:
            return False

        commit_notes = notes[commit_hash]
        if index >= len(commit_notes):
            return False

        commit_notes.pop(index)

        if not commit_notes:
            del notes[commit_hash]

        self._save_notes(notes)
        return True

    def remove_all_notes(self, commit_hash: str) -> int:
        """Remove all notes from a commit."""
        notes = self._load_notes()

        if commit_hash not in notes:
            return 0

        count = len(notes[commit_hash])
        del notes[commit_hash]
        self._save_notes(notes)

        return count

    def get_note_count(self) -> int:
        """Get total number of notes."""
        notes = self._load_notes()
        return sum(len(notes_list) for notes_list in notes.values())


def cmd_catatan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Commit notes system.

    Usage:
      catatan <commit> [pesan]           - Add note to commit
      catatan lihat <commit>             - Show notes for commit
      catatan list                       - List all notes
      catatan hapus <commit> [index]     - Remove note
      catatan bersih <commit>            - Remove all notes for commit
      catatan --namespace <name>         - Filter by namespace
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    notes_mgr = NotesManager(repo)
    args = parsed.args or []

    # Determine subcommand
    if not args:
        return _show_notes_help()

    sub = args[0].lower()

    # Handle flags
    namespace = _get_flag_value(parsed.flags, "--namespace")

    if sub in ("lihat", "show", "view", "tampilkan"):
        # Show notes for a commit
        if len(args) < 2:
            raise VesiError(
                "Tentukan commit yang akan dilihat notes-nya.",
                hint="Contoh:\n  catatan lihat a1b2c3d",
            )

        commit_hash = args[1]
        commit_notes = notes_mgr.get_notes(commit_hash, namespace=namespace)

        if not commit_notes:
            print(f"Tidak ada catatan untuk commit {short_hash(commit_hash)}.")
            return 0

        print_color(f"Catatan untuk {short_hash(commit_hash)}:", "cyan")
        for i, note in enumerate(commit_notes):
            author = note.get("author", "")
            timestamp = note.get("timestamp", "")[:19]
            message = note.get("message", "")
            ns = note.get("namespace", "default")

            print(f"\n  [{i}] {ns} ({author}, {timestamp}):")
            print(f"    {message}")

        return 0

    elif sub in ("list", "daftar", "ls"):
        # List all notes
        all_notes = notes_mgr.list_notes(namespace=namespace)

        if not all_notes:
            print("Belum ada catatan.")
            print("\nBuat catatan baru:")
            print("  catatan a1b2c3d \"pesan catatan\"")
            return 0

        total = sum(len(notes_list) for notes_list in all_notes.values())
        print_color(f"Catatan ({total} total di {len(all_notes)} commit):\n", "cyan")

        for commit, notes_list in all_notes.items():
            print(f"  {short_hash(commit)} ({len(notes_list)} catatan)")
            if verbose:
                for note in notes_list:
                    author = note.get("author", "")
                    message = note.get("message", "")[:50]
                    print(f"    - {author}: {message}")

        return 0

    elif sub in ("hapus", "delete", "remove", "rm"):
        # Remove a note
        if len(args) < 2:
            raise VesiError(
                "Tentukan commit dan index note yang akan dihapus.",
                hint="Contoh:\n  catatan hapus a1b2c3d 0",
            )

        commit_hash = args[1]
        index = int(args[2]) if len(args) > 2 else 0

        if notes_mgr.remove_note(commit_hash, index):
            print_color(f"✓ Catatan dihapus dari {short_hash(commit_hash)}.", "green")
        else:
            print(f"Catatan tidak ditemukan.")

        return 0

    elif sub in ("bersih", "clear", "clean"):
        # Remove all notes for a commit
        if len(args) < 2:
            raise VesiError(
                "Tentukan commit yang notes-nya akan dihapus.",
                hint="Contoh:\n  catatan bersih a1b2c3d",
            )

        commit_hash = args[1]
        count = notes_mgr.remove_all_notes(commit_hash)

        if count > 0:
            print_color(f"✓ {count} catatan dihapus dari {short_hash(commit_hash)}.", "green")
        else:
            print(f"Tidak ada catatan untuk {short_hash(commit_hash)}.")

        return 0

    else:
        # Default: add note to commit
        commit_hash = sub
        message = " ".join(args[1:]) if len(args) > 1 else ""

        if not message:
            raise VesiError(
                "Tulis pesan catatan.",
                hint='Contoh:\n  catatan a1b2c3d "fix bug login"',
            )

        # Verify commit exists
        try:
            from vesi.commands.cmd_blame import _resolve_version
            _resolve_version(repo, commit_hash)
        except Exception:
            raise VersionNotFoundError(commit_hash)

        note = notes_mgr.add_note(commit_hash, message, namespace=namespace or "default")
        print_color(f"✓ Catatan ditambahkan ke {short_hash(commit_hash)}!", "green")
        print(f"  Pesan: {message}")
        print(f"  Author: {note['author']}")

        return 0


def _show_notes_help() -> int:
    """Show notes help."""
    print_color("📝 Sistem Catatan (Notes)\n", "cyan")
    print("Catatan adalah metadata yang bisa ditambahkan ke commit.")
    print("Cocok untuk review, catatan debugging, atau anotasi.\n")

    print("Penggunaan:")
    print("  catatan <commit> <pesan>       Tambah catatan")
    print("  catatan lihat <commit>         Lihat catatan")
    print("  catatan list                   Lihat semua catatan")
    print("  catatan hapus <commit> [idx]   Hapus catatan")
    print("  catatan bersih <commit>        Hapus semua catatan")
    print("  catatan --namespace review     Filter by namespace")

    print("\nContoh:")
    print('  catatan a1b2c3d "perlu review login flow"')
    print('  catatan a1b2c3d "bug di payment" --namespace bug')
    print("  catatan lihat a1b2c3d")

    return 0


def _get_flag_value(flags: list[str], flag_name: str) -> str | None:
    """Extract value from --flag=value or --flag value."""
    for i, flag in enumerate(flags):
        if flag.startswith(f"{flag_name}="):
            return flag[len(flag_name) + 1:]
        if flag == flag_name and i + 1 < len(flags):
            return flags[i + 1]
    return None
