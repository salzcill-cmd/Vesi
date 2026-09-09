"""Command: konfigurasi - Manage repository and user configuration."""

from __future__ import annotations

from vesi.config.schema import CONFIG_SCHEMA
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_konfigurasi(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Manage repository configuration.

    Usage:
      konfigurasi                   - Show all config
      konfigurasi <key>             - Get a config value
      konfigurasi <key> <value>     - Set a config value
      konfigurasi --global <key>    - Scope to global config
      konfigurasi hapus <key>       - Remove a config value
    """
    config_scope = "global" if "--global" in parsed.flags else "repo"

    # Global config doesn't need a repository.
    if config_scope == "repo":
        try:
            repo = Repository.find()
        except RepositoryNotFoundError:
            raise
    else:
        repo = None

    args = parsed.args or []

    if args and args[0] == "hapus":
        key = args[1] if len(args) > 1 else ""
        return _unset_config(repo, args, config_scope, key)
    if not args:
        return _show_config(repo, config_scope, verbose)
    elif len(args) == 1:
        return _get_config(repo, args[0], config_scope)
    elif len(args) >= 2:
        return _set_config(repo, args[0], " ".join(args[1:]), config_scope)
    else:
        raise VesiError(
            "Format: konfigurasi [key] [value]",
            hint='Contoh:\n    konfigurasi user.name "Nama Anda"\n    konfigurasi user.name\n    konfigurasi --global user.name "Nama"',
        )


def _show_config(
    repo: Repository | None,
    config_scope: str,
    verbose: bool = False,
) -> int:
    """Display all configuration."""
    from vesi.config.manager import ConfigManager

    config_path = repo.vesi_dir if repo else None
    config_mgr = ConfigManager(config_path)

    if config_scope == "global":
        data = config_mgr.load_global()
        title = "Konfigurasi global (user):"
    else:
        data = config_mgr.get_all()
        title = "Konfigurasi repository:"

    if not data:
        print(f"Belum ada konfigurasi di scope '{config_scope}'.")
        print("\nAtur konfigurasi:")
        print('    konfigurasi user.name "Nama Anda"')
        print('    konfigurasi user.email "email@contoh.com"')
        return 0

    print(f"{title}\n")
    for key, desc in sorted(CONFIG_SCHEMA.items()):
        value = _lookup(data, key)
        if value == "" or value is False or value is None:
            continue
        print(f"  {key} = {value}")
    if verbose:
        print("\nKunci yang tersedia:")
        for key, (_, type_name, desc) in sorted(CONFIG_SCHEMA.items()):
            print(f"  {key}  [{type_name}]  {desc}")

    return 0


def _get_config(
    repo: Repository | None,
    key: str,
    config_scope: str,
) -> int:
    """Get a specific config value."""
    from vesi.config.manager import ConfigManager

    config_path = repo.vesi_dir if repo else None
    config_mgr = ConfigManager(config_path)

    value = config_mgr.get(key, scope=config_scope)
    if value in ("", None):
        print(f"'{key}' belum diatur.")
        desc = config_mgr.schema.describe(key)
        if desc:
            print(f"  ({desc})")
        return 0
    print(f"{key} = {value}")
    return 0


def _set_config(
    repo: Repository | None,
    key: str,
    value: str,
    config_scope: str,
) -> int:
    """Set a config value."""
    from vesi.config.manager import ConfigManager

    config_path = repo.vesi_dir if repo else None
    config_mgr = ConfigManager(config_path)

    try:
        config_mgr.set(key, value, scope=config_scope)
    except ValueError as e:
        raise VesiError(str(e))

    # Show final coerced value
    final = config_mgr.get(key, scope=config_scope)
    print_color(f"✓ {key} = {final}  ({config_scope})", "green")
    return 0


def _unset_config(
    repo: Repository | None,
    args: list[str],
    config_scope: str,
    key: str,
) -> int:
    """Remove a config value."""
    if not key:
        raise VesiError(
            "Tentukan key yang akan dihapus.",
            hint="Contoh:\n    konfigurasi hapus user.name",
        )
    from vesi.config.manager import ConfigManager

    config_path = repo.vesi_dir if repo else None
    config_mgr = ConfigManager(config_path)

    if config_mgr.unset(key, scope=config_scope):
        print_color(f"✓ '{key}' dihapus.", "green")
    else:
        print(f"'{key}' tidak ada di konfigurasi '{config_scope}'.")
    return 0


def _lookup(data: dict, key: str) -> object:
    """Look up a flat key in a possibly nested dict."""
    if key in data:
        return data[key]
    section, dot, name = key.partition(".")
    if dot:
        nested = data.get(section)
        if isinstance(nested, dict):
            return nested.get(name, "") or nested.get(key, "")
    return ""