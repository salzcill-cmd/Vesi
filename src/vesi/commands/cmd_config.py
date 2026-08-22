"""Command: konfigurasi - Manage repository configuration."""

from __future__ import annotations

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository


def cmd_konfigurasi(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Manage repository configuration."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args

    if not args:
        # Show all config
        return _show_config(repo)
    elif len(args) == 1:
        # Get specific config value
        return _get_config(repo, args[0])
    elif len(args) == 2:
        # Set config value
        return _set_config(repo, args[0], args[1])
    else:
        raise VesiError(
            "Format: konfigurasi [key] [value]",
            hint="Contoh:\n    konfigurasi user.name \"Nama Anda\"\n    konfigurasi user.name",
        )


def _show_config(repo: Repository) -> int:
    """Display all configuration."""
    config = repo.get_config()

    if not config:
        print("Belum ada konfigurasi.")
        print("\nAtur konfigurasi:")
        print('    konfigurasi user.name "Nama Anda"')
        print('    konfigurasi user.email "email@contoh.com"')
        return 0

    print("Konfigurasi repository:\n")
    for section, values in config.items():
        if isinstance(values, dict):
            for key, value in values.items():
                print(f"  {section}.{key} = {value}")
        else:
            print(f"  {section} = {values}")

    return 0


def _get_config(repo: Repository, key: str) -> int:
    """Get a specific config value."""
    config = repo.get_config()
    parts = key.split(".", 1)

    if len(parts) == 2:
        section, name = parts
        value = config.get(section, {}).get(name, "")
    else:
        value = config.get(key, "")

    if value:
        print(f"{key} = {value}")
    else:
        print(f"'{key}' belum diatur.")

    return 0


def _set_config(repo: Repository, key: str, value: str) -> int:
    """Set a config value."""
    repo.set_config_value(key, value)
    print(f"✓ {key} = {value}")
    return 0
