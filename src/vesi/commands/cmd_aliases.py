"""Command: alias - Custom command aliases."""

from __future__ import annotations

import json
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


class AliasManager:
    """Manages custom aliases."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.alias_file = repo.vesi_dir / "aliases.json"

    def _load_aliases(self) -> dict[str, str]:
        """Load aliases from file."""
        if not self.alias_file.is_file():
            return {}
        try:
            return json.loads(self.alias_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_aliases(self, aliases: dict[str, str]) -> None:
        """Save aliases to file."""
        self.alias_file.write_text(
            json.dumps(aliases, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_alias(self, name: str, command: str) -> None:
        """Add a new alias."""
        aliases = self._load_aliases()
        aliases[name] = command
        self._save_aliases(aliases)

    def remove_alias(self, name: str) -> bool:
        """Remove an alias."""
        aliases = self._load_aliases()
        if name in aliases:
            del aliases[name]
            self._save_aliases(aliases)
            return True
        return False

    def get_alias(self, name: str) -> str | None:
        """Get alias command."""
        aliases = self._load_aliases()
        return aliases.get(name)

    def list_aliases(self) -> dict[str, str]:
        """List all aliases."""
        return self._load_aliases()


def cmd_alias(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Manage custom command aliases.

    Usage:
      alias                        - List all aliases
      alias tambah <nama> <cmd>    - Add alias
      alias hapus <nama>           - Remove alias
      alias <nama>                 - Show alias command
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    alias_mgr = AliasManager(repo)

    sub = parsed.subcommand or ""
    args = parsed.args or []

    if sub in ("tambah", "add", "set"):
        # Add alias
        if len(args) < 2:
            raise VesiError(
                "Butuh nama alias dan command.",
                hint="Contoh:\n  alias tambah s simpan\n  alias tambah st stel",
            )

        name = args[0]
        command = " ".join(args[1:])

        # Validate alias name
        if not name.isalnum() and not all(c.isalnum() or c == "_" for c in name):
            raise VesiError("Nama alias hanya boleh huruf, angka, dan underscore.")

        alias_mgr.add_alias(name, command)
        print_color("✓ Alias ditambahkan!", "green")
        print(f"  {name} = {command}")
        print(f"\n  Gunakan dengan: vesi {name}")

    elif sub in ("hapus", "remove", "rm", "del"):
        # Remove alias
        if not args:
            raise VesiError(
                "Tentukan nama alias yang akan dihapus.",
                hint="Contoh:\n  alias hapus s",
            )

        name = args[0]
        if alias_mgr.remove_alias(name):
            print_color("✓ Alias dihapus.", "yellow")
        else:
            raise VesiError(f"Alias '{name}' tidak ditemukan.")

    elif sub in ("list", "ls"):
        # List aliases
        aliases = alias_mgr.list_aliases()
        if not aliases:
            print("Belum ada alias custom.")
            print("\nBuat alias baru:")
            print("  alias tambah s simpan")
            print("  alias tambah st stel")
        else:
            print(f"Alias ({len(aliases)}):\n")
            for name, command in sorted(aliases.items()):
                print(f"  {name:<15} = {command}")

    elif args:
        # Show specific alias
        name = args[0]
        command = alias_mgr.get_alias(name)
        if command:
            print(f"{name} = {command}")
        else:
            print_color(f"Alias '{name}' tidak ditemukan.", "yellow")

    else:
        # List all aliases
        aliases = alias_mgr.list_aliases()
        if not aliases:
            print("Belum ada alias custom.")
            print("\nBuat alias baru:")
            print("  alias tambah s simpan")
            print("  alias tambah st stel")
        else:
            print(f"Alias ({len(aliases)}):\n")
            for name, command in sorted(aliases.items()):
                print(f"  {name:<15} = {command}")

    return 0
